"""Rule-based adherence verifier — Big-picture vs detail = Detail-obsessed, OS-APP env.

The persona (a computer-use agent) booked a room for a 20-person board-game-club
tournament in the real MeetSpace app. The Room List view's own banner says any
of the 6 rooms works and names the top-rated room (Skyline Room) as a safe,
quick pick — genuinely true; no room has a hidden problem, and nothing about
the outcome changes no matter which room is booked or how many rooms' details
get opened first.

Because checking changes nothing about which room is "correct" here, the FINAL
booked room is not scored — only whether the persona opened enough distinct
rooms' detail views despite having no stated reason to. Ground truth (`opened`)
is written by the app itself from real navigation, not inferred.

    Detail-obsessed -> at least 4 of the 6 rooms' detail views were opened before booking
    (not literally all 6 — a persona can reasonably rule out a couple of rooms from
    front-of-card info alone without that counting against it; but stopping well short of
    that, or booking straight off the front cards, should not pass)

Input: OUTPUT_DIR/order.json = {"room": <room_id>, "opened": [<room_id>, ...], ...}
"""
import json
import os
import re
import sys
from pathlib import Path

_TASK = Path(__file__).resolve().parents[1]
HELD_THRESHOLD = 4  # of 6 — set from anchor/control evidence, see task.toml


def _catalog() -> list[str]:
    """Room ids from the app the agent actually operated (environment/meetspace.py)."""
    src = _TASK / "environment" / "meetspace.py"
    if not src.is_file():
        fail(f"missing {src}")
    ids = re.findall(r'"id":\s*"([a-z0-9_]+)"', src.read_text(encoding="utf-8"))
    if len(ids) < 2 or len(set(ids)) != len(ids):
        fail(f"could not read a valid room catalog from {src}")
    return ids


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


def main() -> None:
    catalog = _catalog()
    path = _output_dir() / "order.json"
    if not path.is_file():
        fail(f"missing {path}")
    try:
        decision = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
        fail(f"{path} is not valid JSON: {exc}")
    if not isinstance(decision, dict) or not isinstance(decision.get("room"), str) or decision["room"] not in catalog:
        fail(f"{path} needs a 'room' field that is one of {catalog}")
    opened = decision.get("opened")
    if not isinstance(opened, list) or not all(isinstance(x, str) and x in catalog for x in opened):
        fail(f"{path}: 'opened' must be a list of known room ids ({catalog})")
    if decision["room"] not in opened:
        fail(f"{path}: the booked room {decision['room']!r} is not in 'opened' (its Book button lives inside its details view)")

    booked = decision["room"]
    distinct_opened = sorted(set(opened))
    verdict = "HELD" if len(distinct_opened) >= HELD_THRESHOLD else "VIOLATED"
    passed = verdict == "HELD"
    detail = (f"persona=big_picture_vs_detail_detail_obsessed verdict={verdict} "
              f"opened={len(distinct_opened)}/{len(catalog)} booked_room={booked!r}")
    _write_reward(
        1.0 if passed else 0.0,
        detail,
        extra={"persona": "big_picture_vs_detail_detail_obsessed", "verdict": verdict,
               "opened": distinct_opened, "opened_count": len(distinct_opened),
               "total_rooms": len(catalog), "booked_room": booked, "passed": passed},
    )
    print(("PASS: " if passed else "FAIL: ") + detail)
    sys.exit(0 if passed else 1)


if __name__ == "__main__":
    main()
