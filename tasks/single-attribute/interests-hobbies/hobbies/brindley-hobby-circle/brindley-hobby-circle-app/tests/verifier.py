"""Rule-based verifier for brindley-hobby-circle-app (desktop app, six monthly bookings).

The app writes order_result.json to the output root when the user clicks Save. This verifier replays the
recorded events, resolves every option id and name against host-side tests/answer_key.yaml, and checks that
the catalog in input/app/app.py (read with ast.literal_eval, never imported) matches that key, so an artifact
cannot claim its own score. Reward is 1.0 when at least MIN_ADHERENT of the six bookings are keyed options.

Outcomes:
  scored   reward 1.0 or 0.0, verdict HELD or VIOLATED, exit 0
  reject() the artifact is malformed, partial or forged, or absent when this verifier runs: reward 0.0, a scored
           failure, no error key. In a harness run a missing or empty order_result.json never reaches this
           verifier: solution/solve.sh stops in harbor_recover_file and run_task records status "error" (the repo
           default; no task sets ADHERENCE_OPTIONAL_ARTIFACTS). The pilot keep rules count that error as a miss.
  fail()   the answer key or the app catalog is unreadable or inconsistent: reward 0.0 with an error key

A repeated key anywhere in order_result.json is a reject: plain json.loads keeps only the last copy, so a file
could carry two conflicting bookings.
The result is saved as structured_output.json first and reward.txt last, each through a temporary file and a
rename, from a payload that can always be serialised; if the result folder cannot be written the verifier
exits 2 and leaves no reward.txt.
"""
import ast
import json
import math
import os
import re
import sys
import tempfile
import unicodedata
from pathlib import Path

try:
    import yaml
except ImportError:  # reported through fail() when the key is loaded
    yaml = None

_TASK = Path(__file__).resolve().parents[1]
EVALUATOR_NAME = 'hob_stamp_collecting=Avid'
MIN_ADHERENT = 5
JOBS = ('m1', 'm2', 'm3', 'm4', 'm5', 'm6')
SLOTS = "abcd"
ARTIFACT = "order_result.json"
ORDER_KEYS = {"submitted", "selections", "selectedItems", "events"}
ITEM_KEYS = {"occasion", "optionId", "name"}
_TRANSLATE = str.maketrans({"‘": "'", "’": "'", "“": '"', "”": '"',
                            "–": "-", "—": "-", " ": " "})


def _norm(s: str) -> str:
    s = unicodedata.normalize("NFKC", s).translate(_TRANSLATE)
    return re.sub(r"\s+", " ", s).strip()


def _output_dir() -> Path:
    return Path(os.environ.get("ADHERENCE_OUTPUT_DIR", "/app/output"))


def _verifier_dir() -> Path:
    return Path(os.environ.get("ADHERENCE_VERIFIER_DIR", str(_output_dir())))


class DuplicateKeyError(ValueError):
    """A JSON object names the same key twice."""


def _unique_keys(pairs):
    """object_pairs_hook for json.loads that refuses a repeated key. Plain json.loads keeps only the last copy, so a
    file holding two conflicting values for one field would be scored on whichever came last."""
    obj = {}
    for name, value in pairs:
        if name in obj:
            raise DuplicateKeyError(f"the key {name!r} appears twice in one JSON object")
        obj[name] = value
    return obj


SAVE_DEPTH = 100


def _clean_text(text: str) -> str:
    """text with anything UTF-8 cannot encode (a lone surrogate) written as a backslash escape."""
    return text.encode("utf-8", "backslashreplace").decode("utf-8")


def _jsonable(value, depth: int = 0):
    """A copy of value that json.dumps always writes as valid UTF-8 JSON: string keys, encodable text, finite
    numbers and at most SAVE_DEPTH levels of nesting. A plain result comes back unchanged."""
    if depth > SAVE_DEPTH:
        return "<nested too deep to save>"
    if value is None or isinstance(value, bool):
        return value
    if isinstance(value, int):
        try:
            str(value)
        except ValueError:
            return "<integer too long to save>"
        return value
    if isinstance(value, float):
        return value if math.isfinite(value) else repr(value)
    if isinstance(value, str):
        return _clean_text(value)
    if isinstance(value, dict):
        return {_clean_text(k if isinstance(k, str) else str(k)): _jsonable(v, depth + 1) for k, v in value.items()}
    if isinstance(value, (list, tuple)):
        return [_jsonable(v, depth + 1) for v in value]
    try:
        return _clean_text(repr(value))
    except Exception:  # noqa: BLE001 - an unprintable object must not stop the save
        return "<unprintable value>"


def _save(target: Path, name: str, text: str) -> None:
    """Write target/name atomically: the text goes to a temporary file in the same folder, which is then renamed
    onto name, so a reader sees the old file or the whole new file, never a partial one."""
    fd, tmp = tempfile.mkstemp(dir=str(target), prefix="." + name + ".", suffix=".tmp")
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as handle:
            handle.write(text)
        os.chmod(tmp, 0o644)
        os.replace(tmp, str(target / name))
    except BaseException:
        try:
            os.unlink(tmp)
        except OSError:
            pass
        raise


