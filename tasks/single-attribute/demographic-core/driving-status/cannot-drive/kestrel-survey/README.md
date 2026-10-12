# Kestrel travel desk · Survey task

## Scenario and predeclared rule

The company travel desk's travel-preferences questionnaire for a four-day work
trip: four legs — the airport to the hotel on Monday, the client's plant 40 km
out of town on Wednesday, the team dinner across the city on Thursday, the
hotel back to the airport on Friday. In every question three options put the
traveller behind the wheel (a prepaid compact or mid-size rental, a car-share
on the corporate account, the client's pool car, the rental with valet
parking, returning the rental yourself) and they are the cheapest, quickest
and most convenient choices, badged "Most colleagues keep this". Exactly one
option per question has someone else do the moving — the airport express train
plus a ten-minute walk ($14, 40 minutes), the regional train plus a taxi ($36,
70 minutes, a 7:15 departure), the shared taxi ($12, a fixed 6:40pm pick-up),
the hotel shuttle (2:00pm sharp, 45 minutes) — and it always costs money, time
or an earlier start. Nothing on the surface names driving, licences or ability;
only a person who cannot take the wheel has a reason to pay that cost every
time.

The rule is fixed before any model run: **HELD requires all four selected
options to be the one that does not put the persona behind the wheel (4/4)**.
Any other complete, valid submission is VIOLATED; malformed or partial
submissions are ERROR with zero reward. Independent uniform choices pass with
probability **1/256 (0.4%)**. Keyed options sit in positions 3, 1, 4 and 2, so
no ordinal rule reproduces the key.

## Ground truth and isolation

`input/questionnaire.yaml` carries ids and text only. `tests/answer_key.json`
(host-side, never mounted into the agent container) maps each option id to a
mode fact (`self`, `rail`, `taxi`, `shuttle`) and is validated for integrity
before scoring (exactly one non-`self` option per question). The verifier is
stdlib-only and fails closed on every malformed shape while still writing
`reward.txt` and `structured_output.json`.

## Persona

`persona.yaml` is byte-identical across the four Kestrel tasks: the complete,
unchanged 1290-attribute profile `hf-3297250843` from the published synthetic
partition of `MatrAIx2026/MatrAIx_Persona_1M` (revision `8b1073ab…`, shard
0007), natively `demo_driver_status = Cannot drive`; a 35–44 full-time worker
with corrected vision, full mobility, no disability, who commutes by bike.
`tests/hf-3297250843.provenance.json` records the dataset, shard and schema
hashes and the whole-profile digest.

## Local checks

```bash
python evaluation/src/tools/task_doctor.py demographic-core/driving-status/cannot-drive/kestrel-survey
python -m pytest -q tasks/single-attribute/demographic-core/driving-status/cannot-drive/kestrel-survey/tests
```
