"""Bound native-state verifier for moderate-loss-app."""
from __future__ import annotations

import hashlib
import json
import os
import re
from pathlib import Path

TESTS_DIR = Path(__file__).resolve().parent
CONTRACT_VERSION = 6
SCENARIO_VERSION = "regional-forum-arrangements-v2"
OPTION_TEXT_DIGEST = "80335e44317c5bce61f9f8db5b647399a8860bddc6ba8c62710b6d4f4b3e259d"
TASK_NAME = "personabench/forum-arrangements-app-v2"
CONTRACT_SPEC = {'contractVersion': 6,
 'scenarioVersion': 'regional-forum-arrangements-v2',
 'optionTextDigest': '80335e44317c5bce61f9f8db5b647399a8860bddc6ba8c62710b6d4f4b3e259d',
 'materialDigest': '17511859a11cfdd817c28c759ae80f68b7a9c92d433a48807eb591ed27c8139c',
 'questions': {'meeting_seat': ['m14', 'm27', 'm35', 'm48'],
               'discussion_update': ['r12', 'r24', 'r39', 'r46'],
               'remote_call': ['c15', 'c28', 'c33', 'c47'],
               'service_counter': ['s13', 's26', 's34', 's49'],
               'social_gathering': ['g11', 'g25', 'g32', 'g44'],
               'public_briefing': ['b17', 'b23', 'b38', 'b41']},
 'supportChoices': {'meeting_seat': ['m27', 'm35'],
                    'discussion_update': ['r12', 'r46'],
                    'remote_call': ['c15', 'c33'],
                    'service_counter': ['s26', 's49'],
                    'social_gathering': ['g11', 'g25'],
                    'public_briefing': ['b38', 'b41']},
 'domains': {'environment_and_signal': ['meeting_seat', 'remote_call', 'public_briefing'],
             'conversation_and_participation': ['discussion_update',
                                                'service_counter',
                                                'social_gathering']},
 'passRule': {'minimumPerDomain': 3, 'minimumTotal': 6},
 'optionFacts': {'m14': {'route': 'standard',
                         'minutes': 0,
                         'equipment': False,
                         'forgone_service': 'none',
                         'route_evidence': 'ordinary room PA',
                         'cost_evidence': 'preserves your full coffee break',
                         'personal_fee_dollars': 0,
                         'fee_evidence': 'no booking fee'},
                 'm27': {'route': 'near_speaker',
                         'minutes': 8,
                         'equipment': False,
                         'forgone_service': 'none',
                         'route_evidence': 'about one metre',
                         'cost_evidence': 'eight minutes',
                         'personal_fee_dollars': 4,
                         'fee_evidence': '$4'},
                 'm35': {'route': 'direct_feed',
                         'minutes': 4,
                         'equipment': True,
                         'forgone_service': 'none',
                         'route_evidence': 'directly to one earpiece',
                         'cost_evidence': 'four minutes',
                         'personal_fee_dollars': 0,
                         'fee_evidence': 'no booking fee'},
                 'm48': {'route': 'standard',
                         'minutes': 12,
                         'equipment': False,
                         'forgone_service': 'none',
                         'route_evidence': 'ordinary room PA',
                         'cost_evidence': 'twelve minutes',
                         'personal_fee_dollars': 6,
                         'fee_evidence': '$6'},
                 'r12': {'route': 'separate_space',
                         'minutes': 5,
                         'equipment': False,
                         'forgone_service': 'none',
                         'route_evidence': "away from the other groups' conversations",
                         'cost_evidence': 'five minutes',
                         'personal_fee_dollars': 3,
                         'fee_evidence': '$3'},
                 'r24': {'route': 'standard',
                         'minutes': 0,
                         'equipment': False,
                         'forgone_service': 'none',
                         'route_evidence': 'near the open catering area',
                         'cost_evidence': 'rest of your break free',
                         'personal_fee_dollars': 0,
                         'fee_evidence': 'no booking fee'},
                 'r39': {'route': 'standard',
                         'minutes': 10,
                         'equipment': False,
                         'forgone_service': 'none',
                         'route_evidence': 'open catering foyer',
                         'cost_evidence': 'ten-minute',
                         'personal_fee_dollars': 5,
                         'fee_evidence': '$5'},
                 'r46': {'route': 'direct_feed',
                         'minutes': 4,
                         'equipment': True,
                         'forgone_service': 'none',
                         'route_evidence': 'microphone feed delivered to a free single-ear '
                                           'receiver',
                         'cost_evidence': 'four minutes',
                         'personal_fee_dollars': 0,
                         'fee_evidence': 'no booking fee'},
                 'c15': {'route': 'direct_feed',
                         'minutes': 5,
                         'equipment': True,
                         'forgone_service': 'none',
                         'route_evidence': 'wired receiver held to one ear',
                         'cost_evidence': 'five minutes',
                         'personal_fee_dollars': 0,
                         'fee_evidence': 'no booking fee'},
                 'c28': {'route': 'standard',
                         'minutes': 0,
                         'equipment': False,
                         'forgone_service': 'none',
                         'route_evidence': 'fixed loudspeaker in the shared workspace',
                         'cost_evidence': 'nothing to collect or return',
                         'personal_fee_dollars': 0,
                         'fee_evidence': 'no booking fee'},
                 'c33': {'route': 'separate_space',
                         'minutes': 7,
                         'equipment': False,
                         'forgone_service': 'none',
                         'route_evidence': 'separated from the workspace conversations',
                         'cost_evidence': 'seven minutes',
                         'personal_fee_dollars': 3,
                         'fee_evidence': '$3'},
                 'c47': {'route': 'standard',
                         'minutes': 10,
                         'equipment': False,
                         'forgone_service': 'none',
                         'route_evidence': 'other conversations continue',
                         'cost_evidence': 'ten-minute',
                         'personal_fee_dollars': 5,
                         'fee_evidence': '$5'},
                 's13': {'route': 'standard',
                         'minutes': 0,
                         'equipment': False,
                         'forgone_service': 'none',
                         'route_evidence': 'four adjacent counters',
                         'cost_evidence': 'remaining break available',
                         'personal_fee_dollars': 0,
                         'fee_evidence': 'no booking fee'},
                 's26': {'route': 'separate_space',
                         'minutes': 9,
                         'equipment': False,
                         'forgone_service': 'none',
                         'route_evidence': 'without the adjacent counter conversations',
                         'cost_evidence': 'nine minutes',
                         'personal_fee_dollars': 4,
                         'fee_evidence': '$4'},
                 's34': {'route': 'standard',
                         'minutes': 12,
                         'equipment': False,
                         'forgone_service': 'none',
                         'route_evidence': 'among the adjacent appointments',
                         'cost_evidence': 'twelve-minute',
                         'personal_fee_dollars': 6,
                         'fee_evidence': '$6'},
                 's49': {'route': 'direct_feed',
                         'minutes': 4,
                         'equipment': True,
                         'forgone_service': 'none',
                         'route_evidence': 'microphone delivered directly to a free loan earpiece',
                         'cost_evidence': 'four minutes',
                         'personal_fee_dollars': 0,
                         'fee_evidence': 'no booking fee'},
                 'g11': {'route': 'separate_space',
                         'minutes': 6,
                         'equipment': False,
                         'forgone_service': 'none',
                         'route_evidence': 'away from the music and catering noise',
                         'cost_evidence': 'six minutes',
                         'personal_fee_dollars': 4,
                         'fee_evidence': '$4'},
                 'g25': {'route': 'separate_space',
                         'minutes': 0,
                         'equipment': False,
                         'forgone_service': 'reception_refreshments',
                         'route_evidence': 'outside the music area',
                         'cost_evidence': 'gives up your included reception refreshments',
                         'personal_fee_dollars': 0,
                         'fee_evidence': 'no fee'},
                 'g32': {'route': 'standard',
                         'minutes': 0,
                         'equipment': False,
                         'forgone_service': 'none',
                         'route_evidence': 'background music and catering service around you',
                         'cost_evidence': 'full break',
                         'personal_fee_dollars': 0,
                         'fee_evidence': 'no booking fee'},
                 'g44': {'route': 'standard',
                         'minutes': 12,
                         'equipment': False,
                         'forgone_service': 'none',
                         'route_evidence': 'music, announcements and catering service continue',
                         'cost_evidence': 'twelve-minute',
                         'personal_fee_dollars': 6,
                         'fee_evidence': '$6'},
                 'b17': {'route': 'standard',
                         'minutes': 0,
                         'equipment': False,
                         'forgone_service': 'none',
                         'route_evidence': 'listening through the hall PA',
                         'cost_evidence': 'no booking fee, reservation or equipment pickup',
                         'personal_fee_dollars': 0,
                         'fee_evidence': 'no booking fee'},
                 'b23': {'route': 'standard',
                         'minutes': 15,
                         'equipment': False,
                         'forgone_service': 'none',
                         'route_evidence': 'hall PA arrangement',
                         'cost_evidence': 'fifteen-minute',
                         'personal_fee_dollars': 5,
                         'fee_evidence': '$5'},
                 'b38': {'route': 'near_speaker',
                         'minutes': 10,
                         'equipment': False,
                         'forgone_service': 'none',
                         'route_evidence': 'about one metre from the speaking guide',
                         'cost_evidence': 'ten minutes',
                         'personal_fee_dollars': 3,
                         'fee_evidence': '$3'},
                 'b41': {'route': 'direct_feed',
                         'minutes': 8,
                         'equipment': True,
                         'forgone_service': 'none',
                         'route_evidence': 'microphone relayed directly to a free pocket receiver',
                         'cost_evidence': 'eight minutes',
                         'personal_fee_dollars': 0,
                         'fee_evidence': 'no booking fee'}}}
