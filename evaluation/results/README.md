# results

Trial output from `run_task.py` and `run_suite.py`. Everything under this directory except this README and [CONTRACT.md](CONTRACT.md) is git-ignored.

```
results/<bucket>/<task-path>/<arm>/<effort>/trial-NNN/
    envelope.json            run record (below)
    reward.txt               the verifier's reward
    structured_output.json   per-check verdicts (HELD / VIOLATED) and evidence
    ...                      surface-specific artifacts: transcript.json (chat),
                             trajectory.json + trace.zip (web/app), survey_result.json (survey)
results/suites/<suite-id>/   plan.json, events.jsonl, trials.csv, reports (run_suite.py / report_suite.py)
```

`envelope.json` records the task (`task`, `task_version`, `checks`, `persona_id`, `persona_sha256`), the arm (`arm`, `model`, `provider`, `endpoint`, `temperature`, `max_tokens`, `effort`), the judge (`judge_model`, `judge_provider`), the run (`seed`, `timestamp`, `timing`, `model_usage`, `model_calls`), and the outcome (`status`, `score`, `reward`, `findings`).

`status` is `pass` (every check held), `fail` (at least one check violated) or `error` (the run broke before it could be scored). Only `pass` and `fail` count toward adherence rates.

[CONTRACT.md](CONTRACT.md) is the full output contract.
