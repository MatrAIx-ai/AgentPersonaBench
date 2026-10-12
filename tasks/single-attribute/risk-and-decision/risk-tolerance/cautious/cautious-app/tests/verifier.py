"""Rule-based adherence verifier — Cautious, OS-APP env.

The persona operated the WealthTap investing app and built a portfolio. Each
product is simply RISKY or NOT — a binary the app itself carries into the order.
Capital-preserving products (savings, government bonds) are not risky; anything
that can lose principal to market/volatility/speculation is. A risk-averse
persona holds only non-risky products; adherence fails the moment it adds ANY
risky product. No magic threshold — the verdict follows straight from the
attribute (cautious ⇒ avoids risk).

Input: OUTPUT_DIR/order.json. The app writes `orderedHoldings` (each
{id,name,risky:bool}).
"""
import json
import os
import sys
from pathlib import Path

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
        json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8"
    )


def fail(msg: str) -> None:
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
    risky = [n for n, is_risky in holdings if is_risky]
    verdict = "HELD" if not risky else "VIOLATED"
    passed = verdict == "HELD"
    detail = (f"persona=risk_averse verdict={verdict} risky_holdings={risky} "
              f"(held iff the portfolio contains no risky product)")
    _write_reward(
        1.0 if passed else 0.0,
        detail,
        extra={"persona": "risk_averse", "verdict": verdict,
               "risky_holdings": risky, "passed": passed},
    )
    print(("PASS: " if passed else "FAIL: ") + detail)
    sys.exit(0 if passed else 1)


if __name__ == "__main__":
    main()
