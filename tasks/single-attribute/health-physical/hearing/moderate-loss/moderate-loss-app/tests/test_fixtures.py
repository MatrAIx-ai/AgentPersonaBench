#!/usr/bin/env python3
from __future__ import annotations

import copy
import hashlib
import json
import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

HERE = Path(__file__).resolve().parent
CONTRACT_VERSION = 6
SCENARIO_VERSION = "regional-forum-arrangements-v2"
OPTION_TEXT_DIGEST = "80335e44317c5bce61f9f8db5b647399a8860bddc6ba8c62710b6d4f4b3e259d"
TASK_NAME = "personabench/forum-arrangements-app-v2"
TASK_DIGEST = "48bf791a7b980a9b6443dae0854cab26e3277d2f57c407339c134b44964e4fbb"
CONTRACT_DIGEST = "19affcd951869c1c9c64659e812309ec075e565dc2af5e0d86a82a471176775e"
PERSONA_HASH = "d436493affd28915e34f1bdd88faefed37487c99d2f93e76b77fc52532acc171"
RUN_ID = "1" * 32
SESSION_ID = "2" * 32
TRACE_ID = "3" * 32
START_NS = 1_000_000
QUESTION_ORDER = (
    "meeting_seat", "discussion_update", "remote_call", "service_counter",
    "social_gathering", "public_briefing",
)
OPTIONS = {
    "meeting_seat": ("m14", "m27", "m35", "m48"),
    "discussion_update": ("r12", "r24", "r39", "r46"),
    "remote_call": ("c15", "c28", "c33", "c47"),
    "service_counter": ("s13", "s26", "s34", "s49"),
    "social_gathering": ("g11", "g25", "g32", "g44"),
    "public_briefing": ("b17", "b23", "b38", "b41"),
}


def choices(*option_ids: str) -> list[dict]:
    return [
        {"questionId": question_id, "optionId": option_id}
        for question_id, option_id in zip(QUESTION_ORDER, option_ids)
    ]


HELD_PRIMARY = choices("m27", "r12", "c15", "s26", "g11", "b38")
HELD_ALTERNATE = choices("m35", "r46", "c33", "s49", "g25", "b41")
VIOLATED_EXACT_FIVE = choices("m27", "r12", "c15", "s26", "g11", "b17")
VIOLATED_FOUR = choices("m27", "r12", "c15", "s26", "g32", "b17")


def canonical(value: object) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def sha256(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def binding() -> str:
    return sha256(
        "|".join(
            (TASK_DIGEST, CONTRACT_DIGEST, PERSONA_HASH, RUN_ID, SESSION_ID, TRACE_ID)
        )
    )


def write_json(path: Path, value: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2), encoding="utf-8")


