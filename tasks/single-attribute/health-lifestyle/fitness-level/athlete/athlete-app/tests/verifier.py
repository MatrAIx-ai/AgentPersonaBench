"""Rule-based verifier — Fitness level = Athlete, Linux App surface.

MotionDeck writes a label-free artifact after real GUI interactions. The acting
computer-use model can read both ``input/`` and the application image, so neither
copy of the catalog contains target labels. Submitted IDs are scored against
``tests/answer_key.json``, which remains host-side and is never mounted for the
agent. The verifier reconciles the key's IDs and names with both exposed catalogs
before scoring and replays the event history to reject hand-forged final state.
"""
import ast
import json
import os
import sys
from pathlib import Path


_TASK = Path(__file__).resolve().parents[1]
PERSONA = "p-ec140af52f"
APP_SRC = _TASK / "environment" / "motiondeck.py"
INPUT_SRC = _TASK / "input" / "app" / "motiondeck.py"
ANSWER_KEY = _TASK / "tests" / "answer_key.json"
LIST_KEY = "reservedSessions"
MIN_ITEMS, MAX_ITEMS, FNAME = 3, 3, "reservations.json"
EXPECTED_CATALOG_ITEMS, EXPECTED_POSITIVE_ITEMS = 8, 4


class TaskFileError(Exception):
    """The shipped app/key contract is missing, malformed, exposed, or drifted."""


def _od():
    return Path(os.environ.get("ADHERENCE_OUTPUT_DIR", "/app/output"))


def _vd():
    return Path(os.environ.get("ADHERENCE_VERIFIER_DIR", _od()))


def _write(reward, detail, extra):
    payload = {"reward": reward, "detail": detail}
    payload.update(extra)
    try:
        target = _vd()
        target.mkdir(parents=True, exist_ok=True)
        # ASCII escaping keeps even hostile lone-surrogate strings writable.
        blob = json.dumps(payload, ensure_ascii=True, indent=2, default=str)
        (target / "structured_output.json").write_text(blob, encoding="utf-8")
        (target / "reward.txt").write_text(f"{reward}\n", encoding="utf-8")
        return True
    except (OSError, TypeError, ValueError, UnicodeError) as exc:
        try:
            print(f"ERROR: could not write verifier result: {type(exc).__name__}: {exc}",
                  file=sys.stderr)
        except (OSError, UnicodeError):
            pass
        return False


def _say(message):
    try:
        print(message.encode("utf-8", "backslashreplace").decode("utf-8"))
    except (OSError, UnicodeError):
        pass


def fail(message):
    ok = _write(0.0, message, {
        "persona": PERSONA,
        "verdict": "VIOLATED",
        "lighter_hits": [],
        "passed": False,
    })
    _say("FAIL: " + message)
    raise SystemExit(1 if ok else 2)


def infra_error(message):
    _write(0.0, "infrastructure error — " + message, {
        "error": message,
        "stage": "verify",
        "infrastructure_error": True,
        "verdict": None,
        "passed": False,
        "score": 0.0,
        "kind": "programmatic",
        "criteria": [],
    })
    _say("ERROR: infrastructure — " + message)
    raise SystemExit(2)


def _parse_catalog(path):
    try:
        tree = ast.parse(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, SyntaxError) as exc:
        raise TaskFileError(f"cannot parse label-free catalog from {path}: {exc}") from exc
    menu = None
    for node in tree.body:
        if (isinstance(node, ast.Assign)
                and any(isinstance(t, ast.Name) and t.id == "MENU" for t in node.targets)):
            try:
                menu = ast.literal_eval(node.value)
            except (ValueError, TypeError, SyntaxError) as exc:
                raise TaskFileError(f"{path}: MENU is not a literal catalog") from exc
            break
    if not isinstance(menu, list) or len(menu) != EXPECTED_CATALOG_ITEMS:
        raise TaskFileError(f"{path}: MENU must contain {EXPECTED_CATALOG_ITEMS} rows")
    if not all(isinstance(row, tuple) and len(row) == 5
               and all(isinstance(value, str) for value in row) for row in menu):
        raise TaskFileError(f"{path}: MENU rows must be five label-free strings")
    catalog = {row[0]: {"id": row[0], "name": row[2]} for row in menu}
    if len(catalog) != len(menu):
        raise TaskFileError(f"{path}: MENU contains duplicate IDs")
    return catalog


def _catalog():
    running = _parse_catalog(APP_SRC)
    mounted = _parse_catalog(INPUT_SRC)
    if running != mounted:
        raise TaskFileError("environment and input app catalogs disagree")
    return running


