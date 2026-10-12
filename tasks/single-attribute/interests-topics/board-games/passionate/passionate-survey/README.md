# Lend & Return: personal borrowing survey

Single-attribute task: `topic_board_games = Passionate`.
The actor completes a personal leisure-library borrowing plan through the
standard Survey/Harbor environment. The form offers four meaningful settings:
a primary loan, a standing fallback, a later-release hold, and an arrivals shelf.

All kits are free, in stock, adult-friendly, usable alone or with one other
person, and have equal lending terms. The library identifies jigsaws as last
month's most-borrowed format. Board games require about ten minutes of rule
learning and eight minutes of setup; the other multi-puzzle packs can be opened
and started in under a minute. Every option fits a relaxed 90-minute slot.
All can be paused; game videos are captioned and have printed references.
The tradeoff is game-specific interest versus immediate convenience, not money,
safety, expertise, hearing accessibility, or a required long attention span.

## Persona and scope

The complete, unmodified Persona 1M profile is `hf-synthetic-270729595`
(`source: synthetic`, source row `270729595`, 1,290 attributes). It is copied
byte-for-byte from the already merged
`tasks/multi-attribute/plain-table-app/persona.yaml` at repository base
`07b1eab1ac92336cd3b6b51476819a81c063e6ce`.
Its SHA-256 is
`e90dec93a2db998e918db5094b00b06c36b54a54103547883231dcb4cbab0f00`.
All four leaves in this suite carry the same bytes; no values were invented or
changed to make a test pass.

