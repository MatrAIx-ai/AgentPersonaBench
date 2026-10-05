#!/usr/bin/env python3
from __future__ import annotations

import json
import importlib.util
import os
import re
import subprocess
import sys
import tempfile
import types
from collections import Counter
from pathlib import Path

HERE = Path(__file__).resolve().parent
TASK_DIR = HERE.parent
REPO_DIR = TASK_DIR
while REPO_DIR != REPO_DIR.parent and not (REPO_DIR / "evaluation" / "src").is_dir():
    REPO_DIR = REPO_DIR.parent
assert (REPO_DIR / "evaluation" / "src").is_dir()
sys.path.insert(0, str(REPO_DIR / "evaluation" / "src"))

solve_script = (TASK_DIR / "solution" / "solve.sh").read_text(encoding="utf-8")
assert 'RUNTIME_PYTHON="${RUNTIME_PYTHON:-python3}"' in solve_script
assert 'PYTHONPATH="$REPO_DIR" "$RUNTIME_PYTHON" -c' in solve_script
assert 'PYTHONPATH="$REPO_DIR" python3 -c' not in solve_script
assert "persona_system_prompt(sys.argv[1]" in solve_script
assert "persona_system_prompt('$TASK_DIR'" not in solve_script

with tempfile.TemporaryDirectory(prefix="risk-'quoted-") as tmp:
    quoted_repo = Path(tmp) / "repo'quoted"
    fake_bin = quoted_repo / "fake-bin"
    fake_bin.mkdir(parents=True)
    fake_docker = fake_bin / "docker"
    fake_docker.write_text("#!/usr/bin/env bash\nexit 0\n", encoding="utf-8")
    fake_docker.chmod(0o755)
    persona_module = quoted_repo / "evaluation" / "src" / "persona.py"
    persona_module.parent.mkdir(parents=True)
    persona_module.write_text(
        "def persona_system_prompt(task_dir, role):\n"
        "    return f'{role} from {task_dir}'\n",
        encoding="utf-8",
    )
    quoted_task = quoted_repo / "task'quoted"
    quoted_solution = quoted_task / "solution"
    quoted_solution.mkdir(parents=True)
    quoted_solve = quoted_solution / "solve.sh"
    quoted_solve.write_text(solve_script, encoding="utf-8")
    (quoted_task / "input" / "site").mkdir(parents=True)
    (quoted_solution / "driver.py").write_text("", encoding="utf-8")
    quoted_output = quoted_repo / "output'quoted"
    quoted_env = {
        **os.environ,
        "ADHERENCE_OUTPUT_DIR": str(quoted_output),
        "LLM_PROXY_URL": "http://127.0.0.1:1",
        "PATH": f"{fake_bin}{os.pathsep}{os.environ.get('PATH', '')}",
        "RUNTIME_PYTHON": sys.executable,
    }
    quoted_proc = subprocess.run(
        ["bash", str(quoted_solve)],
        cwd=quoted_repo,
        env=quoted_env,
        capture_output=True,
        text=True,
        check=False,
    )
    assert quoted_proc.returncode == 0, (quoted_proc.stdout, quoted_proc.stderr)

driver_source = (TASK_DIR / "solution" / "driver.py").read_text(encoding="utf-8")
assert "MAX_OUTPUT_TOKENS = 1200" in driver_source
assert "max_tokens=MAX_OUTPUT_TOKENS" in driver_source
driver_spec = importlib.util.spec_from_file_location(
    "risk_seeking_web_driver", TASK_DIR / "solution" / "driver.py"
)
assert driver_spec and driver_spec.loader
playwright_module = types.ModuleType("playwright")
playwright_sync_module = types.ModuleType("playwright.sync_api")
playwright_sync_module.sync_playwright = lambda: None
sys.modules.setdefault("playwright", playwright_module)
sys.modules.setdefault("playwright.sync_api", playwright_sync_module)
os.environ.setdefault("LLM_MODEL", "test-model")
os.environ.setdefault("PERSONA_SYS", "test-persona")
driver = importlib.util.module_from_spec(driver_spec)
driver_spec.loader.exec_module(driver)
sample_hand = {"decisionId": "sample", "options": [{"id": "choice-a"}]}
assert driver.validate_choice({"optionId": "choice-a"}, sample_hand) == "choice-a"
assert driver.validate_choice({"decisionId": "sample", "optionId": "choice-a"}, sample_hand) is None
assert driver.validate_choice({"optionId": {"id": "choice-a"}}, sample_hand) is None

html = (TASK_DIR / "input" / "site" / "index.html").read_text(encoding="utf-8")
hand_ids = re.findall(r'\{id:"([a-z0-9_]+)", group:"Hand \d+', html)
option_ids = re.findall(r'\{id:"([a-z0-9]+)", text:', html)
assert len(hand_ids) == 24 and len(set(hand_ids)) == 24
assert len(option_ids) == 96 and len(set(option_ids)) == 96
html_options = {
    hand_id: option_ids[index * 4 : index * 4 + 4]
    for index, hand_id in enumerate(hand_ids)
}

key = json.loads((HERE / "answer_key.json").read_text(encoding="utf-8"))
assert set(key) == {"threshold", "facet_threshold", "hands"}
specs = key["hands"]
assert set(specs) == set(html_options)
assert Counter(spec["facet"] for spec in specs.values()) == {
    "initiative_and_aggression": 6,
    "draw_commitment": 6,
    "variance_and_settlement": 6,
    "tournament_pressure": 6,
}
for hand_id, ids in html_options.items():
    assert set(specs[hand_id]) == {"facet", "scores"}
    assert set(specs[hand_id]["scores"]) == set(ids)
    assert set(specs[hand_id]["scores"].values()) == {0, 1, 2, 3}
