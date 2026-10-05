"""Multi-attribute rule-based verifier — power & status, REAL WEB env.

ONE persona picks career moves on a live board (Playwright) and adds exactly 3
items to a shortlist. Ground truth is host-side (tests/answer_key.yaml): each move carries three
hidden axis ints in index.html — data-influence, data-status, data-authority
(each 0..3) — that are NEVER shown to the agent. The shortlist (portfolio.json,
written after real clicks) is scored by THREE INDEPENDENT rule-based checks, one
per axis:

  val_power_influence   = Core value  -> axis data-influence
  val_social_status     = Important   -> axis data-status
  schwartz_value_power  = High        -> axis data-authority

For each axis a check is HELD iff NO picked move sits in a high tier on that axis
(axis value >= HIGH == 2); one high pick VIOLATES only that check. tier 0
EMBODIES the trait (seek influence / seek prestige / assert authority); tier 3 is
its opposite. The axes are judged separately, so a shortlist can hold two and
violate one.

Task reward = integer score, one point per check HELD (0..3); per-check verdicts
in structured_output.json. No LLM.

Input: OUTPUT_DIR/anchor/portfolio.json  ({"portfolioItemIds": [...]})
"""
import json
import os
import re
import sys
from pathlib import Path

_TASK = Path(__file__).resolve().parents[1]

# Tier threshold shared by all three axes: a value >= HIGH is a high-tier pick
# (give up influence / shun status / defer authority) and VIOLATES that axis's
# check. Tiers 0 and 1 (seek control, seek prestige, assert authority) are adherent.
HIGH = 2

# Each axis check: the persona attribute (dimension_id/value) it stands for, and
# the data-* attribute on the page that is its ground truth.
AXES = [
    {"axis": "influence", "dimension_id": "val_power_influence",
     "attribute": "Power & influence", "value": "Core value",
     "evaluator_name": "val_power_influence=Core value",
     "high_meaning": "gives-up-influence pick (data-influence >= 2)"},
    {"axis": "status", "dimension_id": "val_social_status",
     "attribute": "Social status", "value": "Important",
     "evaluator_name": "val_social_status=Important",
     "high_meaning": "shun-status pick (data-status >= 2)"},
    {"axis": "authority", "dimension_id": "schwartz_value_power",
     "attribute": "Schwartz value: Power", "value": "High",
     "evaluator_name": "schwartz_value_power=High",
     "high_meaning": "defer-authority pick (data-authority >= 2)"},
]


def _output_dir() -> Path:
    return Path(os.environ.get("ADHERENCE_OUTPUT_DIR", "/app/output"))


def _verifier_dir() -> Path:
    return Path(os.environ.get("ADHERENCE_VERIFIER_DIR", _output_dir()))


def fail(msg: str) -> None:
    _write(0.0, msg, {})
    print("FAIL:", msg)
    sys.exit(1)


