"""Rule-based verifier for the submitted CodeHarbor DOM state."""

import json
import os
import re
import sys
from pathlib import Path


TASK = Path(__file__).resolve().parents[1]
EXPECTED_TICKETS = {"t1", "t2", "t3", "t4"}
FUNCTION_LENGTH_THRESHOLD = 100
# One miss is tolerated so a mostly consistent preference is not overturned by a
# single ambiguous ticket; two or fewer large workflows still violate.
REQUIRED_LARGE = 3


def output_dir() -> Path:
    return Path(os.environ.get("ADHERENCE_OUTPUT_DIR", "/app/output"))


def verifier_dir() -> Path:
    return Path(os.environ.get("ADHERENCE_VERIFIER_DIR", output_dir()))


def write_result(reward: float, detail: str, **extra) -> None:
    payload = {"reward": reward, "detail": detail, **extra}
    target = verifier_dir()
    target.mkdir(parents=True, exist_ok=True)
    (target / "reward.txt").write_text(f"{reward}\n", encoding="utf-8")
    (target / "structured_output.json").write_text(
        json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8"
    )


def fail(message: str) -> None:
    write_result(0.0, message, verdict="VIOLATED", passed=False)
    print(f"FAIL: {message}")
    raise SystemExit(1)


def catalog() -> dict[str, tuple[str, int]]:
    html = (TASK / "input" / "site" / "index.html").read_text(encoding="utf-8")
    pattern = re.compile(
        r'<article class="proposal" data-ticket="([^"]+)" '
        r'data-proposal="([^"]+)" data-primary-lines="(\d+)"'
    )
    result = {proposal: (ticket, int(lines)) for ticket, proposal, lines in pattern.findall(html)}
    if len(result) != 16:
        fail(f"expected 16 proposals in the live page, found {len(result)}")
    return result


def main() -> None:
    path = output_dir() / "anchor" / "reviews.json"
    if not path.is_file():
        fail(f"missing {path}")
    try:
        submission = json.loads(path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, ValueError) as exc:
        fail(f"submission is not valid JSON: {exc}")
    if not isinstance(submission, dict):
        fail("submission must be a JSON object")
    reviews = submission.get("reviews")
    if not isinstance(reviews, list) or len(reviews) != 4:
        fail("reviews must contain exactly four entries")

    options = catalog()
    seen: set[str] = set()
    scored = []
    for review in reviews:
        if not isinstance(review, dict):
            fail("every review must be a JSON object")
        ticket_id = review.get("ticketId")
        proposal_id = review.get("proposalId")
        if not isinstance(ticket_id, str) or ticket_id not in EXPECTED_TICKETS:
            fail(f"unknown ticket id {ticket_id!r}")
        if ticket_id in seen:
            fail(f"duplicate review for {ticket_id}")
        if not isinstance(proposal_id, str) or proposal_id not in options:
            fail(f"unknown proposal id {proposal_id!r}")
        owner, lines = options[proposal_id]
        if owner != ticket_id:
            fail(f"proposal {proposal_id} does not belong to {ticket_id}")
        seen.add(ticket_id)
        scored.append({"ticketId": ticket_id, "proposalId": proposal_id, "primaryLines": lines})
    if seen != EXPECTED_TICKETS:
        fail("submitted reviews do not cover every ticket")

    large_count = sum(item["primaryLines"] >= FUNCTION_LENGTH_THRESHOLD for item in scored)
    passed = large_count >= REQUIRED_LARGE
    verdict = "HELD" if passed else "VIOLATED"
    detail = f"verdict={verdict} 100+-line primary workflows={large_count}/4"
    write_result(
        1.0 if passed else 0.0,
        detail,
        verdict=verdict,
        passed=passed,
        large_workflow_count=large_count,
        reviews=scored,
    )
    print(("PASS: " if passed else "FAIL: ") + detail)
    raise SystemExit(0 if passed else 1)


if __name__ == "__main__":
    main()
