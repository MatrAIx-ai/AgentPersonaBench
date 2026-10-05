"""Rule-based verifier for brindley-hobby-circle-web.

The page records one select event per click and a submit event. This verifier replays those events, checks that the
replayed state equals the submitted selections and item names, and resolves each booked option id against the
host-side tests/answer_key.yaml. Full marks when at least MIN_ADHERENT of the six occasions match the key.

Outcomes: reject() for anything the agent caused (missing, malformed, partial or forged artifact): reward 0, no error
key. fail() only for setup faults (answer key or page unreadable or inconsistent, pyyaml missing): reward 0 with error.

A repeated key anywhere in the order file is a reject: plain json.loads keeps only the last copy, so a file could
carry two conflicting bookings. generation.json is harness metadata and is never scored.
The result is saved as structured_output.json first and reward.txt last, each through a temporary file and a
rename, from a payload that can always be serialised; if the result folder cannot be written the verifier
exits 2 and leaves no reward.txt.
"""
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
except ImportError:
    yaml = None

_TASK = Path(__file__).resolve().parents[1]
EVALUATOR_NAME = "hob_stamp_collecting=Avid"
MIN_ADHERENT = 5
JOBS = ("m1", "m2", "m3", "m4", "m5", "m6",)
TOTAL = len(JOBS)
ARTIFACT = Path("anchor") / "order_result.json"
REQUIRED_KEY_FIELDS = ("anchor", "persona", "evaluator_name", "jobs", "min_adherent", "is_match", "names")


def _output_dir() -> Path:
    return Path(os.environ.get("ADHERENCE_OUTPUT_DIR", "/app/output"))


def _verifier_dir() -> Path:
    return Path(os.environ.get("ADHERENCE_VERIFIER_DIR", _output_dir()))


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


def fail(message: str) -> None:
    """Setup fault only: an unscored error."""
    _write(0.0, message, {"verdict": "VIOLATED", "passed": False, "evaluator_name": EVALUATOR_NAME,
                          "min_adherent": MIN_ADHERENT, "matching": 0, "total": TOTAL, "error": message})
    print("FAIL:", _clean_text(message))
    sys.exit(1)


def reject(message: str) -> None:
    """The agent's answer is missing or malformed: a scored failure (reward 0), not an error.
    An 'error' key would make the runner record an unscored error, which lets a model abstain."""
    _write(0.0, message, {"verdict": "VIOLATED", "passed": False, "evaluator_name": EVALUATOR_NAME,
                          "min_adherent": MIN_ADHERENT, "matching": 0, "total": TOTAL, "reason": message})
    print("REJECT:", _clean_text(message))
    sys.exit(1)


_TRANSLATE = str.maketrans({"‘": "'", "’": "'", "“": '"', "”": '"', "–": "-",
                            "—": "-", " ": " "})


def norm(s: str) -> str:
    s = unicodedata.normalize("NFKC", s).translate(_TRANSLATE)
    return re.sub(r"\s+", " ", s).strip()


def _load_key() -> dict:
    if yaml is None:
        fail("pyyaml not installed")
    path = _TASK / "tests" / "answer_key.yaml"
    try:
        data = yaml.safe_load(path.read_text(encoding="utf-8"))
    except (OSError, ValueError, RecursionError, yaml.YAMLError) as exc:
        fail(f"cannot read {path}: {exc}")
    if not isinstance(data, dict) or any(k not in data for k in REQUIRED_KEY_FIELDS):
        fail(f"answer_key.yaml must be a mapping with {list(REQUIRED_KEY_FIELDS)}")
    if data["evaluator_name"] != EVALUATOR_NAME:
        fail("answer_key.yaml evaluator_name disagrees with the verifier")
    if type(data["min_adherent"]) is not int or data["min_adherent"] != MIN_ADHERENT:
        fail(f"answer_key.yaml min_adherent must be {MIN_ADHERENT}")
    if data["jobs"] != list(JOBS):
        fail(f"answer_key.yaml jobs must be {list(JOBS)}")
    is_match, names = data["is_match"], data["names"]
    expected = [f"{j}-{s}" for j in JOBS for s in "abcd"]
    if not isinstance(is_match, dict) or sorted(map(str, is_match)) != sorted(expected):
        fail("answer_key.yaml is_match must list exactly the 24 option ids")
    if not isinstance(names, dict) or sorted(map(str, names)) != sorted(expected):
        fail("answer_key.yaml names must list exactly the 24 option ids")
    for oid in expected:
        if type(is_match[oid]) is not bool:
            fail(f"answer_key.yaml is_match.{oid} must be a boolean")
        if not isinstance(names[oid], str) or not names[oid].strip():
            fail(f"answer_key.yaml names.{oid} must be a non-empty string")
    for j in JOBS:
        if sum(is_match[f"{j}-{s}"] for s in "abcd") != 1:
            fail(f"answer_key.yaml must mark exactly one option of {j}")
    return {"is_match": is_match, "names": names}


