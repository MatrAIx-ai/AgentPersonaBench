"""Preserve the exhaustive constructed selection grid, using the real verifier."""
import argparse
import itertools
import json
from pathlib import Path

from run_blind import score_reply, source_hashes

QUESTIONS = ("primary", "fallback", "hold", "digest")
OPTIONS = (("p18", "p47", "p29", "p63"), ("f36", "f52", "f81", "f24"),
           ("h65", "h13", "h72", "h48"), ("d91", "d28", "d64", "d35"))
EXPECTED_HELD = ("p47", "f36", "h48", "d28")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    if args.output.exists():
        parser.error("choose a new output directory; evidence is not overwritten")
    args.output.mkdir(parents=True)
    rows = []
    for choices in itertools.product(*OPTIONS):
        directory = args.output / "-".join(choices)
        directory.mkdir()
        raw = json.dumps({"answers": [
            {"questionId": q, "selectedOptionId": choice} for q, choice in zip(QUESTIONS, choices)
        ]})
        result = score_reply(directory, raw)
        expected = "HELD" if choices == EXPECTED_HELD else "VIOLATED"
        rows.append({"case": directory.name, "selected_answers": dict(zip(QUESTIONS, choices)),
                     "expected": expected, "actual": result["verdict"],
                     "correct": result["verdict"] == expected})
    summary = {"kind": "constructed-exhaustive-verifier-grid", "acting_model": None,
               "source_sha256": source_hashes(), "cases": len(rows),
               "correct": sum(row["correct"] for row in rows),
               "held": sum(row["actual"] == "HELD" for row in rows), "records": rows}
    (args.output / "summary.json").write_text(json.dumps(summary, indent=2))
    print(json.dumps({k: v for k, v in summary.items() if k not in ("records", "source_sha256")}))
    raise SystemExit(0 if summary["correct"] == len(rows) else 1)


if __name__ == "__main__":
    main()
