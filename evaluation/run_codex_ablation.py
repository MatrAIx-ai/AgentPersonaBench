"""Repeat the host-Codex runner across persona, blind, and explicit controls."""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

CONDITIONS = ("persona", "blind", "explicit")
RUNNER = Path(__file__).with_name("run_task_codex.py")


def evaluate_ablation(outcomes: dict[str, list[bool]]) -> dict[str, Any]:
    rates = {
        condition: sum(values) / len(values) if values else 0.0
        for condition, values in outcomes.items()
    }
    gates = {
        "persona_pass_rate_at_least_70pct": rates["persona"] >= 0.70,
        "blind_pass_rate_at_most_30pct": rates["blind"] <= 0.30,
        "explicit_pass_rate_at_least_70pct": rates["explicit"] >= 0.70,
        "persona_minus_blind_at_least_40pct": (
            rates["persona"] - rates["blind"] >= 0.40
        ),
        "explicit_minus_blind_at_least_40pct": (
            rates["explicit"] - rates["blind"] >= 0.40
        ),
        "persona_and_explicit_within_30pct": (
            abs(rates["persona"] - rates["explicit"]) <= 0.30
        ),
    }
    return {"rates": rates, "gates": gates, "passed": all(gates.values())}


def default_output_dir(task: str) -> Path:
    slug = "__".join(part for part in Path(task).parts if part not in {".", ".."})
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S.%fZ")
    return Path(tempfile.gettempdir()) / "personabench-codex-ablation" / slug / stamp


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Run repeated noncanonical Codex persona/blind/explicit controls."
    )
    parser.add_argument("task")
    parser.add_argument("--repeats", type=int, default=5)
    parser.add_argument("--output-dir", type=Path, default=None)
    parser.add_argument("--codex-bin", default=None)
    parser.add_argument("--codex-model", default=None)
    parser.add_argument("--timeout", type=float, default=None)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    if args.repeats < 1:
        print("INFRA_ERROR: --repeats must be positive", file=sys.stderr)
        return 3
    output_dir = (args.output_dir or default_output_dir(args.task)).resolve()
    try:
        output_dir.mkdir(parents=True, exist_ok=False)
    except OSError as exc:
        print(
            f"INFRA_ERROR: could not create ablation directory: {exc}", file=sys.stderr
        )
        return 3

    outcomes: dict[str, list[bool]] = {condition: [] for condition in CONDITIONS}
    runs: list[dict[str, Any]] = []
    for repeat in range(1, args.repeats + 1):
        for condition in CONDITIONS:
            trial_dir = output_dir / condition / f"trial-{repeat:03d}"
            command = [
                sys.executable,
                str(RUNNER),
                args.task,
                "--condition",
                condition,
                "--output-dir",
                str(trial_dir),
            ]
            if args.codex_bin:
                command.extend(["--codex-bin", args.codex_bin])
            if args.codex_model:
                command.extend(["--codex-model", args.codex_model])
            if args.timeout is not None:
                command.extend(["--timeout", str(args.timeout)])
            completed = subprocess.run(
                command, capture_output=True, check=False, text=True
            )
            run = {
                "condition": condition,
                "repeat": repeat,
                "exit_code": completed.returncode,
                "stdout": completed.stdout.strip(),
                "stderr": completed.stderr.strip(),
                "artifact_dir": str(trial_dir),
            }
            runs.append(run)
            if completed.returncode in {0, 1}:
                outcomes[condition].append(completed.returncode == 0)
                print(
                    f"{condition} trial {repeat}/{args.repeats}: "
                    f"{'HELD' if completed.returncode == 0 else 'VIOLATED'}"
                )
                continue
            partial = {"task": args.task, "repeats": args.repeats, "runs": runs}
            (output_dir / "ablation_summary.json").write_text(
                json.dumps(partial, indent=2) + "\n", encoding="utf-8"
            )
            print(
                f"ablation stopped: {condition} trial {repeat} returned "
                f"{completed.returncode}",
                file=sys.stderr,
            )
            return completed.returncode if completed.returncode in {2, 3} else 3

    result = evaluate_ablation(outcomes)
    summary = {
        "canonical": False,
        "task": args.task,
        "repeats": args.repeats,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "outcomes": outcomes,
        **result,
        "runs": runs,
    }
    (output_dir / "ablation_summary.json").write_text(
        json.dumps(summary, indent=2) + "\n", encoding="utf-8"
    )
    print(json.dumps({"rates": result["rates"], "passed": result["passed"]}))
    print(f"artifacts: {output_dir}")
    return 0 if result["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
