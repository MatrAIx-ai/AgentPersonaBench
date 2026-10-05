# Running a suite

`run_task.py` runs one task. `run_suite.py` runs many — with preflight, concurrency,
resumability and a per-arm plan — and `report_suite.py` turns the result into a leaderboard
and a task-health report.

The reason for the split: a leaderboard is only meaningful when every compared arm ran the
same tasks and seeds, and when a task that failed to *run* is not confused with a persona the
model failed to *hold*. The suite runner exists to make both of those structural rather than
a matter of discipline.

## Environment

One Python 3.12 environment with the root `requirements.txt` installed, plus
Docker for the `survey`, `web` and `app` surfaces. Provider credentials are read only from
environment variables and are never written into a plan, an envelope, or any report.

```bash
export RUNTIME_PYTHON=/path/to/python
export ANTHROPIC_API_KEY=...        # or OPENAI_API_KEY / GEMINI_API_KEY
```

## 1. Preflight — validate every task without spending anything

```bash
$RUNTIME_PYTHON evaluation/run_suite.py --suite-id preflight-$(date -u +%Y%m%d) --preflight-only
```

Runs `task_doctor` against every discovered task and records the outcome, the pinned Git SHA
and the task inventory in `evaluation/results/suites/<suite-id>/plan.json`. A nonzero exit
means at least one task fails its static contract.

`--preflight-only` also reports **runtime readiness** — interpreter, Docker daemon, and the
credentials each selected arm needs — so a missing prerequisite surfaces before API spend
rather than as 100 identical failures. `--skip-runtime-check` bypasses it and should not be
used for a run you intend to publish.

Inspect or filter the inventory:

```bash
$RUNTIME_PYTHON evaluation/run_suite.py --list
$RUNTIME_PYTHON evaluation/run_suite.py --list --surface app
$RUNTIME_PYTHON evaluation/run_suite.py --list --task '*vegan*'
```

`--task` globs match the task path or `bucket/task`; `--surface` restricts by environment.
Both may be repeated, and they compose.

## 2. Smoke one task per surface

Before a long run, confirm the arm and the four environments end to end:

```bash
$RUNTIME_PYTHON evaluation/run_suite.py --suite-id smoke --model opus-4-8 \
  --task '*cautious-survey' --task '*cautious-chat' \
  --task '*cautious-web' --task '*cautious-app' \
  --seed 0 --workers 2 --effort medium
```

## 3. One-seed health run

Run every task once with a baseline arm. This is the step that finds tasks which pass the
static contract but do not run end to end.

```bash
$RUNTIME_PYTHON evaluation/run_suite.py --suite-id health-v1 \
  --model opus-4-8 --seed 0 --workers 4 --effort medium
$RUNTIME_PYTHON evaluation/report_suite.py health-v1
```

Fix environment-wide failures first, retry transient `error`/`timeout` cells with
`--retry-errors`, then either fix or explicitly quarantine reproducibly broken tasks before
comparing models. **Never remove a task for one arm and not another** — that is exactly the
bias the common-coverage rule below exists to prevent.

## 4. Compare arms

Run the same tasks and seeds for every arm in **one** suite. Seeds for the same task/arm run
sequentially to avoid result-directory collisions; different task/arm groups run concurrently.

```bash
$RUNTIME_PYTHON evaluation/run_suite.py --suite-id compare-v1 \
  --model opus-4-8 --model gpt-5-6-sol \
  --seed 0 --seed 1 --seed 2 --workers 4 --effort medium
$RUNTIME_PYTHON evaluation/report_suite.py compare-v1
```

The suite is resumable: re-run the identical command and completed run keys are skipped.
`--retry-errors` retries only prior infrastructure errors and timeouts.

### Arms whose model id cannot be committed

An arm config may ship a placeholder model id (`"model": "REPLACE_WITH_..."`) and take the
real one at runtime:

```bash
--model my-arm --model-id my-arm=THE_REAL_MODEL_ID
```

The resolved id is pinned in `plan.json` and in every envelope, so the run stays reproducible
without the id living in Git. A suite refuses to start if any selected arm still holds an
unresolved placeholder.

## Outputs

Under `evaluation/results/suites/<suite-id>/`:

| file | contents |
|---|---|
| `plan.json` | immutable run plan: Git SHA, task inventory, resolved model ids, preflight results |
| `events.jsonl` | append-only started/completed events — the basis for resume and crash recovery |
| `leaderboard.md` | normalized arm ranking plus every task's health status |
| `leaderboard.html` | self-contained dashboard: ranking, timing, tokens, cost, task-health filter |
| `trials.csv` | flat analysis table, one row per trial |
| `summary.json` | machine-readable plan and trial records |

Per-trial artifacts stay where `run_task.py` writes them, under
`evaluation/results/<task-path>/<arm>/<effort>/trial-NNN/`. See
[`results/CONTRACT.md`](results/CONTRACT.md) for that schema.

## How results are interpreted

- `pass` / `fail` are **behavioral** outcomes. `error`, `timeout` and `preflight_error` are
  infrastructure or task-health failures and are excluded from behavioral means.
- Ranking uses only the task/seed cells every compared arm completed behaviorally, so a task
  that is missing or broken for one arm cannot improve another arm's rank. The report states
  the comparable coverage it used.
- Multi-attribute reward is normalized by `max_points`, putting every task on a $[0,1]$ scale
  regardless of how many checks it pins.
- Timing and token usage are recorded per trial when the task runtime emits them: total wall
  time, solve time, verifier time, and model-call latency.
- A leaderboard is publishable only when every compared arm has equivalent task/seed coverage
  and infrastructure failures have been resolved or explicitly quarantined. The dashboard
  labels a run that does not meet this bar.
