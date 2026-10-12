# Early bird persona selection

All four surfaces use the same complete `real_human_survey_0236` row from the
[MatrAIx Persona 1M public release](https://huggingface.co/datasets/MatrAIx2026/MatrAIx_Persona_1M_Public_Release/tree/8b1073ab23d0c0ba0928386a041bac55e5365ddc).
The control fixture, `contrast_persona.yaml`, is the complete
`real_human_survey_0100` row. Both come from the release's `real_human_survey`
source. All 1,290 native attribute values are preserved.

| Native attribute | Adherent: 0236 | Contrast: 0100 |
|---|---|---|
| Sleep schedule | Early bird | Night owl |
| Morning routine | Highly structured | Slow |
| Late-night snacking | Never | Weekly |

Selection used these correlated attributes before behavioral validation. This
replaces 0231, whose rushed mornings and weekly late-night snacking created
competing scheduling preferences. The morning times, option IDs, categorical
answer keys, and exact-match scoring are preserved. The survey retains two
binary and two four-choice questions.

## Timing contrast

Every opposing slot now starts at 10:00 PM or later across survey, chat, web,
and app. Multi-option evening lists use 10:00 PM, 10:30 PM, and 11:00 PM;
the chat contrasts 7:30 AM with 10:00 PM. Providers, durations, formats, and
prices remain equal within each choice. This is an authored early-morning
versus late-night contrast, not a universal definition of a sleep schedule.
Ordinary early-evening appointments are no longer labeled as contradictions.

## Source provenance

- Dataset revision: `8b1073ab23d0c0ba0928386a041bac55e5365ddc`.
- Shard: `data/persona-1m-0005.parquet`.
- Shard SHA-256: `27e7a517df0a579708a3b53ec3f6dd580168cf1820d9455637822bdbcee6f8b9`.
- Code schema SHA-256: `a02221ff32c2bc135c5e4290e1383081188712ee88f5c341f5fdb56d3d7b1c5c`.
- Adherent: zero-based shard row 99654, global row 599654, source row 235.
- Contrast: zero-based shard row 99560, global row 599560, source row 99.

Decode the shard's packed `attributes` with the release's
`persona_codes.schema.json`: even attribute indices use the low nibble, odd
indices use the high nibble, and the resulting code indexes that column's
`values`. Respect `null_bitmap` and `attribute_overrides` when present. The
export retains the schema's labels and categories. `test_personas.py` checks
the four copies, native value hashes, completeness, and selection criteria.
The hashes use UTF-8 JSON of `{dimension_id: value}`, sorted keys,
`ensure_ascii=False`, and compact comma/colon separators.

## Behavioral control protocol

Run each surface once with its shipped persona and once with this control,
using identical model, effort, seed, task content, and verifier. The contrast
is scored against the original Early bird target, so its expected target
reward is zero. Preserve the complete source row in both arms.

These are control expectations, not acceptance gates. Preserve valid persona
failures and nonzero contrast scores rather than retuning tasks or personas
to force separation. Results from earlier time options do not validate the
revised 10:00 PM-or-later options.

The shared renderer can replace persona values with `task.toml` pins. A
validation copy must render the actual control values while retaining the
original checks for scoring; simply swapping `persona.yaml` is insufficient.
Apply the same rendering precedence to both validation arms and verify the
adherent prompt is identical to the production prompt. Record this validation
adapter, source hashes, actual persona values, artifacts, and trajectories.
Keep generated run results out of the task package.