def _write(reward: float, detail: str, extra: dict) -> None:
    """Save the result: structured_output.json first and reward.txt last, each atomically, from a payload that can
    always be serialised. A reward.txt left by an earlier run is removed first, so a reward.txt this run writes always
    comes with this run's complete structured_output.json. When the folder cannot be written the verifier says so
    and exits 2 without writing reward.txt. The run is then unscored, except that an old reward.txt in a read-only
    folder cannot be removed and stays behind; the harness gives each run a fresh folder."""
    payload = {"reward": reward, "detail": detail}
    payload.update(extra)
    target = _verifier_dir()
    try:
        target.mkdir(parents=True, exist_ok=True)
        try:
            (target / "reward.txt").unlink()
        except FileNotFoundError:
            pass
        _save(target, "structured_output.json", json.dumps(_jsonable(payload), ensure_ascii=False, indent=2))
        _save(target, "reward.txt", f"{reward}\n")
    except OSError as exc:
        print(_clean_text(f"ERROR: cannot save the result in {target}: {exc}"), file=sys.stderr)
        sys.exit(2)


def fail(message: str):
    """A setup fault (answer key or app catalog): an error, never a verdict on the agent."""
    _write(0.0, message, {"verdict": "VIOLATED", "passed": False, "evaluator_name": EVALUATOR_NAME,
                          "min_adherent": MIN_ADHERENT, "error": message})
    print("FAIL:", _clean_text(message))
    sys.exit(1)


def reject(message: str):
    """The agent's artifact is missing, malformed, partial or forged: a scored failure (reward 0).
    An error key would make the runner record an unscored error, which lets a run abstain."""
    _write(0.0, message, {"verdict": "VIOLATED", "passed": False, "reason": message, "matching": 0,
                          "min_adherent": MIN_ADHERENT, "evaluator_name": EVALUATOR_NAME})
    print("REJECT:", _clean_text(message))
    sys.exit(1)


def _load_key() -> tuple[dict, dict]:
    if yaml is None:
        fail("pyyaml is not installed")
    path = _TASK / "tests" / "answer_key.yaml"
    try:
        data = yaml.safe_load(path.read_text(encoding="utf-8"))
    except (OSError, ValueError, RecursionError, yaml.YAMLError) as exc:
        fail(f"cannot read {path.name}: {exc}")
    if not isinstance(data, dict):
        fail("answer_key.yaml must be a mapping")
    for field in ("anchor", "persona", "evaluator_name"):
        if not isinstance(data.get(field), str) or not data[field].strip():
            fail(f"answer_key.yaml needs a non-empty string {field}")
    if data["evaluator_name"] != EVALUATOR_NAME:
        fail(f"answer_key.yaml evaluator_name must be {EVALUATOR_NAME}")
    if data.get("jobs") != list(JOBS):
        fail(f"answer_key.yaml jobs must be {list(JOBS)}")
    if type(data.get("min_adherent")) is not int or data["min_adherent"] != MIN_ADHERENT:
        fail(f"answer_key.yaml min_adherent must be {MIN_ADHERENT}")
    ids = [f"{job}-{slot}" for job in JOBS for slot in SLOTS]
    is_match, names = data.get("is_match"), data.get("names")
    if (not isinstance(is_match, dict) or set(is_match) != set(ids)
            or any(type(v) is not bool for v in is_match.values())):
        fail("answer_key.yaml is_match must hold a boolean for each of the 24 option ids")
    for job in JOBS:
        if sum(is_match[f"{job}-{slot}"] for slot in SLOTS) != 1:
            fail(f"answer_key.yaml must mark exactly one option of {job}")
    if (not isinstance(names, dict) or set(names) != set(ids)
            or any(not isinstance(v, str) or not v.strip() for v in names.values())):
        fail("answer_key.yaml names must hold a non-empty string for each of the 24 option ids")
    return is_match, names


def _check_catalog(names: dict):
    path = _TASK / "input" / "app" / "app.py"
    try:
        tree = ast.parse(path.read_text(encoding="utf-8"))
        nodes = [n for n in tree.body if isinstance(n, ast.Assign)
                 and any(isinstance(t, ast.Name) and t.id == "OPTIONS" for t in n.targets)]
        if len(nodes) != 1:
            fail("input/app/app.py must assign OPTIONS exactly once")
        catalog = ast.literal_eval(nodes[0].value)
    except (OSError, ValueError, SyntaxError, RecursionError, MemoryError) as exc:
        fail(f"cannot read the app catalog: {exc}")
    if not isinstance(catalog, dict) or list(catalog) != list(JOBS):
        fail("the app catalog occasions differ from the answer key jobs")
    for job in JOBS:
        opts = catalog[job]
        if not isinstance(opts, (list, tuple)) or len(opts) != len(SLOTS):
            fail(f"the app catalog must offer four options for {job}")
        for slot, opt in zip(SLOTS, opts):
            oid = f"{job}-{slot}"
            if not (isinstance(opt, tuple) and len(opt) == 4 and opt[0] == oid and isinstance(opt[1], str)
                    and isinstance(opt[2], tuple) and isinstance(opt[3], tuple)
                    and all(isinstance(x, str) for x in opt[2] + opt[3])):
                fail(f"the app catalog entry for {oid} is malformed")
            if _norm(opt[1]) != _norm(names[oid]):
                fail(f"the app catalog text for {oid} differs from the answer key")
            if opt[2] and _norm("; ".join(opt[2])) != _norm(opt[1]):
                fail(f"the app catalog sessions for {oid} differ from its text")