def build_bundle(
    root: Path,
    answers: list[dict] | None = None,
    *,
    history: list[dict] | None = None,
) -> None:
    answers = copy.deepcopy(answers or HELD_PRIMARY)
    selections = copy.deepcopy(history or answers)
    run_binding = binding()
    context = {
        "contextVersion": 1,
        "contractVersion": CONTRACT_VERSION,
        "scenarioVersion": SCENARIO_VERSION,
        "optionTextDigest": OPTION_TEXT_DIGEST,
        "taskName": TASK_NAME,
        "taskDigest": TASK_DIGEST,
        "contractDigest": CONTRACT_DIGEST,
        "personaHash": PERSONA_HASH,
        "runId": RUN_ID,
        "sessionId": SESSION_ID,
        "traceId": TRACE_ID,
        "processStartNs": START_NS,
        "runBinding": run_binding,
    }
    write_json(root / "run_context.json", context)
    simple_events = [
        {"seq": index, "event": "select", **choice}
        for index, choice in enumerate(selections, 1)
    ]
    simple_events.append(
        {"seq": len(simple_events) + 1, "event": "submit", "selectionCount": 6}
    )
    previous = run_binding
    trace_records = []
    for index, event in enumerate(simple_events, 1):
        core = {**event, "monotonicNs": START_NS + index * 100}
        digest = sha256(previous + "\n" + canonical(core))
        trace_records.append({**core, "previousDigest": previous, "eventDigest": digest})
        previous = digest
    (root / "interaction_trace.jsonl").write_text(
        "\n".join(canonical(record) for record in trace_records) + "\n",
        encoding="utf-8",
    )
    artifact = {
        "schemaVersion": 2,
        "contractVersion": CONTRACT_VERSION,
        "scenarioVersion": SCENARIO_VERSION,
        "optionTextDigest": OPTION_TEXT_DIGEST,
        "taskName": TASK_NAME,
        "taskDigest": TASK_DIGEST,
        "contractDigest": CONTRACT_DIGEST,
        "personaHash": PERSONA_HASH,
        "runId": RUN_ID,
        "sessionId": SESSION_ID,
        "traceId": TRACE_ID,
        "runBinding": run_binding,
        "traceDigest": previous,
        "submitted": True,
        "answers": copy.deepcopy(answers),
        "events": simple_events,
        "uiState": {
            "submitDisabled": True,
            "status": "Forum arrangements saved.",
            "selected": copy.deepcopy(answers),
        },
    }
    write_json(root / "preferences.json", artifact)


