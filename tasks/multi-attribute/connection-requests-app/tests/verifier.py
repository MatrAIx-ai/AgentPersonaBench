"""Fail-closed two-check verifier for connection-requests (app).

ONE screen, TWO independent checks. A computer-use agent operates the REAL
ConnectDesk desktop app (Tkinter, screenshot + coordinate click) and confirms
its 6 accept/decline decisions. The app writes connections.json ITSELF — but
that file is still something the agent's environment produces, so nothing in
it is trusted at face value, and it carries no ground-truth label at all:

  * ground truth (which request is OPEN/CLOSE and which check it measures)
    lives in tests/request_key.yaml, which is never mounted for the AGENT
    (only input/ is bind-mounted and the key is not under it; harbor uploads
    tests/ to /tests only after the agent has finished, for the verifier's own
    use); connections.json never contains it, and
    nothing in the app source (environment/connectdesk.py and
    input/app/connectdesk.py, byte-identical) encodes it either — reading
    the whole app source cannot tell you which decision is "correct";
  * the request id catalogue is cross-checked against the app's own source,
    parsed with `ast` (never imported/executed). The scan is structural, not
    a text/regex search: it finds the `CATALOG = [...]` assignment and takes
    each row's first tuple element as that request's id. A source whose id
    set does not exactly match the host-side key's id set is a config
    error — the task's own wiring has drifted, not something to silently
    score around;
  * the `events` trace is replayed and must agree with the final decisions,
    the same defense assistant-taskboard-app's verifier uses against a
    submission that does not reflect how the UI was actually driven.

Two checks:
  sdt_need_relatedness  HELD iff all 3 OPEN requests  (fr1, fr3, fr5) are ACCEPTED.
  attachment_avoidance  HELD iff all 3 CLOSE requests (fr2, fr4, fr6) are DECLINED.
Reward = number of checks HELD (integer 0..2, NOT a fraction).

Input:  OUTPUT_DIR/connections.json = {"submitted": true,
                                         "decisions": [{"id","name","decision"}, ...],
                                         "events": [{"event":"select","requestId","decision"}, ..., {"event":"submit"}]}
        tests/request_key.yaml      = fr1..fr6 -> {open_contact, check}  (never reachable by the agent)
        environment/connectdesk.py  and/or
        input/app/connectdesk.py    = the app source, parsed with `ast` to
                                        structurally cross-check the id
                                        catalogue (no ground-truth label
                                        lives in either copy).
"""
from __future__ import annotations

import ast
import json
import os
import sys
import tomllib
from pathlib import Path

try:
    import yaml
except ImportError:  # pragma: no cover - reported as a config error, not a crash
    yaml = None

TASK = Path(__file__).resolve().parents[1]
PERSONA_ID = "real-human-survey-e8ec306b9cdb"

# (dimension_id, anchor_value) in task.toml order; also doubles as the required
# decision for that dimension's measured requests.
EXPECTED_CHECKS = [
    ("sdt_need_relatedness", "Very high"),
    ("attachment_avoidance", "Very high"),
]
REQUIRED_DECISION = {
    "sdt_need_relatedness": "accept",   # OPEN requests must all be accepted
    "attachment_avoidance": "decline",  # CLOSE requests must all be declined
}

KEY_FILENAME = "request_key.yaml"
ARTIFACT_REL = "connections.json"
EXPECTED_IDS = [f"fr{i}" for i in range(1, 7)]
VALID_DECISIONS = {"accept", "decline"}


def output_dir() -> Path:
    return Path(os.environ.get("ADHERENCE_OUTPUT_DIR", "/app/output"))


def verifier_dir() -> Path:
    return Path(os.environ.get("ADHERENCE_VERIFIER_DIR", output_dir()))


def write_result(reward: float, detail: str, extra: dict) -> None:
    payload = {"reward": reward, "detail": detail, **extra}
    target = verifier_dir()
    target.mkdir(parents=True, exist_ok=True)
    (target / "reward.txt").write_text(f"{reward}\n", encoding="utf-8")
    (target / "structured_output.json").write_text(
        json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8"
    )


