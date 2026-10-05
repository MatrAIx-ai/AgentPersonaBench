# Output Contract — `evaluation/results/`

This defines **what a run
produces and where it lives**, so every result is uniform, auditable, and
comparable across models.

## Directory layout (mirrors the task path)

```
results/<bucket>/<task-path>/<model>/<effort>/<trial-id>/
```

- `<bucket>` — `single-attribute` or `multi-attribute`.
- `<task-path>` — the task path under that bucket, e.g.
  `health-lifestyle/diet-type/vegan/vegan-web` (mirrors `tasks/<bucket>/…`).
- `<model>` — the model arm id, e.g. `opus-4-8`, `gpt-5-6-sol`, `gemini-3-7-flash`.
- `<effort>` — reasoning effort, e.g. `medium`.
- `<trial-id>` — `trial-001`, `trial-002`, … (one per run; time lives in the record).

A result therefore maps 1-to-1 back to the task that produced it.

## Files each trial must write

| file | contents |
|---|---|
| `reward.txt` | one number: `1.0` / `0.0` (machine-readable pass/fail) |
| `structured_output.json` | the **canonical trial record** (schema below) |
| `generation.json` | full transcript / actions + per-call token log |
| `envelope.json` | run metadata added by the runner (task version, model, seed, timestamp) |
| `trace.zip` | web & app only — replayable Playwright trace (self-contained; no video) |
| `<arm>/…` | raw agent output (e.g. `order.json`, `plan.json`, `solution.py`) |

## Trial record schema (`structured_output.json`)

One uniform schema for every task, whether `rule-based` or `llm-judge`:

```json
{
  "verdict"    : "HELD" | "VIOLATED",     // the binary result
  "reward"     : 1.0 | 0.0,
  "passed"     : true | false,
  "persona"    : "vegan_enthusiast",      // which persona was played
  "detail"     : "animal-in-cart=0 ...",  // the evaluator's reasoning
  "trajectory" : [ {step: "open_page"}, {step: "click_add", id: "m04"}, ... ],
  "generation" : { "model": "...", "token_usage": { "total_tokens": ..., ... } },
  "judge"      : { "raw": "HELD", "usage": {...} }   // llm-judge tasks only
}
```

Multi-attribute tasks additionally carry a `checks` array — one entry per
`evaluator_name`, each with its own `verdict`/`passed` — plus `score` ("2/3"),
`points`, and `max_points`. Their `reward` is an **integer score** (one point per
check held, 0..N), not a fraction. See
[docs/task-format.md](../../docs/task-format.md).

## Rules

1. **Record everything.** Verdict *and* its justification, every action, and
   token usage for both the agent and the judge. A failure must be traceable to
   the exact step.
2. **Same schema regardless of evaluator.** Rule-based and llm-judge tasks emit
   the same top-level fields, so results stay comparable.
3. **Binary verdict, no thresholds.** `verdict` is `HELD`/`VIOLATED`; a single
   task's `reward` is `1.0`/`0.0`. A multi task's `reward` is an integer score
   (points = # checks held, 0..N).
4. **Reproducible.** `envelope.json` pins model, effort, seed, task version, and
   timestamp so a trial can be re-run.
5. **Traces, not videos.** web/app store `trace.zip` (screenshots + DOM +
   network); no separate video files.
