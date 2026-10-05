# Design and reproduction

## Response handling and review revision (2026-09-16)

The driver accepts one JSON object wrapped in prose or a Markdown fence, while
still rejecting missing, duplicate, unknown or cross-question choices and
ambiguous multiple objects. It does not fill missing answers or select a
passing object from a rejected payload. An unrecoverable model reply exports
the browser's empty, unconfirmed receipt and exits normally so the verifier
records a zero-reward VIOLATED result. API/browser failures still propagate as
infrastructure errors. Browser regression fixtures exercise both routes; stubbed
replies are not model validation.

Two questions now include factual-equivalent Italian versions (q2b and q5c).
The unchanged persona has Fluent Italian and Native Arabic, making Italian a
readable alternative rather than an unavailable language. Native and Fluent
are still unequal proficiency levels: this reduces the all-unreadable-distractor
problem, but does not causally isolate primary language from proficiency.
Translations have not received independent native-speaker review.

"Single-model pilot" means that measured behavior used only gpt-5-mini with
medium reasoning and a small sample; it is not evidence of cross-model
robustness. Linux-container runs on Docker Desktop are real browser runs, but
are not native macOS validation. The Darwin routing branch has unit tests only.
Fresh behavioral evidence is required for changed visible choices or order;
old trial counts must remain labeled with their original source revision.

## Review follow-up

The verifier catches a missing PyYAML dependency and writes a structured
infrastructure failure with zero reward. PyYAML is still required for scoring.
Deeply nested JSON also produces a structured failure rather than a traceback.
The solver follows the merged access-display-web task's macOS proxy routing:
loopback addresses become host.docker.internal there; Linux keeps host networking.
Shell-routing unit tests do not establish a successful native macOS run.

Revision-specific browser and end-to-end evidence should accompany these
changes. Earlier model results belong to the previous source. The evaluator
runs the verifier in its Python environment, whose declared dependencies include
PyYAML; the browser-only image does not need that scoring dependency.
A policy that picks one of four languages uniformly and keeps using it
passes with probability 1/4, not the independent-item probability 19/4096.
Full personas confound primary language with proficiency.

## Task design

This is a browser workflow with six concrete choices, not a settings form that
names the tested trait. The visitor saves actual equivalent information snippets for personal use, not a declared language setting. The fictional venue facts are identical across four translated versions. This expands the uncovered Arabic value and includes right-to-left text. It shares the language-choice construct with the other language tasks; comprehension and primary language are not causally separated in this complete persona. The agent receives only visible text and IDs.
The website contains no data-tier answer labels. The answer key remains in
tests/answer_key.yaml, outside the acting model's mounted inputs.
The browser builds a receipt after real radio selections and confirmation;
the driver reads that receipt into selection.json. The verifier scores that
native final state, not the model's proposed choices.

The complete unchanged persona `hf-5170043725` comes from merged source
`tasks/multi-attribute/low-carb-not-tokyo/low-carb-not-tokyo-app/persona.yaml` at `d72bd92e7b8d1cacd686268c84a601d0835d04e4` and carries `primary_language = Arabic`.
The alternate `hf-1557002195` carries
`English`. Full profiles differ on
other traits, so contrasting them does not isolate one causal variable.

The 5/6 threshold tolerates one different choice and is provisional. With four
options per choice, independent uniform guessing passes at 19/4096, but a
consistent unconditioned preference across all items can pass much more often.
Repeated persona-blind controls are necessary; do not interpret the independent
guessing probability as the empirical baseline or six independent constructs.
Static and browser fixture tests do not replace the real model validation.

From the repository root, run task_doctor on `linguistic-language/primary-language/arabic/neighborhood-visitor-reading-packet-web`, then run this task's
`tests/test_fixtures.py`. With a running Docker Engine and configured model key,
run `python evaluation/run_task.py linguistic-language/primary-language/arabic/neighborhood-visitor-reading-packet-web --model gpt-5-6-sol --model-id gpt-5-mini --effort medium --seed 0`.
This is a billable invocation without the contributor's external budget cap.
