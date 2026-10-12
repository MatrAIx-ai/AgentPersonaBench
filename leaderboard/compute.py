#!/usr/bin/env python3
"""Recompute the paper's Table 1 full-pass rates from per_task_results.csv.

A task passes when every check holds (status "pass"). Rates are over scored
trials (pass + fail); "error" trials (infrastructure failures) are excluded,
as in the paper. Costs come from token usage and are not recomputed here.

    python leaderboard/compute.py            # print the table
    python leaderboard/compute.py --check    # also compare with leaderboard.csv
"""
import argparse
import csv
from collections import defaultdict
from pathlib import Path

HERE = Path(__file__).parent
COLS = ["single", "multi", "survey", "chat", "web", "app", "overall"]


def compute(path=HERE / "per_task_results.csv"):
    tally = defaultdict(lambda: defaultdict(lambda: [0, 0]))   # model -> col -> [pass, scored]
    for r in csv.DictReader(open(path, newline="")):
        if r["status"] not in ("pass", "fail"):
            continue
        bucket = "single" if r["task"].startswith("single-attribute/") else "multi"
        for col in (bucket, r["surface"], "overall"):
            t = tally[r["model"]][col]
            t[0] += r["status"] == "pass"
            t[1] += 1
    return {m: {c: (round(100 * p / n, 1) if n else None) for c, (p, n) in cols.items()}
            for m, cols in tally.items()}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--check", action="store_true", help="compare with leaderboard.csv")
    args = ap.parse_args()
    table = compute()
    order = sorted(table, key=lambda m: -table[m]["overall"])
    print(f"{'model':22s}" + "".join(f"{c:>9s}" for c in COLS))
    for m in order:
        print(f"{m:22s}" + "".join(f"{'N/A' if table[m].get(c) is None else table[m][c]:>9}" for c in COLS))
    if args.check:
        bad = 0
        for r in csv.DictReader(open(HERE / "leaderboard.csv", newline="")):
            for c in COLS:
                want = float(r[c]) if r[c] else None
                if table[r["model"]].get(c) != want:
                    bad += 1
                    print(f"MISMATCH {r['model']} {c}: {table[r['model']].get(c)} != {want}")
        print("all cells match leaderboard.csv" if not bad else f"{bad} mismatches")
        raise SystemExit(1 if bad else 0)


if __name__ == "__main__":
    main()
