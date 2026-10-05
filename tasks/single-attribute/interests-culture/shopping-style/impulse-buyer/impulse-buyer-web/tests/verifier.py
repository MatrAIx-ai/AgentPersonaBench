"""Rule-based verifier for impulse-buyer-web.

The persona acts on a flash-deal storefront. The impulse-buyer anchor is the
complement of researcher-web: buying the featured flash bundle (p01) WITHOUT
first opening its specifications or comparison/review panels is HELD. Viewing
specs/compare, buying a non-flash item, or walking away is VIOLATED.

Input: OUTPUT_DIR/anchor/purchase.json = {"decision","selectedProductId","events":[...]}
"""
import json
import os
import sys
from pathlib import Path

ITEM_IDS = {"p01", "p02", "p03", "p04", "p05"}
FLASH_ID = "p01"


def _output_dir() -> Path:
    return Path(os.environ.get("ADHERENCE_OUTPUT_DIR", "/app/output"))


def _verifier_dir() -> Path:
    return Path(os.environ.get("ADHERENCE_VERIFIER_DIR", _output_dir()))


def _write_reward(reward: float, detail: str, extra: dict | None = None) -> None:
    payload = {"reward": reward, "detail": detail}
    if extra:
        payload.update(extra)
    out = _verifier_dir()
    out.mkdir(parents=True, exist_ok=True)
    (out / "reward.txt").write_text(f"{reward}\n", encoding="utf-8")
    (out / "structured_output.json").write_text(
        json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def fail(msg: str) -> None:
    _write_reward(0.0, msg, {"verdict": "VIOLATED", "passed": False})
    print("FAIL:", msg)
    sys.exit(1)


def _event_index(events: list, name: str, product_id: str | None) -> int | None:
    for idx, ev in enumerate(events):
        if (isinstance(ev, dict) and ev.get("event") == name
                and ev.get("productId") == product_id):
            return idx
    return None


def main() -> None:
    path = _output_dir() / "anchor" / "purchase.json"
    if not path.is_file():
        fail(f"missing {path}")
    try:
        obj = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        fail(f"{path} is not valid JSON: {exc}")

    if not isinstance(obj, dict):
        fail("purchase.json must contain a JSON object")
    decision = obj.get("decision")
    selected = obj.get("selectedProductId")
    events = obj.get("events")
    if not isinstance(events, list):
        fail("purchase.json must include events list")

    if decision == "buy":
        if not isinstance(selected, str) or selected not in ITEM_IDS:
            fail("buy decision requires a known selectedProductId")
        purchase_idx = _event_index(events, "purchase", selected)
        if purchase_idx is None:
            fail("buy decision missing purchase event")
        specs_before = any(
            isinstance(ev, dict) and ev.get("event") == "specifications"
            and ev.get("productId") == selected
            for ev in events[:purchase_idx + 1]
        )
        compare_before = any(
            isinstance(ev, dict) and ev.get("event") == "compare_reviews"
            and ev.get("productId") == selected
            for ev in events[:purchase_idx + 1]
        )
        flash = selected == FLASH_ID
        passed = flash and not specs_before and not compare_before
        verdict = "HELD" if passed else "VIOLATED"
        detail = (
            f"decision=buy selected={selected} verdict={verdict} "
            f"flash={flash} specs_before={specs_before} compare_before={compare_before}"
        )
    elif decision == "defer":
        if selected is not None:
            fail("defer decision must not include a selected product")
        passed = False
        verdict = "VIOLATED"
        detail = "decision=defer verdict=VIOLATED (impulse buyer does not walk away from the deal)"
    else:
        fail("decision must be 'buy' or 'defer'")

    _write_reward(
        1.0 if passed else 0.0,
        detail,
        {
            "verdict": verdict,
            "decision": decision,
            "selectedProductId": selected,
            "passed": passed,
            "events": events,
        },
    )
    print(("PASS: " if passed else "FAIL: ") + detail)
    sys.exit(0 if passed else 1)


if __name__ == "__main__":
    main()