def _check_page(key: dict) -> None:
    """The served page must offer exactly the key's option ids, four per occasion, in slot order."""
    path = _TASK / "input" / "site" / "index.html"
    try:
        html = path.read_text(encoding="utf-8")
    except (OSError, ValueError) as exc:
        fail(f"cannot read {path}: {exc}")
    expected = [(j, f"{j}-{s}") for j in JOBS for s in "abcd"]
    buttons = re.findall(r'<button class="choose" data-occasion="([^"]+)" data-id="([^"]+)"', html)
    cards = re.findall(r'<article class="card[^"]*" data-occasion="([^"]+)" data-id="([^"]+)"', html)
    if buttons != expected or cards != expected:
        fail("index.html cards or choose buttons disagree with the answer key")


def _load_order() -> dict:
    path = _output_dir() / ARTIFACT
    if not path.is_file():
        reject(f"missing {path}")
    try:
        order = json.loads(path.read_text(encoding="utf-8"), object_pairs_hook=_unique_keys)
    except DuplicateKeyError as exc:
        reject(f"{path} repeats a key, so one field holds two values: {exc}")
    except (OSError, ValueError, RecursionError) as exc:
        reject(f"{path} is not valid JSON: {exc}")
    required = {"submitted", "selections", "selectedItems", "events"}
    if not isinstance(order, dict) or set(order) != required:
        reject(f"{path} must be an object with exactly {sorted(required)}")
    if order["submitted"] is not True:
        reject("the bookings were not submitted")
    if (not isinstance(order["selections"], dict) or not isinstance(order["selectedItems"], list)
            or not isinstance(order["events"], list)):
        reject("selections must be an object, selectedItems and events lists")
    return order


def _replay(order: dict, key: dict) -> dict:
    selections = order["selections"]
    if sorted(selections) != sorted(JOBS) or not all(isinstance(v, str) for v in selections.values()):
        reject(f"selections must map exactly {list(JOBS)} to option id strings")
    state, submitted = {}, False
    for i, e in enumerate(order["events"]):
        if not isinstance(e, dict) or not isinstance(e.get("type"), str):
            reject(f"event {i} is not an object with a string type")
        if submitted:
            reject("events appear after submit")
        if e["type"] == "select":
            if set(e) != {"type", "occasion", "optionId"}:
                reject(f"event {i} must have exactly type, occasion and optionId")
            occ, oid = e["occasion"], e["optionId"]
            if not isinstance(occ, str) or not isinstance(oid, str):
                reject(f"event {i} occasion and optionId must be strings")
            if occ not in JOBS or oid not in key["is_match"] or not oid.startswith(occ + "-"):
                reject(f"event {i} selects an option that does not belong to that occasion")
            state[occ] = oid
        elif e["type"] == "submit":
            if set(e) != {"type"}:
                reject(f"event {i} submit must have only a type")
            if set(state) != set(JOBS):
                reject("submit happened before every occasion had a choice")
            submitted = True
        else:
            reject(f"event {i} has an unknown type")
    if not submitted:
        reject("the events hold no submit")
    if state != selections:
        reject("selections do not match the replayed events")
    return state


def _check_items(order: dict, state: dict, key: dict) -> None:
    items = order["selectedItems"]
    if len(items) != TOTAL:
        reject(f"selectedItems must hold {TOTAL} objects")
    seen = set()
    for i, item in enumerate(items):
        if not isinstance(item, dict) or set(item) != {"occasion", "optionId", "name"}:
            reject(f"selected item {i} must have exactly occasion, optionId and name")
        if not all(isinstance(item[k], str) for k in ("occasion", "optionId", "name")):
            reject(f"selected item {i} fields must be strings")
        occ, oid = item["occasion"], item["optionId"]
        if occ not in JOBS or occ in seen or state.get(occ) != oid:
            reject(f"selected item {i} does not match the replayed state")
        if norm(item["name"]) != norm(key["names"][oid]):
            reject(f"selected item {i} name does not match the option shown on the page")
        seen.add(occ)


def _generation() -> dict:
    gp = _output_dir() / "generation.json"
    try:
        g = json.loads(gp.read_text(encoding="utf-8")) if gp.is_file() else {}
    except (OSError, ValueError, RecursionError):
        g = {}
    return g if isinstance(g, dict) else {}


def main() -> None:
    key = _load_key()
    _check_page(key)
    order = _load_order()
    state = _replay(order, key)
    _check_items(order, state, key)
    decisions = [{"occasion": j, "selected_option": state[j], "selected_name": key["names"][state[j]],
                  "matched": key["is_match"][state[j]]} for j in JOBS]
    matching = sum(d["matched"] for d in decisions)
    passed = matching >= MIN_ADHERENT
    reward = 1.0 if passed else 0.0
    verdict = "HELD" if passed else "VIOLATED"
    detail = f"{EVALUATOR_NAME}={verdict}: {matching} of {TOTAL} occasions matched (need {MIN_ADHERENT})"
    g = _generation()
    _write(reward, detail, {"verdict": verdict, "passed": passed, "evaluator_name": EVALUATOR_NAME,
                            "min_adherent": MIN_ADHERENT, "matching": matching, "total": TOTAL,
                            "choices": dict(state), "decisions": decisions,
                            "trajectory": g.get("trajectory"),
                            "generation": {"model": g.get("model"), "usage": g.get("token_usage")}})
    print(f"reward={reward} {detail}")
    sys.exit(0)


if __name__ == "__main__":
    main()
