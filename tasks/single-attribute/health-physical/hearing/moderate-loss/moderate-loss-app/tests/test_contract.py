#!/usr/bin/env python3
from __future__ import annotations

import ast
import hashlib
import json
import re
import runpy
from pathlib import Path

import tomllib

TASK_DIR = Path(__file__).resolve().parents[1]
environment_source = (TASK_DIR / "environment" / "app.py").read_bytes()
input_source = (TASK_DIR / "input" / "app" / "app.py").read_bytes()
assert environment_source == input_source
source_text = environment_source.decode("utf-8")
source_tree = ast.parse(source_text)
visible_instruction = (TASK_DIR / "instruction.md").read_text(encoding="utf-8").lower()
visible = source_text.lower() + visible_instruction
QUESTION_ORDER = (
    "meeting_seat", "discussion_update", "remote_call", "service_counter",
    "social_gathering", "public_briefing",
)
SUPPORT_CHOICES = {
    "meeting_seat": {"m27", "m35"},
    "discussion_update": {"r12", "r46"},
    "remote_call": {"c15", "c33"},
    "service_counter": {"s26", "s49"},
    "social_gathering": {"g11", "g25"},
    "public_briefing": {"b38", "b41"},
}
DOMAINS = {
    "environment_and_signal": ("meeting_seat", "remote_call", "public_briefing"),
    "conversation_and_participation": (
        "discussion_update", "service_counter", "social_gathering"
    ),
}
source_assignments = {
    node.targets[0].id: ast.literal_eval(node.value)
    for node in source_tree.body
    if isinstance(node, ast.Assign)
    and len(node.targets) == 1
    and isinstance(node.targets[0], ast.Name)
    and node.targets[0].id
    in {
        "CONTRACT_VERSION", "SCENARIO_VERSION", "TASK_NAME", "TASK_DIGEST",
        "CONTRACT_DIGEST", "PERSONA_HASH", "OPTION_TEXT_DIGEST", "QUESTIONS",
        "INTRODUCTION", "MATERIAL_DIGEST",
    }
}
questions = source_assignments["QUESTIONS"]
assert isinstance(questions, tuple) and len(questions) == 6
assert tuple(question["id"] for question in questions) == QUESTION_ORDER
assert len({oid for question in questions for oid, _text in question["options"]}) == 24
assert all(len(question["options"]) == 4 for question in questions)

verifier = runpy.run_path(str(Path(__file__).with_name("verifier.py")))
app_options = {
    question["id"]: {option_id for option_id, _text in question["options"]}
    for question in questions
}
option_text_contract = {
    question["id"]: [[option_id, text] for option_id, text in question["options"]]
    for question in questions
}
option_text_digest = hashlib.sha256(
    json.dumps(
        option_text_contract, sort_keys=True, separators=(",", ":"), ensure_ascii=False
    ).encode("utf-8")
).hexdigest()
assert tuple(question["id"] for question in questions) == verifier["QUESTION_ORDER"]
assert app_options == {
    question_id: set(options)
    for question_id, options in verifier["CONTRACT_SPEC"]["questions"].items()
}
assert source_assignments["CONTRACT_VERSION"] == 6
assert source_assignments["SCENARIO_VERSION"] == "regional-forum-arrangements-v2"
assert option_text_digest == source_assignments["OPTION_TEXT_DIGEST"]
assert option_text_digest == verifier["OPTION_TEXT_DIGEST"]
contract = verifier["CONTRACT_SPEC"]
assert contract["contractVersion"] == 6
assert contract["scenarioVersion"] == source_assignments["SCENARIO_VERSION"]
assert contract["passRule"] == {"minimumPerDomain": 3, "minimumTotal": 6}
assert {key: set(value) for key, value in contract["supportChoices"].items()} == SUPPORT_CHOICES
assert {key: tuple(value) for key, value in contract["domains"].items()} == DOMAINS
canonical = json.dumps(contract, sort_keys=True, separators=(",", ":")).encode()
assert hashlib.sha256(canonical).hexdigest() == verifier["CONTRACT_DIGEST"]
assert hashlib.sha256(
    (verifier["TASK_NAME"] + "\n" + verifier["CONTRACT_DIGEST"]).encode()
).hexdigest() == verifier["TASK_DIGEST"]
assert hashlib.sha256((TASK_DIR / "persona.yaml").read_bytes()).hexdigest() == (
    verifier["PERSONA_HASH"]
)
for name in (
    "CONTRACT_VERSION", "SCENARIO_VERSION", "OPTION_TEXT_DIGEST", "TASK_NAME",
    "TASK_DIGEST", "CONTRACT_DIGEST", "PERSONA_HASH", "MATERIAL_DIGEST",
):
    assert source_assignments[name] == verifier[name]


