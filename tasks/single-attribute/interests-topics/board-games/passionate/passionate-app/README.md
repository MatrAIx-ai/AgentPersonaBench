# Lend & Return — native App

A Linux desktop borrowing-plan task for the single native persona attribute
`topic_board_games = Passionate`. The complete, unmodified Persona 1M profile
is `hf-synthetic-270729595` (`source: synthetic`, source row `270729595`,
1,290 attributes). It is copied byte-for-byte from the already merged
`tasks/multi-attribute/plain-table-app/persona.yaml` at repository base
`07b1eab1ac92336cd3b6b51476819a81c063e6ce`. Its SHA-256 is
`e90dec93a2db998e918db5094b00b06c36b54a54103547883231dcb4cbab0f00`.
All four suite leaves carry those same bytes. This App does not edit the persona.

Independent decoding of the [original HF record](https://huggingface.co/datasets/MatrAIx2026/MatrAIx_Persona_1M/blob/8b1073ab23d0c0ba0928386a041bac55e5365ddc/data/persona-1m-0006.parquet),
and an independent replay of the saved check, matched all 1,290 values, labels
and categories. Location: shard 0006, row group 0, position 2498 (global row
602345), all zero-based, no overrides. This source check is not behavioral E2E.

The live coverage refresh on 2026-09-13 found newly opened
[PR187](https://github.com/MatrAIx-ai/Agent_PersonaBench/pull/187), whose
`film-nights-sofa-screenings` tasks also use `topic_board_games = Passionate`,
paired with animation-film preference. This is disclosed attribute reuse in a
different, crossed-trait film-selection context; this App is a single-attribute
physical borrowing plan. No destination path collides.

## Current design — task version 3.0

The user chooses the leisure kit they most want to borrow for their own use
during a two-week loan, plus an acceptable substitute if that kit becomes
unavailable. The loan period is not a daily schedule or repeat-play requirement.
All kits are free, in stock, adult-friendly, have equal pickup and loan terms,
include quick-start cards, and work alone or with one other person. There is
no staff recommendation or popularity cue. This remains a leisure-kit lending
application, not a game-playing application or a books-only catalog.

Version 3 changes the scene, comparable option copy and pass rule in response
to the original-persona variability documented below. It keeps the complete
published persona, native GUI/runtime, product IDs and schema-2 receipt checks.
Old trials are not rescored or claimed as evidence for this changed task.

## Bounded measurement

The primary loan must be a board game for the one binary check to hold. Any
valid fallback is acceptable: passion for a subject does not imply exclusivity
when choosing a substitute. Both groups must still be complete and match the
catalog, redundant receipt fields and ordered interaction history. The fallback
category is recorded as a diagnostic, not scored as a second preference.

- Board-game primary + any valid fallback: HELD, reward 1.
- Any other primary + valid fallback: VIOLATED, reward 0, completed true.
- Missing, unknown or contradictory selections/catalog/history: fail closed,
  reward 0, completed false. A valid primary alone is insufficient.

All three previous completed target failures selected a jigsaw as the primary;
relaxing the fallback criterion alone would not turn those failures into passes.

The three alternatives in each section are jigsaw, number/logic-grid, and
word-search puzzles. They intentionally avoid this persona's separate dislikes
of films, infrequent reading, and lack of origami participation. General hobby
intensity, expertise, competitiveness, and sociability are not scored. Games
include solo and two-player rules, and do not require a group or tournament.

The board games have a five-minute quick start including setup, then 30–45
minutes of play. Captioned game videos are explicitly optional. Jigsaws take
two minutes to set up and 30–60 minutes of activity; number and word puzzles
take one minute to set up and 20–40 minutes of activity. All options describe
pause/resume and contain varied layouts, images or puzzles. The games retain a
modest learning/setup tradeoff without the former asymmetric 10-minute video
plus 8-minute setup framing. Time is not a numeric definition of passion.

The scored board game is primary position 2; the unscored fallback board game
is position 1. Four of the 16 complete primary/fallback pairs pass. Uniform
guessing therefore passes with probability `1/4 = 25%`, not the old `1/16`.
This is a deliberately narrow one-choice measure, not a low-chance multi-item
instrument. Chance is a mathematical diagnostic, not measured blind behavior.

### Review revision: option-length policy

Within each displayed group, normalized label-plus-description text is limited to
125–150 characters and 19–26 whitespace-delimited words. Descriptions alone are
limited to 110–135 characters and 17–24 words. The keyed choice must be strictly
between the shortest and longest option under each of those four measurements;
ties at an extreme are not allowed. These are presentation safeguards, not
persona definitions. The copy uses comparable preparation/activity/pause fields;
the common header explains solo/two-player use and optional captioned videos.

Offline fixture tests measure the actual App source and score both longest-only
and shortest-only selections through the production verifier. They supplement,
not replace, native acting-agent and persona-blind runs.

## Native interface and evidence

The app starts with no selection. Its `940x800` content window is positioned at
`+20+20` on the required `1024x900` desktop. Each section must be
selected independently. Empty and partial submissions display a visible warning
and do not create an artifact. Successful saves display both selected titles.

The application writes `loan_plan.json` using a task-created temporary file and
atomic replacement. Receipt schema version 2 contains opaque product IDs,
submitted state, redundant selection records, ordered selection/submission
events, and the full public choice catalog: group, ID, label, description and
badge for all eight choices. The catalog is frozen once and used for both
rendering and receipt export. It carries no answer categories, target trait,
score or verdict.

The independent verifier reconstructs that catalog from its private key and
requires exact agreement before scoring. Thus even a changed unselected
description cannot silently pass with stale ID mappings. It does not import the
GUI or require an `environment/` source file in the tests-only packaged layout.
Source/key and byte-identical App-mirror fixture checks remain in place.
Exact schemas, group membership, completeness and final-state/event consistency
are also checked. Catalog snapshots are consistency evidence, not cryptographic
proof of user interaction; real GUI and acting-agent traces remain necessary.

The hidden answer key maps products to activity categories, not to invented
persona-interest levels. Duplicate JSON keys, unknown or wrong-type IDs,
partial submissions, forged labels, and contradictory histories fail closed.
Verifier configuration failures are `ERROR` with reward 0 and exit 3. An otherwise
complete, structurally valid receipt whose catalog text differs from the private
contract is also `ERROR`, with `completed=false`: its option IDs cannot be scored
reliably against that contract. This detects a mismatch, not its cause; the
receipt alone cannot distinguish environment/key drift from a fabricated catalog.
Missing, malformed, duplicated, reordered, or unknown catalog entries remain
invalid evidence. All selection and event-history checks run before a catalog
text mismatch can become `ERROR`, so adding drift cannot hide a partial or
contradictory submission. Invalid evidence and genuine nonmatching choices with
an unchanged catalog remain `VIOLATED` with reward 0.

Direct host verification writes alongside the native answer by default.
`tests/test.sh` instead routes Harbor rewards to `/logs/verifier` and permits
its tests-only packaged contract. Explicit `ADHERENCE_VERIFIER_DIR` overrides
remain available. The shared production solver and runtime are unchanged.

Harbor runs its healthcheck before the computer-use agent starts Xvfb/XFCE.
The healthcheck therefore validates dependencies and acknowledges a singleton
background keeper without waiting for a display. The keeper waits for live X
and a window manager, then launches and focuses the app. Readiness of this
bootstrap is distinct from proof that the eventual GUI is operable.

## Offline reproduction

From the repository root, with the repository's Python dependencies installed:

```bash
export PYTHONDONTWRITEBYTECODE=1
TASK_ID=interests-topics/board-games/passionate/passionate-app
TASK="$(pwd)/tasks/single-attribute/$TASK_ID"
EVIDENCE_DIR="$(mktemp -d)"
python -B evaluation/src/tools/task_doctor.py "$TASK_ID"
python -B -m pytest -p no:cacheprovider "$TASK/tests"
python -B "$TASK/tests/run_contrasts.py" --output-dir "$EVIDENCE_DIR/constructed"
```

The contrast output directory must be new and outside the repository. The runner
retains production-verifier inputs, results, source hashes, and subprocess output.
Its cases include all 16 complete pairs (4 HELD / 12 VIOLATED), malformed
evidence, changed final choices, missing/legacy catalogs and altered labels,
descriptions, IDs, groups, order and badges. They are constructed verifier
fixtures, not model runs or GUI evidence.

For physical checks, Docker must be running. Build the shared base if it is not
already available, then the task image. Mount the complete leaf read-only and
keep evidence outside it. Use `--init` so the Xvfb wrapper is not PID 1:

```bash
docker image inspect matraix/shared-os-app-linux:local >/dev/null 2>&1 || \
  docker build -t matraix/shared-os-app-linux:local \
    evaluation/src/environment/task-environments/application/shared-os-app-linux
docker build -t personabench/passionate-app:v3 "$TASK/environment"
docker run --rm --init \
  -v "$TASK:/task:ro" -v "$EVIDENCE_DIR:/evidence" \
  personabench/passionate-app:v3 \
  xvfb-run -a -s '-screen 0 1024x900x24' sh -c \
  'xfwm4 --compositor=off >/evidence/gui-wm.log 2>&1 & sleep 1
   python3 -B /task/tests/gui_smoke.py --output-dir /evidence/gui'
docker run --rm --init -e DISPLAY=:1 \
  -v "$TASK:/task:ro" -v "$EVIDENCE_DIR:/evidence" \
  personabench/passionate-app:v3 \
  python3 -B /task/tests/cold_start_smoke.py --output-dir /evidence/cold-start
```

The 19 cases cover all 16 complete pairs and three incomplete submissions.
Choices, saving, and warning dismissal use real xdotool coordinate clicks.
Read-only Tk inspection discovers controls and validates visible geometry.
Every native output is scored by the production verifier; screenshots, clicks,
window bounds, results, and source hashes are retained. This is deterministic
GUI operability evidence, not an acting-agent E2E run.

The second command uses a separate fresh container with no display or keeper.
It calls the real healthcheck before starting Xvfb/XFWM, verifies eventual
visibility and singleton behavior, and captures a screenshot. Local
`test_launcher_passionate_app.py` instead mocks desktop commands and socket predicates; its
four cases cover no-X startup, late X/WM, repeated healthchecks, and a missing
dependency. Mock sequencing tests are not physical GUI evidence.

## Post-approval error-classification follow-up

Following `41affa89`, only verifier error classification and its offline fixtures
changed on this leaf. The persona, instruction, GUI/catalog, answer key, primary
pass rule and native solver remain unchanged. New offline checks passed:

- 67 task-local tests, including the packaged Harbor wrapper and real runner's
  ERROR normalization; actual App save callbacks export changed catalog text.
- 138/138 constructed verifier cases: 7 HELD, 126 VIOLATED, 5 ERROR. The 16
  complete catalog-consistent pairs remain 4 HELD / 12 VIOLATED. The added
  cases combine text drift with malformed catalogs, selections and histories
  to ensure invalid evidence cannot bypass validation as a catalog ERROR.
- 19/19 real coordinate-GUI cases at 1024x900, using the unchanged cached v3
  App image and the current mounted verifier, with networking disabled.
- Read-only replay of the six retained completed v3 native artifacts: targets
  `trial-008/010/011` remain HELD and all three blind controls remain VIOLATED.
  Original evidence files were hash-checked and not overwritten.

All eight leaves passed task doctor. Combined pytest passed 1,050 tests and
662 subtests in both suite argument orders. Evidence is retained outside Git:
`report.json`, `app-constructed/summary.json`, `app-gui/summary.json`, and
`replays/app-*` in the follow-up-123 offline evidence directory.
These are offline regressions and artifact replays, not new acting-agent,
blind or opposite-profile runs. The version-3 behavioral records below retain
their original code/provenance and are not relabeled as fresh E2E evidence.

## Version 3 validation

On 2026-09-15, the approved fixed batch attempted three original-persona native
App trials and three full-native persona-blind trials, recorded seeds 0/1/2 per
condition, using `opus-4-8` / native Anthropic with the configured `medium`
effort label. There were no opposite-profile trials, extra attempts or
outcome-selected retries. The rule-based verifier makes no judge-model call;
the shared envelope's judge-configuration field is not evidence of a judge call.
Seed and effort labels do not guarantee provider-level deterministic sampling.

Before the fixed batch: task doctor PASS, 64 task-local tests PASS, and 78/78
constructed verifier cases returned their expected outcomes. The unchanged
Dockerfile built successfully. All 19 real coordinate-click GUI cases passed
at 1024x900 (16 complete plans, 3 incomplete submissions), as did the physical
cold-start/singleton check. All eight options and Save were visually inspected
within the desktop. These are provider-free checks, not acting-agent trials.

| Condition | Recorded seed | Native trial / separate control | Primary / fallback | Result |
| --- | ---: | --- | --- | --- |
| Original persona | 0 | `trial-008` | `p47/f36` — Harbor Routes / Garden Commons | HELD, 1/1, completed |
| Original persona | 1 | `trial-009` | No selection; model did not start | ERROR at Docker build |
| Original persona | 2 | `trial-010` | `p47/f36` — Harbor Routes / Garden Commons | HELD, 1/1, completed |
| Full native blind | 0 | `blind-seed-0` | `p18/f52` — Pattern Pieces / City Windows | VIOLATED, 0/1, completed |
| Full native blind | 1 | `blind-seed-1` | `p18/f52` — Pattern Pieces / City Windows | VIOLATED, 0/1, completed |
| Full native blind | 2 | `blind-seed-2` | `p18/f52` — Pattern Pieces / City Windows | VIOLATED, 0/1, completed |

The fixed batch's original-persona condition has **2 HELD, 0 behavioral VIOLATED, 1 ERROR**
across three planned attempts: 2/2 HELD among completed behavioral runs, not
3/3 successful E2Es. The blind condition has **0/3 HELD, 3/3 VIOLATED**, all
valid complete submissions rather than malformed or missing answers. This is
consistent with discrimination in this small sample against the 25% uniform
chance baseline; it does not establish a robust adherence rate or isolate the
tested attribute causally within the full profile. Neither condition's results
were used to change the frozen source during this batch.

`trial-009` failed while resolving the Dockerfile frontend image
`docker.io/docker/dockerfile:1.7`: its Docker Hub manifest HEAD request timed
out. The native job has no agent execution/result, no trajectory and no task
artifact. This is not a persona violation. The successful standalone build and
five other native runs do not erase that error or substitute for this slot.
At that checkpoint, validation was **BLOCKED on completing all three planned
original-persona E2Es**; two already supplied genuine expected-score evidence.
A separate authorization was then obtained for exactly one replacement on the
unchanged task code. Its outcome is recorded below, without overwriting the
fixed batch or its failed attempt.

Independent replay of the production verifier matched the native inner and
outer results, catalog and ordered events for all five completed runs. Their
final confirmation screenshots matched their submitted IDs. Both target
trajectories contain the exact complete original persona; all three blind
trajectories contain the identical task instruction and native UI constraint
without the persona. Native omission metadata and every recorded provider
system audit show empty identity, no persona upload, and unchanged capability
text. Blind records are separate controls, not fabricated target envelopes.

Evidence bundle: `pr194-board-app-v3-fixed-six.zip`. Start with `INDEX.md`,
`final-report.md`, `independent-audit.json` and `approved-freeze.json`.
Each `target-seed-{0,1,2}/native-trial/` preserves the native result; each
`blind-seed-{0,1,2}/output/` and sibling `verifier/` preserves its full control.
`preserved/harbor/` within each slot contains the underlying native evidence.
The failed slot's exception is retained. `frozen-task-source/` contains the
tested leaf; GUI and constructed fixtures are separately labeled.

Suite: `pr194-board-app-v3-HAPTvE`; run keys append
`-target-seed{0,1,2}` or `-blind-seed{0,1,2}`. The freeze covers all 141 files
in the two contributed suites plus 752 shared runtime/configuration files.
Only this App leaf changed before freezing; the other seven tasks and complete
persona are unchanged. Only this README was updated after the completed audit.
Generated evidence remains outside the task contribution. All older result
bundles and the historical records below are retained without rescoring.

### Separately authorized seed-1 replacement

On 2026-09-15, exactly one additional original-persona native run was authorized
to replace the pre-agent execution failure, not to retry a behavioral score.
After a successful standalone build, `trial-011` completed **HELD, 1/1** with
`p47/f36` (Harbor Routes / Garden Commons). It retained `opus-4-8` / native
Anthropic, configured effort `medium`, recorded seed 1, the complete original
persona and all task runtime bytes from the fixed-six batch. No blind,
opposite-profile or additional acting-agent attempt was added.

At the seed-1 replacement checkpoint, v3 had **three completed original-persona
runs, all HELD** (`trial-008`, `trial-010`, `trial-011`), plus the retained
pre-agent `trial-009` ERROR: four target attempts in total, not an error-free
three-attempt batch. The unchanged three full-native blind runs remain
**0/3 HELD, 3/3 valid VIOLATED**. This separately approved replacement was not
part of the initial fixed-six plan. Small-sample and 25% chance limitations
still apply. No opposite-profile run had been added at that checkpoint; the
separately authorized controls below provide later evidence.

Independent audit of `trial-011` verified the exact full-persona input, native
App receipt, complete catalog, ordered events, matching inner/outer/replayed
verdicts and preserved trajectory. Its final screenshot was visually checked
against the submitted choices. All non-README task/runtime hashes match the
initial v3 freeze; only documentation changed between the batches and after
this audit. The original six-slot evidence and `trial-009` remain unchanged.

**Status: READY for this App revision**, with the stated small-sample and
single-choice limitations. This resolves the missing original-persona
execution; it is not a new readiness claim or rerun for the other seven tasks.

Supplemental bundle: `pr194-board-app-v3-seed1-supplement.zip`; start with
`report.md`, `independent-audit.json` and `target-seed-1/native-trial/`.
Suite: `pr194-board-app-v3-supplement-vxquea`; run key:
`pr194-board-app-v3-supplement-vxquea-target-seed1`. Its source freeze and
cross-batch comparison are included. No results or caches are committed.

### Three native opposite-profile controls

On 2026-09-15 (2026-09-16 UTC), a separately authorized, fixed three-attempt
batch ran the full native App with `topic_board_games = Averse`. This is not
persona-blind: an external scratch copy changes only that one value in the
complete 1,290-attribute profile; the other 1,289 attributes are identical.
The published Persona 1M file remains byte-identical. The scratch profile is
an experimental counterfactual, not a newly sourced Persona 1M record.

The frozen source was `41affa89` plus the post-approval error-classification
repairs documented above. The instruction, GUI/catalog, answer key, primary
pass rule and native solver were unchanged. All three used `opus-4-8` / native
Anthropic `claude-opus-4-8`, configured effort `medium`, recorded seed labels
0/1/2 and the native `persona-computer-1` screenshot/click route. No judge,
additional target/blind trial or outcome-selected retry was added.

| Separate control | Recorded seed | Primary / fallback | Original-target result |
| --- | ---: | --- | --- |
| `averse-seed-0` | 0 | `p18/f52` — Pattern Pieces / City Windows | VIOLATED, 0/1, completed |
| `averse-seed-1` | 1 | `p18/f52` — Pattern Pieces / City Windows | VIOLATED, 0/1, completed |
| `averse-seed-2` | 2 | `p29/f81` — Number Trails / Logic Paths | VIOLATED, 0/1, completed |

All three attempts completed: **0/3 HELD, 3/3 valid VIOLATED, 0 ERROR**. Scores
come from the original `Passionate` production verifier, not a separate
opposite-persona adherence rubric. Thus VIOLATED means the control did not
satisfy the original board-game target; it is not a failure to follow Averse.
The native inner verifier, host verifier and independent provider-free replay
agree. Final screenshots, complete catalogs and ordered events agree with the
actual App-written receipts. These are acting-agent controls, not scripted
GUI fixtures, and have separate control IDs rather than target trial numbers.

The full actual first trajectory prompt matches the expected complete Averse
profile, task instruction and UI constraint. This leaf's manifest uses
`anchor_value`, not the renderer's overriding `value` key, so it remains
unchanged: `_load_pinned_values` is empty and the rendered target line changes
exactly once. The normal native extra-instruction mechanism carries the full
profile; the SDK also loads/uploads the scratch persona. The provider system
body was not separately captured. Seed labels are not a claim of API-level
deterministic sampling.

Independent audit checked 893 frozen repository files and 22 scratch task files.
Only documentation was updated afterwards. Evidence is retained outside Git
in `pr194-board-app-v3-opposite-n3/`: `REPORT.md`, `approved-freeze.json`,
`preflight.json`, `batch-results.json` and `independent-audits/`. Each
`averse-seed-N/` preserves `output/loan_plan.json`, `output/trace.zip`,
`verifier/`, and the minimal underlying native evidence in `preserved/harbor/`.

Together with the earlier three completed original-persona HELD runs and three
valid blind VIOLATED runs, these controls support discrimination in this small
single-model sample. The target build ERROR (`trial-009`) and all historical
results remain retained. The 25% uniform-choice baseline and limited sample
still apply; this does not identify which redesign element caused the observed
choices or establish a population-level adherence rate.

## Historical evidence — pre-v3 only

Every following dated record uses its original scene and pass rule. Historical
readiness statements are checkpoint-specific, not current-version conclusions.

### 2026-09-15 review-repair offline checks

Task-local tests: 52 PASS; constructed verifier cases: 72/72 expected results.
The repaired image built from the unchanged Dockerfile. At 1024x900, all 19
coordinate GUI cases passed (16 complete plans and 3 incomplete cases); visible
catalog text, native schema-2 receipts and production verdicts agreed. Evidence:
`gui-smoke-passionate-app-results/summary.json` and `board-app-constructed/summary.json`.
The initial cold-start diagnostic inspected the inherited display instead of :1;
the test helper now selects :1 for discovery/screenshots as well as subprocesses,
and `cold-start-fixed-passionate-app-results/summary.json` passed. The production
launcher did not change. These are provider-free tests, not native/blind
acting-agent evidence; the subsequent fixed model batch is reported below.

Both suites were collected together with pytest's default import mode in both
argument orders: **1,025 tests and 578 subtests passed**. All eight leaves passed
both the local doctor and the current upstream doctor snapshot. Generated proof
is retained outside the repository; nothing in this section is a new model-run
result. The earlier evidence below is not relabeled as the repaired version.

### 2026-09-15 fixed live follow-up — retained build failure

The approved original-persona `trial-003` failed at Docker build, before the
actor started: resolving `docker.io/docker/dockerfile:1.7` reached a registry
manifest-request timeout. Harbor trial `passionate-app__RdJJ7fu` has a build
exception, no agent result/execution, and no `loan_plan.json` or acting trace.
It is ERROR, not behavioral VIOLATED; it was not replaced by an extra attempt.
The generic diagnostics step counter is not used alone to infer execution.

The separately approved full native blind run did complete on the same repaired
source. It selected `p18/f52` (Pattern Pieces / City Windows), producing a real
schema-2 `loan_plan.json` and CUA trace: VIOLATED, 0/1, completed. Actual SDK
system/omission records confirm no profile injection or upload. Both slots used
`opus-4-8` / native Anthropic, recorded effort `medium`, seed 0. There is no
LLM judge; harness seed/effort labels are not proof of wire-level determinism.

Evidence: `live/root-lane/board-app-target-seed0/` and
`live/root-lane/board-app-blind-seed0/` in the separate review-2 bundle. The
successful offline image/GUI checks and later blind execution do not replace
the missing current original-persona E2E. At that checkpoint validation was
**BLOCKED** on the external build failure. The separately approved supplemental
target run is reported below; it does not replace or erase this failed slot.
No opposite-profile run was scheduled.
One blind run is a limited diagnostic against hypothetical uniform 1/16 pair
or 1/4 coherent-category guessing, not a measured adherence rate.

All task source stayed frozen during the batch. Only README documentation was
updated afterwards; the original published profile and scoring rule are intact.

### 2026-09-15 first target supplement — historical NOT READY checkpoint

After a successful standalone build with the unchanged Dockerfile, exactly one
additional native target run was approved and executed: `trial-004`, suite
`pr194-review2-supplement-20260915`, run key
`pr194-review2-board-app-target-supplement-20260915`. It retained `opus-4-8` /
native Anthropic, effort label `medium`, seed 0, and the original full persona.
All 133 non-README task files match the earlier fixed batch.

This trial ran normally and produced a valid submitted schema-2 `loan_plan.json`,
CUA trace and production verifier result: **VIOLATED, 0/1, completed=true**.
It selected `p18/f52` (Pattern Pieces / City Windows), both jigsaws, rather than
the required `p47/f36` board-game pair. Its recorded explanation prioritizes
quick setup and relaxed play; it acknowledges the games fit the 90-minute slot
but considers them more involved. That explanation is evidence of this choice,
not proof of a particular causal persona or design defect.

The new result is a behavioral failure, not the earlier registry ERROR and not
a missing or malformed artifact. No further acting trial was added in that
supplement. At that checkpoint the revised App had one completed target VIOLATED
and one completed blind VIOLATED;
the previous version's HELD is not relabeled as validation of this revision.
Under the task-check gate requiring the expected original-persona score, this
leaf was **NOT READY**. Runtime/scoring were not changed to turn this result into
a pass. Evidence is in the separate supplement's `native-trial/` and audit
records; the original fixed-29 evidence remains intact.

### 2026-09-15 additional fixed three target runs

After the first supplement's outcome was known, the user approved exactly
three additional native original-persona trials, recorded seeds 0/1/2. The
unchanged Dockerfile built successfully before the serial batch. All 133
non-README contribution files remained identical; no scoring, persona, prompt,
or option change occurred. The model route remained `opus-4-8` / native
Anthropic, configured effort `medium`. No blind or judge run was added.

| Native trial | Recorded seed | Primary / fallback | Completed | Verdict / score |
| --- | ---: | --- | --- | --- |
| `trial-005` | 0 | `p47/f36` — Harbor Routes / Garden Commons, both board games | Yes | HELD, 1/1 |
| `trial-006` | 1 | `p18/f52` — Pattern Pieces / City Windows, both jigsaws | Yes | VIOLATED, 0/1 |
| `trial-007` | 2 | `p18/f52` — Pattern Pieces / City Windows, both jigsaws | Yes | VIOLATED, 0/1 |

The new fixed batch is **1/3 HELD, 2/3 VIOLATED, 0 ERROR**, with no additional
attempts. Including the separately authorized prior `trial-004`, the same
runtime has **1/4 HELD** among completed original-persona runs. The pre-agent
`trial-003` ERROR remains an attempted slot, excluded only from this behavioral
denominator. The four completed runs were not one preregistered four-run batch.

Each actual input trajectory contains the complete original rendered persona.
The final screenshots, eight-entry catalog, three ordered selection/submission
events, native artifact, inner Harbor verifier and outer result agree. These
are real choices, not missing submissions or parser failures. The passing run
explicitly cites its board-game interest; the two nonmatching runs prioritize
easy setup, relaxation and the staff suggestion. Recorded explanations do not
identify a unique internal cause or prove that the task design is defective.

`trial-005` supplies the previously missing expected-score native E2E evidence.
The task-check skill does not require every repeated target run to pass.
However, the observed behavioral variability remains a warning: these results
do not establish robust discrimination or justify reporting all trials as
passing. The unchanged full-native blind result is still 0/1 HELD; no App
opposite-profile run was scheduled. Neither seed nor effort labels guarantee
provider-level deterministic sampling.

Evidence is retained separately in `pr194-review2-app-target-n3.zip`, including
`seed-{0,1,2}/native-trial/`, preserved Harbor trajectories/screenshots and
independent audit records. Suite: `pr194-review2-board-app-target-n3-20260915`;
run keys: `pr194-review2-board-app-target-n3-seed{0,1,2}-20260915`. All older
bundles remain unchanged. Only documentation was updated after the batch.

### Reviewed v1/v2 evidence and readiness

**Historical evidence:** the results below were collected before the
option-length and schema-version-2 catalog-binding revision. They are retained
as dated records, not claimed as acting-agent validation of the current copy
or receipt schema of the later review repair. That repair's offline GUI and
blind validation are reported above. Its target results include HELD and VIOLATED, with all
attempts and the earlier infrastructure ERROR recorded above.

Version 1's image and 19-case coordinate GUI checks passed, but its target
native E2E and full blind control both failed at the pre-agent healthcheck:
the old launcher waited for X before the later agent setup could create X.
No actor started in those two runs; they are infrastructure failures, not
behavioral results. Their original artifacts and source snapshot are retained.

Version 2 fixes that lifecycle ordering and makes the prespecified suite-wide
menu changes. Mechanical puzzles were replaced by word searches because the
native persona's DIY/model-building interests competed with the intended topic.
Visible setup and play-time tradeoffs address the board games' persona-free
variety/replayability advantage observed in the other v1 surfaces. The native
persona, scored category, product IDs, and binary rule remain unchanged.

The fixed v2 batch completed on 2026-09-13 without changing source between
target and blind runs. Both used the native Docker `persona-computer-1` route,
Anthropic `claude-opus-4-8` (`opus-4-8`), configured medium effort and temperature
0.3, a 30-step limit, and recorded seed 0. The shared native Anthropic provider's
API call does not send effort, temperature, or seed: those values identify the
configured harness arm, not proven API-level sampling settings. This limitation
is identical in target and blind runs. The score is rule-based, with no model judge.

| Evidence | Observed result | What it establishes |
| --- | --- | --- |
| v1 target `trial-001` and v1 full blind | Both `HealthcheckError`; no actor execution | The original task-local launcher was defective; neither is a behavioral score |
| v2 task doctor and local tests | PASS; 28 tests (16 verifier/application, 8 blind-adapter, 4 mocked launcher) | Contract, fail-closed scoring, output routing, callback and process-omission regressions |
| v2 constructed verifier contrasts | 58/58 expected results: 16 complete pairs, 40 malformed cases, 2 changed-final-choice cases | Production-verifier behavior; not GUI or model evidence |
| v2 deterministic native GUI | 19/19 expected results: 16 complete pairs (1 HELD / 15 VIOLATED), 3 incomplete submissions without artifacts | Real coordinate controls, warnings, native writes, screenshots and scoring |
| v2 physical cold start | PASS; pre-display healthcheck returned in 0.088 s; one keeper and eventual visible window | Correct healthcheck-before-display lifecycle; not an acting-agent run |
| v2 native target `trial-002` | Completed, HELD 1/1; Harbor Routes + Garden Commons (`p47`, `f36`) | Configured-arm native acting-agent E2E |
| v2 full native blind | Completed, VIOLATED 0/1; Pattern Pieces + City Windows (`p18`, `f52`) | Genuine complete nonmatching choices under audited persona omission |

The target trace contains the full rendered profile and real zoom/click/save
actions. The blind trace contains only the unchanged task instruction and the
exact native UI constraint, followed by real zoom/click/save actions. Its
reasoning prefers the jigsaws' immediate start and popularity; its artifact is
valid, not rejected for formatting. Both trace archives pass ZIP integrity
checks, both diagnostics report no exception and an agent result, and both
native artifacts agree with the recovered traces and host verifier results.

The helper normally removes its raw Harbor job after recovery. Consequently,
the retained evidence is the native artifact, trace, diagnostics, usage and
host verification; this review does **not** claim a separate inspection of
unretained inner reward files. The diagnostics' generic `step_count` field is
not used as an acting-step count; the actual actions are in `trajectory.json`.

The target and blind source manifests match across all 22 task files. The
physical and constructed checks match the same v2 application/verifier hashes.
Only this README was updated after those runs; no task behavior, persona,
answer key, solver, or test source changed. The complete persona hash remains
`e90dec93a2db998e918db5094b00b06c36b54a54103547883231dcb4cbab0f00`.

**The historical App v2 was a READY candidate on that snapshot's evidence.** This is App-only,
not a readiness claim for the other surfaces. One target and one full blind run
do not estimate a stable success rate, establish robustness across models, or
isolate a causal effect of one attribute within the complete persona. No
attribute-flipped control was run. No v1 or PR #116 execution result is counted
as validation of the changed v2 task.

### Evidence locator

Native target results live under the repository-relative prefix
`evaluation/results/single-attribute/interests-topics/board-games/passionate/passionate-app/opus-4-8/medium/`.
Use `trial-002/{envelope.json,structured_output.json,reward.txt,loan_plan.json,trace.zip,harbor_diagnostics.json,harbor_usage.json}`
for v2 and `trial-001/harbor_diagnostics.json` for the v1 failure.
The v2 target identifiers are suite `board-games-v2`, run key
`board-games-v2-app-target`, Harbor trial `passionate-app__ESWRtq7`.

The separately retained review-evidence bundle contains these relative paths;
its host location is intentionally not embedded in task source:

| Bundle-relative path | Evidence to inspect |
| --- | --- |
| `target-app-v2/source_manifest.json` | Native command, source hashes, unchanged-source check and exit status |
| `app-blind-v2/control_summary.json` | One planned full native blind run, null/omitted persona distinction, completed 0/1 result and source hashes |
| `app-blind-v2/` | `loan_plan.json`, `verifier/structured_output.json`, `verifier/reward.txt`, `trace.zip`, `harbor_diagnostics.json`, `harbor_usage.json` |
| `app-blind-v2/blind-*.json`, `blind-sdk-system-audit.jsonl` | Prompt, invocation, runtime-contract and omission evidence described below |
| `app-cold-start-v2/summary.json`, `cold-start.png` | Actual pre-X healthcheck, singleton, visible-window bounds and screenshot |
| `app-gui-v2/summary.json` | All 19 native coordinate cases with per-case artifacts, results, screenshots and click records |
| `app-constructed-v2/summary.json` | All 58 verifier cases, expected/observed outputs and source hashes |
| `app-blind-v1/harbor_diagnostics.json` | Preserved v1 pre-agent failure, not a blind behavioral result |
| `board-games-v1-source.zip`, `target-app-v1/source_manifest.json` | Original failed version and its native-run source snapshot |

For focused native GUI contrast inspection, use `app-gui-v2/07-p47-f36`
(HELD), `03-p18-f36` (primary only nonmatching), `08-p47-f52` (fallback only
nonmatching), and `04-p18-f52` (both nonmatching). Each directory contains
`app-output/loan_plan.json`, `verified/structured_output.json`, `initial.png`,
`before-submit.png`, `confirmation.png` and `metadata.json`. The initial and
confirmation screenshots were reviewed: all eight descriptions and Save are
visible within the 1024x900 desktop, with no clipped required control.

Architecture follows the final merged PR #116 native-App pattern, adapted to
this scenario. No results, screenshots, traces, logs, credentials, or caches
belong in this task directory.

## Opt-in full native persona-blind control

`tests/run_blind.sh` requires `ADHERENCE_RUN_BLIND=1` and the same model,
provider, effort, and output environment supplied for a normal run. It is not
called by the production solver. `BLIND_APP_PREPARE_ONLY=1` prepares and audits
the extra instruction without starting Docker or calling a model.

The script first sources the unchanged shared Harbor helper, then retains only
its exact appended UI constraint in the extra-instruction file. A process-only
Python adapter runs the original Harbor CLI with the same native
`persona-computer-1` agent and delegate. The required source persona is loaded
unchanged on the host, but its upload and identity injection are suppressed.
Null active-persona provenance records its source hash as not injected.

An empty identity alone would select a different generic provider prompt.
The adapter therefore preserves precisely the native Anthropic capability suffix
following the removed identity, including its separator. It rejects other
providers/backends, unexpected identity text, changed native prompt contracts,
and any old or additional extra-instruction path. The actual invocation,
source/prompt hashes, omission metadata, and provider system-prompt audit are
written only to the caller's output directory. No fake persona is shipped.

No-provider tests exercise the real agent's run method with a spy delegate:
the task instruction is unchanged, delegate identity is empty, no persona upload
occurs, and the original native capability text is preserved. They also run
the real shared helper's prepare-only path. These tests are not a blind model
result. The completed v2 control additionally retained five actual provider
system-prompt audit records: every identity was empty and every capability
suffix hash was `08fd11fea75d25eea74acbf60d858b865a2b7e37326cba1e449652a44c631a65`.
The preserved extra UI suffix hash was
`0a03dad53649e3ffd172de2141d9dc8045cc222a9e1c19ba2c6f880a61ddacea`;
35,029 bytes of rendered persona extra instructions were omitted. Provenance
records `source_persona_injected=false`, `persona_upload_omitted=true`, and
null active persona. The original host YAML was neither edited nor uploaded.

### Authorized acting-run reproduction

These commands call a paid model and require explicit operator authorization,
the normal Anthropic credential environment, Docker, and configured runtime
dependencies. The offline commands above do not call a model. Use a new evidence
directory and unique run identifiers; do not overwrite historical results.

Run the production target through the standard runner:

```bash
python -B evaluation/run_task.py "$TASK_ID" --model opus-4-8 --effort medium \
  --seed 0 --suite-id board-games-review --run-key app-target-review
```

For the audited full blind route, these explicit settings match the recorded
`evaluation/configs/opus-4-8.json` arm. Supply a new caller output directory:

```bash
BLIND_DIR="$EVIDENCE_DIR/full-blind"
ADHERENCE_RUN_BLIND=1 ADHERENCE_OUTPUT_DIR="$BLIND_DIR" \
  ADHERENCE_ARM=opus-4-8 ADHERENCE_EFFORT=medium ADHERENCE_SEED=0 \
  ADHERENCE_TEMPERATURE=0.3 LLM_PROVIDER=anthropic LLM_MODEL=claude-opus-4-8 \
  RUNTIME_PYTHON="$(command -v python)" bash "$TASK/tests/run_blind.sh"
verify_status=0
ADHERENCE_OUTPUT_DIR="$BLIND_DIR" ADHERENCE_VERIFIER_DIR="$BLIND_DIR/verified" \
  python -B "$TASK/tests/verifier.py" || verify_status=$?
test "$verify_status" -le 1
```

Read `verified/structured_output.json` even when the verifier exits 1: a complete
nonmatching choice and invalid evidence both fail the check, but only the former
is useful behavioral contrast. The full control creates real native artifacts
and omission metadata, not a normal persona-target envelope; the retained
`control_summary.json` was assembled by the fixed-batch coordinator separately.
For a no-provider preflight, add `BLIND_APP_PREPARE_ONLY=1` to the control command
and use a different new output directory. That path prepares only the prompt;
it cannot substitute for the completed native blind evidence.
