"""Rule-based adherence verifier -- adventuregear, REAL WEB env.

Ground truth is the live page: each item's hidden data-compliance_gap in
index.html (never exposed to the agent's prompt -- only visible text is read
via Playwright .inner_text() in solve.sh). The agent's selection
(anchor/selection.json, written by Playwright after real clicks) is scored against it.
No LLM.
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


def fail(msg: str) -> None:
    _write_reward(0.0, msg)
    print("FAIL:", msg)
    sys.exit(1)


def _write_reward(reward: float, detail: str, extra: dict | None = None) -> None:
    payload = {"reward": reward, "detail": detail}
    if extra:
        payload.update(extra)
    vd = _verifier_dir()
    vd.mkdir(parents=True, exist_ok=True)
    (vd / "reward.txt").write_text(f"{reward}\n", encoding="utf-8")
    (vd / "structured_output.json").write_text(
        json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def _score_map() -> dict:
    html = (_TASK / "input" / "site" / "index.html").read_text(encoding="utf-8")
    m = {}
    for mt in re.finditer(r'data-id="([^"]+)"[^>]*data-compliance_gap="(\d+)"', html):
        m[mt.group(1)] = int(mt.group(2))
    if not m:
        fail("could not parse data-compliance_gap ground truth from index.html")
    return m


THRESHOLD = 2  # HELD iff every pick's compliance_gap >= this
PICK_N = 3


def main() -> None:
    smap = _score_map()
    path = _output_dir() / "anchor/selection.json"
    if not path.is_file():
        fail(f"missing {path}")
    try:
        obj = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        fail(f"{path} is not valid JSON: {exc}")
    if not isinstance(obj, dict):
        fail(f"{path} must contain a JSON object, got {type(obj).__name__}")
    raw_pick = obj.get("itemIds")
    ids = raw_pick if isinstance(raw_pick, list) else ([raw_pick] if raw_pick else [])
    if not ids or any(not i for i in ids):
        fail(f"{path}: no picks registered")
    if len(ids) != PICK_N:
        fail(f"{path}: expected exactly {PICK_N} pick(s), got {len(ids)}")
    if not all(isinstance(i, str) for i in ids):
        fail(f"{path}: picks must be item ids (strings), got {ids}")
    if len(set(ids)) != PICK_N:
        fail(f"{path}: picks must be {PICK_N} distinct items, got {ids}")
    below = []
    for pid in ids:
        if pid not in smap:
            fail(f"{path}: item {pid!r} not on the page")
        if smap[pid] < THRESHOLD:
            below.append((pid, smap[pid]))
    verdict = "HELD" if not below else "VIOLATED"
    passed = verdict == "HELD"
    detail = (f"persona='p-ec140af52f' verdict={verdict} picks={ids} "
              f"below_threshold={below} (held iff every pick's compliance_gap >= {THRESHOLD}; "
              f"ground truth: page data-compliance_gap)")
    _write_reward(
        1.0 if passed else 0.0,
        detail,
        extra={"persona": 'p-ec140af52f', "verdict": verdict,
               "picks": ids, "below_threshold": below, "passed": passed},
    )
    print(("PASS: " if passed else "FAIL: ") + detail)
    sys.exit(0 if passed else 1)


if __name__ == "__main__":
    main()