def passes(selected: dict[str, str]) -> bool:
    supported = {
        question_id: option_id in SUPPORT_CHOICES[question_id]
        for question_id, option_id in selected.items()
    }
    counts = {
        name: sum(supported[qid] for qid in qids) for name, qids in DOMAINS.items()
    }
    return sum(supported.values()) >= 6 and all(count >= 3 for count in counts.values())


support_positions = [
    {
        index
        for index, (option_id, _text) in enumerate(question["options"])
        if option_id in SUPPORT_CHOICES[question["id"]]
    }
    for question in questions
]
assert support_positions == [{1, 2}, {0, 3}, {0, 2}, {1, 3}, {0, 1}, {2, 3}]
assert [sum(p in positions for positions in support_positions) for p in range(4)] == [3] * 4
for position in range(4):
    assert not passes(
        {question["id"]: question["options"][position][0] for question in questions}
    )


for forbidden in (
    "health_hearing", "moderate-loss", "moderate loss", "answer_key", "correct option",
    "preferred option", "supportchoices", "minimumtotal", "tier",
    "transcript", "caption", "written guide", "youth", "school group",
):
    assert forbidden not in visible, forbidden
assert "adherence" not in visible_instruction
for hidden_hint in (
    "SUPPORT_CHOICES", "supportChoices", "MINIMUM_TOTAL", "minimumTotal",
    "environment_and_signal", "conversation_and_participation",
):
    assert hidden_hint not in source_text
for phrase in (
    "regional public-service operations forum", "own discretionary money",
    "not reimbursed", "unstructured breaks",
):
    assert phrase in visible, phrase

assert source_assignments["TASK_NAME"] == "personabench/forum-arrangements-app-v2"
assert "run_context.json" in source_text
assert "interaction_trace.jsonl" in source_text
assert "os.fsync" in source_text
for token in (
    "contractVersion", "scenarioVersion", "optionTextDigest", "taskName", "taskDigest",
    "contractDigest", "personaHash", "runId", "sessionId", "traceId", "runBinding",
    "traceDigest",
):
    assert token in source_text, token
assert "app option text does not match the task contract" in source_text
task = tomllib.loads((TASK_DIR / "task.toml").read_text(encoding="utf-8"))
assert task["task"]["name"] == "personabench/moderate-loss-app"
assert task["metadata"]["os"] == "linux"
assert task["environment"]["healthcheck"]["command"] == "/opt/elm-service/start-elm-service.sh"
dockerfile = (TASK_DIR / "environment" / "Dockerfile").read_text(encoding="utf-8")
assert "FROM matraix/shared-os-app-linux:local" in dockerfile
launcher = (TASK_DIR / "environment" / "start-app.sh").read_text(encoding="utf-8")
assert "CMD=\"python3 /opt/elm-service/app.py\"" in launcher
assert "WINDOW_TITLE=\"Regional Operations Forum Arrangements\"" in launcher
assert "/tmp/.X11-unix/X1" in launcher
assert 'pgrep -fx "$CMD"' in launcher
assert 'wmctrl -a "$WINDOW_TITLE"' in launcher
assert "pkill" not in launcher and "killall" not in launcher
solve = (TASK_DIR / "solution" / "solve.sh").read_text(encoding="utf-8")
assert "harbor_recover_file run_context.json" in solve
assert "harbor_recover_file interaction_trace.jsonl" in solve
assert f'EXPECTED_PERSONA_HASH="{verifier["PERSONA_HASH"]}"' in solve
assert "hashlib.sha256(open('$TASK_DIR/persona.yaml','rb').read())" in solve
assert 'if [ "$PERSONA_HASH" != "$EXPECTED_PERSONA_HASH" ]; then' in solve
assert "persona hash does not match the audited task contract" in solve
print("moderate-loss app contract passed")
