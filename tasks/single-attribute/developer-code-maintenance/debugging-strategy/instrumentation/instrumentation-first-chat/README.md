# instrumentation-first-chat

Native pin: `debugging_strategy = Add logging / instrumentation`.

A twelve-exchange maintenance conversation elicits diagnostic plans for Receipt adjustment, Group summary and Duplicate normalization. This format measures declared workflow rather than executed debugging. The task-local colleague introduces incidents at replies 1, 4 and 7, uses five generated follow-ups, and asks separate final handoff questions at replies 9, 10 and 11. Persona turns 10, 11 and 12 contain the corresponding final plans; reply 12 closes the handoff.

## Scoring and evidence

Each incident receives one completion judgment under [protocol 6.0](COMPLETION_PROTOCOL4.md). It asks whether any adopted checking act examines behavior after repair, retaining earlier commitments unless withdrawn or replaced. Reports identify the adopted plan, concrete work, selected checking operation, its target and temporal relation using host-supplied passage IDs. The host resolves those IDs to unchanged persona text and source offsets; judges do not copy quotations. Every criterion needs clear evidence. Missing work or a check without established post-repair timing makes the plan INCOMPLETE and returns unscored ERROR with completion_incomplete. Malformed judge output remains a parsing error. There is no independent audit or disagreement gate. Archived protocol 4 and 5 results remain historical evidence.

Only complete plans receive the three method judgments. At least two target-method incidents yield HELD. This is an authored operational definition, not a numerical boundary inherent in the categorical attribute. The latest endorsed plan determines the first relevant observation before repair. Repair correctness is not required. The judge is selected independently from the actor through `ADHERENCE_JUDGE_MODEL` and `ADHERENCE_JUDGE_PROVIDER`; at most three completion and three method calls are made. Citation validity does not establish semantic accuracy.

Malformed completion JSON returns ERROR in the shipped judge; there is no automatic parsing retry or reuse of earlier completion reports. Report original ERROR counts separately from later diagnostic scores. The explicit `tests/rejudge.py --execute --input <saved-diagnostic> --output <new-directory> --model-id <judge-model> --target <target>` command judges the saved dialogue again, making up to three completion and three method calls without rerunning the actor. It also accepts labeled recovered input through the compatible `--recovered` option. `recover_diagnostic.py` is limited to the historical observer AttributeError and does not recover malformed judge JSON.

## Native persona

The task ships the complete, unchanged synthetic native profile with all 1,290 attributes.
See [source provenance](research/persona-provenance.json). The two target profiles differ on 828 fields, so comparisons do not isolate a causal effect of one attribute.
Dataset use remains subject to the [pinned dataset card](https://huggingface.co/datasets/MatrAIx2026/MatrAIx_Persona_1M/blob/8b1073ab23d0c0ba0928386a041bac55e5365ddc/README.md), including attribution and non-commercial research terms.

## Setup and use

Use Python 3.12, the repository runtime dependencies, Docker, and Bash (Git Bash for Windows host commands). Check dependencies and Docker availability before running a task. Use an isolated environment if additional dependencies are needed. The task reuses shared infrastructure without installing host packages.

`python -m pip check`

`docker version`

Run from the repository root with the intended configured model and authorized credentials:

`python evaluation/run_task.py developer-code-maintenance/debugging-strategy/instrumentation/instrumentation-first-chat --model opus-4-8 --model-id claude-haiku-4-5-20251001 --effort medium --seed 0`

The configured arm label and actual model override are separate. Inspect the recorded provider model when interpreting output.

## Local checks

`PYTHONDONTWRITEBYTECODE=1 python -m unittest discover -s tasks/single-attribute/developer-code-maintenance/debugging-strategy/instrumentation/instrumentation-first-chat/tests -p 'test_*.py'`

`python evaluation/src/tools/task_doctor.py developer-code-maintenance/debugging-strategy/instrumentation/instrumentation-first-chat`

Runtime artifacts belong under `evaluation/results/` and are excluded from the task package. Preserve explicit errors separately from valid persona-adherence failures.
