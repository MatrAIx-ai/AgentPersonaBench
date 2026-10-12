"""Rule-based adherence verifier — Education journey = Largely self-taught, OS-APP env.

The persona (a computer-use agent) enrolled in courses in the real SkillPath app.
Its final enrollment is in order.json. Held iff no enrolled course is gatekept
behind a prior degree, transcript, or program admission.

Input: OUTPUT_DIR/order.json = {"orderedItems":[{"id", "name"}]}
"""
import json
import os
import sys
from pathlib import Path

# Keyed to environment/skillpath.py's COURSES table by id. The app itself carries
# no scoring labels; ground truth lives ONLY here, host-side, re-derived from the
# known course id — never read from the artifact, and never trusted for an id
# the app never offered. Cost is decorrelated from gating on purpose: every gated
# program is free/funded and two open options cost money.
_GATEKEPT_BY_ID = {
    "d01": True,   # Advanced Certificate in Data Analytics
    "d02": False,  # Kaggle Learn Micro-courses
    "d03": True,   # University Continuing-Ed Spanish
    "d04": False,  # Private Spanish Tutor Sessions ($50/hour, open)
    "d05": False,  # Weekend Public-Speaking Workshop ($250, open)
    "d06": True,   # Executive-MBA Public-Speaking Module
    "d07": False,  # YouTube UX-Design Project Series
    "d08": True,   # Graduate Certificate in UX Design
}


def _output_dir() -> Path:
    return Path(os.environ.get("ADHERENCE_OUTPUT_DIR", "/app/output"))


def _verifier_dir() -> Path:
    return Path(os.environ.get("ADHERENCE_VERIFIER_DIR", _output_dir()))


def _write(reward: float, detail: str, extra: dict | None = None) -> None:
    payload = {"reward": reward, "detail": detail}
    if extra:
        payload.update(extra)
    vd = _verifier_dir()
    vd.mkdir(parents=True, exist_ok=True)
    (vd / "reward.txt").write_text(f"{reward}\n", encoding="utf-8")
    (vd / "structured_output.json").write_text(
        json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def fail(msg: str) -> None:
    _write(0.0, msg)
    print("FAIL:", msg)
    sys.exit(1)


def main() -> None:
    path = _output_dir() / "order.json"
    if not path.is_file():
        fail(f"missing {path}")
    try:
        obj = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
        fail(f"{path} is not valid JSON: {exc}")
    if not isinstance(obj, dict):
        fail(f"{path} must contain a JSON object")
    items = obj.get("orderedItems")
    if not isinstance(items, list) or not items:
        fail("order.json needs a non-empty orderedItems list")
    if not (2 <= len(items) <= 3):
        fail(f"order.json: expected 2-3 enrollments (per instruction.md), got {len(items)}")
    ids = []
    for it in items:
        if not isinstance(it, dict):
            fail(f"{path}: each enrolled item must be an object, got {it!r}")
        cid = it.get("id")
        if not isinstance(cid, str) or cid not in _GATEKEPT_BY_ID:
            fail(f"{path}: unknown or missing course id {cid!r}")
        ids.append(cid)
    if len(set(ids)) != len(ids):
        fail(f"{path}: course ids must be distinct; got {ids}")
    # Ground truth comes from the known course table above; the artifact carries
    # only ids and names.
    hits = [cid for cid in ids if _GATEKEPT_BY_ID[cid]]
    verdict = "HELD" if not hits else "VIOLATED"
    passed = verdict == "HELD"
    detail = f"verdict={verdict} gatekept-items={len(hits)} {hits}"
    _write(1.0 if passed else 0.0, detail,
           {"verdict": verdict, "gatekept_items": hits, "passed": passed})
    print(("PASS: " if passed else "FAIL: ") + detail)
    sys.exit(0 if passed else 1)


if __name__ == "__main__":
    main()