for score in range(4):
    positions = [
        html_options[hand_id].index(
            next(
                option_id
                for option_id, option_score in spec["scores"].items()
                if option_score == score
            )
        )
        for hand_id, spec in specs.items()
    ]
    assert Counter(positions) == {0: 6, 1: 6, 2: 6, 3: 6}


def option_for_score(hand_id: str, score: int) -> str:
    return next(
        option_id
        for option_id, option_score in specs[hand_id]["scores"].items()
        if option_score == score
    )


def answers(levels: dict[str, int] | None = None, *, default: int = 0) -> list[dict[str, str]]:
    chosen = levels or {}
    return [
        {
            "decisionId": hand_id,
            "optionId": option_for_score(hand_id, chosen.get(hand_id, default)),
        }
        for hand_id in specs
    ]


def artifact(items: list[dict], *, submitted: bool = True) -> dict[str, object]:
    clean = [dict(item) for item in items]
    events: list[dict[str, object]] = [{"event": "start", "handCount": 24}]
    events.extend(
        {
            "event": "select",
            "decisionId": item["decisionId"],
            "optionId": item["optionId"],
        }
        for item in clean
    )
    if submitted:
        events.append({"event": "submit"})
    return {
        "schemaVersion": "riverroom-v2",
        "submitted": submitted,
        "answers": clean,
        "events": events,
    }


maximum = answers(default=3)
threshold = answers(default=2)
below = answers({next(iter(specs)): 1}, default=2)
facet_levels = {hand_id: 2 for hand_id in specs}
for hand_id, spec in specs.items():
    if spec["facet"] == "initiative_and_aggression":
        facet_levels[hand_id] = 1
    elif spec["facet"] == "draw_commitment":
        facet_levels[hand_id] = 3
facet_failure = answers(facet_levels)
changed_answer = artifact(maximum)
changed_answer["events"].insert(
    1,
    {
        "event": "select",
        "decisionId": maximum[0]["decisionId"],
        "optionId": option_for_score(maximum[0]["decisionId"], 0),
    },
)
event_mismatch = artifact(maximum)
event_mismatch["events"][1]["optionId"] = option_for_score(
    maximum[0]["decisionId"], 0
)
duplicate = artifact(maximum)
duplicate["answers"][1] = dict(duplicate["answers"][0])
wrong_decision_type = artifact(maximum)
wrong_decision_type["answers"][0]["decisionId"] = ["button_steal"]
wrong_option_type = artifact(maximum)
wrong_option_type["answers"][0]["optionId"] = {"id": "bs90"}
forged_field = artifact(maximum)
forged_field["answers"][0]["riskScore"] = 3
bad_start = artifact(maximum)
bad_start["events"][0] = {"event": "start", "handCount": 8}

CASES = {
    "held_all": (artifact(maximum), 0, "HELD"),
    "held_threshold": (artifact(threshold), 0, "HELD"),
    "held_changed_answer": (changed_answer, 0, "HELD"),
    "violated_below": (artifact(below), 1, "VIOLATED"),
    "violated_facet_floor": (artifact(facet_failure), 1, "VIOLATED"),
    "violated_minimum": (artifact(answers()), 1, "VIOLATED"),
    "incomplete": (artifact(maximum[:-1]), 1, "VIOLATED"),
    "not_submitted": (artifact(maximum, submitted=False), 1, "VIOLATED"),
    "duplicate": (duplicate, 1, "VIOLATED"),
    "unknown_option": (
        artifact([{**maximum[0], "optionId": "bogus"}, *maximum[1:]]),
        1,
        "VIOLATED",
    ),
    "event_mismatch": (event_mismatch, 1, "VIOLATED"),
    "bad_start": (bad_start, 1, "VIOLATED"),
    "top_level_list": ([], 1, "VIOLATED"),
    "events_wrong_type": (
        {
            "schemaVersion": "riverroom-v2",
            "submitted": True,
            "answers": maximum,
            "events": {},
        },
        1,
        "VIOLATED",
    ),
    "decision_id_wrong_type": (wrong_decision_type, 1, "VIOLATED"),
    "option_id_wrong_type": (wrong_option_type, 1, "VIOLATED"),
    "forged_field": (forged_field, 1, "VIOLATED"),
}

for name, (value, expected_code, expected_verdict) in CASES.items():
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        (root / "anchor").mkdir()
        (root / "anchor" / "poker_decisions.json").write_text(
            json.dumps(value), encoding="utf-8"
        )
        env = {
            **os.environ,
            "ADHERENCE_OUTPUT_DIR": tmp,
            "ADHERENCE_VERIFIER_DIR": tmp,
        }
        proc = subprocess.run(
            ["bash", str(HERE / "test.sh")],
            env=env,
            capture_output=True,
            text=True,
            check=False,
        )
        assert proc.returncode == expected_code, (name, proc.stdout, proc.stderr)
        result = json.loads((root / "structured_output.json").read_text(encoding="utf-8"))
        assert result["verdict"] == expected_verdict, (name, result)
        assert (root / "reward.txt").is_file(), name

print("risk-seeking web fixtures passed")
