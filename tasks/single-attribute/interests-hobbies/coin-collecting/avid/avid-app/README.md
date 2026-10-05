# Home Hobby Support Desk — native App

One single-attribute check: `hob_coin_collecting = Avid`. A real Tkinter packing
workbench lets the user compare four support packs for future personal use,
configure the workspace, outer case and pickup method, inspect the resulting
packing list, and confirm a local reservation. Nothing is ordered externally.

## One preference, not four hobby tests

| Field | Choices | Verification role |
|---|---|---|
| Pack | `b29` Page Layout; `b73` Coin Collection; `b46` Fold & Keep; `b85` Piece & Pause | Only scored choice; coin support holds |
| Workspace | `w14` full fold-out panel; `w62` two smaller linked panels | Required but unscored; changes panel quantity |
| Outer case | `c83` reusable zip folio; `c25` shallow carry box | Required but unscored; changes packing list |
| Collection | `r45` staffed desk; `r82` collection locker | Required but unscored; changes collection instructions |

No field is preselected. All offers are free, in stock, compact, brief to set out
and self-paced. Both workspace arrangements provide the same total working area;
both cases fit every pack, and collection methods have identical availability
and price. Each pack contains a working mat, a reusable put-away component and
an illustrated guide. These are support supplies, not complete hobby inventories
or purchases of collectible coins. No owned collection size, identification,
appraisal, investment, expertise or meticulous catalogue is assumed.

Exactly one known option for each field is necessary for a valid reservation.
All eight valid coin configurations score HELD/1.0. All 24 valid alternatives
score VIOLATED/0.0 with `completed: true`. Missing, partial, inconsistent,
unreviewed or malformed evidence fails closed with `completed: false`; it is not
misreported as a completed alternative. A broken verifier contract returns
ERROR/exit 3, including an explicit error criterion preserved by the host runner.

This is a modest, bounded hobby-priority observation. It does not imply that an
avid collector must reject every other hobby or establish a calibrated boundary
between Avid and other collecting levels. The target is the second catalog card.
Uniform pack choice passes **1/4**, equivalently 8/32 complete configurations.
Extra configuration fields do not turn this into a 1/32 or 1/256 preference test.

### Review revision: option-length policy

Normalized pack name plus description is limited to 135–160 characters and
20–24 whitespace-delimited words; descriptions alone are limited to 115–145
characters and 17–20 words. The keyed pack must be strictly between the extremes
for each measurement, so neither longest-only nor shortest-only choice, even
with different tie breaking, selects it. Fixture tests measure the actual App
catalog, export genuine receipts through the App's state machine, and score
those length-only choices using the production verifier. These presentation
checks are not substitutes for native target and persona-blind model runs.

The copy retains all supplied materials and keeps skill, collection size,
inventory logging and collectible supply out of scope in the common terms.
No persona, option ID, pack category or pass rule was changed.

## Persona and coverage