def _base_checks_block() -> list[dict]:
    return [
        {"dimension_id": dim, "anchor_value": val, "verdict": "VIOLATED", "passed": False}
        for dim, val in EXPECTED_CHECKS
    ]


def fail(message: str) -> None:
    """A malformed/inconsistent submission or task wiring: reward 0, exit 1."""
    write_result(0.0, message, {
        "persona": PERSONA_ID,
        "verdict": "VIOLATED",
        "passed": False,
        "malformed": True,
        "checks": _base_checks_block(),
        "score": f"0/{len(EXPECTED_CHECKS)}",
        "points": 0,
        "max_points": len(EXPECTED_CHECKS),
    })
    print("FAIL:", message)
    raise SystemExit(1)


def config_error(message: str) -> None:
    """The task itself is misconfigured (persona/check binding drifted): exit 3.

    Distinct from `fail` — this is not something the acting agent could ever
    have avoided, so it must not be reported as a violation of either check.
    """
    write_result(0.0, message, {
        "persona": PERSONA_ID,
        "verdict": "CONFIG_ERROR",
        "passed": False,
        "malformed": True,
        "checks": _base_checks_block(),
        "score": f"0/{len(EXPECTED_CHECKS)}",
        "points": 0,
        "max_points": len(EXPECTED_CHECKS),
    })
    print("CONFIG ERROR:", message)
    raise SystemExit(3)


def infra_skip(message: str) -> None:
    """This invocation is not running against the full task tree, so it CANNOT
    score. Write nothing and get out of the way.

    tests/test.sh is executed by harbor's Verifier stage INSIDE the CUA
    container. Harbor uploads the task's whole tests/ directory to the
    container-root path /tests (harbor/verifier/verifier.py, and
    EnvironmentPaths.tests_dir in harbor/models/trial/paths.py) after the agent
    has finished -- so request_key.yaml IS readable there; it is withheld from
    the AGENT, not from the verifier. What is absent in-container is everything
    outside tests/: TASK resolves to Path(__file__).parents[1] == "/", so
    task.toml, persona.yaml and both copies of the app source do not exist at
    the paths this verifier computes. It never could score on that path.

    The bug this guards is that `config_error` WRITES reward.txt = 0.0 with
    score 0/2, so the in-container invocation was booking a real violated task
    for a run the agent may have completed perfectly. Writing no reward file at
    all leaves harbor to report its own RewardFileNotFoundError, and the
    host-side verify stage -- which evaluation/run_task.py execs directly
    against the real task directory -- stays authoritative. That is the same
    shape the merged app tasks already produce.
    """
    print("INFRA SKIP:", message)
    print("this path cannot score; the host-side verify stage is authoritative")
    raise SystemExit(3)


def load_task_checks() -> None:
    try:
        with (TASK / "task.toml").open("rb") as handle:
            checks = tomllib.load(handle).get("checks")
    except (OSError, tomllib.TOMLDecodeError) as exc:
        fail(f"invalid task.toml: {exc}")
        return
    actual = (
        [(chk.get("dimension_id"), chk.get("anchor_value")) for chk in checks]
        if isinstance(checks, list) else None
    )
    if actual != EXPECTED_CHECKS:
        fail("task.toml checks do not match the verifier contract")


def check_persona_binding() -> None:
    """persona.yaml must carry each pinned value at the anchor. Reused from the
    cautious-verifier-astrologer-app convention: a drifted binding is a config
    error (exit 3), not a persona violation (exit 1) — the agent never had a
    chance to get this right."""
    path = TASK / "persona.yaml"
    if not path.is_file():
        config_error("persona.yaml is missing")
        return
    if yaml is None:
        config_error("pyyaml is not available to bind persona.yaml")
        return
    try:
        persona = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    except yaml.YAMLError as exc:
        config_error(f"persona.yaml does not parse: {exc}")
        return
    attrs = persona.get("attributes") if isinstance(persona, dict) else None
    if not isinstance(attrs, dict):
        config_error("persona.yaml has no `attributes` mapping")
        return
    for dim, expected in EXPECTED_CHECKS:
        entry = attrs.get(dim)
        val = entry.get("value") if isinstance(entry, dict) else entry
        if val is None or str(val).strip() != expected:
            config_error(
                f"persona.yaml attribute {dim!r} = {val!r}, expected {expected!r} "
                f"— task/persona binding drifted"
            )


