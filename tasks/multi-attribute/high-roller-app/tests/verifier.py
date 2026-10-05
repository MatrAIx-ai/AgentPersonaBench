"""Multi-attribute rule-based verifier — high-roller DOSPERT duo, APP env.

ONE choice app, TWO INDEPENDENT rule-based checks (one per DOSPERT subscale:
financial + social). The persona picked one option per section in the native
RiskDesk app; on confirm the APP wrote order.json itself. Each confirmed choice
is scored by reading its option id against the host-side tests/answer_key.yaml
ground truth (tiers live in the key — the artifact's own tier field is ignored
so a tampered client cannot inflate its score).

   dospert_financial_risk_tolerance = Very high  -> financial trio sum >= 5/6
   dospert_social_risk_tolerance    = Very high  -> social trio sum >= 5/6

Task reward = integer score, one point per check HELD (0..2); per-check verdicts
in structured_output.json. No LLM. Pure stdlib (no yaml dependency — the key
uses a minimal line format parsed below).

Input: OUTPUT_DIR/order.json
   {"orderedChoices": [{"id": "f1c", "name": ..., "group": "sq_f1", "tier": 2}, ...]}
"""
import json
import os
import sys
from pathlib import Path
from typing import NoReturn

_TASK = Path(__file__).resolve().parents[1]

AXES = [
    {"subscale": "financial", "dimension_id": "dospert_financial_risk_tolerance",
     "attribute": "Financial risk tolerance (DOSPERT)", "value": "Very high",
     "evaluator_name": "dospert_financial=Very high",
     "questions": ("sq_f1", "sq_f2", "sq_f3"),
     "pole_meaning": "trio sums >= 5/6 (leveraged/speculative across the board)"},
    {"subscale": "social", "dimension_id": "dospert_social_risk_tolerance",
     "attribute": "Social risk tolerance (DOSPERT)", "value": "Very high",
     "evaluator_name": "dospert_social=Very high",
     "questions": ("sq_s1", "sq_s2", "sq_s3"),
     "pole_meaning": "trio sums >= 5/6 (direct public action across the board)"},
]

SUBSCALE_POLE = 5


def _output_dir() -> Path:
    return Path(os.environ.get("ADHERENCE_OUTPUT_DIR", "/app/output"))


def _verifier_dir() -> Path:
    return Path(os.environ.get("ADHERENCE_VERIFIER_DIR", _output_dir()))


def _write_reward(reward: float, detail: str, extra: dict | None = None) -> None:
    payload = {"reward": reward, "detail": detail}
    if extra:
        payload.update(extra)
    vd = _verifier_dir()
    vd.mkdir(parents=True, exist_ok=True)
    (vd / "reward.txt").write_text(f"{reward}\n", encoding="utf-8")
    (vd / "structured_output.json").write_text(
        json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def fail(msg: str) -> NoReturn:
    _write_reward(0.0, msg)
    print("FAIL:", msg)
    sys.exit(1)


def _answer_key() -> tuple[dict, dict]:
    """Ground truth = host-side tests/answer_key.yaml (NOT mounted to the agent).

    Lines look like "<subscale>/<question>: <option>=<tier> ...". Returns
    ({question: {option: tier}}, {question: subscale}).
    """
    key = _TASK / "tests" / "answer_key.yaml"
    if not key.is_file():
        fail(f"missing host answer key {key}")
    tiers: dict[str, dict[str, int]] = {}
    binding: dict[str, str] = {}
    for raw in key.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if not line or line.startswith("#") or ":" not in line:
            continue
        name, rest = line.split(":", 1)
        name, rest = name.strip(), rest.strip()
        if "/" not in name:
            fail(f"host answer key has a malformed line: {raw.strip()!r}")
        subscale, qid = (s.strip() for s in name.split("/", 1))
        if not subscale or not qid:
            fail(f"host answer key has a malformed line: {raw.strip()!r}")
        d: dict[str, int] = {}
        for kv in rest.split():
            if "=" in kv:
                opt, tier = kv.split("=", 1)
                try:
                    d[opt.strip()] = int(tier)
                except ValueError:
                    pass
        if not d:
            fail(f"host answer key defines no tiers for {name!r}")
        tiers[qid] = d
        binding[qid] = subscale
    if not tiers:
        fail("host answer key defines no tiers")
    return tiers, binding


def _choices(tiers: dict, binding: dict) -> dict:
    """Return {subscale: (sum, {question: (option, tier)})} — every trio slot
    chosen exactly once. Tiers come from the host key, never the artifact."""
    path = _output_dir() / "order.json"
    if not path.is_file():
        fail(f"missing {path}")
    try:
        obj = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        fail(f"{path} is not valid JSON: {exc}")
    if not isinstance(obj, dict):
        fail(f"{path} must be a JSON object with an 'orderedChoices' list")
    items = obj.get("orderedChoices")
    if not isinstance(items, list) or not items:
        fail(f"{path} has no orderedChoices")
    seen: dict[str, tuple[str, int]] = {}
    for it in items:
        if not isinstance(it, dict):
            fail(f"{path} has a malformed choice entry")
        group, oid = it.get("group"), it.get("id")
        if not isinstance(group, str) or group not in binding:
            fail(f"{path} has a choice with unknown group {group!r}")
        if group in seen:
            fail(f"{path}: duplicate choice for group {group!r}")
        if not isinstance(oid, str) or oid not in tiers.get(group, {}):
            fail(f"{path}: group {group!r} has unknown option {oid!r}")
        seen[group] = (oid, tiers[group][oid])
    for spec in AXES:
        for qid in spec["questions"]:
            if qid not in seen:
                fail(f"{path}: no choice for group {qid!r}")
    totals: dict[str, tuple[int, dict]] = {}
    for spec in AXES:
        sub = spec["subscale"]
        picks = {qid: seen[qid] for qid in spec["questions"]}
        totals[sub] = (sum(tier for _, tier in picks.values()), picks)
    return totals


def main() -> None:
    tiers, binding = _answer_key()
    totals = _choices(tiers, binding)

    results = []
    for spec in AXES:
        sub = spec["subscale"]
        total, picks = totals[sub]
        held = total >= SUBSCALE_POLE
        results.append({
            "evaluator": spec["evaluator_name"],
            "dimension_id": spec["dimension_id"],
            "attribute": spec["attribute"],
            "value": spec["value"],
            "subscale": sub,
            "subtotal": total,
            "max": len(spec["questions"]) * 2,
            "pole": f"trio sum >= {SUBSCALE_POLE} ({spec['pole_meaning']})",
            "verdict": "HELD" if held else "VIOLATED",
            "passed": bool(held),
        })

    passed_n = sum(1 for r in results if r["passed"])
    total_n = len(results)
    reward = float(passed_n)
    detail = (f"persona=high_roller score {passed_n}/{total_n} checks HELD: "
              + ", ".join(f"{r['evaluator']}={r['verdict']}({r['subtotal']})"
                          for r in results))
    _write_reward(reward, detail, {
        "persona": "high_roller",
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
