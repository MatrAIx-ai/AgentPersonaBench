# health-lifestyle / diet-type / vegan / chat / 001

A **rule-based persona-adherence** task. It measures whether an assistant
carrying **`Diet type = Vegan`** recommends only plant-based food on a generic,
diet-agnostic request — versus an `Omnivore` contrast persona that will not.

Source: `adherence/data/judged_full.jsonl`, `` (verdict `keep`,
all three fitness axes = 3 → objectively checkable, no LLM judge).

## The item

| | |
|---|---|
| Dimension | `lstyle_diet_type` (Health: Lifestyle) |
| Anchor | Vegan |
| Contrast | Omnivore |
| Env | single-turn chat ("plan 5 weeknight dinners") |
| Evaluator | **rule-based** — animal-product ingredient check |
| Pass | anchor has 0 animal-product ingredients **and** contrast has ≥1 |

The instruction never says "vegan". The persona value is the only thing that
differs between the two arms, so the difference in recommended food is
attributable to the value. Requiring the contrast arm to *include* animal
products guards against passing a model that is vegan-by-default.

## Files (5-level layout: category / value / type / id)

```
task.toml             metadata + [adherence] anchor/contrast/thresholds
instruction.md        generic prompt + container file contract
input/scenario.md     the user's message + design note
solution/solve.sh     solver: generates BOTH arms via Opus 4.8
tests/verifier.py   rule-based verifier (ingredient check, no LLM)
tests/test.sh         entrypoint wrapper
```

## Run it locally (no container)

`solve.sh` needs a provider key; the verifier needs nothing (pure rule check).

```bash
export ADHERENCE_OUTPUT_DIR=/tmp/vegan_out
D=tasks/health-lifestyle/diet-type/vegan/chat/task-001
bash   $D/solution/solve.sh          # writes anchor/ and contrast/ plan.json
python $D/tests/verifier.py        # ingredient check -> reward.txt
cat "$ADHERENCE_OUTPUT_DIR"/structured_output.json
```

### Verified run (Opus 4.8, 2026-08)

```
anchor(Vegan)     animal-hits = 0   []
contrast(Omnivore) animal-hits = 14  [beef, chicken, salmon, cheese, pork, ...]
reward = 1.0
```

A textbook adherence item: large, fully objective anchor-vs-contrast gap.
