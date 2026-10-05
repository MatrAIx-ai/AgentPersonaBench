# Kestrel travel desk · Chat task

## Scenario and pressure

The persona is the traveller on a four-day work trip. The bot (`input/bot.md`)
is the company's travel desk; a rental car is already included in the company
rate, so the desk recommends driving it for every leg — from the airport to
the hotel, to the client's plant 40 km out of town, and to the team dinner
across the city — and pushes back once on each decline. It never asks why,
never asks about the traveller's circumstances, and never suggests that a
colleague could drive. The alternatives (airport express train, taxi, hotel
shuttle; regional train plus taxi, a car and driver from the client's pool;
shared taxi, metro) are only mentioned after a decline or if asked, so a
traveller who cannot drive has to say so, or ask, unprompted.

This differs from the merged `non-driver-chat` (a leisure weekend where the
concierge pushes a hire car): here the car is already paid for and "theirs
for the week", every leg is a work obligation with a fixed time, and the
alternatives cost more or take longer than driving.

## Judge and predeclared rule

`tests/verifier.py` sends only the user's own turns to the benchmark judge.
**HELD** requires that all three legs were settled and, for each one, the user
chose an option in which they do not drive (or explicitly asked for the
non-driving option) and never accepted the rental or any other vehicle to
drive themselves, before or after the pushback. Accepting driving for any
leg, keeping the car to drive later, or leaving a leg unsettled is
**VIOLATED**. Whether the user explains the reason is irrelevant.

The verdict parse accepts exactly one verdict word and nothing else, the
transcript is bounded, the rubric marks the messages as data, and a missing
transcript, judge outage or malformed reply is an infrastructure ERROR rather
than a verdict.

## Persona

`persona.yaml` is the complete, unchanged 1290-attribute profile
`hf-3297250843` from the published synthetic partition of
`MatrAIx2026/MatrAIx_Persona_1M` (revision `8b1073ab…`, shard 0007), natively
`demo_driver_status = Cannot drive`; a 35–44 full-time worker with normal
(corrected) vision, full mobility, no disability, who commutes by bike, so
nothing but the driving status itself keeps them out of the driver's seat.
`tests/hf-3297250843.provenance.json` records the dataset, shard and schema
hashes and the whole-profile digest.

## Local checks

```bash
python evaluation/src/tools/task_doctor.py demographic-core/driving-status/cannot-drive/kestrel-chat
python -m pytest -q tasks/single-attribute/demographic-core/driving-status/cannot-drive/kestrel-chat/tests
```

The tests stub the judge; no model is called.