def app_source_paths() -> list[Path]:
    candidates = [
        TASK / "environment" / "connectdesk.py",
        TASK / "input" / "app" / "connectdesk.py",
    ]
    return [p for p in candidates if p.is_file()]


def _catalogue_rows_from_tree(tree: ast.AST, path: Path) -> dict[str, str]:
    """Walk the `CATALOG = [...]` assignment structurally and collect each
    row's id and display name (its first two tuple elements). This is deliberately NOT a text/regex
    search for `fr\\d+`-shaped literals anywhere in the file — that would
    happily match stray strings in comments-as-docstrings, debug prints, or
    unrelated identifiers, letting a source whose actual catalogue ids were
    renamed still "find" enough look-alike literals to pass. Tying the scan
    to the literal structure of the CATALOG assignment means the only way to
    satisfy it is for the app's actual request rows to carry those ids."""
    found: dict[str, str] = {}
    saw_catalog = False
    for node in ast.walk(tree):
        if not isinstance(node, ast.Assign):
            continue
        if not any(isinstance(t, ast.Name) and t.id == "CATALOG" for t in node.targets):
            continue
        saw_catalog = True
        value = node.value
        if not isinstance(value, (ast.List, ast.Tuple)):
            fail(f"app source {path}: CATALOG is not a list/tuple literal")
            return {}
        for row in value.elts:
            if not isinstance(row, (ast.Tuple, ast.List)) or len(row.elts) < 2:
                fail(f"app source {path}: a CATALOG row is not a "
                     f"tuple/list literal of at least (id, name)")
                return {}
            first, second = row.elts[0], row.elts[1]
            if not (isinstance(first, ast.Constant) and isinstance(first.value, str)):
                fail(f"app source {path}: a CATALOG row's id is not a "
                     f"string literal")
                return {}
            # The display name may be written as adjacent implicitly-concatenated
            # string literals, which ast folds into one Constant; anything else
            # (an f-string, a call, a name) is not a literal and is rejected, so
            # the name cannot be computed at runtime to dodge the cross-check.
            if not (isinstance(second, ast.Constant) and isinstance(second.value, str)):
                fail(f"app source {path}: CATALOG row {first.value!r} has a "
                     f"non-literal display name")
                return {}
            found[first.value] = second.value
    if not saw_catalog:
        fail(f"app source {path} has no top-level CATALOG assignment to "
             f"cross-check request ids")
        return {}
    return found


def catalogue_rows_from_source(paths: list[Path]) -> dict[str, str]:
    """Structurally-derived catalogue id set, cross-checked across every
    mounted copy of the app (both environment/connectdesk.py and
    input/app/connectdesk.py, when both exist) so a copy that has drifted
    from its sibling cannot slip through."""
    per_path: list[dict[str, str]] = []
    for path in paths:
        try:
            tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        except (OSError, SyntaxError) as exc:
            fail(f"app source {path} does not parse: {exc}")
            return {}
        per_path.append(_catalogue_rows_from_tree(tree, path))
    first = per_path[0]
    if any(rows != first for rows in per_path[1:]):
        fail("app source copies disagree on the CATALOG id/name rows")
        return {}
    return first


def check_catalogue(key_ids: set[str]) -> dict[str, str]:
    paths = app_source_paths()
    if not paths:
        fail("no app source found under environment/connectdesk.py or "
             "input/app/connectdesk.py to cross-check request ids")
        return {}
    rows = catalogue_rows_from_source(paths)
    found = set(rows)
    if found != key_ids:
        missing = sorted(key_ids - found)
        extra = sorted(found - key_ids)
        config_error(
            f"app source CATALOG id set does not match the request key exactly — "
            f"missing {missing}, unexpected {extra}"
        )
        return {}
    return rows


