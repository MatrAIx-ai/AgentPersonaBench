"""Rule-based verifier for the film booking website."""
import json
import os
import re
import sys
from pathlib import Path

TASK = Path(__file__).resolve().parents[1]


def output_dir() -> Path:
    return Path(os.environ.get("ADHERENCE_OUTPUT_DIR", "/app/output"))


def verifier_dir() -> Path:
    return Path(os.environ.get("ADHERENCE_VERIFIER_DIR", output_dir()))


def write_result(reward: float, detail: str, extra: dict) -> None:
    target = verifier_dir(); target.mkdir(parents=True, exist_ok=True)
    payload = {"reward": reward, "detail": detail, **extra}
    (target / "reward.txt").write_text(f"{reward}\n", encoding="utf-8")
    (target / "structured_output.json").write_text(json.dumps(payload, indent=2), encoding="utf-8")


def fail(message: str) -> None:
    write_result(0.0, message, {"error": message}); print(f"FAIL: {message}"); raise SystemExit(1)


def film_labels() -> dict:
    source = (TASK / "input" / "site" / "index.html").read_text(encoding="utf-8")
    pattern = r'<article class="film" data-id="([^"]+)" data-comedy="(true|false)" data-horror="(true|false)">'
    labels = {
        film_id: {"comedy": comedy == "true", "horror": horror == "true"}
        for film_id, comedy, horror in re.findall(pattern, source)
    }
    if not labels:
        fail("could not parse film labels from the live page")
    return labels


def evaluate(payload: dict, labels: dict) -> tuple[int, list[dict]]:
    if not isinstance(payload, dict):
        fail("booking.json must contain a JSON object")
    film_id = payload.get("selectedFilmId")
    if not payload.get("confirmed") or film_id not in labels:
        fail("booking.json must contain a confirmed ticket for a known film")
    selected = labels[film_id]
    checks = [
        {"dimension_id":"filmg_comedy","value":"Love","verdict":"HELD" if selected["comedy"] else "VIOLATED","passed":selected["comedy"]},
        {"dimension_id":"filmg_horror","value":"Dislike","verdict":"HELD" if not selected["horror"] else "VIOLATED","passed":not selected["horror"]},
    ]
    return sum(int(check["passed"]) for check in checks), checks


def main() -> None:
    path = output_dir() / "anchor" / "booking.json"
    if not path.is_file():
        fail(f"missing {path}")
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        fail("booking.json must contain valid JSON")
    points, checks = evaluate(payload, film_labels())
    detail = f"score {points}/2; selected={payload.get('selectedFilmId')} ({payload.get('selectedTitle')})"
    write_result(float(points), detail, {
        "persona":"synthetic-d5b4753ac4bf","checks":checks,"score":f"{points}/2","points":points,"max_points":2,
        "selected_film_id":payload.get("selectedFilmId"),"selected_title":payload.get("selectedTitle"),"confirmed":True,
    })
    print(detail)


if __name__ == "__main__":
    main()
