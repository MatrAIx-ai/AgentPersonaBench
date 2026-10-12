# Vendored harbor runtime

`evaluation/src/harbor/` is a copy of the [Harbor](https://github.com/laude-institute/harbor) agent runtime (Apache 2.0), extended with APB's persona agents (`evaluation/src/matraix/agents/`). The `survey` and `app` surfaces run their agents through it inside Docker; task `solution/solve.sh` scripts find it automatically.

Setup is covered by the root README (Python 3.12, `pip install -r requirements.txt`, Docker). `requirements.txt` in this directory is the runtime's own dependency list, kept for reference; the root `requirements.txt` is a superset.

Licensing: see `NOTICE` at the repository root.