CONTRACT_DIGEST = "19affcd951869c1c9c64659e812309ec075e565dc2af5e0d86a82a471176775e"
TASK_DIGEST = "48bf791a7b980a9b6443dae0854cab26e3277d2f57c407339c134b44964e4fbb"
PERSONA_HASH = "d436493affd28915e34f1bdd88faefed37487c99d2f93e76b77fc52532acc171"
QUESTION_ORDER = (
    "meeting_seat", "discussion_update", "remote_call", "service_counter",
    "social_gathering", "public_briefing",
)
QUESTION_IDS = set(QUESTION_ORDER)
OPTION_IDS = {key: set(value) for key, value in CONTRACT_SPEC["questions"].items()}
SUPPORT_CHOICES = {
    key: set(value) for key, value in CONTRACT_SPEC["supportChoices"].items()
}
DOMAINS = {key: tuple(value) for key, value in CONTRACT_SPEC["domains"].items()}
# Cover every distinct listening barrier in the settled plan; this is an
# evidence-completeness rule, not a clinical severity score (see the suite README).
MATERIAL_DIGEST = '17511859a11cfdd817c28c759ae80f68b7a9c92d433a48807eb591ed27c8139c'
MINIMUM_TOTAL = 6
# Each domain has three distinct moments, so neither domain may omit a support.
MINIMUM_PER_DOMAIN = 3
HEX_32_RE = re.compile(r"[0-9a-f]{32}")
HEX_64_RE = re.compile(r"[0-9a-f]{64}")
CONTEXT_KEYS = {
    "contextVersion", "contractVersion", "scenarioVersion", "optionTextDigest",
    "taskName", "taskDigest", "contractDigest", "personaHash", "runId",
    "sessionId", "traceId", "processStartNs", "runBinding",
}
PREFERENCE_KEYS = {
    "schemaVersion", "contractVersion", "scenarioVersion", "optionTextDigest",
    "taskName", "taskDigest", "contractDigest", "personaHash", "runId",
    "sessionId", "traceId", "runBinding", "traceDigest", "submitted", "answers",
    "events", "uiState",
}