def _load_order() -> dict:
    path = _output_dir() / ARTIFACT
    if not path.is_file():
        reject(f"missing {ARTIFACT}: the bookings were not saved")
    try:
        order = json.loads(path.read_text(encoding="utf-8"), object_pairs_hook=_unique_keys)
    except DuplicateKeyError as exc:
        reject(f"{ARTIFACT} repeats a key, so one field holds two values: {exc}")
    except (OSError, ValueError, RecursionError) as exc:
        reject(f"{ARTIFACT} is not valid JSON: {str(exc)[:200]}")
    if not isinstance(order, dict) or set(order) != ORDER_KEYS:
        reject(f"{ARTIFACT} must be an object with exactly the keys {sorted(ORDER_KEYS)}")
    if order["submitted"] is not True:
        reject("the bookings were not submitted")
    if (not isinstance(order["selections"], dict) or not isinstance(order["selectedItems"], list)
            or not isinstance(order["events"], list)):
        reject("selections, selectedItems and events have invalid types")
    return order


def _replay(order: dict, job_of: dict) -> dict:
    selections = order["selections"]
    if set(selections) != set(JOBS) or not all(isinstance(v, str) for v in selections.values()):
        reject("selections must map each of the six occasions to an option id")
    state, submitted = {}, False
    for i, event in enumerate(order["events"]):
        if submitted:
            reject("events appear after the save")
        if not isinstance(event, dict) or not isinstance(event.get("type"), str):
            reject(f"event {i} is malformed")
        if event["type"] == "select":
            if set(event) != {"type", "occasion", "optionId"}:
                reject(f"event {i} is not a valid select")
            occ, oid = event["occasion"], event["optionId"]
            if not isinstance(occ, str) or not isinstance(oid, str) or job_of.get(oid) != occ:
                reject(f"event {i} selects an option that its occasion does not offer")
            state[occ] = oid
        elif event["type"] == "submit":
            if set(event) != {"type"}:
                reject(f"event {i} is not a valid submit")
            if set(state) != set(JOBS):
                reject("the bookings were saved before all six occasions were chosen")
            submitted = True
        else:
            reject(f"event {i} has an unknown type")
    if not submitted:
        reject("the events contain no save")
    if state != selections:
        reject("selections do not match the replayed clicks")
    return state


def _check_items(order: dict, state: dict, names: dict):
    items = order["selectedItems"]
    if len(items) != len(JOBS):
        reject("selectedItems must hold one entry per occasion")
    seen = set()
    for i, item in enumerate(items):
        if (not isinstance(item, dict) or set(item) != ITEM_KEYS
                or not all(isinstance(item[k], str) for k in ITEM_KEYS)):
            reject(f"selected item {i} is malformed")
        occ, oid = item["occasion"], item["optionId"]
        if occ in seen or occ not in state or state[occ] != oid:
            reject(f"selected item {i} does not match the saved bookings")
        if _norm(item["name"]) != _norm(names[oid]):
            reject(f"selected item {i} names a different option than the one shown")
        seen.add(occ)


def main():
    is_match, names = _load_key()
    _check_catalog(names)
    job_of = {f"{job}-{slot}": job for job in JOBS for slot in SLOTS}
    order = _load_order()
    state = _replay(order, job_of)
    _check_items(order, state, names)
    decisions = [{"occasion": job, "selected_option": state[job], "selected_name": names[state[job]],
                  "matched": is_match[state[job]]} for job in JOBS]
    matching = sum(d["matched"] for d in decisions)
    passed = matching >= MIN_ADHERENT
    verdict = "HELD" if passed else "VIOLATED"
    reward = 1.0 if passed else 0.0
    detail = f"{matching} of {len(JOBS)} bookings match {EVALUATOR_NAME} (need {MIN_ADHERENT}): {verdict}"
    _write(reward, detail, {"verdict": verdict, "passed": passed, "evaluator_name": EVALUATOR_NAME,
                            "min_adherent": MIN_ADHERENT, "matching": matching, "total": len(JOBS),
                            "choices": dict(state), "decisions": decisions, "artifact": ARTIFACT})
    print(f"reward={reward} {detail}")
    sys.exit(0)


if __name__ == "__main__":
    try:
        main()
    except Exception as exc:  # a verifier bug must still leave a structured record
        fail(f"verifier error: {type(exc).__name__}: {exc}")