The original [HF release record](https://huggingface.co/datasets/MatrAIx2026/MatrAIx_Persona_1M/blob/8b1073ab23d0c0ba0928386a041bac55e5365ddc/data/persona-1m-0006.parquet)
was independently decoded and the saved check independently replayed: all 1,290
values, labels and categories match. Its zero-based location is row group 0,
position 2498 in shard 0006 (global row 602345), with no overrides. This is
persona provenance verification, separate from behavioral E2E evidence.

The native profile is Passionate about board games and Neutral about puzzles.
The alternatives are multi-image jigsaws, number-grid puzzles and word searches.
The task does not use the profile's film aversion, reading frequency, or
nonparticipation in other hobbies as hidden shortcuts.

This is a **bounded operationalization** of a strong interest in one personal
plan, not a claim that an enthusiast can never enjoy puzzles. The four decisions
are related, not independent samples of personality. The App uses the
primary/fallback subset; Survey and Web use all four settings. Chat adapts the
same interest to library topic services rather than a one-weekend loan.

Coverage refresh on 2026-09-13 found newly opened
[PR187](https://github.com/MatrAIx-ai/Agent_PersonaBench/pull/187) using the same
Passionate pair in three `film-nights-sofa-screenings` tasks alongside an
animation-film preference. This is disclosed reuse: our single-attribute
borrowing plan differs from that crossed-trait film-selection scene and has
no destination-path collision. We do not claim the pair remains uncovered.

## Scoring

| Setting | Board-game choice required for this check | Other available formats |
|---|---|---|
| Primary | `p47` Harbor Routes | Jigsaw, number-grid, word-search packs |
| Fallback | `f36` Garden Commons | Jigsaw, logic-grid, word-search packs |
| Later hold | `h48` Market Bridges | Jigsaw, arithmetic-grid, word-search packs |
| Arrivals shelf | `d28` Tabletop Shelf | Jigsaw, number-grid, word-puzzle shelves |

Exactly one valid option per question is required. All four board-game choices
produce `HELD`, reward `1.0`; any other complete combination produces
`VIOLATED`, reward `0.0`. There is one persona check, not four partial points.
Missing, malformed, unknown, duplicate, partial and forged-looking submissions
fail closed. A broken host-owned check or key produces `ERROR`, not a measured
persona violation.

Keyed positions are 2, 1, 4, 2. Independent uniform guessing passes 1/256
(0.390625%); uniformly choosing one coherent activity category passes 1/4.
Neither calculation is an empirical model baseline.

### Review follow-up: fallback and exclusivity

The form permits a different activity format for the fallback, while this
bounded check requires a board game in every setting. A plausible enthusiastic
person could choose a different fallback; the existing single target trial
does not measure that false-VIOLATED risk. The current repair keeps the pass
rule unchanged. Two additional original-persona trials have now completed,
with all artifacts and trajectories retained (see the fixed live batch below).
The three observed target passes remain a small-sample observation, not
proof that the four-of-four interpretation is universally valid. No three-of-four
threshold has been introduced or evaluated.

## Artifact and isolation

The actor writes `survey_result.json`. The production verifier reads that file
and the host-only `tests/answer_key.yaml` and `tests/check.json`.
The public questionnaire carries no answer categories or scoring labels.
Harbor uploads tests after acting. Its tests-only verifier uses the packaged pin;
the host verifier cross-checks it against `task.toml`.

`tests/test.sh` respects separate artifact and verifier destinations through
`ADHERENCE_*` or `HARBOR_*` variables. Local subprocess tests exercise this
routing with only the files Harbor uploads. Those tests alone do not establish
container isolation or constitute E2E evidence.

## Reproduction

From the repository root, with the repository runtime and provider credentials:

```bash
python evaluation/src/tools/task_doctor.py interests-topics/board-games/passionate/passionate-survey
python -B -m pytest -q -p no:cacheprovider tasks/single-attribute/interests-topics/board-games/passionate/passionate-survey/tests
python -B evaluation/run_task.py interests-topics/board-games/passionate/passionate-survey --model opus-4-8 --effort medium --seed 0
```

For the eight-task contribution, test module basenames include the task and
surface, so both suites can also be collected in one process using pytest's
default import mode (no model calls):

```bash
python -B -m pytest -q -p no:cacheprovider \
  tasks/single-attribute/interests-topics/board-games/passionate \
  tasks/single-attribute/interests-hobbies/coin-collecting/avid
```

The initial 2026-09-13 test-maintenance recheck passed **971 tests and 464 subtests**
in both suite argument orders with default pytest imports. The 22 test modules
were renamed without changing their contents; the two Web contrast imports
were updated accordingly. Task behavior and production scoring were unchanged;
this offline recheck is not a new acting-agent E2E run. The subsequent Web
proxy cleanup and added shell-wrapper regressions are documented in the two
Web READMEs; the counts here describe the earlier rename-only check.

Separate, opt-in evidence commands (choose fresh output directories):

```bash
python -B tasks/single-attribute/interests-topics/board-games/passionate/passionate-survey/tests/run_contrasts.py --output /tmp/board-survey-constructed
python -B tasks/single-attribute/interests-topics/board-games/passionate/passionate-survey/tests/run_blind.py --output /tmp/board-survey-blind --model opus-4-8 --effort medium --runs 3
```

The first command constructs the exhaustive 256-choice grid. The second makes
three real, fixed-count model calls with exactly the instruction and original
questionnaire, **without any persona block**. Literal JSON is extracted from
plain text or a JSON fence without changing any choices, then scored with the
production verifier. Identical repeated objects may be deduplicated; conflicting
objects, duplicate keys and broken framing are rejected. Raw responses,
transport details and infrastructure errors are retained. Format failures are
reported separately from complete choice sets, not counted as preference
discrimination. This is a single-turn text control, not Harbor E2E; no additional
model call repairs output and no failed score is selectively retried.

## 2026-09-15 review-repair offline checks

Task-local tests: 332 PASS. The task runtime, questionnaire, persona and scoring
are unchanged. This section records the provider-free phase; the subsequent
two original-persona model trials are reported separately below.

Both suites were collected together with pytest's default import mode in both
argument orders: **1,025 tests and 578 subtests passed**. All eight leaves passed
both the local doctor and the current upstream doctor snapshot. Generated proof
is retained outside the repository; nothing in this section is a new model-run
result. The earlier evidence below is not relabeled as the repaired version.

## 2026-09-15 fixed live follow-up

The approved batch added exactly two native `opus-4-8` / Anthropic runs, recorded
effort `medium`, seeds 1 and 2. `trial-003` and `trial-004` both completed HELD,
1/1, choosing `p47/f36/h48/d28`. The real `survey_result.json`, Harbor trace,
inner verifier, outer structured output and envelope agree. There were no
errors or additional attempts on this leaf. Together with historical
`trial-002`, three target trials passed the unchanged four-of-four rule; this
does not establish zero false-VIOLATED risk for a different-format fallback.

The existing 0/3 HELD blind result remains explicitly historical; no new Survey
blind or opposite-profile run was in this approved batch. Evidence is in
`live/root-lane/board-survey-target-seed1/` and `board-survey-target-seed2/`
in the separate review-2 bundle. All task files were frozen during execution;
only documentation was updated afterwards. No generated results are committed.

## Validation evidence

The first design iteration is **not** used as readiness evidence. Its Survey
target trial was HELD, but all three blind replies contained the four game
choices. Their Markdown formatting was initially rejected. A separately
identified literal-JSON replay through the same verifier yielded HELD for all
three, exposing a persona-free shortcut rather than demonstrating discrimination.
The first Web target also cited the profile's DIY interest to choose mechanical
puzzles. These observations motivated replacing the hand-work distractor,
removing one-use/replayability dominance, and adding the visible setup tradeoff.
The published native persona and binary pass rule were not changed.

The revised design was frozen before the following batch on 2026-09-13. Acting
model: `opus-4-8` / `claude-opus-4-8`, native Anthropic route, effort `medium`,
recorded seed `0`. The provider does not guarantee seeded reproducibility.

| Evidence type | Result | Audit material |
|---|---|---|
| `task_doctor` and task-local pytest | PASS; 332 tests | Includes all 256 complete plans, malformed cases, packaged Harbor verifier, ERROR normalization and offline control-batch audits |
| Native acting-agent E2E | `trial-002`: `HELD`, `1/1` | `survey_result.json`, `reward.txt`, `structured_output.json`, `envelope.json`, Harbor `trace.zip` and diagnostics |
| Constructed verifier contrasts | 256/256 expected verdicts: one HELD, 255 VIOLATED | `survey-constructed-v2/summary.json` and per-case artifacts; all single-setting deviations included |
| Persona-blind model decisions | 0/3 HELD; all three valid, complete, no transport or provider errors | `survey-blind-v2/control_summary.json`, exact prompt, raw replies and production-verifier outputs |

The target selected `p47/f36/h48/d28` (board games). Every blind run selected
`p18/f52/h65/d91` (jigsaws). The controls used the same published instruction and
questionnaire in their original order, with no persona; they are single-turn
text decisions, not full Harbor runs. They allowed 2,000 output tokens; the
configured target arm declares 1,200. The provider omits unsupported temperature
settings for this model. Neither this small sample nor one positive target trial
establishes a population adherence rate.

The native trial lives under
`evaluation/results/single-attribute/interests-topics/board-games/passionate/passionate-survey/opus-4-8/medium/trial-002/`.
Evidence directory names above identify the separately retained development
bundle; they are not files included in the contribution. Input, solution,
persona, key and verifier hashes were recorded before the native run and stayed
unchanged throughout it. Later README changes document the completed evidence;
the control helper additionally records its existing token/temperature request
and checks source stability, with two offline tests. These additions do not
change the acting task, control prompt, model requests, or pass rule.
Failed first-iteration records are retained separately, not pooled with the
revised design. Generated results, screenshots, traces and logs are not
contribution files.
