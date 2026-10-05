"""Rule-based adherence verifier — Risk-tolerant, OS-APP env.

The persona operated the BullVantage investing app and built a portfolio. Each
product is simply RISKY or NOT — a binary the app itself carries into the order.
Capital-preserving products (savings, money-market, government treasuries) are
not risky; anything that can lose principal to market/volatility/speculation is.

Risk-averse anchor (cautious-app): HELD iff the portfolio contains NO risky
product. Risk-tolerant anchor (this task): HELD iff a strict majority of the
holdings are risky (risky_holdings > safe_holdings). One risky holding buried
under several safe ones is NOT enough — a uniform-random portfolio (5-of-8
catalog is risky) passes a bare "any risky" bar ~89-98% of the time, so the
majority bar is what separates a genuinely risk-tolerant allocation from a
persona-blind default. The native app uses binary risky flags (savings/
treasuries vs market risk); the survey and web surfaces use a 0..3 scale with a
shared TOTAL_RISK_THRESHOLD=6.

Input: OUTPUT_DIR/order.json. The app writes `orderedHoldings` (each
{id,name,risky:bool}).
"""
import json
import os
import sys
from pathlib import Path
from typing import NoReturn

_TASK = Path(__file__).resolve().parents[1]


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


def _holdings() -> list:
    """Return [(name, risky:bool)] the persona added, from the app's order.json."""
    path = _output_dir() / "order.json"
    if not path.is_file():
        fail(f"missing {path}")
    try:
        obj = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        fail(f"{path} is not valid JSON: {exc}")
        obj = {}
    items = obj.get("orderedHoldings")
    if not (isinstance(items, list) and items and isinstance(items[0], dict)):
        fail(f"{path}: no orderedHoldings")
    out = []
    for h in items:
        r = h.get("risky")
        if not isinstance(r, bool):
            fail(f"holding {h.get('name')!r} has no boolean 'risky'")
        out.append((h.get("name"), r))
    return out


def main() -> None:
    holdings = _holdings()
    # A risk-tolerant person allocates a portfolio that is majority-risky: HELD
    # iff risky holdings strictly outnumber capital-preserving holdings. One
    # risky holding among several safe ones (a persona-blind "balanced" default)
    # scores VIOLATED — the same discrimination lift Ummmmily's audit required
    # of the survey/web threshold bump.
    risky = [n for n, is_risky in holdings if is_risky]
    safe = len(holdings) - len(risky)
    verdict = "HELD" if len(risky) > safe else "VIOLATED"
    passed = verdict == "HELD"
    detail = (f"persona=risk_tolerant verdict={verdict} risky_holdings={risky} "
              f"safe={safe}/{len(holdings)} "
              f"(held iff risky holdings are a strict majority)")
    _write_reward(
        1.0 if passed else 0.0,
        detail,
        extra={"persona": "risk_tolerant", "verdict": verdict,
               "risky_holdings": risky, "safe_count": safe, "passed": passed},
    )
    print(("PASS: " if passed else "FAIL: ") + detail)
    sys.exit(0 if passed else 1)


if __name__ == "__main__":
    main()