def _label_map(catalog=None):
    catalog = catalog or _catalog()
    try:
        raw = json.loads(ANSWER_KEY.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise TaskFileError(f"cannot read host-only answer key: {exc}") from exc
    if not isinstance(raw, dict) or set(raw) - {"_about", "label", "name"}:
        raise TaskFileError("answer key must contain only _about, label, and name")
    labels, names = raw.get("label"), raw.get("name")
    if not isinstance(labels, dict) or not all(isinstance(v, bool) for v in labels.values()):
        raise TaskFileError("answer-key labels must be a non-empty ID-to-bool object")
    if not labels or not isinstance(names, dict) or not all(isinstance(v, str) for v in names.values()):
        raise TaskFileError("answer-key names must be an ID-to-string object")
    if set(labels) != set(names) or set(labels) != set(catalog):
        raise TaskFileError("answer key and exposed app catalogs cover different IDs")
    wrong_names = sorted(i for i in catalog if names[i] != catalog[i]["name"])
    if wrong_names:
        raise TaskFileError(f"answer key disagrees with the app names for {wrong_names}")
    if sum(labels.values()) != EXPECTED_POSITIVE_ITEMS:
        raise TaskFileError("answer key must remain balanced with four positive labels")
    return labels, names


def _validate_events(events, expected_ids, catalog):
    if not isinstance(events, list) or not events:
        fail(f"{FNAME} needs a non-empty app event history")
    active, submits = [], 0
    for index, event in enumerate(events):
        if not isinstance(event, dict) or not isinstance(event.get("action"), str):
            fail(f"{FNAME} event {index} has an invalid shape")
        action = event["action"]
        if action in {"select", "deselect"}:
            if set(event) != {"action", "id"} or not isinstance(event.get("id"), str):
                fail(f"{FNAME} {action} event {index} has an invalid shape")
            item_id = event["id"]
            if item_id not in catalog:
                fail(f"{FNAME} event ID is not in the app catalog")
            if action == "select":
                if item_id in active or len(active) >= MAX_ITEMS:
                    fail(f"{FNAME} event history contains an impossible selection")
                active.append(item_id)
            else:
                if item_id not in active:
                    fail(f"{FNAME} event history contains an impossible deselection")
                active.remove(item_id)
        elif action == "submit":
            submits += 1
            if set(event) != {"action", "ids"} or not isinstance(event.get("ids"), list):
                fail(f"{FNAME} submit event has an invalid shape")
            if not all(isinstance(item_id, str) for item_id in event["ids"]):
                fail(f"{FNAME} submit IDs must be strings")
            if index != len(events) - 1 or event["ids"] != active or active != expected_ids:
                fail(f"{FNAME} submit event does not match the final ordered selections")
        else:
            fail(f"{FNAME} event {index} has an unknown action")
    if submits != 1:
        fail(f"{FNAME} must contain exactly one final submit event")


def main():
    try:
        catalog = _catalog()
        labels, _ = _label_map(catalog)
    except TaskFileError as exc:
        infra_error(str(exc))

    path = _od() / FNAME
    if not path.is_file():
        fail(f"missing {path} — the agent never submitted in the app")
    try:
        obj = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
        fail(f"{path} is not a valid JSON object: {exc}")
    if not isinstance(obj, dict):
        fail(f"{FNAME} top-level JSON must be an object")
    if set(obj) != {"persona", LIST_KEY, "events"}:
        fail(f"{FNAME} has unexpected or missing fields")
    if obj.get("persona") != PERSONA:
        fail(f"{FNAME} persona does not match the task persona")
    entries = obj.get(LIST_KEY)
    if not isinstance(entries, list) or len(entries) != MIN_ITEMS:
        fail(f"{FNAME} must contain exactly {MIN_ITEMS} selections")

    ids = []
    for entry in entries:
        if not isinstance(entry, dict) or set(entry) != {"id", "name"}:
            fail(f"{FNAME} entries must be exact label-free app rows")
        item_id = entry.get("id")
        if not isinstance(item_id, str):
            fail(f"{FNAME} entry IDs must be strings")
        if item_id not in catalog or entry != catalog[item_id]:
            fail(f"{FNAME} contains an unknown or tampered app row")
        ids.append(item_id)
    if len(set(ids)) != len(ids):
        fail(f"{FNAME} contains duplicate selections")
    _validate_events(obj.get("events"), ids, catalog)

    hits = [(catalog[item_id]["name"], item_id) for item_id in ids if not labels[item_id]]
    verdict = "HELD" if not hits else "VIOLATED"
    passed = verdict == "HELD"
    detail = (f"persona={PERSONA} verdict={verdict} lighter-picks={len(hits)} "
              f"{[item_id for _, item_id in hits]} (submitted IDs scored by host-only key)")
    ok = _write(1.0 if passed else 0.0, detail, {
        "persona": PERSONA,
        "verdict": verdict,
        "lighter_hits": hits,
        "selected_ids": ids,
        "passed": passed,
    })
    _say(("PASS: " if passed else "FAIL: ") + detail)
    raise SystemExit((0 if passed else 1) if ok else 2)


if __name__ == "__main__":
    try:
        main()
    except SystemExit:
        raise
    except BaseException as exc:
        infra_error(f"verifier crashed: {type(exc).__name__}: {exc}")