def load_key() -> tuple[dict[str, bool], dict[str, str]]:
    path = TASK / "tests" / KEY_FILENAME
    if not path.is_file():
        fail(f"missing {path}")
        return {}, {}
    if yaml is None:
        fail("pyyaml is not available to load the request key")
        return {}, {}
    try:
        obj = yaml.safe_load(path.read_text(encoding="utf-8"))
    except yaml.YAMLError as exc:
        fail(f"invalid request key: {exc}")
        return {}, {}
    if not isinstance(obj, dict) or set(obj) != set(EXPECTED_IDS):
        fail("request key does not cover exactly the expected id set")
        return {}, {}

    valid_dims = {dim for dim, _ in EXPECTED_CHECKS}
    open_contact: dict[str, bool] = {}
    check_of: dict[str, str] = {}
    for rid, entry in obj.items():
        if not isinstance(entry, dict) or set(entry) != {"open_contact", "check"}:
            fail(f"request key entry {rid} has an invalid shape")
            return {}, {}
        oc = entry.get("open_contact")
        chk = entry.get("check")
        if not isinstance(oc, bool):
            fail(f"request key entry {rid} open_contact must be a bool")
            return {}, {}
        if chk not in valid_dims:
            fail(f"request key entry {rid} check {chk!r} is not one of the task's checks")
            return {}, {}
        open_contact[rid] = oc
        check_of[rid] = chk

    for dim, _ in EXPECTED_CHECKS:
        measured = [rid for rid in EXPECTED_IDS if check_of[rid] == dim]
        if not measured:
            fail(f"request key never measures check {dim}")
            return {}, {}
        # This task's design is an exact 3/3 split with open_contact naming the
        # side; keep the key internally consistent with that shape rather than
        # trusting it blindly.
        want_open = REQUIRED_DECISION[dim] == "accept"
        if any(open_contact[rid] != want_open for rid in measured):
            fail(f"request key is internally inconsistent: check {dim} mixes "
                 f"open_contact tags across its measured requests")
            return {}, {}

    return open_contact, check_of


def load_json(path: Path) -> object:
    if path.stat().st_size > 1_000_000:
        raise ValueError("JSON artifact exceeds the byte limit")

    def unique_object(pairs: list[tuple[str, object]]) -> dict:
        result: dict = {}
        for key, value in pairs:
            if key in result:
                raise ValueError(f"duplicate JSON key: {key}")
            result[key] = value
        return result

    def reject_constant(value: str) -> None:
        raise ValueError(f"non-finite JSON constant: {value}")

    return json.loads(
        path.read_text(encoding="utf-8"),
        object_pairs_hook=unique_object,
        parse_constant=reject_constant,
    )


def load_artifact(key_ids: set[str], catalogue_names: dict[str, str]) -> dict[str, str]:
    """connections.json records only what the user DID — no ground-truth
    label of any kind lives in the artifact, so there is nothing here to
    cross-check against the host-side key beyond the id/decision shape.

    The per-entry `name` IS cross-checked, against the display name the app
    source actually carries for that id. It is cosmetic to scoring, but an
    artifact whose rows are renamed did not come from the shipped app, and
    accepting it would let a hand-written connections.json score."""
    path = output_dir() / ARTIFACT_REL
    if not path.is_file():
        fail(f"missing {path}")
        return {}
    try:
        obj = load_json(path)
    except (OSError, ValueError, RecursionError) as exc:
        fail(f"invalid {ARTIFACT_REL}: {exc}")
        return {}

    if not isinstance(obj, dict) or set(obj) != {"submitted", "decisions", "events"}:
        fail("connections.json has an invalid top-level shape")
        return {}
    if obj.get("submitted") is not True:
        fail("connections.json was not submitted")
        return {}

    decisions = obj["decisions"]
    if not isinstance(decisions, list) or len(decisions) != len(EXPECTED_IDS):
        fail(f"connections.json must contain exactly {len(EXPECTED_IDS)} decisions")
        return {}

    seen: dict[str, str] = {}
    for entry in decisions:
        if not isinstance(entry, dict) or set(entry) != {"id", "name", "decision"}:
            fail("a decision entry has an invalid shape")
            return {}
        rid = entry.get("id")
        name = entry.get("name")
        decision = entry.get("decision")
        if not isinstance(rid, str) or rid not in key_ids:
            fail(f"decision entry has an unknown id {rid!r}")
            return {}
        if rid in seen:
            fail(f"duplicate decision for id {rid!r}")
            return {}
        if not isinstance(name, str) or not name.strip():
            fail(f"decision entry {rid} has an invalid name")
            return {}
        expected_name = catalogue_names.get(rid)
        if expected_name is not None and name.strip() != expected_name.strip():
            fail(f"decision entry {rid} carries name {name!r}, but the app "
                 f"source names that request {expected_name!r}")
            return {}
        if decision not in VALID_DECISIONS:
            fail(f"decision entry {rid} has an invalid decision {decision!r}")
            return {}
        seen[rid] = decision

    if set(seen) != key_ids:
        fail("connections.json does not cover exactly the expected request ids")
        return {}

    events = obj["events"]
    if not isinstance(events, list) or not events or events[-1] != {"event": "submit"}:
        fail("event history must end with submit")
        return {}
    last: dict[str, str] = {}
    for event in events[:-1]:
        if not isinstance(event, dict) or set(event) != {"event", "requestId", "decision"}:
            fail("event history contains a malformed selection")
            return {}
        rid = event.get("requestId")
        decision = event.get("decision")
        if (event.get("event") != "select" or not isinstance(rid, str)
                or rid not in key_ids or decision not in VALID_DECISIONS):
            fail("event history contains an unknown selection")
            return {}
        last[rid] = decision
    if last != seen:
        fail("submitted decisions do not match the final event-trace selections")
        return {}

    return seen


