# APB task format — task, input, persona, output

The unified contract every task follows, regardless of kind or environment. It
ties together four layers:

1. **Task** — what is measured (the attribute pin)
2. **Input** — the per-env material the persona acts on (schema below)
3. **Persona** — who plays it, and how that is recorded (this is a *persona* bench)
4. **Output** — what a run produces (see also
   [`evaluation/results/CONTRACT.md`](../evaluation/results/CONTRACT.md))

This document is the authority on the task shape, the **input schema**, and
**persona recording** for both single- and multi-attribute tasks. Multi-attribute
tasks score one point per check held, out of N (§1).

---

## 1. What is measured — the attribute, not the person

PersonaBench measures **attribute adherence**. The unit under test is an
`(attribute = value)` pair — `dimension_id = value`, drawn from the MatrAIx
attribute schema; the persona is the *vehicle* that carries it. Every `task.toml`
pins its attribute(s) the same way — a `[[checks]]` array, one entry per attribute:

```toml
[task]
name  = "personabench/vegan-app"
theme = "Diet type: Vegan"        #  one-line, human-readable "what this measures"

[[checks]]                        #  one entry per attribute
dimension_id    = "lstyle_diet_type"
dimension_label = "Diet type"     #  optional human label / category
value           = "Vegan"         #  the value the agent must exhibit in character
evaluator       = "rule-based"    #  HOW it's judged: rule-based | llm-judge
adherence_signal = "…"            #  plain-English definition of "held"
# extra fields a check may add: evaluator_name (a display label) + metric / pass_*
# thresholds when the verifier scores each check programmatically.
```

The attribute pin (`dimension_id` + `value`) is the **primary record** of every
trial — it makes results comparable across personas and models. `theme` is the
at-a-glance subject line; `evaluator` is *how* a check is judged.

### How many checks — and how it scores

A task is not two different kinds; it just has **one or more checks**, and scores
accordingly:

| checks | `reward` | max | meaning |
|---|---|---|---|
| **one** | `1.0` / `0.0` | `1` | held / violated — binary |
| **several** (from ONE generation) | integer `0..N` | `N` = number of checks | one point per check held ("test 3 traits ⇒ out of 3") |

- One check → binary verdict, reward `1.0` (HELD) or `0.0` (VIOLATED).
- Several checks → the verifier scores each independently; reward is the **count
  held** (three checks ⇒ max 3, e.g. `2/3`). Use several checks only when the
  attributes are **naturally co-exposed by a single artifact** — e.g. one Python
  function reveals comment style + indentation + error handling at once. This
  amortizes one generation across several attributes; it is not for bundling
  unrelated tasks. A given `(attribute = value)` should be scored in exactly one
  task, never counted twice across the suite.

> The `tasks/single-attribute/` and `tasks/multi-attribute/` folders are just
> where one-check vs several-check tasks live; the task shape is identical.

## 2. Input schema — per environment

Input is organized **by environment**: each `type` has a fixed input filename and
internal shape. A contributor building a task of a given type follows the shape
below. Ground truth is pre-defined at authoring time — never hand-picked at verify
time. **Everything under `input/` is bind-mounted verbatim into the agent's
container and the instruction routinely tells the agent to read it**, so ground
truth must NOT live inline in `input/`. For survey tasks the option→label map
lives in `tests/answer_key.yaml` (never mounted); web/app carry the label in a
runtime surface (the DOM / the app process) the agent cannot introspect for the
answer. `task_doctor` fails any task that leaves a label key inside `input/`.

| env | input file | internal shape | ground truth |
|---|---|---|---|
| **survey** | `input/questionnaire.yaml` (ids + text only) | questions, each with options; option ids are opaque | `tests/answer_key.yaml`: option-id → label (`animal` / `risk` / …), host-side only |
| **chat** | `input/bot.md` + `input/context.md` | the assistant bot's framing/pressure (`bot.md`) + the conversation setup (`context.md`) | LLM judge over the user's turns |
| **web** | `input/site/index.html` | a live page with `data-*` attributes per item | `data-animal` / `data-risk` on each item, read from the real DOM |
| **app** | `input/app/<app>.py` + `environment/` | a **native desktop GUI** (Tkinter) the agent drives by screenshot + coordinate click | a hidden per-item label the app carries; the app writes the chosen items to `order.json` itself |

### survey — `questionnaire.yaml`

`input/questionnaire.yaml` — shown to the agent, ids + text only, NO labels:

```yaml
questions:
  - id: q1
    prompt: "Pick a dinner for tonight."
    options:
      - {id: q1a, text: "Grilled chicken salad"}
      - {id: q1b, text: "Quinoa & roasted vegetable bowl"}
```

`tests/answer_key.yaml` — host-side only, NEVER mounted into the container:

```yaml
animal:            # option-id -> hidden ground-truth label
  q1a: true
  q1b: false
```

The agent returns **option ids only** (`survey_result.json`), pure choice, no free
text. The verifier (which runs on the host) joins those ids against
`tests/answer_key.yaml` and checks no flagged option was chosen. Because the key
never enters the container, the agent cannot read the answer.

### web — `index.html`

Each selectable item declares a hidden ground-truth attribute the verifier reads
back from the DOM:

```html
<div class="item" data-id="m03" data-animal="true">   <!-- ground truth -->
  <span>Grilled chicken Caesar salad</span>
  <button class="add" data-id="m03">Add</button></div>
```

- `data-animal="true|false"` (diet) or `data-risk="0..3"` (risk) — **never rendered
  visually**; the agent cannot see the label, only the human-readable text.
- The verdict is read from the real cart/portfolio DOM after real clicks — not a
  JSON the model wrote about itself.

### app — native desktop GUI (`input/app/<app>.py` + `environment/`)

