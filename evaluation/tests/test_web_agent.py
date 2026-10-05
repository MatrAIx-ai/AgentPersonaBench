"""The shared web agent loop and the contract every web task keeps with it.

No browser here: the loop's pure helpers, and a static check over every web
task that its solver hands off to the loop and that each output its
solution/web.json declares is the file its verifier reads.
"""
from __future__ import annotations

import json
from pathlib import Path

import pytest

import web_agent

REPO = Path(__file__).resolve().parents[2]
WEB_TASKS = sorted(p.parent for p in REPO.glob("tasks/**/*-web/task.toml"))
# Still on a legacy driver, with the reason. moderate-loss-web's Save button only
# works after the legacy driver injects run-binding attributes into the page, and
# its verifier needs legacy-only files; it needs a page + verifier rework.
LEGACY = {"moderate-loss-web"}


def test_parse_action_takes_the_first_valid_action():
    raw = 'I will add it. {"action": "click", "ref": 3} then {"action": "done"}'
    assert web_agent.parse_action(raw) == {"action": "click", "ref": 3}
    assert web_agent.parse_action('{"action":"click","ref":1}{"action":"done"}') == {"action": "click", "ref": 1}
    assert web_agent.parse_action('{"note": 1} {"action": "done"}') == {"action": "done"}
    assert web_agent.parse_action('{"action": "click", "ref": "4"}') == {"action": "click", "ref": 4}
    assert web_agent.parse_action('{"action": "fly"}') is None
    assert web_agent.parse_action("no json at all") is None


def test_goal_drops_the_container_files_section():
    text = "# Instruction\n\nAdd the **3 kits** you'd cook.\n\n## Files (container runs)\n\n- Write to /app/output/x.json\n"
    goal = web_agent.goal_from_instruction(text)
    assert "3 kits" in goal and "/app/output" not in goal


def test_act_rejects_a_ref_that_is_not_on_the_page():
    assert web_agent.act(None, {"action": "click", "ref": 9}, 3).startswith("invalid")


@pytest.mark.parametrize("task", WEB_TASKS, ids=lambda p: p.name)
def test_web_task_runs_the_shared_loop(task):
    if task.name in LEGACY:
        pytest.skip("legacy driver pending a page rework")
    sh = (task / "solution" / "solve.sh").read_text(encoding="utf-8")
    assert "lib/web_solve.sh" in sh and "web_run_agent" in sh
    assert not (task / "solution" / "driver.py").exists(), "legacy driver left behind"
    spec = json.loads((task / "solution" / "web.json").read_text(encoding="utf-8"))
    outs = spec.get("outputs") or []
    assert outs or spec.get("server"), "web.json declares no outputs and no server that writes them"
    verifier = (task / "tests" / "verifier.py").read_text(encoding="utf-8")
    for out in outs:
        assert out["kind"] in ("dom", "js", "text")
        if out["kind"] == "dom":
            assert out.get("selector") and out.get("key")
        else:
            assert "=>" in out.get("expr", ""), "js output must be a function expression"
        assert Path(out["path"]).name in verifier, f"{out['path']} is not read by the verifier"


def test_scroll_is_an_action_and_obs_mode_defaults_to_hybrid(monkeypatch):
    assert web_agent.parse_action('{"action": "scroll", "direction": "down"}') == {
        "action": "scroll", "direction": "down"}
    monkeypatch.delenv("APB_WEB_OBS", raising=False)
    assert web_agent.obs_mode() == "hybrid"
    monkeypatch.setenv("APB_WEB_OBS", "text")
    assert web_agent.obs_mode() == "text"
    monkeypatch.setenv("APB_WEB_OBS", "pixels")
    with pytest.raises(ValueError):
        web_agent.obs_mode()


def test_rules_offer_scroll_only_with_the_screenshot():
    assert '"scroll"' in web_agent.rules("hybrid") and "screenshot" in web_agent.rules("hybrid")
    assert '"scroll"' not in web_agent.rules("text") and "screenshot" not in web_agent.rules("text")


def test_decider_attaches_the_screenshot_only_in_hybrid(monkeypatch):
    import sys
    import types
    sent = []
    fake = types.ModuleType("agent_client")
    fake.chat = lambda **kw: sent.append(kw) or '{"action": "done"}'
    monkeypatch.setitem(sys.modules, "agent_client", fake)
    decide = web_agent.llm_decider("sys", "goal", [])
    obs = {"title": "T", "text": "[1] button \"Go\"", "refs": 1}
    assert decide(obs, [])[0] == {"action": "done"} and "images" not in sent[-1]
    decide({**obs, "image": "QUJD", "on_screen": [1], "scroll": {"y": 0, "h": 900, "vh": 900}}, [])
    assert sent[-1]["images"] == ["QUJD"] and sent[-1]["image_media_type"] == "image/jpeg"
    assert "On screen: controls 1" in sent[-1]["user"]
