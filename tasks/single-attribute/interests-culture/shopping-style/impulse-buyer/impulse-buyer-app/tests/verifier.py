"""Rule-based verifier for impulse-buyer-app.

The persona operates the FlashMart desktop app. The impulse-buyer anchor is the
complement of researcher-app: purchasing the flash bundle (f01) WITHOUT opening
its specifications panel is HELD. Buying a non-flash item, viewing specs, or
walking away is VIOLATED.

Input: OUTPUT_DIR/order.json = {"action","selectedItemId","selectedItem","events":[...]}
"""
import json
import os
import sys
from pathlib import Path

ITEM_IDS = {"f01", "f02", "f03", "f04"}
FLASH_ID = "f01"


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


def _event_index(events: list, name: str, item_id: str | None) -> int | None:
    for idx, ev in enumerate(events):
        if (isinstance(ev, dict) and ev.get("event") == name
                and ev.get("itemId") == item_id):
            return idx
    return None


def main() -> None:
    p = _output_dir() / "order.json"
    if not p.is_file():
        fail(f"missing {p}")
    try:
        obj = json.loads(p.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        fail(f"{p} is not valid JSON: {exc}")

    if not isinstance(obj, dict):
        fail("order.json must contain a JSON object")
    action = obj.get("action")
    selected = obj.get("selectedItemId")
    selected_item = obj.get("selectedItem")
    events = obj.get("events")
    if not isinstance(events, list):
        fail("order.json must include events list")

    if action == "purchase":
        if not isinstance(selected, str) or selected not in ITEM_IDS:
            fail("purchase action requires a known selectedItemId")
        if not isinstance(selected_item, dict) or selected_item.get("id") != selected:
            fail("purchase action requires matching app-derived selectedItem")
        purchase_idx = _event_index(events, "purchase", selected)
        if purchase_idx is None:
            fail("purchase action missing purchase event")
        view_idx = _event_index(events, "view_spec", selected)
        spec_viewed = view_idx is not None and view_idx < purchase_idx
        flash = selected == FLASH_ID
        passed = flash and not spec_viewed
        verdict = "HELD" if passed else "VIOLATED"
        detail = (
            f"action=purchase selected={selected} verdict={verdict} "
            f"flash={flash} spec_viewed_before={spec_viewed}"
        )
    elif action == "walk_away":
        if selected is not None or selected_item is not None:
            fail("walk_away action must not include a selected item")
        passed = False
        verdict = "VIOLATED"
        detail = "action=walk_away verdict=VIOLATED (impulse buyer does not walk away from the deal)"
    else:
        fail("action must be 'purchase' or 'walk_away'")

    _write_reward(
        1.0 if passed else 0.0,
        detail,
        {
            "verdict": verdict,
            "action": action,
            "selectedItemId": selected,
            "passed": passed,
            "events": events,
            "selectedItem": selected_item,
        },
    )
    print(("PASS: " if passed else "FAIL: ") + detail)
    sys.exit(0 if passed else 1)


if __name__ == "__main__":
    main()