The app is a **real native application** (a Tkinter GUI), not a web page. It runs
on a local Linux CUA desktop (Xvfb + XFCE) built by the task's `environment/`
Dockerfile; the `persona-computer-1` agent operates it purely by **screenshot +
coordinate click** — there is no DOM, selector, or JS shortcut into the result.

```python
# input/app/<app>.py — the ground-truth label lives ONLY in this process,
# is NEVER drawn on screen, and the app writes the order file itself.
MENU = [("d01", "Grilled Chicken Caesar", "…", True),   # (id, name, desc, is_animal)
        ("d03", "Quinoa & Roasted Veg Bowl", "…", False), …]
# on "Place order": write {"orderedDishes": [{"id","name","animal"}]} to order.json
```

- The hidden label (animal / risky / …) is carried server-side by the app, so the
  agent must judge each item from its **visible name/description**, like a person.
- The verdict is read from the file the **app** wrote after real clicks — never a
  JSON the model wrote about itself. Persona is injected via the framework
  (`persona_system_prompt` → harbor `--extra-instruction-path`), not hand-written.
- Like every other env, an app task still ships `solution/solve.sh` — it just
  sources the shared solver (`evaluation/src/lib/harbor_solve.sh`), which runs the
  harbor agent and drops the app-written output into `$ADHERENCE_OUTPUT_DIR` for
  the task's `verifier.py`. So all four envs share one flow: `solve.sh` → `verifier.py`.

### chat — `bot.md` + `context.md`

`bot.md` sets the assistant bot's role and the **pressure** it applies (e.g.
"suggest 3 dinners, at least two containing meat/fish"); `context.md` sets the
conversation framing. The persona is the *user*; the judge reads only the user's
turns.

## 3. Persona recording — this is a *persona* bench

The attribute is the subject; the persona is the **traceable vehicle**. A task must
make it verifiable that the attribute was measured on a *real, complete* person who
genuinely carries the value. Recording is therefore **provenance**, not a full
dump of all dimensions.

### Shipped as `persona.yaml` in the task dir

Each task carries a complete persona file (`<task>/persona.yaml`) — a complete person
sampled from MatrAIx Persona 1M whose tested dimension holds the value under test.
It is **never hand-written**. The framework renders it to a role-play prompt
(`persona_system_prompt`) and injects it the same way every run — for text envs
inside `solve.sh`, for app via harbor `--extra-instruction-path`.

```yaml
persona_id: p-ec140af52f
source: MatrAIx_Persona_1M
attributes:                        # hundreds of dims; the tested value lives here
  lstyle_diet_type: { value: Vegan, label: "Diet type", category: "Health: Lifestyle" }
  att_veganism:     { value: Enthusiast, … }
  …
```

The reviewer's check is simply: does `attributes[dimension_id].value == value`?
That proves the persona genuinely carries the attribute under test.

### Recorded per trial — the provenance triple

The in-task `persona.yaml` already carries its provenance:

```yaml
persona_id: p-3f9a1c2e            # stable, opaque id
source: MatrAIx_Persona_1M        # the corpus it was sampled from
note: "… shard 0000 row 7968"
attributes: { lstyle_diet_type: { value: Vegan, … }, … }   # the tested value lives here
```

So the measurement is reproducible and auditable, a trial's **provenance triple** is:

1. **`persona_id`** — which persona played it
2. **`source`** — where it came from (corpus / shard / row)
3. **the tested dimension's value** — proof the persona actually carries the value
   under test (`attributes[dimension_id].value == value`)

The full persona is self-contained in the task's `persona.yaml` (there is no shared
pool directory). Trial provenance is captured in `envelope.json` — the runner pins
the attribute (`dimension_id` / `anchor_value`), model/arm, config, seed and
timestamp there — alongside the un-modified `persona.yaml` in the task dir. We
record the *pin + persona file*, not a duplicate dump of all hundreds of dimensions.

## 4. Output — uniform per trial

Every trial writes the same records regardless of env or evaluator:

- `reward.txt` — the one-number result a harness reads.
- `structured_output.json` — the canonical record: verdict + how it was reached
  (single: `verdict`/`passed`; multi: `criteria[]` + integer `score`).
- `generation.json` — everything the agent said/did + tokens per call (normalized
  by the runner into `trajectory.json`, an ATIF-lite step list).
- `envelope.json` — run metadata: attribute pin (`dimension_id` / `anchor_value`),
  model/arm, config, seed, timestamp (written by the runner). Persona provenance
  (§3) lives in the task's `persona.yaml`.
- `trace.zip` — web/app only; web = replayable Playwright trace, app = the CUA
  run's per-step screenshots + trajectory bundled into one archive.

Full schema: [`evaluation/results/CONTRACT.md`](../evaluation/results/CONTRACT.md).

## 5. Acceptance checklist

- [ ] `task.toml` pins the attribute(s) in `[[checks]]` (single = one check, multi = N) and sets `[task].theme`
- [ ] input follows the per-env schema (§2), with hidden ground-truth labels
- [ ] `instruction.md` names **no** tested attribute and never says "you are tested"
- [ ] a real `persona.yaml` sits in the task dir, its tested dimension **equals** the value;
      the persona is injected by the framework (`persona_system_prompt`), never hand-written
- [ ] `solution/solve.sh` present for every env (app sources `evaluation/src/lib/harbor_solve.sh`)
- [ ] `verifier.py` reads the real output (web DOM / the app-written file / survey ids /
      chat turns) and emits the verdict — single: binary `1.0`/`0.0`; multi: integer `0..N`
- [ ] runs locally via `run_task.py` and produces a verdict + trajectory (provenance is the in-task `persona.yaml` + `envelope.json` pin)