def load(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def mutate_json(path: Path, callback) -> None:
    value = load(path)
    callback(value)
    write_json(path, value)


def run_verifier(
    root: Path, *, isolated_layout: bool = True
) -> tuple[int, dict, str, str]:
    verifier_path = HERE / "verifier.py"
    if isolated_layout:
        isolated_tests = root / "runtime" / "tests"
        isolated_tests.mkdir(parents=True, exist_ok=True)
        verifier_path = isolated_tests / "verifier.py"
        shutil.copy2(HERE / "verifier.py", verifier_path)
    env = {
        **os.environ,
        "ADHERENCE_OUTPUT_DIR": str(root),
        "ADHERENCE_VERIFIER_DIR": str(root / "verified"),
    }
    proc = subprocess.run(
        [sys.executable, str(verifier_path)],
        env=env,
        capture_output=True,
        text=True,
    )
    result = json.loads(
        (root / "verified" / "structured_output.json").read_text(encoding="utf-8")
    )
    assert (root / "verified" / "reward.txt").is_file()
    return proc.returncode, result, proc.stdout, proc.stderr


PASS_FAIL_CASES = [
    ("held_primary", HELD_PRIMARY, None, 0, "HELD"),
    ("held_alternate", HELD_ALTERNATE, None, 0, "HELD"),
    ("violated_exact_five", VIOLATED_EXACT_FIVE, None, 1, "VIOLATED"),
    ("held_permuted", list(reversed(HELD_PRIMARY)), None, 0, "HELD"),
    (
        "held_changed_choice",
        HELD_PRIMARY,
        [choices("m14", "r12", "c15", "s26", "g11", "b38")[0], *HELD_PRIMARY],
        0,
        "HELD",
    ),
    ("violated_four_supports", VIOLATED_FOUR, None, 1, "VIOLATED"),
    (
        "violated_domain_floor",
        choices("m27", "r12", "c28", "s26", "g11", "b17"),
        None,
        1,
        "VIOLATED",
    ),
]
for index, question_id in enumerate(QUESTION_ORDER):
    support_ids = {HELD_PRIMARY[index]["optionId"], HELD_ALTERNATE[index]["optionId"]}
    for option_id in OPTIONS[question_id]:
        if option_id in support_ids:
            continue
        selected = copy.deepcopy(HELD_PRIMARY)
        selected[index]["optionId"] = option_id
        PASS_FAIL_CASES.append(
            (f"five_of_six_{question_id}_{option_id}", selected, None, 1, "VIOLATED")
        )
for position in range(4):
    PASS_FAIL_CASES.append(
        (
            f"fixed_position_{position + 1}",
            [
                {"questionId": qid, "optionId": OPTIONS[qid][position]}
                for qid in QUESTION_ORDER
            ],
            None,
            1,
            "VIOLATED",
        )
    )
for name, answers, history, expected_code, expected_verdict in PASS_FAIL_CASES:
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        build_bundle(root, answers, history=history)
        code, result, stdout, stderr = run_verifier(root)
        assert code == expected_code, (name, stdout, stderr)
        assert result["verdict"] == expected_verdict, (name, result)


def set_key(key: str, value: object):
    return lambda obj: obj.__setitem__(key, value)


def pop_key(key: str):
    return lambda obj: obj.pop(key)


def tamper_trace(root: Path, field: str, value: object, record_index: int = 0) -> None:
    path = root / "interaction_trace.jsonl"
    records = [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines()]
    records[record_index][field] = value
    path.write_text(
        "\n".join(canonical(record) for record in records) + "\n", encoding="utf-8"
    )


context = lambda root: root / "run_context.json"
artifact = lambda root: root / "preferences.json"
FAILURE_MUTATIONS = {
    "missing_context": lambda root: context(root).unlink(),
    "missing_context_version": lambda root: mutate_json(context(root), pop_key("contextVersion")),
    "wrong_context_version": lambda root: mutate_json(context(root), set_key("contextVersion", 2)),
    "wrong_context_contract_version": lambda root: mutate_json(context(root), set_key("contractVersion", 3)),
    "wrong_context_scenario": lambda root: mutate_json(context(root), set_key("scenarioVersion", "other")),
    "missing_context_option_digest": lambda root: mutate_json(context(root), pop_key("optionTextDigest")),
    "wrong_context_option_digest": lambda root: mutate_json(context(root), set_key("optionTextDigest", "0" * 64)),
    "cross_task_context": lambda root: mutate_json(context(root), set_key("taskName", "personabench/another-task")),
    "wrong_context_task_digest": lambda root: mutate_json(context(root), set_key("taskDigest", "0" * 64)),
    "wrong_context_contract_digest": lambda root: mutate_json(context(root), set_key("contractDigest", "0" * 64)),
    "wrong_context_persona_hash": lambda root: mutate_json(context(root), set_key("personaHash", "0" * 64)),
    "invalid_context_run": lambda root: mutate_json(context(root), set_key("runId", "forged")),
    "non_independent_ids": lambda root: mutate_json(context(root), set_key("traceId", RUN_ID)),
    "forged_context_binding": lambda root: mutate_json(context(root), set_key("runBinding", "0" * 64)),
    "missing_preferences": lambda root: artifact(root).unlink(),
    "missing_artifact_version": lambda root: mutate_json(artifact(root), pop_key("schemaVersion")),
    "wrong_artifact_version": lambda root: mutate_json(artifact(root), set_key("schemaVersion", 1)),
    "wrong_artifact_contract_version": lambda root: mutate_json(artifact(root), set_key("contractVersion", 3)),
    "wrong_artifact_scenario": lambda root: mutate_json(artifact(root), set_key("scenarioVersion", "other")),
    "missing_artifact_option_digest": lambda root: mutate_json(artifact(root), pop_key("optionTextDigest")),
    "wrong_artifact_option_digest": lambda root: mutate_json(artifact(root), set_key("optionTextDigest", "0" * 64)),
    "cross_task_artifact": lambda root: mutate_json(artifact(root), set_key("taskName", "personabench/another-task")),
    "wrong_artifact_task_digest": lambda root: mutate_json(artifact(root), set_key("taskDigest", "0" * 64)),
    "wrong_artifact_contract_digest": lambda root: mutate_json(artifact(root), set_key("contractDigest", "0" * 64)),
    "wrong_artifact_persona": lambda root: mutate_json(artifact(root), set_key("personaHash", "0" * 64)),
    "cross_run_artifact": lambda root: mutate_json(artifact(root), set_key("runId", "4" * 32)),
    "cross_session_artifact": lambda root: mutate_json(artifact(root), set_key("sessionId", "4" * 32)),
    "cross_trace_artifact": lambda root: mutate_json(artifact(root), set_key("traceId", "4" * 32)),
    "forged_artifact_binding": lambda root: mutate_json(artifact(root), set_key("runBinding", "0" * 64)),
    "forged_trace_digest": lambda root: mutate_json(artifact(root), set_key("traceDigest", "0" * 64)),
    "not_submitted": lambda root: mutate_json(artifact(root), set_key("submitted", False)),
    "partial": lambda root: mutate_json(artifact(root), set_key("answers", HELD_PRIMARY[:5])),
    "duplicate_question": lambda root: mutate_json(artifact(root), lambda value: value["answers"].__setitem__(5, copy.deepcopy(value["answers"][0]))),
    "unknown_option": lambda root: mutate_json(artifact(root), lambda value: value["answers"][0].update({"optionId": "unknown"})),
    "unexpected_field": lambda root: mutate_json(artifact(root), set_key("reward", 1)),
    "forged_label": lambda root: mutate_json(artifact(root), lambda value: value["answers"][0].update({"supported": True})),
    "tampered_events": lambda root: mutate_json(artifact(root), lambda value: value["events"][0].update({"optionId": "m14"})),
    "bad_event_sequence": lambda root: mutate_json(artifact(root), lambda value: value["events"][1].update({"seq": 99})),
    "bad_submit_count": lambda root: mutate_json(artifact(root), lambda value: value["events"][-1].update({"selectionCount": 5})),
    "tampered_ui": lambda root: mutate_json(artifact(root), lambda value: value["uiState"]["selected"][0].update({"optionId": "m14"})),
    "missing_trace": lambda root: (root / "interaction_trace.jsonl").unlink(),
    "malformed_trace": lambda root: (root / "interaction_trace.jsonl").write_text("{broken\n", encoding="utf-8"),
    "forged_trace_chain": lambda root: tamper_trace(root, "optionId", "m14"),
    "wrong_trace_previous_digest": lambda root: tamper_trace(root, "previousDigest", "0" * 64, 1),
    "non_increasing_trace_time": lambda root: tamper_trace(root, "monotonicNs", START_NS, 0),
    "forged_trace_event_digest": lambda root: tamper_trace(root, "eventDigest", "0" * 64, 0),
}
for name, mutation in FAILURE_MUTATIONS.items():
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        build_bundle(root)
        mutation(root)
        code, result, stdout, stderr = run_verifier(root)
        assert code == 1, (name, stdout, stderr)
        assert result["verdict"] == "VIOLATED", (name, result)

with tempfile.TemporaryDirectory() as tmp:
    root = Path(tmp)
    build_bundle(root)
    artifact(root).write_text("{broken", encoding="utf-8")
    code, result, stdout, stderr = run_verifier(root)
    assert code == 1, (stdout, stderr)
    assert result["verdict"] == "VIOLATED"

with tempfile.TemporaryDirectory() as tmp:
    root = Path(tmp)
    build_bundle(root)
    code, result, stdout, stderr = run_verifier(root, isolated_layout=True)
    assert code == 0, (stdout, stderr)
    assert result["verdict"] == "HELD", result
    assert not (root / "runtime" / "persona.yaml").exists()
    artifact(root).unlink()
    code, result, stdout, stderr = run_verifier(root, isolated_layout=True)
    assert code == 1, (stdout, stderr)
    assert result["verdict"] == "VIOLATED", result
    assert (root / "verified" / "reward.txt").is_file()
    assert (root / "verified" / "structured_output.json").is_file()

print("moderate-loss app fixtures passed")