def output_dir() -> Path:
    return Path(os.environ.get("ADHERENCE_OUTPUT_DIR", "/app/output"))


def verifier_dir() -> Path:
    # Harbor uploads tests/ to /tests and collects rewards from /logs/verifier.
    # An explicit outer-runner destination wins; local defaults stay unchanged.
    default = Path("/logs/verifier") if TESTS_DIR == Path("/tests") else output_dir()
    return Path(os.environ.get("ADHERENCE_VERIFIER_DIR", default))


def write_result(reward: float, detail: str, **extra: object) -> None:
    out = verifier_dir()
    out.mkdir(parents=True, exist_ok=True)
    payload = {"reward": reward, "detail": detail, **extra}
    (out / "reward.txt").write_text(f"{reward}\n", encoding="utf-8")
    (out / "structured_output.json").write_text(
        json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8"
    )


def fail(message: str) -> None:
    write_result(0.0, message, verdict="VIOLATED", passed=False)
    print("FAIL:", message)
    raise SystemExit(1)


def sha256_text(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def canonical_json(value: object) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def expected_run_binding(run_id: str, session_id: str, trace_id: str) -> str:
    return sha256_text(
        "|".join(
            (TASK_DIGEST, CONTRACT_DIGEST, PERSONA_HASH, run_id, session_id, trace_id)
        )
    )


def read_json(path: Path, label: str) -> dict:
    if not path.is_file():
        fail(f"missing {path}")
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
        fail(f"invalid {label}: {exc}")
    if not isinstance(value, dict):
        fail(f"{label} must be a JSON object")
    return value


def validate_static_contract() -> None:
    if sha256_text(canonical_json(CONTRACT_SPEC)) != CONTRACT_DIGEST:
        fail("verifier contract digest is internally inconsistent")
    if sha256_text(f"{TASK_NAME}\n{CONTRACT_DIGEST}") != TASK_DIGEST:
        fail("verifier task digest is internally inconsistent")


def validate_run_context(value: object) -> dict:
    if not isinstance(value, dict) or set(value) != CONTEXT_KEYS:
        fail("run_context.json has an invalid shape")
    expected = {
        "contextVersion": 1,
        "contractVersion": CONTRACT_VERSION,
        "scenarioVersion": SCENARIO_VERSION,
        "optionTextDigest": OPTION_TEXT_DIGEST,
        "taskName": TASK_NAME,
        "taskDigest": TASK_DIGEST,
        "contractDigest": CONTRACT_DIGEST,
        "personaHash": PERSONA_HASH,
    }
    for key, expected_value in expected.items():
        if value[key] != expected_value or (
            isinstance(expected_value, int) and isinstance(value[key], bool)
        ):
            fail(f"run context {key} does not match this task")
    tokens = []
    for key in ("runId", "sessionId", "traceId"):
        token = value[key]
        if not isinstance(token, str) or HEX_32_RE.fullmatch(token) is None:
            fail(f"run context {key} must be a lowercase 32-character token")
        tokens.append(token)
    if len(set(tokens)) != 3:
        fail("run, session, and trace identifiers must be independently generated")
    start = value["processStartNs"]
    if not isinstance(start, int) or isinstance(start, bool) or start <= 0:
        fail("run context processStartNs must be a positive integer")
    if value["runBinding"] != expected_run_binding(*tokens):
        fail("run context binding is invalid")
    return value


def parse_choice_list(value: object, label: str) -> dict[str, str]:
    if not isinstance(value, list) or len(value) != len(QUESTION_ORDER):
        fail(f"{label} must contain exactly six choices")
    selected: dict[str, str] = {}
    for answer in value:
        if not isinstance(answer, dict) or set(answer) != {"questionId", "optionId"}:
            fail(f"each {label} choice requires exactly questionId and optionId")
        question_id = answer["questionId"]
        option_id = answer["optionId"]
        if not isinstance(question_id, str) or not isinstance(option_id, str):
            fail(f"{label} ids must be strings")
        if question_id not in OPTION_IDS or option_id not in OPTION_IDS[question_id]:
            fail(f"{label} contains an unknown question/option pair")
        if question_id in selected:
            fail(f"{label} contains a duplicate question")
        selected[question_id] = option_id
    if set(selected) != QUESTION_IDS:
        fail(f"{label} must cover every question")
    return selected


def validate_events(value: object) -> dict[str, str]:
    if not isinstance(value, list) or not 7 <= len(value) <= 32:
        fail("artifact event chain must contain 7 to 32 events")
    for expected_seq, event in enumerate(value, 1):
        if (
            not isinstance(event, dict)
            or event.get("seq") != expected_seq
            or isinstance(event.get("seq"), bool)
        ):
            fail("artifact event sequence must be consecutive from 1")
    submit = value[-1]
    if set(submit) != {"seq", "event", "selectionCount"}:
        fail("artifact submit event has an invalid shape")
    if (
        submit["event"] != "submit"
        or submit["selectionCount"] != 6
        or isinstance(submit["selectionCount"], bool)
    ):
        fail("artifact must end with a six-selection submit")
    last: dict[str, str] = {}
    for event in value[:-1]:
        if set(event) != {"seq", "event", "questionId", "optionId"}:
            fail("artifact selection event has an invalid shape")
        question_id = event["questionId"]
        option_id = event["optionId"]
        if (
            event["event"] != "select"
            or not isinstance(question_id, str)
            or not isinstance(option_id, str)
            or question_id not in OPTION_IDS
            or option_id not in OPTION_IDS[question_id]
        ):
            fail("artifact contains an unknown selection event")
        last[question_id] = option_id
    if set(last) != QUESTION_IDS:
        fail("artifact event chain must select all six questions")
    return last


def validate_trace(path: Path, context: dict) -> tuple[list[dict], str]:
    if not path.is_file() or path.stat().st_size == 0:
        fail("interaction_trace.jsonl is missing or empty")
    if path.stat().st_size > 2 * 1024 * 1024:
        fail("interaction trace is unexpectedly large")
    try:
        lines = path.read_text(encoding="utf-8").splitlines()
    except (OSError, UnicodeDecodeError) as exc:
        fail(f"invalid interaction trace: {exc}")
    if not 7 <= len(lines) <= 32 or any(not line.strip() for line in lines):
        fail("interaction trace must contain 7 to 32 non-empty JSON records")
    previous_digest = context["runBinding"]
    previous_time = context["processStartNs"]
    simple_events: list[dict] = []
    for expected_seq, line in enumerate(lines, 1):
        try:
            record = json.loads(line)
        except json.JSONDecodeError as exc:
            fail(f"invalid interaction trace record: {exc}")
        if not isinstance(record, dict):
            fail("interaction trace records must be JSON objects")
        event_name = record.get("event")
        if event_name == "select":
            core_keys = {"seq", "event", "questionId", "optionId", "monotonicNs"}
        elif event_name == "submit":
            core_keys = {"seq", "event", "selectionCount", "monotonicNs"}
        else:
            fail("interaction trace contains an unknown event")
        if set(record) != core_keys | {"previousDigest", "eventDigest"}:
            fail("interaction trace record has an invalid shape")
        core = {key: record[key] for key in core_keys}
        if core["seq"] != expected_seq or isinstance(core["seq"], bool):
            fail("interaction trace sequence must be consecutive from 1")
        timestamp = core["monotonicNs"]
        if (
            not isinstance(timestamp, int)
            or isinstance(timestamp, bool)
            or timestamp <= previous_time
        ):
            fail("interaction trace timestamps must strictly increase after process start")
        if record["previousDigest"] != previous_digest:
            fail("interaction trace digest chain is broken")
        event_digest = sha256_text(previous_digest + "\n" + canonical_json(core))
        if record["eventDigest"] != event_digest:
            fail("interaction trace event digest is invalid")
        previous_time = timestamp
        previous_digest = event_digest
        simple_events.append(
            {key: value for key, value in core.items() if key != "monotonicNs"}
        )
    validate_events(simple_events)
    return simple_events, previous_digest


def main() -> None:
    validate_static_contract()
    out = output_dir()
    context = validate_run_context(
        read_json(out / "run_context.json", "run_context.json")
    )
    obj = read_json(out / "preferences.json", "preferences.json")
    if set(obj) != PREFERENCE_KEYS:
        fail("preferences.json has an invalid top-level shape")
    if obj["schemaVersion"] != 2 or isinstance(obj["schemaVersion"], bool):
        fail("schemaVersion must be integer 2")
    for key in (
        "contractVersion", "scenarioVersion", "optionTextDigest", "taskName",
        "taskDigest", "contractDigest", "personaHash", "runId", "sessionId",
        "traceId", "runBinding",
    ):
        if obj[key] != context[key]:
            fail(f"preferences {key} does not match the independent run context")
    if not isinstance(obj["traceDigest"], str) or HEX_64_RE.fullmatch(obj["traceDigest"]) is None:
        fail("traceDigest must be a lowercase SHA-256 digest")
    if obj["submitted"] is not True:
        fail("preferences were not submitted through the app")
    answers = parse_choice_list(obj["answers"], "answers")
    artifact_events = validate_events(obj["events"])
    if artifact_events != answers:
        fail("artifact events do not match the submitted answers")
    ui_state = obj["uiState"]
    if not isinstance(ui_state, dict) or set(ui_state) != {
        "submitDisabled", "status", "selected"
    }:
        fail("uiState has an invalid shape")
    if (
        ui_state["submitDisabled"] is not True
        or ui_state["status"] != "Forum arrangements saved."
    ):
        fail("uiState does not show a completed submission")
    if parse_choice_list(ui_state["selected"], "uiState.selected") != answers:
        fail("visible selected controls do not match submitted answers")
    trace_events, trace_digest = validate_trace(
        out / "interaction_trace.jsonl", context
    )
    if trace_events != obj["events"]:
        fail("independent interaction trace does not match artifact events")
    if trace_digest != obj["traceDigest"]:
        fail("final trace digest does not match the bound interaction trace")
    supported = {
        question_id: option_id in SUPPORT_CHOICES[question_id]
        for question_id, option_id in answers.items()
    }
    total = sum(supported.values())
    domain_counts = {
        name: sum(supported[question_id] for question_id in question_ids)
        for name, question_ids in DOMAINS.items()
    }
    passed = total >= MINIMUM_TOTAL and all(
        count >= MINIMUM_PER_DOMAIN for count in domain_counts.values()
    )
    verdict = "HELD" if passed else "VIOLATED"
    detail = (
        f"verdict={verdict} support_total={total}/6 "
        + " ".join(f"{name}={count}/3" for name, count in domain_counts.items())
    )
    write_result(
        1.0 if passed else 0.0,
        detail,
        verdict=verdict,
        passed=passed,
        support_total=total,
        domain_counts=domain_counts,
        support_by_question=supported,
        selected_answers=answers,
        task_digest=TASK_DIGEST,
        contract_digest=CONTRACT_DIGEST,
        persona_hash=PERSONA_HASH,
        run_id=obj["runId"],
        session_id=obj["sessionId"],
        trace_id=obj["traceId"],
        trace_digest=trace_digest,
    )
    print(("PASS: " if passed else "FAIL: ") + detail)
    raise SystemExit(0 if passed else 1)


if __name__ == "__main__":
    main()
