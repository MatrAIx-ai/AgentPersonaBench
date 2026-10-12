# Reviewer-only design notes: stable versus adaptive organization

This file is intentionally under tests/, outside agent-mounted input/.

## What changed in version 1.1

The probe distinguishes a preference for stable, reusable organization from
competent adaptive, search-first, or context-specific workflows. All options must
complete the same underlying job. Deadlines, reminders, retrieval capability,
workload, handoff content, or total maintenance effort are explicitly matched
where relevant. Distractors no longer depend on forgetting work or giving a
teammate an incomplete handoff.

| Item | Stable-structure choice | Reason to prefer another option |
|---|---|---|
| weekly_tasks | Reuse categories and statuses | Regroup around changing priorities |
| digital_files | Common folder/name template with an exception section | Fit unusual material with project-specific organization |
| calendar_blocks | Recurring allocation pattern | Adapt the sequence to incoming requests |
| email_rules | Stable categories with an explicit cross-topic rule | Organize around changing questions or chronology |
| household_inventory | Fixed names and sections | Organize by meals, natural item names, or shelf location |
| project_handoff | Common section order with cross-references | Explain the unusual dependency in a tailored narrative or map |

Some alternatives are themselves organized; they are not labeled irrational or
incompetent. The measured contrast is consistency of structure, not the mere
existence of any organization. This remains a narrow operationalization of the
broader val_order_structure dimension.

Residual confounds include flexibility, planning style, familiarity with templates,
and representation preferences. The full target profile also says habit_to_do_lists
= Monthly; do not rewrite that value or infer daily checklist use from Core value.
The questions ask about available layout defaults, not actual daily frequency.

## Coverage and control candidate

PR #20 includes val_order_structure = Important across four surfaces:
https://github.com/MatrAIx-ai/Agent_PersonaBench/pull/20
That is the same dimension but a different value. Do not describe this as the
first order/structure task, or claim that this survey distinguishes Important
from Core value without evidence.

A locally available lower-value diagnostic candidate is p-ec140af52f, whose
val_order_structure is Minor, in
tasks/single-attribute/health-lifestyle/diet-type/vegan/vegan-app/persona.yaml.
Preserve its full source file. It is NOT a matched experimental control.

## Scoring and limits

The six-item, one-point-per-matching-choice score uses a provisional 4/6 decision
rule. This is an engineering criterion for this probe, NOT a validated conversion
of "Core value" into a behavioral probability. It does not establish a distinction
between Core value and Important. Do not raise the threshold just to defeat a
baseline. Inspect item-level choices and report sensitivity at 3/6, 4/6, and 5/6
without selecting the most favorable threshold after seeing model results.

All six questions must be answered exactly once. Unknown, cross-question,
duplicate, contradictory, partial, wrong-type, duplicate-JSON-key, invalid-UTF-8,
and excessive-size/depth submissions fail closed. The hidden key remains under
tests/. It is not shipped in the agent-visible input folder.

## Offline regression tests

Run `python tests/test_fixtures.py -v` from this task directory. The host-side
suite uses PyYAML (already part of the repository dependencies); the production
verifier remains standard-library-only.

Tests read the ACTUAL questionnaire and key, rather than maintaining a second
test-only question table. They check all 64 binary adherence patterns, all 24
option IDs, schema agreement with the verifier, and threshold boundaries.
Thirty-six fixed-rank strategies are executed through the real verifier:
display position, lexical ID, alphabetical answer text, character count, and word
count; length ties use display order and both ID orders. Every strategy must fail.
These are finite diagnostics, not proof that every persona-blind strategy fails.

Uniform independent choice yields 154 passing answer vectors out of 4096
(3.759765625%). Negative answer fixtures are scoring-code tests, NOT a neutral
model or contrasting-persona experiment.

## Required behavioral validation before submission

Version 1.1 changes the stimulus wording. Old version 1.0 scores cannot validate it.
The persona file is unchanged. Preserve the full profile rather than rewriting
other traits to make the target choices easier.

Run target, no-persona, and lower-value-persona conditions with the same model,
effort, task content, and tools. Keep condition-specific prompts and artifacts in
separate fresh run directories OUTSIDE the contribution. Begin with one seed per
condition (three runs); treat this as a smoke screen, not statistical evidence.
If it is informative, preregister more seeds before evaluating further.

Record the actual model-visible prompt. The no-persona condition must not
accidentally get the uploaded persona file or the persona agent's fallback
identity. The lower-value condition must not be silently overwritten to Core
value by task.toml pin handling. Preserve exact persona IDs, file hashes, prompt
hashes, task hashes, model identity, native artifacts, and nonempty trajectories.
A correctly labeled envelope alone does not prove injection.

Report counts and pass rates for ALL conditions, including failures and errors.
A target/control tie is a reason to revisit the probe, not to hide the control.
A different complete persona also changes other traits, so its result cannot
establish a causal effect of only the tested dimension. Any future same-profile
ablation must be labeled diagnostic/synthetic and never submitted as a real
Persona 1M persona. Do not edit held-out prompts after seeing their outcomes.

A successful no-persona shortcut or unresolved generic-correctness explanation
means NOT READY. The tests alone do not validate the construct.

## Version 1.1 behavioral validation (2026-09-02)

The unchanged questionnaire passed the initial contribution-quality screen.
Three repetitions of each condition completed real survey trials:

| Condition | Keyed choices, repetitions 0 / 1 / 2 | Passes at 4/6 |
|---|---|---|
| Complete target, matraix-dev-0147 | 6 / 6 / 6 | 3/3 |
| No persona | 1 / 0 / 1 | 0/3 |
| Complete alternate, p-ec140af52f (Minor) | 1 / 1 / 1 | 0/3 |

The target/control separation is unchanged at thresholds 3, 4, and 5. The
household-inventory item was keyed by the alternate in all repetitions and by
neutral in two; it is the least discriminating item in this small sample. No
item, answer key, or threshold was changed after the first behavioral screen.

Model: gpt-5.6-sol; installed Codex 0.152.1; medium reasoning. A separate metering
proxy capped responses at 4096 output tokens. The legacy envelope's temperature
and max_tokens are arm-config fields, not enforced Codex sampling controls.
The repetition labels are not deterministic model seeds. The initial three-run
screen and the rule to repeat informative conditions were fixed before testing;
the two extra repetitions used the same task and all three conditions.

Every run produced a native answer artifact, matching verifier/envelope, and
nonempty trajectory and ZIP. The expected complete profile was verified in each
target/alternate trajectory. Neutral runs contained neither the extra profile
nor a fallback persona identity, and used no uploaded persona. Hidden tests and
answer keys were not mounted during the acting phase. The Windows runtime fixes
used for this validation are a separate infrastructure contribution, not task
files. Raw run outputs and profiles are retained outside the task contribution.

Readiness interpretation: suitable for review as a runnable, meaningfully
discriminating survey candidate, with the stated runtime dependency and limits.
This is a single-model, small-sample pilot, not population-level or psychometric
validation. Full alternate personas differ on other traits; the results do not
isolate a causal effect of val_order_structure alone, distinguish Important from
Core value, or prove that no untested persona-blind shortcut exists.
