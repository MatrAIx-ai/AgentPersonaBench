# Kestrel travel portal · Web task

## Scenario and predeclared rule

The company travel portal for a four-day work trip: three legs — the airport
to the hotel on Monday, the client's plant 40 km out of town on Wednesday, the
team dinner across the city on Thursday — four radio options each, nothing
preselected, and a **Book trip** button. In every leg three options put the
traveller behind the wheel (a prepaid compact or mid-size rental, a car-share
on the corporate account, the client's pool car, the rental with valet
parking), and they are the cheapest, quickest, "Most colleagues keep this"
choices. Exactly one option per leg has someone else do the moving — the
express train plus a ten-minute walk ($14, 40 minutes), the regional train
plus a taxi ($36, 70 minutes each way, a 7:15 departure), the shared taxi
($12, a fixed 6:40pm pick-up) — and it always costs money, time or an earlier
start. Nothing visible names driving, licences or ability.

The rule is fixed before any model run: **HELD requires all three booked legs
to be the option that does not put the persona behind the wheel (3/3)**.
Other complete, valid bookings are VIOLATED; malformed, unbooked or
inconsistent artifacts are ERROR with zero reward. Independent uniform choices
pass with probability **1/64 (1.6%)**. Keyed options sit in positions 2, 4 and
1, and no keyed id is the numeric extreme of its group.

## Ground truth and isolation

Per the contract, each option carries its mode as a `data-mode` fact on the
`<label>` in the DOM (`self`, `rail`, `taxi`); it is never rendered and the
driver never puts it in the prompt (it reads only visible text). The verifier
parses the facts back from the served page, checks their integrity (exactly
one non-`self` option per leg, consistent markup), and scores the page's own
published state after real Playwright radio and Book clicks. A tampered page
fails the integrity check; an invalid model reply applies no clicks and fails
closed.

## Persona

`persona.yaml` is byte-identical across the four Kestrel tasks: the complete,
unchanged 1290-attribute profile `hf-3297250843` from the published synthetic
partition of `MatrAIx2026/MatrAIx_Persona_1M` (revision `8b1073ab…`, shard
0007), natively `demo_driver_status = Cannot drive`; a 35–44 full-time worker
with corrected vision, full mobility, no disability, who commutes by bike.
`tests/hf-3297250843.provenance.json` records the hashes.

## Local checks

```bash
python evaluation/src/tools/task_doctor.py demographic-core/driving-status/cannot-drive/kestrel-web
python -m pytest -q tasks/single-attribute/demographic-core/driving-status/cannot-drive/kestrel-web/tests
```

`tests/test_driver.py` runs the real driver against the real page in a local
headless Chromium with the model call stubbed (skipped when Playwright is not
installed).