The complete, unchanged profile is `hf-synthetic-483855902`, `source: synthetic`,
with 1,290 attributes. It was copied from the four byte-identical merged
`tasks/multi-attribute/science-books-noromance-*/persona.yaml` files at base
`07b1eab1ac92336cd3b6b51476819a81c063e6ce`. First introduced in
[PR73](https://github.com/MatrAIx-ai/Agent_PersonaBench/pull/73), commit
`199e345ea5de31d0f5f53525065f317af0fbb8f4`, Git blob
`7ce8fca9550059c272fc90ff3a5bc390960ca4a9`.
YAML SHA-256: `63ae1812c33d3926db9bf2e500160923d6b14a5f752c4cd38254e46d96fbf184`.

The original [HF packed record](https://huggingface.co/datasets/MatrAIx2026/MatrAIx_Persona_1M/blob/8b1073ab23d0c0ba0928386a041bac55e5365ddc/data/persona-1m-0006.parquet)
was independently decoded at revision
`8b1073ab23d0c0ba0928386a041bac55e5365ddc`: source index 483855902;
shard 0006, row group 2 / position 5409, shard row 25647, global row 625494
(all positions zero-based). All 1,290 values, labels and categories matched,
with a null missing-value bitmap and zero overrides. Packed-row SHA-256:
`88a69505ef08c378b1fa71a1cca4f061af7f7b0345c1c283f2c5ef6e595330b8`.
This used bounded primary-source byte-range reads, not a complete-shard download;
no full-shard checksum verification is claimed. The selected profile was chosen
through static design comparison, not acting-model outcomes.

Native coin collecting is Avid; general collecting, history and visual art are
Neutral. Scrapbooking is Occasional, origami Curious, and puzzles Neutral, so
alternatives are plausible competing hobbies, not uniformly neutral traits.
Scrapbooking does not require journaling (Never), photo editing or photographic
skill (None). Very short attention and low patience/detail orientation motivate
brief self-paced use. Hard-saver and reluctant-technology traits are not measured
through unequal costs or required digital equipment. English is Fluent C1–C2.

[PR187](https://github.com/MatrAIx-ai/Agent_PersonaBench/pull/187), discovered in
the 2026-09-13 coverage refresh, also uses `hob_coin_collecting=Avid` in
`film-nights-late-show-club-{survey,chat,app}` paired with documentary-film
preference. This is disclosed, non-blocking attribute reuse. Its crossed-trait
film-selection scenario differs from this single-attribute physical-support
reservation, and there is no destination-path collision. Existing stamp and
coin/stamp-fair scenarios are adjacent coverage; this task uses no fair, auction,
swap or appraisal. See the external `COVERAGE-REFRESH-PR187.md` audit record.

[PR200](https://github.com/MatrAIx-ai/Agent_PersonaBench/pull/200) also pins
`hob_coin_collecting = Avid` in its four-surface `quiet-numismatic-archive`
multi-attribute suite, paired with `peeve_being_interrupted = Major peeve`.
It uses the different persona `synthetic-98ba03a0cd7e` and shares no task paths.
This is disclosed, non-blocking attribute reuse in a different scenario.

## Native workflow and artifact integrity

The 940×800 client window fits a 1024×900 Linux CUA desktop. The compact catalog,
all configuration controls and the review button are visible without scrolling.
Review shows the actual five-entry packing list, workspace quantity, case and
collection instructions. Editing destroys the previous review; the changed plan
must be reviewed again. Confirmation writes `hobby_reservation.json` itself.

The receipt contains only observable IDs, packing data, a random session ID,
revision and ordered select/review/edit/confirm evidence. The independent
verifier replays that history and compares the final receipt and review against
its own host-only catalog. It validates exact schemas, types, IDs, quantities,
sequence and stage transitions before applying the one pack-category criterion.
It rejects duplicates, non-finite JSON, excessive sizes/nesting, stale reviews,
extra claims, unknown options and contradictory packing instructions.
This checks internal consistency; it is not a cryptographic proof of human
clicks. Real CUA trajectories provide the interaction evidence for model runs.

Both application copies are byte-identical. Neither exposes a target value,
dimension ID, category map, reward or answer key. Only `tests/answer_key.json`
contains the scoring map, outside acting inputs and the image. Harbor uploads
tests after acting. `tests/test.sh` explicitly enables the tests-only contract
and routes rewards to Harbor's verifier directory; direct host verification
requires the manifest and defaults to the requested output directory.

Publishing uses a flushed temporary file and exclusive atomic linking. Existing
receipts, directories and symlinks are never overwritten. Write failures retain
the review and display an error instead of reporting confirmation. The singleton
launcher acknowledges bootstrap before X exists, then waits for live X and the
window manager before launching; it does not deadlock Harbor's pre-agent
healthcheck. The native solver uses the shared Harbor helper unchanged.

## Reproduce

From the repository root with project dependencies installed:

```bash
TASK=tasks/single-attribute/interests-hobbies/coin-collecting/avid/avid-app
python -B evaluation/src/tools/task_doctor.py interests-hobbies/coin-collecting/avid/avid-app
python -B -m pytest -p no:cacheprovider -q "$TASK/tests"
python -B "$TASK/tests/run_contrasts.py" --output-dir "$PROOF/coin-app-constructed"
```

`PROOF` must identify an external evidence directory; each named output must be
new. The contrast runner authors artifacts and calls the production verifier;
it is not a GUI run. The following provider-free checks operate real Linux UI:

```bash
docker build -t personabench/avid-app:review2 "$TASK/environment"
docker run --rm --init -v "$PWD/$TASK:/task:ro" -v "$PROOF:/evidence" \
  -e PYTHONDONTWRITEBYTECODE=1 personabench/avid-app:review2 \
  python3 -B /task/tests/cold_start_smoke.py --output-dir /evidence/cold-start
docker run --rm --init -v "$PWD/$TASK:/task:ro" -v "$PROOF:/evidence" \
  -e PYTHONDONTWRITEBYTECODE=1 personabench/avid-app:review2 \
  xvfb-run -a -s '-screen 0 1024x900x24' sh -c \
  'xfwm4 --compositor=off >/tmp/hobby-wm.log 2>&1 & sleep 1; python3 -B /task/tests/gui_smoke.py --output-dir /evidence/gui'
```

The GUI driver uses real coordinate clicks for all choices, review/edit/confirm
actions and warning dismissals. Read-only Tk queries check geometry, text and
state. It refuses a baked image whose App source differs from the task copy.
Screenshots and actual app-written receipts are retained externally.

Acting-agent E2E, when authorized and source-frozen:

```bash
python -B evaluation/run_task.py interests-hobbies/coin-collecting/avid/avid-app --model opus-4-8 --effort medium --seed 0
```

The opt-in full native persona-omission control is separate from the solver:

```bash
ADHERENCE_RUN_BLIND=1 ADHERENCE_OUTPUT_DIR="$PROOF/coin-app-blind" \
  ADHERENCE_ARM=opus-4-8 LLM_MODEL=claude-opus-4-8 LLM_PROVIDER=anthropic \
  bash "$TASK/tests/run_blind.sh"
```

It retains the production PersonaComputer1 delegate, provider, UI constraint and
native capability suffix, omitting both persona-prompt paths and persona upload.
Only process-local patches are used; the published YAML and shared runtime stay
unchanged. Prompt hashes, actual invocation, explicit null active-persona
provenance and provider-system-boundary audit are recorded. Offline tests run the
production wrapper path with a mock delegate and confirm no identity or persona
upload, without a provider call. The native helper's 30-step limit is retained.
No opposite synthetic persona is part of this control.

## 2026-09-15 review-repair offline checks

Task-local tests: 123 PASS; constructed verifier cases: 89/89 expected results.
The repaired image built from the unchanged Dockerfile. All 14 coordinate GUI
cases passed at 1024x900, including real reservations, edits, incomplete choices
and safe handling of pre-existing files. Cold start also passed. Evidence:
`gui-smoke-avid-app-results/summary.json`, `coin-app-constructed/summary.json` and
`cold-start-avid-app-results/summary.json`. These are provider-free tests, not
native/blind acting-agent evidence; the subsequent fixed model batch follows.

Both suites were collected together with pytest's default import mode in both
argument orders: **1,025 tests and 578 subtests passed**. All eight leaves passed
both the local doctor and the current upstream doctor snapshot. Generated proof
is retained outside the repository; nothing in this section is a new model-run
result. The earlier evidence below is not relabeled as the repaired version.

## 2026-09-15 fixed live follow-up

On the frozen option-length revision, native `trial-002` completed HELD, 1/1:
`b73/w14/c83/r45` (pack / workspace / case / pickup). The separately approved
full native blind run chose `b85/w14/c83/r45`, a jigsaw reservation, and
completed VIOLATED, 0/1. Both used `opus-4-8` / native Anthropic
`claude-opus-4-8`, recorded effort `medium`, seed 0, with the original native
CUA route. No ERROR, incomplete choice or extra attempt occurred.

The app wrote the real `hobby_reservation.json`; its final selections, packing
list, review, ordered events and production score agree with the CUA trajectory.
Actual SDK system and omission evidence verifies the blind profile was neither
injected nor uploaded. No LLM judge or opposite-profile trial was used. Harness
seed/effort settings do not establish provider-level deterministic sampling.

Evidence: `live/root-lane/coin-app-target-seed0/` and
`live/root-lane/coin-app-blind-seed0/` in the separate review-2 bundle. All task
source was fixed across both trials; only README documentation changed later.
This is one target and one full native blind, not a stable adherence estimate.
The hypothetical uniform pack pass rate is 1/4; the three independent packing
settings are intentionally unscored. This leaf's evidence is not a readiness
claim for the whole eight-task contribution. Historically, the separate
`passionate-app` pre-v3 target build ERROR was followed by a separately approved
VIOLATED result and a later fixed three-run batch with 1 HELD and 2 VIOLATED:
one of four completed pre-v3 target runs was HELD. Those results remain
historical and are not rescored or pooled with the redesigned App.
The [current `passionate-app` v3 evidence](../../../../interests-topics/board-games/passionate/passionate-app/README.md#version-3-validation)
has three completed target runs, all HELD (`trial-008`, `trial-010`,
`trial-011`), plus the retained pre-agent `trial-009` ERROR; its three full-native
blind runs are all valid VIOLATED results. V3's separate 1/4 uniform-choice
baseline is a mathematical chance rate, not the pre-v3 observed HELD fraction.
The later [three native App Averse controls](../../../../interests-topics/board-games/passionate/passionate-app/README.md#three-native-opposite-profile-controls)
also completed as VIOLATED (0/3 HELD, no ERROR); they are separate opposite-profile
evidence, not additional blind or original-persona runs.
The linked README preserves all attempts and the small-sample limitations.
This update does not change or relabel this `avid-app` evidence.

## Historical completed validation — 2026-09-13

The results below predate the option-length revision. They remain historical
evidence for that source snapshot, not new acting-agent results for the revised
copy. The new native target and persona-blind validation on the repaired frozen
snapshot is reported above, without relabeling these older results.

| Evidence | Historical result |
|---|---|
| task_doctor / source isolation | PASS; Linux metadata and identical source copies |
| All task-local tests | 115 PASS |
| Authored verifier contrasts | 89/89 expected, including all 32 valid configurations: 8 HELD and 24 completed VIOLATED |
| Real coordinate GUI | 14/14 PASS: every pack under two configuration sets, empty/partial feedback, edit/review recovery, foreign-file/link/directory refusal |
| Cold launch and singleton recovery | PASS; pre-X healthcheck 0.084 seconds; decorated bounds x25/y49/950×834 within 1024×900 |
| Target native acting-agent E2E | 1/1 HELD, completed; `b73 / w14 / c83 / r82` |
| Full native persona-blind control | 0/1 HELD; completed VIOLATED jigsaw reservation, `b85 / w14 / c83 / r45` |

The tested App source SHA-256 is
`88430bc6b528533c02a7797eff66da1051e05a50c77e1b5ea422f27566870357`.
Passing evidence is in the external `coin-app-constructed-v2`,
`coin-app-gui-v2b`, and `coin-app-cold-v2` directories. These are not committed
results. Early provider-free checks are retained: v1 exposed a clipped footer,
fixed before any model run by natural-height cards and reserved footer space;
test-only display selection, Tcl conversion and dialog-readiness issues were
also corrected. No failed diagnostic is presented as a behavior trial.

The target is the first native acting trial, `opus-4-8/medium/trial-001`, under
`evaluation/results/single-attribute/interests-hobbies/coin-collecting/avid/avid-app/`.
Its suite ID is `coin-collecting-v2` and run key
`coin-collecting-v2-app-target`. It ran 07:22:19–07:23:01 UTC. The full native
blind run, retained separately in external `coin-app-blind-v2`, ran
07:22:23–07:23:08 UTC. Both used `claude-opus-4-8`, Anthropic and the same
production Docker computer-use delegate, task, image, UI and scorer. The `v2`
label identifies the pre-model layout/build revision, not a discarded model
trial; the task manifest version is `1.0`.

The before/after manifests (`coin-target-app-v2/source_manifest.json` and
`coin-app-blind-v2/control_summary.json`) show identical 23-file snapshots and
`source_unchanged: true`. A separate post-run audit reproduced every source hash
before this README-only evidence update. The persona, App, launcher, solver,
tests and scoring behavior were not changed after either run.

Both `trace.zip` files contain six physical coordinate-click actions followed by
`mark_task_complete`: choose pack, pickup, workspace and case, then review and
confirm. Their six ordered artifact events agree with those actions. The actual
review and confirmed screenshots (`screenshot_ep4.webp` and
`screenshot_ep5.webp`) were independently inspected at 1024×900: the complete
packing list and local-only confirmation fit on screen. Replaying both real
artifacts through the unchanged independent verifier reproduced HELD and
completed VIOLATED, respectively. Neither run has a Harbor exception. The
diagnostic `step_count: 0` is an adapter field, not the observed action count.
Raw temporary Harbor jobs were cleaned by the shared helper; no independently
retained inner-Harbor reward is claimed. The retained evidence is the actual
artifact, host verifier result, native CUA trace, diagnostics and Harbor usage.

The omission audit reconstructed the native extra prompt from the unchanged
YAML and matched its recorded hash. The blind trajectory's initial user message
is exactly the original task, the unchanged separator, and the original UI-only
constraint; the native trajectory additionally contains the full rendered
profile. The omitted identity hash also matches the native renderer. All seven
blind provider-system audit records show an empty identity and the exact native
capability suffix, not a replacement generic prompt. Persona upload was omitted,
active-persona provenance is explicitly null, and the original runtime-method
fingerprints match the source inspected after the run. These records are in
`blind-prompt-metadata.json`, `blind-persona-omission.json`,
`blind-runtime-contract.json`, `blind-harbor-invocation.json` and
`blind-sdk-system-audit.jsonl`; this is a full native control, not a text-only
surrogate.

For artifact identification, native receipt SHA-256 is
`f3fa04cb95fd2d0ab328b6e6493a7473f51949d2132e1e110607c9ec82ad41a6`
and blind receipt SHA-256 is
`a2cbeddbf48235223230608a629414482fb4d1f6e350ea9e14ca7ce94e3021f4`.
The unchanged verifier SHA-256 is
`dd46ad57d8db3b679d09fa7d2cc9f62944fee183505af3420aec76ce6039e8aa`.

## Evidence limits and App readiness

The prescribed sample is only one target and one full blind run. The difference
is an observed contrast, not an estimated population success rate, a causal
isolation of one trait from the other 1,289 attributes, or proof that every
avid collector would make this choice. Uniform selection among the four packs
still passes 1/4; workspace, case and pickup are completion details, not extra
persona dimensions. No repetition or reselection was used to obtain a passing
target. This intentionally bounded pack workflow does not become a four-setting
preference test merely because other suite surfaces use a broader workflow.

`medium`, temperature `0.3` and seed `0` are recorded/requested harness settings,
not guaranteed SDK controls. Inspection of the unchanged
`evaluation/src/harbor/agents/computer_1/providers/anthropic.py` shows that this
native provider forwards neither effort, temperature nor seed to
`beta.messages.create`; it uses `max_tokens=4096`, not the outer envelope's
`max_tokens=1200`. There is no claim of deterministic seeded replay or verified
medium-effort inference. Both compared runs use that same provider behavior.
The criterion is rule-based; envelope judge-model metadata does not indicate a
judge-model call for this task.

Historical App candidate verdict: **READY**, with the bounded construct and
small-sample limitations above. The actual target E2E, full native blind
control, malformed/contrast tests, physical GUI checks and artifact/trajectory
audit are complete. This verdict applies only to this App leaf, not to the
readiness of other suite surfaces.
