# evaluation

The APB harness. Every task, on every surface, runs the same way:

```
run_task.py  ->  tasks/<task>/solution/solve.sh  ->  tasks/<task>/tests/verifier.py  ->  envelope.json
```

| Path | What it is |
|---|---|
| `run_task.py` | Runs one task with one arm and writes a trial to `results/<bucket>/<task>/<arm>/<effort>/trial-NNN/`. |
| `run_suite.py` | Runs many tasks × arms × seeds with preflight, concurrency and resume. See [SUITES.md](SUITES.md). |
| `report_suite.py`, `leaderboard.py` | Turn a suite into a report and a leaderboard. |
| `configs/` | One JSON per model arm (the paper's 20) and `judge.json`, the fixed LLM judge. |
| `src/` | Provider layer (`llm_client.py`, `openai_compat.py`, `agent_client.py`, `llm_proxy.py`), the judge, the web agent, the chat harness, the vendored harbor runtime and the Docker environment definitions. |
| `src/lib/` | Shell libraries the task solvers source (`harbor_solve.sh` for survey/app, `web_solve.sh` for web). |
| `src/tools/` | `task_doctor.py` (static task contract check), `verifier_smoke.py`, `new_task.py` and the task generators. |
| `results/` | Trial output (git-ignored). [results/CONTRACT.md](results/CONTRACT.md) documents the envelope format. |
| `tests/` | Harness unit tests: `PYTHONPATH=evaluation/src python -m pytest evaluation/tests`. |
| `run_*codex*.py` | The Codex-agent ablation runners. |

Each trial directory holds `envelope.json` (task, arm, model, seed, status, timings, token usage, cost, judge), `reward.txt`, `structured_output.json` (per-check verdicts) and, for agentic surfaces, the transcript or `trace.zip`.

Status is one of `pass` (every check held), `fail` (at least one check violated) or `error` (the run itself broke: timeout, provider outage, missing artifact). Leaderboard rates are over `pass + fail`; errors are reported separately and never counted as persona failures.