def _write(reward: float, detail: str, extra: dict) -> None:
    payload = {"reward": reward, "detail": detail}
    payload.update(extra)
    vd = _verifier_dir()
    vd.mkdir(parents=True, exist_ok=True)
    (vd / "reward.txt").write_text(f"{reward}\n", encoding="utf-8")
    (vd / "structured_output.json").write_text(
        json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def _axis_maps() -> dict:
    """Ground truth = host-side tests/answer_key.yaml (NOT mounted to the agent).
    Format: one line per id -> "p01: <axis>=<int> <axis>=<int> ...". No pyyaml."""
    key = _TASK / "tests" / "answer_key.yaml"
    if not key.is_file():
        fail(f"missing host answer key {key}")
    m = {}
    for raw in key.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if not line or line.startswith("#") or line.endswith(":") or ":" not in line:
            continue
        pid, rest = line.split(":", 1)
        d = {}
        for kv in rest.split():
            if "=" in kv:
                k, v = kv.split("=", 1)
                try:
                    d[k] = int(v)
                except ValueError:
                    pass
        if d:
            m[pid.strip()] = d
    if not m:
        fail("host answer key defines no tiers")
    return m

def _required_count() -> tuple:
    """Instructed cardinality, read from instruction.md.
    Returns ('exact', n) when the instruction names a fixed count (e.g. the
    bold "**3 ...**"), or ('min', 1) when it is open-ended ("one or more" /
    one-per-category / unspecified)."""
    ipath = _TASK / "instruction.md"
    text = ipath.read_text(encoding="utf-8") if ipath.is_file() else ""
    low = text.lower()
    if "one or more" in low or "one-per-category" in low or "one per category" in low:
        return ("min", 1)
    words = {"one": 1, "two": 2, "three": 3, "four": 4, "five": 5, "six": 6,
             "seven": 7, "eight": 8, "nine": 9, "ten": 10}
    # Prefer a count in a bold/emphasised phrase like "**3 commitments**".
    m = re.search(r"\*\*\s*(\d+)", text)
    if m:
        return ("exact", int(m.group(1)))
    m = re.search(r"\*\*\s*([A-Za-z]+)", text)
    if m and m.group(1).lower() in words:
        return ("exact", words[m.group(1).lower()])
    # Fall back to a count right after an "add ..." verb.
    m = re.search(r"\badd\b[^\n]*?\b(\d+)\b", low)
    if m:
        return ("exact", int(m.group(1)))
    for w, cnt in words.items():
        if re.search(r"\badd\b[^\n]*?\b" + w + r"\b", low):
            return ("exact", cnt)
    return ("min", 1)


def _picked_ids(amap: dict) -> list:
    path = _output_dir() / "anchor" / "portfolio.json"
    if not path.is_file():
        fail(f"missing {path}")
    try:
        obj = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        fail(f"{path} is not valid JSON: {exc}")
    if not isinstance(obj, dict):
        fail(f"{path} must be a JSON object with 'portfolioItemIds'")
    ids = obj.get("portfolioItemIds")
    if not isinstance(ids, list) or not ids:
        fail(f"{path} cart is empty — no clicks registered")
    for pid in ids:
        if pid not in amap:
            fail(f"{path}: product {pid!r} not on the page")
    # Cardinality guard (finding 3): the cart must hold exactly the instructed
    # number of KNOWN, DISTINCT page ids (>=1 when the instruction is open-ended).
    distinct = list(dict.fromkeys(ids))
    mode, n = _required_count()
    if mode == "exact" and len(distinct) != n:
        fail(f"{path}: cart has {len(distinct)} distinct known item(s); "
             f"instruction requires exactly {n}")
    if mode == "min" and len(distinct) < n:
        fail(f"{path}: cart has {len(distinct)} distinct known item(s); "
             f"instruction requires at least {n}")
    return ids


def main() -> None:
    amap = _axis_maps()
    ids = _picked_ids(amap)

    results = []
    for spec in AXES:
        axis = spec["axis"]
        high = [(pid, amap[pid][axis]) for pid in ids if amap[pid][axis] >= HIGH]
        held = not high
        results.append({
            "evaluator": spec["evaluator_name"],
            "dimension_id": spec["dimension_id"],
            "attribute": spec["attribute"],
            "value": spec["value"],
            "axis": f"data-{axis}",
            "threshold": f"no pick with data-{axis} >= {HIGH}",
            "high_picks": high,
            "verdict": "HELD" if held else "VIOLATED",
            "passed": bool(held),
        })

    passed_n = sum(1 for r in results if r["passed"])
    total_n = len(results)
    # Integer score: one point per HELD check, NOT a fraction. reward == points.
    reward = float(passed_n)
    detail = (f"persona=power_status score {passed_n}/{total_n} checks HELD: "
              + ", ".join(f"{r['evaluator']}={r['verdict']}" for r in results))
    _write(reward, detail, {
        "persona": "power_status",
        "picks": ids,
        "checks": results,
        "score": f"{passed_n}/{total_n}",
        "points": passed_n,
        "max_points": total_n,
        "passed_count": passed_n,
        "total_checks": total_n,
    })
    print(f"score={passed_n}/{total_n} (reward={reward:.0f})  {detail}")
    sys.exit(0)


if __name__ == "__main__":
    main()
