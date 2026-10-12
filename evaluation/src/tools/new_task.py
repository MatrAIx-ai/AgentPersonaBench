#!/usr/bin/env python3
"""new_task — scaffold a new PersonaBench task from an env template.

Contributors currently hand-write 5-8 files per task with no starting point.
This drops a working skeleton for one of the four environments (chat / survey /
web / app) into tasks/<bucket>/<task-path>/, with every file the runner and
task_doctor expect, and a clear `TODO(contributor):` marker at each spot you
must fill in. The skeleton is designed to pass task_doctor immediately (before
you customise it), so you always start from green.

Usage:
    python evaluation/src/tools/new_task.py <task-path> --env {chat,survey,web,app} \
        [--attribute lstyle_diet_type --value Vegan] [--name ...] [--theme ...] \
        [--multi] [--dry-run] [--root /tmp/scratch] [--force]

    <task-path> is the path UNDER the bucket, exactly as run_task.py expects, e.g.
        health-lifestyle/diet-type/vegan/vegan-survey

Buckets: single-attribute/ (default) or multi-attribute/ (--multi).

The template for each env is based on the simplest existing task of that type:
    survey -> vegan-survey   (slim solve.sh sourcing evaluation/src/lib/harbor_solve.sh)
    chat   -> vegan-chat     (chat_harness pattern; no output file)
    web    -> vegan-web      (Playwright docker-driver pattern)
    app    -> vegan-app      (harbor CUA + slim solve.sh; QuickBite-style GUI)

Dependencies: stdlib only.
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[3]

_TODO = "TODO(contributor):"


# --------------------------------------------------------------------------- #
# shared file bodies
# --------------------------------------------------------------------------- #
def _persona_yaml(attribute: str, value: str) -> str:
    """A minimal but schema-valid persona stub.

    Real tasks embed a full ~300-attribute MatrAIx-1M persona; for a fresh
    skeleton we ship a small self-contained one that already carries the tested
    attribute at the tested value (so task_doctor's persona cross-check passes).
    """
    return f"""persona_id: SCAFFOLD-REPLACE-ME
version: '2.0'
source: scaffold
# {_TODO} replace this stub with a REAL, coherent persona sampled from the
# MatrAIx Persona 1M dataset (hundreds of attributes):
#   https://huggingface.co/datasets/MatrAIx2026/MatrAIx_Persona_1M
# The persona is the vehicle that carries the tested attribute inside a realistic
# whole human — not a single-trait stub. The ONE line that must stay is
# `{attribute}` = the tested value below; everything else comes from the sampled persona.
attributes:
  {attribute}:
    value: {value}
    label: "{_TODO} human-readable label"
    category: "{_TODO} schema category"
"""


def _task_toml(name: str, theme: str, env: str, attribute: str, value: str,
               multi: bool, evaluator: str) -> str:
    difficulty = {"survey": "easy", "chat": "easy",
                  "web": "medium", "app": "medium"}[env]
    # single-attribute tasks conventionally use anchor_value; multi use value.
    val_key = "value" if multi else "anchor_value"
    extra_checks = ""
    if multi:
        extra_checks = f"""
# {_TODO} a multi-attribute task tests SEVERAL attributes with one generation.
# Add more [[checks]] blocks (one per attribute); the verifier scores one point
# per check held (0..N). Delete this note and the block below if single-check.
[[checks]]
dimension_id = "{_TODO}_second_dimension_id"
dimension_label = "{_TODO} label"
category = "{_TODO} category"
value = "{_TODO} second value"
evaluator = "{evaluator}"
adherence_signal = "{_TODO} what observable behavior shows this attribute held"
"""
    env_block = {
        "survey": '''[environment]
definition = "application/shared-survey-form"
build_timeout_sec = 300.0
cpus = 1
memory_mb = 1024
storage_mb = 4096
gpus = 0''',
        "chat": '''[environment]
definition = "application/shared-chat-persona"
build_timeout_sec = 600.0
cpus = 1
memory_mb = 2048
storage_mb = 10240
gpus = 0''',
        "web": '''[environment]
# Reuses the shared Playwright image (Chromium + playwright python).
definition = "application/shared-web-playwright"
build_timeout_sec = 900.0
cpus = 1
memory_mb = 2048
storage_mb = 10240
gpus = 0
network_mode = "public"''',
        "app": '''[environment]
# Task-local Linux CUA desktop with your GUI baked in — see ./environment/Dockerfile.
# No `definition` key: harbor uses the task's own environment/ dir when present.
cpus = 4
memory_mb = 4096
storage_mb = 40960
gpus = 0

[environment.healthcheck]
# TODO(contributor): launch your app once the desktop is up so the agent finds it.
command = "/opt/app/start-app.sh"
timeout_sec = 60.0
retries = 5''',
    }[env]
    agent_timeout = {"survey": 300.0, "chat": 600.0,
                     "web": 600.0, "app": 1800.0}[env]
    verifier_timeout = {"survey": 30.0, "chat": 60.0,
                        "web": 300.0, "app": 300.0}[env]
    os_line = '\nos = "linux"' if env == "app" else ""
    return f'''version = "1.0"
artifacts = [ "/app/output",]

[task]
# {_TODO} confirm a unique, descriptive name and a one-line human theme.
name = "{name}"
theme = "{theme}"

[metadata]
difficulty = "{difficulty}"
type = "{env}"{os_line}
domain = "{_TODO}"
tags = [ "persona-adherence", "{_TODO}-tag",]

# --- Persona-adherence check(s) --------------------------------------------- #
# Each check isolates one (attribute = value) pair the task measures. The persona
# carries the value; the evaluator returns HELD / VIOLATED from the agent's behavior.
[[checks]]
dimension_id = "{attribute}"
dimension_label = "{_TODO} label"
category = "{_TODO} category"
{val_key} = "{value}"
evaluator = "{evaluator}"
# {_TODO} describe the OBSERVABLE signal that proves the attribute held/violated.
adherence_signal = "{_TODO} what in the agent's output reveals adherence"
{extra_checks}
[verifier]
timeout_sec = {verifier_timeout}

[agent]
timeout_sec = {agent_timeout}

{env_block}
'''


# --------------------------------------------------------------------------- #
# per-env instruction.md / solve.sh / verifier.py / input
# --------------------------------------------------------------------------- #
SURVEY_INSTRUCTION = f"""# Instruction

Answer every question in the survey by choosing the single option you would
genuinely pick. Do not explain — just choose.

## Files (container runs)

- Questionnaire (ids, prompts, option ids/text): `/app/input/questionnaire.yaml`
- Write your answers to `/app/output/survey_result.json`:

```json
{{
  "answers": [
    {{"questionId": "q1", "selectedOptionId": "<one option id>"}}
  ]
}}
```

One answer per question, using the exact option ids from the questionnaire.

{_TODO} Keep this instruction GENERIC — it must NOT mention the tested attribute
or its value, and must NOT reveal that behavior is being scored. The persona
reveals the trait through WHICH options it picks, not by being told to.
"""

SURVEY_QUESTIONNAIRE = f"""# {_TODO} Replace with your own questions. Each option carries a HIDDEN label
# (here `flag: true/false`) the verifier reads; it is NOT shown to the persona.
# Design options so an adherent persona picks the flag=false ones and a
# non-adherent persona would pick flag=true ones.
questions:
  - id: q1
    prompt: "{_TODO} a natural question that indirectly probes the attribute"
    type: single_choice
    options:
      - {{id: q1a, text: "{_TODO} option a", flag: true}}
      - {{id: q1b, text: "{_TODO} option b", flag: false}}
"""

SURVEY_SOLVE = """#!/usr/bin/env bash
# Solver — SURVEY env. A real harbor agent runs in docker, reads instruction.md +
# /app/input/questionnaire.yaml, and writes /app/output/survey_result.json itself.
# All the harbor/gateway/recovery boilerplate lives in evaluation/src/lib/harbor_solve.sh;
# this file only names what to recover. No edits normally needed.
set -euo pipefail
TASK_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
REPO_DIR="$TASK_DIR"; while [ "$REPO_DIR" != "/" ] && [ ! -d "$REPO_DIR/evaluation/src" ]; do REPO_DIR="$(dirname "$REPO_DIR")"; done
# shellcheck source=/dev/null
source "$REPO_DIR/evaluation/src/lib/harbor_solve.sh"

harbor_run_agent
harbor_recover_file survey_result.json survey_result.json
harbor_pack_trace
"""

SURVEY_VERIFIER = f'''"""Rule-based adherence verifier — SURVEY env.

The persona selects options from a questionnaire. Each option carries a hidden
`flag` label; adherence is read purely from WHICH option ids were chosen.

Input: OUTPUT_DIR/survey_result.json = {{"answers":[{{"questionId","selectedOptionId"}}]}}
"""
import json
import os
import sys
from pathlib import Path

try:
    import yaml
except ImportError:
    yaml = None

_TASK = Path(__file__).resolve().parents[1]


def _output_dir() -> Path:
    return Path(os.environ.get("ADHERENCE_OUTPUT_DIR", "/app/output"))


def _verifier_dir() -> Path:
    return Path(os.environ.get("ADHERENCE_VERIFIER_DIR", _output_dir()))


def _write(reward: float, detail: str, extra: dict | None = None) -> None:
    payload = {{"reward": reward, "detail": detail}}
    if extra:
        payload.update(extra)
    vd = _verifier_dir()
    vd.mkdir(parents=True, exist_ok=True)
    (vd / "reward.txt").write_text(f"{{reward}}\\n", encoding="utf-8")
    (vd / "structured_output.json").write_text(
        json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def fail(msg: str) -> None:
    _write(0.0, msg)
    print("FAIL:", msg)
    sys.exit(1)


def _flag_map() -> dict:
    if yaml is None:
        fail("pyyaml not installed (needed to read questionnaire.yaml)")
    data = yaml.safe_load((_TASK / "input" / "questionnaire.yaml").read_text())
    return {{opt["id"]: bool(opt.get("flag", False))
            for q in data["questions"] for opt in q["options"]}}


def main() -> None:
    path = _output_dir() / "survey_result.json"
    if not path.is_file():
        fail(f"missing {{path}}")
    picks = json.loads(path.read_text()).get("answers")
    if not isinstance(picks, list) or not picks:
        fail(f"{{path}} must contain a non-empty 'answers' list")
    fmap = _flag_map()
    # {_TODO} decide adherence from the picks. Default: HELD iff no flag=true option chosen.
    hits = [a.get("selectedOptionId") for a in picks
            if fmap.get(a.get("selectedOptionId"))]
    verdict = "HELD" if not hits else "VIOLATED"
    passed = verdict == "HELD"
    detail = f"verdict={{verdict}} flagged-picks={{len(hits)}} {{hits}}"
    _write(1.0 if passed else 0.0, detail,
           {{"verdict": verdict, "flagged_picks": hits, "passed": passed}})
    print(("PASS: " if passed else "FAIL: ") + detail)
    sys.exit(0 if passed else 1)


if __name__ == "__main__":
    main()
'''

# --- chat ------------------------------------------------------------------- #
CHAT_INSTRUCTION = f"""# Instruction

You are the assistant in a multi-turn conversation with a user. Talk it through
naturally across several turns — react to what the user says and adjust as the
conversation develops.

Stay in character the whole time. Respond conversationally; there are no files to
write and nothing to output in any special format. Just keep replying to the
user's latest message.

{_TODO} Keep this GENERIC. Do NOT mention the tested attribute/value, that you're
role-playing a persona, or that behavior is being scored. The trait stays latent.
"""

CHAT_BOT = f"""{_TODO} Write the BOT's system prompt here (input/bot.md).

The bot is the persona's conversation partner. Design it to gently PRESSURE the
persona AWAY from the tested attribute, so holding the attribute is observable.
Example (vegan task): a meal assistant that keeps suggesting meat dishes and
tempts the user to accept one. Keep replies short; never fully give up pushing.
"""

CHAT_CONTEXT = f"""# Scenario

{_TODO} One paragraph describing the situation, and the user's OPENING message.
Keep the request generic — it must never name the tested attribute. We test
*latent adherence*: a persona carrying the value should reveal it unprompted.

## The user's message

> {_TODO} the persona's first message that kicks off the conversation.

{_TODO} The opening must stay generic — it must not name the tested attribute.
"""

CHAT_SOLVE = """#!/usr/bin/env bash
# Solver — CHAT env. The persona is run as a real AGENT: harbor's UserSimulator
# drives the conversation in character from persona.yaml, talking to the bot this
# task defines (input/bot.md). All plumbing lives in evaluation/src/chat_harness.py.
# Output: user_turns.json = {"turns":[...]} (+ transcript.json). No edits normally needed.
set -euo pipefail
TASK_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
REPO_DIR="$TASK_DIR"; while [ "$REPO_DIR" != "/" ] && [ ! -d "$REPO_DIR/evaluation/src" ]; do REPO_DIR="$(dirname "$REPO_DIR")"; done
OUTPUT_DIR="${ADHERENCE_OUTPUT_DIR:-/app/output}"; mkdir -p "$OUTPUT_DIR"
ARM="${ADHERENCE_ARM:-opus-4-8}"
RUNTIME="$REPO_DIR/evaluation/src"
RUNTIME_PYTHON="${RUNTIME_PYTHON:-python3}"

PYTHONPATH="$RUNTIME" "$RUNTIME_PYTHON" -c "
from chat_harness import run_chat_adherence
run_chat_adherence('$TASK_DIR', '$OUTPUT_DIR', '$ARM')
"
"""

CHAT_VERIFIER = f'''"""LLM-judge adherence verifier — CHAT env.

We judge the USER's own turns for whether the persona held the tested attribute
while the bot pushed against it. Binary verdict: HELD or VIOLATED.

Input: OUTPUT_DIR/user_turns.json = {{"turns":[...]}}
"""
import json
import os
import re
import sys
from pathlib import Path

_REPO = Path(__file__).resolve()
while _REPO != _REPO.parent and not (_REPO / "evaluation" / "src").is_dir():
    _REPO = _REPO.parent
sys.path.insert(0, str(_REPO / "evaluation" / "src"))
from llm_client import chat  # noqa: E402

JUDGE_MODEL = os.environ.get("ADHERENCE_JUDGE_MODEL", "claude-opus-4-8")

# {_TODO} write the judge rubric for YOUR attribute. Keep it binary.
JUDGE_PROMPT = (
    "Below are a USER's messages from a chat. Decide whether the user behaved "
    "consistently with {_TODO}: <the tested attribute>.\\n"
    "- Answer VIOLATED if {_TODO} <condition that breaks the attribute>.\\n"
    "- Answer HELD if {_TODO} <condition that keeps the attribute>.\\n"
    "Answer with exactly one word: HELD or VIOLATED."
)


def _output_dir() -> Path:
    return Path(os.environ.get("ADHERENCE_OUTPUT_DIR", "/app/output"))


def _verifier_dir() -> Path:
    return Path(os.environ.get("ADHERENCE_VERIFIER_DIR", _output_dir()))


def _write(reward: float, detail: str, extra: dict) -> None:
    payload = {{"reward": reward, "detail": detail}}
    payload.update(extra)
    vd = _verifier_dir()
    vd.mkdir(parents=True, exist_ok=True)
    (vd / "reward.txt").write_text(f"{{reward}}\\n", encoding="utf-8")
    (vd / "structured_output.json").write_text(
        json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def fail(msg: str) -> None:
    _write(0.0, msg, {{}})
    print("FAIL:", msg)
    sys.exit(1)


def main() -> None:
    path = _output_dir() / "user_turns.json"
    if not path.is_file():
        fail(f"missing {{path}}")
    turns = json.loads(path.read_text()).get("turns")
    if not isinstance(turns, list) or not turns:
        fail(f"{{path}} must contain a non-empty 'turns' list")
    turns_text = "\\n".join(f"- {{t}}" for t in turns)
    out = chat([{{"role": "system", "content": JUDGE_PROMPT}},
                {{"role": "user", "content": turns_text}}],
               model=JUDGE_MODEL, temperature=0.0, max_tokens=2000)
    verdict = "HELD" if re.search(r"\\bHELD\\b", out, re.I) else (
        "VIOLATED" if re.search(r"\\bVIOLATED\\b", out, re.I) else None)
    if verdict is None:
        fail(f"judge did not return HELD/VIOLATED: {{out!r}}")
    passed = verdict == "HELD"
    _write(1.0 if passed else 0.0, f"judge={{JUDGE_MODEL}} verdict={{verdict}}",
           {{"judge_model": JUDGE_MODEL, "judge_raw": out.strip(),
            "verdict": verdict, "passed": passed, "user_turns": turns}})
    print(("PASS: " if passed else "FAIL: ") + f"verdict={{verdict}}")
    sys.exit(0 if passed else 1)


if __name__ == "__main__":
    main()
'''

# --- web -------------------------------------------------------------------- #
WEB_INSTRUCTION = f"""# Instruction

{_TODO} Describe the on-page task in ONE or two sentences (e.g. "Order dinner by
adding 3 dishes you'd genuinely eat from the menu").

## Files (container runs)

- Site: `/app/input/site/index.html`
- Write your result to `/app/output/anchor/order.json`:

```json
{{ "orderedItemIds": ["<id>", "<id>", "<id>"] }}
```

Use exact element ids from the page. Just do the task — no explanation.

{_TODO} Keep GENERIC: do NOT mention the tested attribute/value or that behavior
is being scored. The trait shows up in WHICH items the persona clicks.
"""

WEB_INDEX = f"""<!DOCTYPE html>
<html lang="en">
<head><meta charset="utf-8"><title>{_TODO} page title</title></head>
<body>
  <h1>{_TODO} heading</h1>
  <!-- {_TODO} Build your interactive page. Each choosable item carries a
       data-id (used by the agent + verifier) and a HIDDEN data-flag="true/false"
       ground-truth label the verifier reads. Design items so an adherent persona
       clicks only data-flag="false" ones. The cart state must live in the DOM so
       Playwright can read it back after real clicks. -->
  <div id="menu">
    <div class="item" data-id="m01" data-flag="true">
      <span>{_TODO} item that a NON-adherent persona would pick</span>
      <button class="add" data-id="m01">Add</button></div>
    <div class="item" data-id="m02" data-flag="false">
      <span>{_TODO} item that an ADHERENT persona would pick</span>
      <button class="add" data-id="m02">Add</button></div>
  </div>
  <div id="cart"><h2>Your order</h2><ul id="cart-items"></ul></div>
  <script>
    window.__cart = [];
    document.querySelectorAll('button.add').forEach(function (btn) {{
      btn.addEventListener('click', function () {{
        var id = btn.getAttribute('data-id');
        if (window.__cart.indexOf(id) !== -1) return;
        window.__cart.push(id);
        var li = document.createElement('li');
        li.setAttribute('data-id', id);
        li.textContent = btn.closest('.item').querySelector('span').textContent;
        document.getElementById('cart-items').appendChild(li);
      }});
    }});
  </script>
</body>
</html>
"""

WEB_SOLVE = r'''#!/usr/bin/env bash
# Solver — REAL WEB env. A full persona drives a live menu page via Playwright in
# a docker container, records a replayable trace, and writes the DOM cart to
# /app/output/anchor/order.json. Based on the vegan-web docker-driver pattern.
set -euo pipefail
TASK_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
REPO_DIR="$TASK_DIR"
while [ "$REPO_DIR" != "/" ] && [ ! -d "$REPO_DIR/evaluation/src" ]; do REPO_DIR="$(dirname "$REPO_DIR")"; done
OUTPUT_DIR="${ADHERENCE_OUTPUT_DIR:-/app/output}"
IMAGE="matraix/shared-web-playwright:local"
# TODO(contributor): point ENVDEF at the shared Playwright env definition, or
# provide your own Dockerfile that produces an image with playwright+chromium.
ENVDEF="$REPO_DIR/evaluation/src/environment/task-environments/application/shared-web-playwright"
if ! docker image inspect "$IMAGE" >/dev/null 2>&1; then docker build -q -t "$IMAGE" "$ENVDEF" >/dev/null; fi
PERSONA_SYS="$(PYTHONPATH="$REPO_DIR" python3 -c "from evaluation.src.persona import persona_system_prompt; print(persona_system_prompt('$TASK_DIR', role='a user'))")"
mkdir -p "$OUTPUT_DIR"
DRIVER="$(mktemp /tmp/rw_solve.XXXX.py)"; trap 'rm -f "$DRIVER"' EXIT
cat > "$DRIVER" <<'PY'
import json, os, re, time
from playwright.sync_api import sync_playwright
from agent_client import chat  # host-proxied LLM; no SDK/key/provider in-container
MODEL=os.environ.get("LLM_MODEL","claude-opus-4-8")
# TODO(contributor): adjust the prompt + selectors to YOUR page.
PERSONA_SYS=os.environ["PERSONA_SYS"]+"\n\nYou are doing a task on a website. Pick the items you'd genuinely choose."
traj=[]; out="/app/output"; os.makedirs(out,exist_ok=True)
with sync_playwright() as p:
    browser=p.chromium.launch(headless=True); ctx=browser.new_context()
    ctx.tracing.start(screenshots=True, snapshots=True, sources=True)
    page=ctx.new_page(); page.goto("file:///app/site/index.html", wait_until="domcontentloaded")
    items=[(it.get_attribute("data-id"), it.locator("span").inner_text().strip()) for it in page.locator("#menu .item").all()]
    menu="\n".join(f"  {d}) {n}" for d,n in items)
    raw=chat(system=PERSONA_SYS,user="Items:\n"+menu+'\n\nReturn ONLY JSON: {"pick":["m01","m02"]}',max_tokens=2000)
    picks=json.loads(re.search(r"\{.*\}",raw,re.S).group())["pick"]
    for pid in picks:
        page.locator(f'button.add[data-id="{pid}"]').click(); traj.append({"step":"click_add","id":pid})
    cart=[li.get_attribute("data-id") for li in page.locator("#cart-items li").all()]
    d=out+"/anchor"; os.makedirs(d,exist_ok=True)
    json.dump({"orderedItemIds":cart}, open(d+"/order.json","w"), indent=2)
    ctx.tracing.stop(path=out+"/trace.zip"); browser.close()
json.dump({"model":MODEL,"trajectory":traj}, open(out+"/generation.json","w"), indent=2)
print(f"cart {cart}")
PY
docker run --rm --network=host -v "$REPO_DIR/evaluation/src/agent_client.py:/app/agent_client.py:ro" -v "$TASK_DIR/input/site:/app/site:ro" -v "$OUTPUT_DIR:/app/output" -v "$DRIVER:/app/rw_solve.py:ro" \
  -e LLM_PROXY_URL="$LLM_PROXY_URL" -e PERSONA_SYS="$PERSONA_SYS" \
  "$IMAGE" python3 /app/rw_solve.py
'''

WEB_VERIFIER = f'''"""Rule-based adherence verifier — REAL WEB env.

Ground truth is the live page: the `data-flag` attribute on each menu item in
input/site/index.html. The agent's DOM cart (order.json, written after real
clicks) is checked against it. No LLM.

Input: OUTPUT_DIR/anchor/order.json = {{"orderedItemIds":[...]}}
"""
import json
import os
import re
import sys
from pathlib import Path

_TASK = Path(__file__).resolve().parents[1]


def _output_dir() -> Path:
    return Path(os.environ.get("ADHERENCE_OUTPUT_DIR", "/app/output"))


def _verifier_dir() -> Path:
    return Path(os.environ.get("ADHERENCE_VERIFIER_DIR", _output_dir()))


def _write(reward: float, detail: str, extra: dict | None = None) -> None:
    payload = {{"reward": reward, "detail": detail}}
    if extra:
        payload.update(extra)
    vd = _verifier_dir()
    vd.mkdir(parents=True, exist_ok=True)
    (vd / "reward.txt").write_text(f"{{reward}}\\n", encoding="utf-8")
    (vd / "structured_output.json").write_text(
        json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def fail(msg: str) -> None:
    _write(0.0, msg)
    print("FAIL:", msg)
    sys.exit(1)


def _flag_map() -> dict:
    html = (_TASK / "input" / "site" / "index.html").read_text()
    amap = {{}}
    for m in re.finditer(r'class="item"\\s+data-id="([^"]+)"\\s+data-flag="([^"]+)"', html):
        amap[m.group(1)] = (m.group(2).strip().lower() == "true")
    if not amap:
        fail("could not parse data-flag ground truth from index.html")
    return amap


def main() -> None:
    path = _output_dir() / "anchor" / "order.json"
    if not path.is_file():
        fail(f"missing {{path}}")
    ids = json.loads(path.read_text()).get("orderedItemIds")
    if not isinstance(ids, list) or not ids:
        fail(f"{{path}} DOM cart is empty — no clicks registered")
    fmap = _flag_map()
    hits = [oid for oid in ids if fmap.get(oid)]
    verdict = "HELD" if not hits else "VIOLATED"
    passed = verdict == "HELD"
    detail = f"verdict={{verdict}} flagged-in-cart={{len(hits)}} {{hits}}"
    _write(1.0 if passed else 0.0, detail,
           {{"verdict": verdict, "flagged_in_cart": hits, "passed": passed}})
    print(("PASS: " if passed else "FAIL: ") + detail)
    sys.exit(0 if passed else 1)


if __name__ == "__main__":
    main()
'''

# --- app -------------------------------------------------------------------- #
APP_INSTRUCTION = f"""# {_TODO} Task title (e.g. "Order dinner in the FooApp app")

The **{_TODO} app** is already open on screen. Use it to {_TODO} do the task.

1. {_TODO} Browse — scroll to see all the options.
2. {_TODO} Tap to select the 2-3 items you would genuinely choose, as this person.
3. {_TODO} Confirm/submit. You're done once the app confirms.

Decide based on what each item contains. You do not need to write any files;
the app records your action itself.

{_TODO} Keep GENERIC: do NOT name the tested attribute/value or reveal that
behavior is being scored.
"""

APP_SOLVE = """#!/usr/bin/env bash
# Solver — APP env. The persona operates your native GUI on a local CUA desktop by
# screenshot + coordinate click; the app writes the result (order.json) itself.
# Uses the harbor CUA agent (persona-computer-1). Boilerplate lives in
# evaluation/src/lib/harbor_solve.sh; this file only picks the CUA agent + recovers.
set -euo pipefail
TASK_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
REPO_DIR="$TASK_DIR"; while [ "$REPO_DIR" != "/" ] && [ ! -d "$REPO_DIR/evaluation/src" ]; do REPO_DIR="$(dirname "$REPO_DIR")"; done
export ADHERENCE_AGENT="${ADHERENCE_AGENT:-persona-computer-1}"
export HARBOR_EXTRA_AK="max_steps=40"
# shellcheck source=/dev/null
source "$REPO_DIR/evaluation/src/lib/harbor_solve.sh"

harbor_run_agent
# TODO(contributor): recover whatever artifact your app writes (name it in your app).
harbor_recover_file order.json order.json
harbor_recover_dir solution solution
harbor_pack_trace
"""

APP_VERIFIER = f'''"""Rule-based adherence verifier — OS-APP env.

The persona (a computer-use agent) operated the app and its final action wrote
order.json. Adherence is read from the recorded result.

Input: OUTPUT_DIR/order.json = {{"orderedItems":[{{"name", "flag"}}]}}
"""
import json
import os
import sys
from pathlib import Path


def _output_dir() -> Path:
    return Path(os.environ.get("ADHERENCE_OUTPUT_DIR", "/app/output"))


def _verifier_dir() -> Path:
    return Path(os.environ.get("ADHERENCE_VERIFIER_DIR", _output_dir()))


def _write(reward: float, detail: str, extra: dict | None = None) -> None:
    payload = {{"reward": reward, "detail": detail}}
    if extra:
        payload.update(extra)
    vd = _verifier_dir()
    vd.mkdir(parents=True, exist_ok=True)
    (vd / "reward.txt").write_text(f"{{reward}}\\n", encoding="utf-8")
    (vd / "structured_output.json").write_text(
        json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def fail(msg: str) -> None:
    _write(0.0, msg)
    print("FAIL:", msg)
    sys.exit(1)


def main() -> None:
    path = _output_dir() / "order.json"
    if not path.is_file():
        fail(f"missing {{path}}")
    items = json.loads(path.read_text()).get("orderedItems")
    if not isinstance(items, list) or not items:
        fail("order.json needs a non-empty orderedItems list")
    # {_TODO} Your app should carry authoritative ground truth into each item as a
    # `flag` bool (like web's data-flag). Held iff no flagged item was chosen.
    hits = [it.get("name") for it in items if it.get("flag")]
    verdict = "HELD" if not hits else "VIOLATED"
    passed = verdict == "HELD"
    detail = f"verdict={{verdict}} flagged-items={{len(hits)}} {{hits}}"
    _write(1.0 if passed else 0.0, detail,
           {{"verdict": verdict, "flagged_items": hits, "passed": passed}})
    print(("PASS: " if passed else "FAIL: ") + detail)
    sys.exit(0 if passed else 1)


if __name__ == "__main__":
    main()
'''

APP_DOCKERFILE = f"""# syntax=docker/dockerfile:1.7
# {_TODO} OS-APP desktop: the shared Linux CUA desktop (Xvfb + XFCE + xdotool +
# scrot) PLUS your native GUI app. The CUA agent drives it by screenshot +
# coordinate click; when the user submits, your app writes /app/output/order.json.
FROM matraix/shared-os-app-linux:local

ENV DEBIAN_FRONTEND=noninteractive
RUN apt-get update && apt-get install -y --no-install-recommends \\
        python3-tk fonts-dejavu-core \\
    && rm -rf /var/lib/apt/lists/*

# {_TODO} copy YOUR app + launcher. The build context is this environment/ dir,
# so app.py here must stay byte-identical to the canonical input/app/app.py.
COPY app.py /opt/app/app.py
COPY start-app.sh /opt/app/start-app.sh
RUN chmod +x /opt/app/start-app.sh

WORKDIR /app
"""

APP_START = """#!/usr/bin/env bash
# TODO(contributor): launch your native GUI and keep it in front of Chromium (the
# harbor CUA runtime starts Chromium last during bringup). Model this on the
# vegan-app start-quickbite.sh keeper loop if your app gets buried.
set -u
# Resolve the live X display: harbor's CUA runtime serves the desktop on :1
# (not :0), so ask the X socket dir rather than assuming, and fall back to
# :1 for the cold-start case where the healthcheck runs before Xvfb is up.
# Do NOT hardcode :0 here — the agent screenshots :1 and would never see the app.
if [ -z "${DISPLAY:-}" ]; then
  for _xs in /tmp/.X11-unix/X*; do
    [ -e "$_xs" ] && DISPLAY=":${_xs##*X}"
  done
fi
export DISPLAY="${DISPLAY:-:1}"
export ADHERENCE_OUTPUT_DIR="${ADHERENCE_OUTPUT_DIR:-/app/output}"
mkdir -p "$ADHERENCE_OUTPUT_DIR"
# If you add a keeper loop, assemble the app path at runtime rather than writing
# it as one literal — `bash -c "$(declare -f keeper); keeper"` carries the
# function source in its own command line, so `pgrep -f /opt/app/app.py` would
# match the keeper itself and a dead app would never be respawned.
if ! pgrep -fx "python3 /opt/app/app.py" >/dev/null 2>&1; then
  setsid nohup python3 /opt/app/app.py >>/tmp/app.log 2>&1 < /dev/null &
fi
exit 0
"""

APP_PY = f'''#!/usr/bin/env python3
# {_TODO} Your native Tkinter GUI. It must:
#   - show the choosable items (each carrying a hidden ground-truth `flag`),
#   - let the user select items and submit,
#   - on submit, write /app/output/order.json = {{"orderedItems":[{{"name","flag"}}]}}.
# See tasks/single-attribute/health-lifestyle/diet-type/vegan/vegan-app/input/app/quickbite.py
# for a complete working example.
#
# This file is the CANONICAL app source (input/app/app.py). A byte-identical copy
# lives at environment/app.py purely as the Dockerfile build context (the shared
# os-app image is built from environment/, so it can only COPY files there); keep
# the two in sync. The `raise` below is a deliberate TODO(contributor) placeholder
# so an unfinished app can't silently ship — replace the whole body with your GUI.
raise NotImplementedError("{_TODO} implement your GUI app")
'''


# verifier entrypoint (shared by every env) — harbor execs this to score a trial.
TEST_SH = """\
#!/usr/bin/env bash
set -euo pipefail
HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
exec python3 "$HERE/verifier.py"
"""


# --------------------------------------------------------------------------- #
# assembly
# --------------------------------------------------------------------------- #
def _files_for(env: str) -> dict[str, str]:
    """Return {relative_path: contents} for the env's extra (non-shared) files."""
    if env == "survey":
        return {
            "instruction.md": SURVEY_INSTRUCTION,
            "input/questionnaire.yaml": SURVEY_QUESTIONNAIRE,
            "solution/solve.sh": SURVEY_SOLVE,
            "tests/verifier.py": SURVEY_VERIFIER,
        }
    if env == "chat":
        return {
            "instruction.md": CHAT_INSTRUCTION,
            "input/bot.md": CHAT_BOT,
            "input/context.md": CHAT_CONTEXT,
            "solution/solve.sh": CHAT_SOLVE,
            "tests/verifier.py": CHAT_VERIFIER,
        }
    if env == "web":
        return {
            "instruction.md": WEB_INSTRUCTION,
            "input/site/index.html": WEB_INDEX,
            "solution/solve.sh": WEB_SOLVE,
            "tests/verifier.py": WEB_VERIFIER,
        }
    if env == "app":
        return {
            "instruction.md": APP_INSTRUCTION,
            "solution/solve.sh": APP_SOLVE,
            "tests/verifier.py": APP_VERIFIER,
            "environment/Dockerfile": APP_DOCKERFILE,
            "environment/start-app.sh": APP_START,
            # Real app tasks (see vegan-app) keep the GUI source at input/app/<app>.py
            # as the CANONICAL location, with a byte-identical copy under environment/
            # solely as the Dockerfile build context. Scaffold both, in sync.
            "input/app/app.py": APP_PY,
            "environment/app.py": APP_PY,
        }
    raise ValueError(env)


def main() -> int:
    ap = argparse.ArgumentParser(
        description="Scaffold a new PersonaBench task for one of the four envs.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="example:\n  python evaluation/src/tools/new_task.py "
               "health-lifestyle/diet-type/vegan/vegan-survey --env survey \\\n"
               "      --attribute lstyle_diet_type --value Vegan",
    )
    ap.add_argument("task", help="task path relative to the bucket "
                                 "(same form as run_task.py)")
    ap.add_argument("--env", required=True,
                    choices=["chat", "survey", "web", "app"],
                    help="which environment template to scaffold")
    ap.add_argument("--attribute", default="TODO_dimension_id",
                    help="the dimension_id the task tests (persona attribute key)")
    ap.add_argument("--value", default="TODO_value",
                    help="the value that attribute must carry")
    ap.add_argument("--name", default=None,
                    help="[task].name (default personabench/<leaf>)")
    ap.add_argument("--theme", default=None,
                    help="[task].theme (default derived from attribute/value)")
    ap.add_argument("--multi", action="store_true",
                    help="place under multi-attribute/ (default single-attribute/)")
    ap.add_argument("--root", default=None,
                    help="scaffold under this root instead of tasks/<bucket> "
                         "(for testing; e.g. /tmp/scratch)")
    ap.add_argument("--dry-run", action="store_true",
                    help="print the files that WOULD be written, write nothing")
    ap.add_argument("--force", action="store_true",
                    help="overwrite an existing task dir")
    args = ap.parse_args()

    bucket = "multi-attribute" if args.multi else "single-attribute"
    if args.root:
        base = Path(args.root) / bucket
    else:
        base = REPO / "tasks" / bucket
    task_dir = base / args.task
    leaf = Path(args.task).name

    name = args.name or f"personabench/{leaf}"
    theme = args.theme or f"{args.attribute} = {args.value}"
    evaluator = "llm-judge" if args.env == "chat" else "rule-based"

    files = {
        "task.toml": _task_toml(name, theme, args.env, args.attribute,
                                args.value, args.multi, evaluator),
        "persona.yaml": _persona_yaml(args.attribute, args.value),
        # verifier entrypoint — harbor needs this to discover/run the task; every
        # env ships the same one-liner that execs verifier.py.
        "tests/test.sh": TEST_SH,
    }
    files.update(_files_for(args.env))

    if task_dir.exists() and not (args.force or args.dry_run):
        print(f"error: {task_dir} already exists (use --force to overwrite)",
              file=sys.stderr)
        return 2

    print(f"scaffold: {args.env} task -> {task_dir}")
    if args.dry_run:
        print("(dry-run — nothing written)")
    for rel, body in sorted(files.items()):
        dest = task_dir / rel
        marker = "would write" if args.dry_run else "wrote"
        if not args.dry_run:
            dest.parent.mkdir(parents=True, exist_ok=True)
            dest.write_text(body, encoding="utf-8")
            if rel.endswith(".sh"):
                dest.chmod(0o755)
        print(f"  {marker}: {rel}")

    print()
    print("next steps:")
    print(f"  1. Fill in every {_TODO} marker (grep for it):")
    print(f"       grep -rn '{_TODO}' {task_dir}")
    print("  2. Self-check the contract:")
    doctor_path = "evaluation/src/tools/task_doctor.py"
    if args.root:
        print(f"       (task_doctor resolves under tasks/; move the task there "
              f"first, or test-scaffold without --root)")
    print(f"       python {doctor_path} {args.task}"
          + ("   # add --multi-aware path if needed" if args.multi else ""))
    print("  3. Run it end-to-end:")
    print(f"       python evaluation/run_task.py {args.task}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
