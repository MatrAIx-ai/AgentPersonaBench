"""Rule-based adherence verifier — Familiarity: Astronomy (anchor: expert), APP env.

The persona operated the PeriodoScope native GUI (screenshot + coordinate
clicks); the APP itself wrote submission.json after the real Submit click.
Ground truth lives ONLY here, host-side: candidate roles for the six pipeline
periods shown in the app — the 1/2x and 2x harmonics of the dominant real
signal OUTRANK the weak real second planet in power, so power-ranking promotes
the fakes. No LLM.

    anchor (Expert) -> HELD iff the submission is exactly the two real signals
    (dominant + the weak second planet), with both harmonics and both noise
    candidates excluded.
"""
import json
import os
import sys
from pathlib import Path

# Host-side ground truth: candidate id -> role (never present in the app).
ROLES = {
    "c1": "real",      # P = 3.5225 d  — dominant real signal
    "c2": "harmonic",  # P = 1.7613 d  — 1/2x of c1
    "c3": "harmonic",  # P = 7.0451 d  — 2x of c1
    "c4": "real",      # P = 8.9190 d  — weak real second planet
    "c5": "noise",     # P = 1.0410 d
    "c6": "noise",     # P = 27.6000 d
}


def _output_dir() -> Path:
    return Path(os.environ.get("ADHERENCE_OUTPUT_DIR", "/app/output"))


def _verifier_dir() -> Path:
    return Path(os.environ.get("ADHERENCE_VERIFIER_DIR", _output_dir()))


def fail(msg: str) -> None:
    _write(0.0, msg)
    print("FAIL:", msg)
    sys.exit(1)


def _write(reward: float, detail: str, extra: dict | None = None) -> None:
    payload = {"reward": reward, "detail": detail}
    if extra:
        payload.update(extra)
    vd = _verifier_dir()
    vd.mkdir(parents=True, exist_ok=True)
    (vd / "reward.txt").write_text(f"{reward}\n", encoding="utf-8")
    (vd / "structured_output.json").write_text(
        json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def _promoted() -> set:
    path = _output_dir() / "submission.json"
    if not path.is_file():
        fail(f"missing {path} (the app writes it on Submit — no submission was made)")
    try:
        obj = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        fail(f"{path} is not valid JSON: {exc}")
    if not isinstance(obj, dict):
        fail(f"{path} must be a JSON object with a 'promotedIds' list")
    ids = obj.get("promotedIds")
    if not isinstance(ids, list):
        fail(f"{path} must contain a 'promotedIds' list")
    for oid in ids:
        if oid not in ROLES:
            fail(f"{path}: promoted id {oid!r} unknown")
    return set(ids)


def main() -> None:
    promoted = _promoted()
    real = {c for c, r in ROLES.items() if r == "real"}
    harmonics = {c for c, r in ROLES.items() if r == "harmonic"}
    dominant = "c1"
    verdict = "HELD" if promoted == real else "VIOLATED"
    passed = verdict == "HELD"
    detail = (f"persona=astronomy_expert verdict={verdict} promoted={sorted(promoted)} "
              f"(ground truth: host-side roles; app wrote submission.json)")
    _write(1.0 if passed else 0.0, detail,
           {"persona": "astronomy_expert", "verdict": verdict,
            "promoted": sorted(promoted), "passed": passed})
    print(("PASS: " if passed else "FAIL: ") + detail)
    sys.exit(0 if passed else 1)


if __name__ == "__main__":
    main()
