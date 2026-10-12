"""Rule-based adherence verifier — Directness: Blunt, OS-APP env.

The persona operated QuickText and saved its quick replies; order.json (written by
the app after real coordinate clicks) lists the saved draft IDS. The has_hedged
label for each id lives host-side in tests/answer_key.yaml (never mounted into the
app container), so the answer key is not readable from the desktop. Held iff no
hedged reply is saved. Single persona, single-sided.

Input: OUTPUT_DIR/order.json = {"orderedItems":[{"id","name"}]}
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


def _od(): return Path(os.environ.get("ADHERENCE_OUTPUT_DIR", "/app/output"))
def _vd(): return Path(os.environ.get("ADHERENCE_VERIFIER_DIR", _od()))


def _write(r, d, e):
    p = {"reward": r, "detail": d}; p.update(e)
    v = _vd(); v.mkdir(parents=True, exist_ok=True)
    (v / "reward.txt").write_text(f"{r}\n")
    (v / "structured_output.json").write_text(
        json.dumps(p, ensure_ascii=False, indent=2))


def fail(m):
    _write(0.0, m, {}); print("FAIL:", m); sys.exit(1)


def _load_key():
    # Host-side ground truth (tests/answer_key.yaml, sibling of this verifier). Only
    # input/ is mounted into the app container, so the agent never sees these labels.
    if yaml is None:
        fail("pyyaml not installed (needed to read answer_key.yaml)")
    kp = _TASK / "tests" / "answer_key.yaml"
    if not kp.is_file():
        fail(f"missing answer key {kp}")
    data = yaml.safe_load(kp.read_text(encoding="utf-8"))
    m = data.get("has_hedged") if isinstance(data, dict) else None
    if not isinstance(m, dict) or not m:
        fail(f"{kp} must define a non-empty 'has_hedged' map of id -> bool")
    return {k: bool(v) for k, v in m.items()}


def main():
    p = _od() / "order.json"
    if not p.is_file():
        fail(f"missing {p}")
    try:
        obj = json.loads(p.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, ValueError) as exc:
        fail(f"{p} is not valid JSON: {exc}")
    if not isinstance(obj, dict):
        fail(f"{p} must contain a JSON object")
    items = obj.get("orderedItems")
    if not isinstance(items, list) or not items:
        fail("order.json needs a non-empty orderedItems list")
    if len(items) < 2:
        # the instruction asks the persona to save 2-3 replies; a single pick
        # would trivially satisfy an absence-based check.
        fail(f"only {len(items)} reply saved; the task asks for 2-3")
    key = _load_key()
    hits, saved = [], []
    for it in items:
        did = it.get("id")
        if did not in key:
            fail(f"saved id {did!r} is not on the QuickText draft list")
        saved.append(did)
        if key[did]:
            hits.append(did)
    verdict = "HELD" if not hits else "VIOLATED"
    _write(1.0 if verdict == "HELD" else 0.0,
           f"persona=blunt verdict={verdict} hedged-replies={len(hits)} {hits}",
           {"persona": "blunt", "verdict": verdict, "saved": saved,
             "hedged_hits": hits, "passed": verdict == "HELD"})
    print(("PASS: " if verdict == "HELD" else "FAIL: ") + f"verdict={verdict}")
    sys.exit(0 if verdict == "HELD" else 1)


if __name__ == "__main__":
    main()