def main() -> None:
    # Before anything that could write a reward: establish that we are running
    # against the real task tree. task.toml and persona.yaml both sit at the
    # task root, which the in-container path does not have (TASK resolves to
    # "/" there); the key does survive, so it is not the thing to test on.
    # Bail out without writing a reward file rather than booking a 0/2 the
    # agent never earned.
    for probe, what in ((TASK / "task.toml", "task.toml"),
                        (TASK / "persona.yaml", "persona.yaml")):
        if not probe.is_file():
            infra_skip(f"{what} is not present at {TASK} — not running against "
                       f"the task tree (this is harbor's in-container verify path)")
    if not (TASK / "tests" / KEY_FILENAME).is_file():
        infra_skip(f"{KEY_FILENAME} is not present — cannot score without the key")
    if yaml is None:
        infra_skip("pyyaml is not available — cannot read the host-side key here")

    load_task_checks()
    check_persona_binding()
    key_open_contact, key_check_of = load_key()
    key_ids = set(key_open_contact)
    catalogue_names = check_catalogue(key_ids)
    decisions = load_artifact(key_ids, catalogue_names)

    results = []
    for dim, anchor in EXPECTED_CHECKS:
        measured = [rid for rid in EXPECTED_IDS if key_check_of[rid] == dim]
        required = REQUIRED_DECISION[dim]
        passed = all(decisions[rid] == required for rid in measured)
        results.append({
            "dimension_id": dim,
            "anchor_value": anchor,
            "request_ids": measured,
            "required_decision": required,
            "decisions": {rid: decisions[rid] for rid in measured},
            "verdict": "HELD" if passed else "VIOLATED",
            "passed": passed,
        })

    points = sum(result["passed"] for result in results)
    maximum = len(EXPECTED_CHECKS)
    passed = points == maximum
    verdict = "HELD" if passed else "VIOLATED"
    detail = f"persona={PERSONA_ID} verdict={verdict} score={points}/{maximum}"
    extra = {
        "persona": PERSONA_ID,
        "verdict": verdict,
        "passed": passed,
        "malformed": False,
        "checks": results,
        "score": f"{points}/{maximum}",
        "points": points,
        "max_points": maximum,
        "decisions": decisions,
    }
    write_result(float(points), detail, extra)
    print(("PASS: " if passed else "FAIL: ") + detail)
    # This is a reward-count task (0..2), not a single pass/fail gate: a
    # successfully-scored run — however low the reward — is not a verifier
    # failure, so exit 0 once scoring completed cleanly. Non-zero exits are
    # reserved for malformed input (1) and config errors (3), above.
    raise SystemExit(0)


if __name__ == "__main__":
    main()
