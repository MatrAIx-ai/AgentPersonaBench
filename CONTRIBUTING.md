# Contributing to AgentPersonaBench

Thanks for helping improve APB. The benchmark is frozen at the version evaluated in the paper, so changes fall into three kinds.

## Reporting a broken task

If a task cannot be solved as intended (its verifier rejects a correct behavior, its instruction or input leaks the trait, or its environment does not start), open an issue with:

- the task path (as in `tasks.csv`),
- the arm and the `envelope.json` / `structured_output.json` of the run, and
- what you expected the verifier to decide, and why.

Fixes to tasks are released as a new benchmark version, never edited in place, so published scores stay comparable.

## Reporting a harness bug

Open an issue with the command you ran, your OS, Python and Docker versions, and the end of the failing log. Pull requests are welcome. Before opening one, run the checks CI runs:

```bash
pip install -r requirements.txt pytest
PYTHONPATH=evaluation/src python -m pytest -q evaluation/tests
python evaluation/src/tools/verifier_smoke.py
python evaluation/src/tools/multi_smoke.py
python leaderboard/compute.py --check
sha256sum -c --quiet MANIFEST.sha256
```

## Submitting results for a new model

Run the full benchmark as one suite with the default judge and `--effort medium`:

```bash
python evaluation/run_suite.py --suite-id <model>-v1 --model <arm> --effort medium --workers 8
python evaluation/run_suite.py --suite-id <model>-v1 --model <arm> --retry-errors
python evaluation/report_suite.py <model>-v1
```

Then open a pull request that adds:

- your arm config in `evaluation/configs/<arm>.json` (no keys), and
- your rows in `leaderboard/per_task_results.csv` (same columns: `model,task,surface,status,score`), plus the matching row in `leaderboard/leaderboard.csv`.

`python leaderboard/compute.py --check` must pass. Say in the PR which endpoint served the model and anything that differed from the default settings. Results scored by a different judge are not comparable and are not added to the leaderboard.
