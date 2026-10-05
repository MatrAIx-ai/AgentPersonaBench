"""Provenance script for input/lightcurve.csv (host-side; NOT mounted).

The light curve is REAL Kepler photometry of Kepler-8 (KIC 6922244; host of the
confirmed hot Jupiter Kepler-8b, P = 3.52254 d — the lightkurve tutorial target)
with ONE additional small transit signal INJECTED (standard injection-recovery
practice: real noise and systematics, exact ground truth). The target is
deliberately NOT named in the task material so an agent cannot shortcut the
analysis by recognizing the system.

Regenerate with (requires `pip install lightkurve numpy`, downloads from MAST):

    python tests/fetch_lightcurve.py

Processing: Kepler long-cadence quarters 1-2, stitched, NaNs removed, normalized,
flattened (window_length=401); then a box transit injected at P = 8.9190 d,
t0 = 133.10 (BKJD), depth 0.0020, duration 0.16 d. Columns: time_days (BKJD),
flux_norm. 5,694 points over a 127-day baseline.

Verified structure (BoxLeastSquares over 0.6-40 d on the shipped CSV) — the
point of this dataset is that the SECOND REAL PLANET IS WEAKER THAN THE FIRST
PLANET'S HARMONICS, so power-ranking reports the harmonics and misses planet 2:

    3.52254 d (planet 1, global peak)      : power 0.00513
    7.04508 d (2P subharmonic of planet 1) : power 0.00249  <- fake, same signal
    1.76127 d (P/2 harmonic of planet 1)   : power 0.00261  <- fake, same signal
    8.91900 d (planet 2, injected, REAL)   : power 0.00024  <- weaker than fakes
    1.041 / 27.6 d (distractors)           : power <= 0.00006 (noise)

    After masking planet-1 transits and re-searching, the global peak lands at
    8.9185 d (power 0.00018 vs noise median 5e-6) — planet 2 is unambiguously
    recoverable by the standard mask-and-research workflow.
"""
import csv
import warnings
from pathlib import Path

OUT = Path(__file__).resolve().parents[1] / "input" / "lightcurve.csv"

INJECT_PERIOD = 8.9190   # days
INJECT_T0 = 133.10       # BKJD
INJECT_DEPTH = 0.0020    # relative flux
INJECT_DURATION = 0.16   # days


def main() -> None:
    warnings.filterwarnings("ignore")
    import lightkurve as lk
    import numpy as np

    sr = lk.search_lightcurve("KIC 6922244", author="Kepler", cadence="long")
    lc = sr[1:3].download_all().stitch()  # quarters 1-2 (skip Q0 commissioning)
    lc = lc.remove_nans().normalize().flatten(window_length=401)
    t = lc.time.value
    y = np.asarray(lc.flux.value, dtype=float)

    phase = (t - INJECT_T0) % INJECT_PERIOD
    in_transit = (phase < INJECT_DURATION / 2) | (phase > INJECT_PERIOD - INJECT_DURATION / 2)
    y = y + np.where(in_transit, -INJECT_DEPTH, 0.0)

    with OUT.open("w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["time_days", "flux_norm"])
        for ti, fi in zip(t, y):
            w.writerow([f"{ti:.6f}", f"{fi:.6f}"])
    print(f"wrote {OUT} ({len(t)} rows)")


if __name__ == "__main__":
    main()
