#!/usr/bin/env python3
"""task_doctor — self-check a PersonaBench task dir for contract compliance.

Run this on a task BEFORE opening a PR. It catches the mistakes contributors
actually make when hand-writing the 5-8 files of a task: a malformed task.toml,
a value that leaks into instruction.md, a persona whose attribute value drifted
away from the check it is supposed to carry, a solve.sh with a shell syntax
error, a verifier that will not compile, and an output path the instruction and
the verifier disagree on.

Usage:
    python evaluation/src/tools/task_doctor.py <task-path>

    <task-path> is relative to tasks/, exactly like run_task.py, e.g.
        health-lifestyle/diet-type/vegan/vegan-survey

The task dir is resolved against both task roots (single-attribute/ and
multi-attribute/), mirroring run_task.py's _resolve_task_dir.

Exit code: 0 if every check PASSes (WARNs are allowed), 1 otherwise.

Dependencies: stdlib only + pyyaml (for persona.yaml). tomllib is stdlib on 3.11+.
"""
from __future__ import annotations

import argparse
import functools
import json
import re
import subprocess
import sys
import tomllib
from collections.abc import Iterable
from pathlib import Path

try:
    import yaml
except ImportError:  # pragma: no cover - reported as a check, not a crash
    yaml = None

sys.path.insert(0, str(Path(__file__).resolve().parent))
import app_env_check  # noqa: E402 - sibling tool, imported after the path fix

# Mirror run_task.py: a task path is given WITHOUT the bucket prefix and resolved
# against each root so the same path works regardless of which bucket holds it.
REPO = Path(__file__).resolve().parents[3]
TASK_ROOTS = [
    REPO / "tasks" / "single-attribute",
    REPO / "tasks" / "multi-attribute",
]

# ANSI (best-effort; degrade to plain if not a tty)
_TTY = sys.stdout.isatty()
_G = "\033[32m" if _TTY else ""
_R = "\033[31m" if _TTY else ""
_Y = "\033[33m" if _TTY else ""
_B = "\033[1m" if _TTY else ""
_0 = "\033[0m" if _TTY else ""


class Report:
    """Collects PASS / WARN / FAIL lines; FAIL flips the process exit to 1."""

    def __init__(self) -> None:
        self.rows: list[tuple[str, str]] = []
        self.failed = False

    def ok(self, msg: str) -> None:
        self.rows.append(("PASS", msg))

    def warn(self, msg: str) -> None:
        self.rows.append(("WARN", msg))

    def bad(self, msg: str) -> None:
        self.rows.append(("FAIL", msg))
        self.failed = True

    def render(self) -> None:
        icon = {"PASS": f"{_G}PASS{_0}", "WARN": f"{_Y}WARN{_0}",
                "FAIL": f"{_R}FAIL{_0}"}
        for status, msg in self.rows:
            print(f"  [{icon[status]}] {msg}")


def _resolve_task_dir(task: str) -> tuple[Path | None, str | None]:
    """Return (task_dir, root_name); models run_task.py._resolve_task_dir."""
    for root in TASK_ROOTS:
        d = root / task
        if (d / "task.toml").is_file():
            return d, root.name
    return None, None


# --------------------------------------------------------------------------- #
# individual checks
# --------------------------------------------------------------------------- #
def check_task_toml(task_dir: Path, rep: Report) -> dict | None:
    """Parse task.toml; verify [task].name+theme and >=1 well-formed [[checks]]."""
    path = task_dir / "task.toml"
    if not path.is_file():
        rep.bad("task.toml is missing")
        return None
    try:
        meta = tomllib.loads(path.read_text(encoding="utf-8"))
    except (tomllib.TOMLDecodeError, OSError) as exc:
        rep.bad(f"task.toml does not parse: {exc}")
        return None
    rep.ok("task.toml parses")

    task_tbl = meta.get("task") or {}
    if task_tbl.get("name"):
        rep.ok(f"[task].name = {task_tbl['name']!r}")
    else:
        rep.bad("[task].name is missing or empty")
    if task_tbl.get("theme"):
        rep.ok(f"[task].theme = {task_tbl['theme']!r}")
    else:
        rep.bad("[task].theme is missing or empty")

    checks = meta.get("checks") or []
    if not checks:
        rep.bad("no [[checks]] entries — need at least one")
        return meta
    rep.ok(f"{len(checks)} [[checks]] entry(ies) present")

    for i, chk in enumerate(checks):
        tag = f"[[checks]][{i}]"
        dim = chk.get("dimension_id")
        if not dim:
            rep.bad(f"{tag}: missing dimension_id")
        val = chk.get("value")
        anchor = chk.get("anchor_value")
        if val is None and anchor is None:
            rep.bad(f"{tag} ({dim}): needs a `value` or `anchor_value`")
        if not chk.get("evaluator"):
            rep.bad(f"{tag} ({dim}): missing `evaluator`")
    return meta


def _value_mention_re(value: str) -> re.Pattern:
    r"""Match `value` as a standalone mention, with endpoint-aware boundaries.

    `\b` is a boundary between a word and a non-word character, so wrapping a
    value in `\b...\b` silently never matches when the value's own endpoint is
    not a word character. Dimension values in `evaluation/src/persona/schema/dimensions.json` routinely
    end (or start) in punctuation — `85+`, `20+`, `$200k+`, `Fluent (C1-C2)`,
    `10,000+` — and for those the trailing `\b` is asserted between `+` and the
    following space, two non-word characters, which can never be a boundary. The
    guard therefore passed a `context.md` that named exactly that value, and the
    file was then injected into the simulator prompt.

    Assert "not glued to a word character" only at the ends where the value
    itself is a word character; where it is punctuation the escaped literal is
    already its own anchor.
    """
    esc = re.escape(value)
    left = r"(?<!\w)" if re.match(r"\w", value) else ""
    right = r"(?!\w)" if re.search(r"\w\Z", value) else ""
    return re.compile(left + esc + right)


def _check_values(meta: dict) -> list[tuple[str, str]]:
    """(dimension_id, tested-value) pairs, preferring value then anchor_value."""
    out = []
    for chk in meta.get("checks") or []:
        dim = chk.get("dimension_id")
        val = chk.get("value")
        if val is None:
            val = chk.get("anchor_value")
        if dim and val is not None:
            out.append((dim, str(val)))
    return out


def check_instruction(task_dir: Path, meta: dict, rep: Report) -> None:
    """instruction.md must exist and not leak the tested value or announce a test."""
    path = task_dir / "instruction.md"
    if not path.is_file():
        rep.bad("instruction.md is missing")
        return
    text = path.read_text(encoding="utf-8")
    low = text.lower()
    rep.ok("instruction.md exists")

    # Leak check: the literal tested value string must not appear verbatim. That
    # would hand the agent the answer and defeat the latent-adherence measurement.
    leaked = []
    for dim, val in _check_values(meta):
        v = val.strip()
        # ignore trivially-short/ambiguous values that would false-positive
        # endpoint-aware boundaries: a plain \b...\b can never match a value that
        # ends in punctuation ("85+", "$200k+"), so it would pass silently.
        if len(v) >= 3 and _value_mention_re(v.lower()).search(low):
            leaked.append((dim, val))
    if leaked:
        for dim, val in leaked:
            rep.bad(f"instruction.md LEAKS the tested value {val!r} (dim {dim}) — "
                    f"the agent must not be told the answer")
    else:
        rep.ok("instruction.md does not leak any tested value")

    # "you are being tested" / evaluation framing check. A task can legitimately
    # instruct the agent NOT to mention evaluation (a negation); only flag phrasing
    # that tells the agent it IS under test.
    leak_phrases = [
        "you are being tested", "this is a test", "you are being evaluated",
        "this is an evaluation", "we are testing", "we are evaluating",
        "adherence", "persona.yaml", "dimension_id",
    ]
    hits = []
    for ph in leak_phrases:
        idx = low.find(ph)
        if idx < 0:
            continue
        window = low[max(0, idx - 40):idx]
        # allow negated framing: "don't mention ... evaluation", "not a test"
        if re.search(r"(don't|do not|never|not|isn't|no)\b[^.]*$", window):
            continue
        hits.append(ph)
    if hits:
        rep.bad(f"instruction.md leaks the evaluation framing: {hits} — "
                f"the agent should just do the task in character")
    else:
        rep.ok("instruction.md does not announce that this is a test/evaluation")


def check_persona(task_dir: Path, meta: dict, rep: Report) -> None:
    """For each check, persona.attributes[dim].value must equal the check value.

    This is exactly the codestyle dimension_id-drift trap: a task.toml that names
    a dimension the persona does not actually carry (or carries at a different
    value) silently measures nothing.
    """
    path = task_dir / "persona.yaml"
    if not path.is_file():
        rep.bad("persona.yaml is missing")
        return
    if yaml is None:
        rep.warn("pyyaml not installed — cannot cross-check persona values")
        return
    try:
        persona = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    except yaml.YAMLError as exc:
        rep.bad(f"persona.yaml does not parse: {exc}")
        return
    rep.ok("persona.yaml parses")

    attrs = persona.get("attributes") or {}
    if not isinstance(attrs, dict):
        rep.bad("persona.yaml has no `attributes` mapping")
        return

    for dim, val in _check_values(meta):
        entry = attrs.get(dim)
        if entry is None:
            rep.bad(f"persona is missing attribute {dim!r} that check tests "
                    f"(dimension_id drift?)")
            continue
        pval = str(entry.get("value")) if isinstance(entry, dict) else str(entry)
        if pval.strip() == val.strip():
            rep.ok(f"persona {dim} = {pval!r} matches check")
        else:
            rep.bad(f"persona {dim} = {pval!r} but check expects {val!r} — "
                    f"value drift; the agent would carry the wrong value")


def check_solve(task_dir: Path, rep: Report) -> None:
    """solution/solve.sh must exist and pass `bash -n` (syntax-only parse)."""
    path = task_dir / "solution" / "solve.sh"
    if not path.is_file():
        rep.bad("solution/solve.sh is missing")
        return
    rep.ok("solution/solve.sh exists")
    proc = subprocess.run(["bash", "-n", str(path)],
                          capture_output=True, text=True)
    if proc.returncode == 0:
        rep.ok("solve.sh passes `bash -n` (no shell syntax errors)")
    else:
        rep.bad(f"solve.sh has a shell syntax error: {proc.stderr.strip()}")


def check_verifier(task_dir: Path, rep: Report) -> None:
    """tests/verifier.py must exist and byte-compile cleanly."""
    path = task_dir / "tests" / "verifier.py"
    if not path.is_file():
        rep.bad("tests/verifier.py is missing")
        return
    rep.ok("tests/verifier.py exists")
    proc = subprocess.run([sys.executable, "-m", "py_compile", str(path)],
                          capture_output=True, text=True)
    if proc.returncode == 0:
        rep.ok("verifier.py compiles (py_compile)")
    else:
        rep.bad(f"verifier.py does not compile: {proc.stderr.strip().splitlines()[-1] if proc.stderr.strip() else proc.stderr}")


def check_test_sh(task_dir: Path, rep: Report) -> None:
    """tests/test.sh must exist — harbor execs it to score the trial. A task
    without it fails at `harbor run` with an opaque 'datasets or tasks must be
    provided' error, so catch it here instead."""
    path = task_dir / "tests" / "test.sh"
    if path.is_file():
        rep.ok("tests/test.sh exists (verifier entrypoint)")
    else:
        rep.bad("tests/test.sh is missing — harbor needs it to run the task "
                "(scaffold generates it; add a one-liner that execs verifier.py)")


def check_no_todos(task_dir: Path, rep: Report) -> None:
    """A task must be FINISHED before a PR: no leftover scaffold TODO markers and
    no stub persona. This catches half-filled scaffolds that otherwise pass every
    structural check."""
    todo_files = []
    for path in sorted(task_dir.rglob("*")):
        if not path.is_file() or "__pycache__" in path.parts:
            continue
        try:
            text = path.read_text(encoding="utf-8")
        except (UnicodeDecodeError, OSError):
            continue
        n = text.count("TODO(contributor)")
        if n:
            todo_files.append((path.relative_to(task_dir).as_posix(), n))
    if todo_files:
        total = sum(n for _, n in todo_files)
        where = ", ".join(f"{f} ({n})" for f, n in todo_files)
        rep.bad(f"{total} unfilled TODO(contributor) marker(s) remain: {where}")
    else:
        rep.ok("no leftover scaffold TODO markers")

    persona = task_dir / "persona.yaml"
    if persona.is_file() and "SCAFFOLD-REPLACE-ME" in persona.read_text(encoding="utf-8"):
        rep.bad("persona.yaml is still the scaffold stub (persona_id "
                "SCAFFOLD-REPLACE-ME) — replace it with a real sampled persona")


# input label-leak guard ------------------------------------------------------
# Everything under input/ is bind-mounted verbatim, read-only, into the agent's
# container (trial.py build_task_input_mounts), and instructions routinely tell
# the agent to read those files. So a hidden ground-truth label left inline in an
# input file (e.g. `animal: true`, `risk: 2`, `data-risk="3"`) is readable by the
# agent — it can score itself and adherence stops being latent. Ground truth must
# live under tests/ (e.g. tests/answer_key.yaml), which is never mounted.
# A label is a structured `key: <scalar>` pair (a bool or small int ground-truth
# tag), NOT the word appearing in prose. Requiring a scalar VALUE after the colon
# avoids flagging sentences like "keep pushing risk: press again" in a bot prompt.
_LABEL_VALUE = r"""(?:true|false|["']?\d{1,2}["']?)"""
_LABEL_KEY_RE = re.compile(
    rf"""(?ix)
    (?:^|[\s,{{"'])                # start / separator before the key
    (?:
        (?:animal|risk|adherence|ground[_-]?truth|label|expected)
            \s* : \s* {_LABEL_VALUE} \b   # yaml/json: key -> scalar label
      |
        data-(?:risk|animal|label) \s* = \s* ["']?\d{{1,2}}   # html data attrs
    )
    """
)
# Files whose label-looking tokens are legitimately part of the task surface and
# not a leak (the agent SEEING these is the point). Extend deliberately.
_LABEL_ALLOW_SUFFIXES = ()

# --- structural label detection ------------------------------------------------
# The regex above only fires on label KEYS it already knows (`animal`, `risk`, …),
# which are the names the two reference suites happen to use. A contributor who
# calls the same thing `flag`, `check`, `eco` or `keyed` slips through silently.
# So for parseable declarative files we also detect a label by its SHAPE: inside
# an entry that carries an `id` (i.e. a question or an option), any other key
# whose value is a bool, a small int, or a real dimension id is ground truth,
# whatever it is named.
_PRESENTATION_KEYS = frozenset({
    "id", "text", "prompt", "title", "name", "description", "desc", "body",
    "type", "options", "questions", "sections", "items", "choices",
    "price", "cost", "amount", "value", "unit", "currency", "order", "index",
    "placeholder", "hint", "help", "image", "icon", "url", "href", "alt",
    # Harness configuration that legitimately sits beside an id and happens to be
    # a small integer or a bool. These describe how the surface RUNS, not which
    # option is correct — `maxTurns: 3` in a chat scenario is a turn budget, and
    # flagging it made this check reject a merged task on its first wider run.
    "maxturns", "max_turns", "minturns", "min_turns", "turns",
    "timeout", "timeout_sec", "retries", "seed", "version", "count",
    "min", "max", "step", "rows", "cols", "width", "height", "size",
    "required", "multiple", "enabled", "visible", "default",
    "applicationid", "application_id", "scenarioid", "scenario_id",
})


@functools.lru_cache(maxsize=1)
def _dimension_ids() -> frozenset[str]:
    """Schema ids, read once — this is consulted for every file under input/."""
    path = REPO / "evaluation" / "src" / "persona" / "schema" / "dimensions.json"
    if not path.is_file():
        return frozenset()
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (ValueError, OSError):
        return frozenset()
    rows = data if isinstance(data, list) else data.get("dimensions", [])
    return frozenset(
        str(r.get("id") or r.get("dimension_id"))
        for r in rows if isinstance(r, dict) and (r.get("id") or r.get("dimension_id"))
    )


def _looks_like_label(key: str, val: object, dim_ids: frozenset[str]) -> bool:
    if key.lower() in _PRESENTATION_KEYS or key in _PRESENTATION_KEYS:
        return False
    if isinstance(val, bool):
        return True
    if isinstance(val, int) and 0 <= val <= 9:
        return True
    if isinstance(val, str) and val in dim_ids:
        return True
    return False


def _walk_for_labels(node: object, dim_ids: frozenset[str],
                     trail: str = "") -> list[tuple[str, str]]:
    """Return (path, "key: value") for every ground-truth-shaped key found."""
    found: list[tuple[str, str]] = []
    if isinstance(node, dict):
        entry = "id" in node          # a question/option entry, not a wrapper
        for k, v in node.items():
            where = f"{trail}.{k}" if trail else str(k)
            if entry and _looks_like_label(str(k), v, dim_ids):
                found.append((where, f"{k}: {v}"))
            else:
                found.extend(_walk_for_labels(v, dim_ids, where))
    elif isinstance(node, list):
        for i, v in enumerate(node):
            found.extend(_walk_for_labels(v, dim_ids, f"{trail}[{i}]"))
    return found


# A structured-label scan reads the parsed document, so it cannot see a comment.
# But a comment in a mounted file is read by the agent exactly like the data is,
# and "the keyed option is the most expensive one in q3" gives the answer away as
# surely as `flag: true` does. Scan the raw text for prose that identifies an
# option, names a scored dimension, or explains the scoring.
# Narrow on purpose. Saying WHERE ground truth lives ("the labels are in
# tests/answer_key.yaml") tells the agent nothing it can act on, and every merged
# suite documents itself that way. What leaks is prose that lets you IDENTIFY the
# keyed option: naming option ids, a position, or a rule for spotting it.
# Option ids are OPAQUE by contract (docs/task-format.md: "option ids are
# opaque"), so this scan must not assume a shape. Merged tasks already use ids a
# shape guess misses — `apt_harbor`, `animals_one_dog`, `code_sample`,
# `visit_review` — and `# correct answer is option_a` went undetected. Read the
# ids the mounted files themselves DECLARE and match exactly those.
_ID_DECL_RE = re.compile(
    r"""(?ix)
      (?:^|[\s,{\[(]) id \s* : \s* ["']? ([a-z][\w.-]{1,31}) ["']?  # yaml  id: x
    | ["'] id ["'] \s* : \s* ["'] ([a-z][\w.-]{1,31}) ["']          # json  "id":"x"
    | \b data-id \s* = \s* ["'] ([a-z][\w.-]{1,31}) ["']            # html  data-id="x"
    | \b id \s* = \s* ["'] ([a-z][\w.-]{1,31}) ["']                 # html  id="x"
    """
)
# The two conventional shapes stay as a fallback for surfaces that declare ids
# some other way (an app source carries them as tuple elements, not an `id:` key).
_ID_SHAPE_FALLBACK = r"q\d+[a-z]|[a-z]\d{2}"
# An id that is also an ordinary English word would turn this into a word search
# and cost the check its zero false-positive rate; skip those and let the
# fallback shapes or the surrounding frame carry the line.
_ID_STOPWORDS = frozenset("""
    id name text type value price label option options answer answers item items
    question questions choice choices is are the a an and or of to in on it no
    yes true false one two three first last top bottom none all
""".split())


def _declared_ids(texts: Iterable[str]) -> tuple[str, ...]:
    """Every id literal declared by the mounted files, longest first."""
    found: set[str] = set()
    for text in texts:
        for m in _ID_DECL_RE.finditer(text):
            tok = next(g for g in m.groups() if g)
            if len(tok) >= 2 and tok.lower() not in _ID_STOPWORDS:
                found.add(tok)
    return tuple(sorted(found, key=lambda s: (-len(s), s)))


@functools.lru_cache(maxsize=None)
def _prose_answer_re(ids: tuple[str, ...]) -> re.Pattern:
    alts = "|".join([*(re.escape(i) for i in ids), _ID_SHAPE_FALLBACK])
    id_run = rf"""[`'"]?(?:{alts})[`'"]?(?:\s*[,/&]\s*|\s+and\s+)?"""
    return re.compile(
        rf"""(?ix)
          # "the keyed option is ..." / "persona-consistent picks are s01 and s04"
          \b(?:keyed|flagged|correct|adherent|persona[ _-]?(?:consistent|inconsistent))\b
            [^.\n]{{0,40}}?
            (?: \b(?:is|are)\b | : ) \s* {id_run}
        | \b(?:keyed|flagged|correct|adherent)\s+(?:option|answer|pick|choice|line)\b
            [^.\n]{{0,40}}?
            \b(?:most|least|cheapest|dearest|first|last|only|top|bottom)\b
        | \b(?:answer|keyed\s+option)\s+is\s+the\b
        """
    )


def _prose_answer_hints(path: Path,
                        ids: tuple[str, ...] = ()) -> list[tuple[int, str]]:
    """Comment/prose lines under input/ that describe the scoring."""
    try:
        lines = path.read_text(encoding="utf-8").splitlines()
    except (UnicodeDecodeError, OSError):
        return []
    pat = _prose_answer_re(ids)
    return [(i, ln.strip()[:110]) for i, ln in enumerate(lines, 1)
            if pat.search(ln)]


def _structural_labels(path: Path) -> list[tuple[str, str]]:
    if path.suffix.lower() not in {".yaml", ".yml", ".json"}:
        return []
    try:
        text = path.read_text(encoding="utf-8")
    except (UnicodeDecodeError, OSError):
        return []
    try:
        if path.suffix.lower() == ".json":
            doc = json.loads(text)
        else:
            if yaml is None:
                return []
            doc = yaml.safe_load(text)
    except Exception:  # noqa: BLE001 - an unparseable input file is not our call
        return []
    return _walk_for_labels(doc, _dimension_ids())


def _leak_norm(text: str) -> str:
    """Fold the two label passes' renderings of one hit onto comparable text.

    The regex pass records the RAW source line; the structural pass records the
    PARSED pair, so a YAML `animal: true` comes back through Python's repr as
    `animal: True` and a JSON `"animal": true` carries quotes the pair does not.
    Case-fold, drop quotes and collapse runs of whitespace so the two spellings
    of one hit compare equal. Nothing else is folded: values are left otherwise
    intact so two genuinely different labels never collapse into one.
    """
    return re.sub(r"\s+", " ", text.lower().replace('"', "").replace("'", "")).strip()


def _already_reported(pair: str, fragments: Iterable[str]) -> bool:
    r"""True when the structural pass's `key: value` is one the regex already hit.

    `fragments` are the regex pass's own MATCHES, not the whole source lines it
    reports: a line can carry two labels, and only the one the regex actually
    matched is a duplicate. Delimited on both sides against `[\w.-]` so this
    stays a match of the whole key and the whole value — `animal: 1` must not
    swallow `animal: 10`, `animal: true` must not swallow `is_animal: true`.
    """
    needle = _leak_norm(pair)
    if not needle:
        return False
    pat = re.compile(rf"(?<![\w.-]){re.escape(needle)}(?![\w.-])")
    return any(pat.search(_leak_norm(f)) for f in fragments)


# Severity is named at every append site below rather than implied by which list
# a hit lands in, so appending a new pass's hits to the wrong list can no longer
# silently change what CI gates on.
_SEV_FAIL = "FAIL"
_SEV_WARN = "WARN"


def check_app_launcher(task_dir: Path, meta: dict, rep: Report) -> None:
    """App launchers must target the display the CUA agent actually screenshots.

    harbor's CUA runtime serves the desktop on :1 (``_DEFAULT_DISPLAY`` in
    ``harbor/agents/computer_1/runtime.py``) and passes DISPLAY only as an
    inline prefix on the commands it builds itself — a healthcheck script runs
    with DISPLAY unset. A launcher written ``${DISPLAY:-:0}`` therefore starts
    the app on a display nothing serves: the container is healthy, screenshots
    are captured, and the agent stares at an empty desktop until it times out.

    Second fault, same file: a keeper spawned through
    ``bash -c "$(declare -f keeper); keeper"`` carries its own function source in
    its command line, so a ``pgrep -f`` for a contiguous literal app path matches
    the keeper itself. The liveness check then never fires and a crashed app is
    never respawned. Assemble the path at runtime, or anchor the pattern
    (``pgrep -fx``, or ``^``/``$`` around it).
    """
    if (meta.get("metadata") or {}).get("type") != "app":
        return
    scripts = sorted((task_dir / "environment").glob("*.sh"))
    if not scripts:
        rep.warn("app task has no environment/*.sh launcher — is the app started "
                 "by the Dockerfile CMD?")
        return

    for path in scripts:
        name = f"environment/{path.name}"
        text = path.read_text(encoding="utf-8")
        # Comments legitimately mention :0 to explain why the script avoids it,
        # so only assignments count. Full-line comments are enough to strip: a
        # trailing `#` inside a launcher is rare and only costs a false FAIL.
        code = "\n".join(ln for ln in text.splitlines()
                         if not ln.lstrip().startswith("#"))

        if re.search(r"""DISPLAY=["']?(?:\$\{DISPLAY:-)?:0\b""", code):
            rep.bad(f"{name}: assigns DISPLAY :0, but the CUA runtime serves the "
                    f"desktop on :1 — the agent never sees the app. Use "
                    f'`export DISPLAY="${{DISPLAY:-:1}}"`.')
        elif "DISPLAY" in code:
            rep.ok(f"{name}: DISPLAY targets :1 (the display the agent screenshots)")
        else:
            rep.warn(f"{name}: never sets DISPLAY — Tkinter will inherit whatever "
                     f"the container has; pin :1 to be sure the agent sees the app")

        keeper = re.search(r"^keeper\(\) \{\n(.*?)^\}", text, re.S | re.M)
        if keeper is None:
            continue
        body = keeper.group(1)
        selfmatch = [
            pat for flag, pat in re.findall(
                r"pgrep\s+(-\S+)\s+(\"[^\"]*\"|'[^']*'|\S+)", body)
            if "x" not in flag                       # -fx compares the whole cmdline
            and not pat.strip("\"'").startswith("^")  # anchored can't match `bash -c`
            and not pat.strip("\"'").endswith("$")
            and "$" not in pat                       # assembled at runtime
        ]
        if selfmatch:
            rep.bad(f"{name}: keeper's `pgrep -f {selfmatch[0]}` also matches the "
                    f"keeper's own `bash -c` command line, so a dead app is never "
                    f"respawned — assemble the path at runtime or use `pgrep -fx`.")
        else:
            rep.ok(f"{name}: keeper liveness check cannot self-match")


def check_input_no_labels(task_dir: Path, rep: Report) -> None:
    """Flag files under input/ that carry an inline ground-truth label.

    Severity is a property of the PASS that found the hit, not of the list it is
    collected in — each append below names its own:

      - FAIL — the named-key regex pass on a declarative choice file (survey
        questionnaire.yaml/.json). The label belongs in tests/answer_key.yaml, a
        trivial no-cost move, and this is the gate the checker exists for. Zero
        hits on merged main, so keeping it a FAIL turns no merged task red.
      - WARN — the structural (shape-based) pass and the prose/answer-hint pass.
        Both are new, and both fire on merged tasks this PR does not touch
        (two questionnaires ship a `dimension_id`), so shipping them as FAIL
        would turn main red and the check would never land. Detection is
        identical either way; flip these two to _SEV_FAIL once those tasks are
        cleaned up. Do not flip the regex pass — it is already a FAIL.
      - WARN — any pass firing on the web page (input/site/*.html) or app source
        (input/app/*.py): these surfaces need the label at RUNTIME (the DOM
        renders it, the app process reads it to build order.json), so it cannot
        simply be deleted from the file. It is still readable by an agent that
        `cat`s the mounted source, so it is a real — but structural — leak
        tracked separately from surveys.
    """
    input_dir = task_dir / "input"
    if not input_dir.is_dir():
        rep.ok("no input/ dir (nothing mounted to the agent)")
        return
    # (severity, rel, lineno, snippet) — severity is set by the pass that appends.
    leaks: list[tuple[str, str, int, str]] = []
    # Runtime surfaces are aggregated into a single WARN line of their own.
    runtime: list[tuple[str, int, str]] = []
    files = [p for p in sorted(input_dir.rglob("*")) if p.is_file()
             and "__pycache__" not in p.parts
             and not p.name.endswith(_LABEL_ALLOW_SUFFIXES)]
    # The prose scan matches the ids this task's own mounted files declare, not a
    # guessed id shape — a comment naming an id leaks the same way whichever file
    # it sits in, so the pool is task-wide.
    texts = []
    for p in files:
        try:
            texts.append(p.read_text(encoding="utf-8"))
        except (UnicodeDecodeError, OSError):
            continue
    ids = _declared_ids(texts)
    for path in files:
        try:
            lines = path.read_text(encoding="utf-8").splitlines()
        except (UnicodeDecodeError, OSError):
            continue
        rel = path.relative_to(task_dir).as_posix()
        # runtime surfaces that legitimately hold the label to function
        runtime_surface = (path.suffix in {".html", ".htm"}
                           or "/app/" in f"/{rel}" or rel.startswith("input/app/"))
        # Regex pass: a known label key with a scalar value. FAIL on a
        # declarative file — the whole point of the checker.
        matched: list[str] = []          # the matched `key: value`s, for the dedupe
        for lineno, line in enumerate(lines, 1):
            hits = [m.group(0) for m in _LABEL_KEY_RE.finditer(line)]
            if not hits:
                continue
            matched.extend(hits)
            snippet = line.strip()
            if runtime_surface:
                runtime.append((rel, lineno, snippet))
            else:
                leaks.append((_SEV_FAIL, rel, lineno, snippet))
        # Name-independent pass: catches a label the regex has never heard of.
        # WARN (see the severity table in the docstring).
        for where, pair in _structural_labels(path):
            if _already_reported(pair, matched):
                continue          # already reported by the regex pass
            entry = (rel, 0, f"{where} → {pair}")
            if runtime_surface:
                runtime.append(entry)
            else:
                leaks.append((_SEV_WARN, *entry))
        # Prose pass: a comment that explains the scoring leaks it just as
        # surely. WARN (see the severity table in the docstring).
        for lineno, snippet in _prose_answer_hints(path, ids):
            leaks.append((_SEV_WARN, rel, lineno, snippet))
    # Report each severity as its own group, overflow line included, so the
    # "... and N more" line can never be louder or quieter than the hits it
    # stands for.
    for severity, emit in ((_SEV_FAIL, rep.bad), (_SEV_WARN, rep.warn)):
        group = [h for h in leaks if h[0] == severity]
        for _, rel, lineno, snippet in group[:8]:
            emit(f"input/ LEAKS a ground-truth label: {rel}:{lineno}  {snippet!r} "
                 f"— move it to tests/answer_key.yaml (input/ is mounted to the agent)")
        if len(group) > 8:
            emit(f"... and {len(group) - 8} more label leak(s) in declarative "
                 f"input files")
    if runtime:
        rel, lineno, snippet = runtime[0]
        rep.warn(f"web/app runtime surface carries a label an agent could read from "
                 f"mounted source ({rel}:{lineno} {snippet!r}, {len(runtime)} total) — "
                 f"structural leak; de-leaking needs a server-side/label-free rewrite")
    if not leaks and not runtime:
        rep.ok("input/ carries no inline ground-truth labels")


# chat sim context ------------------------------------------------------------
# input/context.md is not just mounted: chat_harness reads it whole and passes it
# as `sut_desc` into the persona simulator's own prompt. So a design note in that
# file is spoken directly to the acting model. check_instruction only ever reads
# instruction.md, so this file has been unchecked — and it is prose, not a
# structured label, so the input/ label guard cannot see it either.
_SIM_COACHING_RE = re.compile(
    r"""(?ix)
      we \s are \s (?:testing|evaluating|measuring)
    | latent \s adherence
    | (?:anchor|contrast) \s value
    | persona \s should \b
    | a \s persona \s (?:holding|with|carrying) \b
    | should \s (?:speak|resist|decline|refuse|steer|avoid|not\b)
    """
)


def check_sim_context(task_dir: Path, meta: dict, rep: Report) -> None:
    """input/context.md reaches the persona simulator — it must not coach it."""
    path = task_dir / "input" / "context.md"
    if not path.is_file():
        return                      # only chat tasks carry one
    text = path.read_text(encoding="utf-8")
    low = text.lower()

    # endpoint-aware boundaries (see _value_mention_re): with a plain \b...\b a
    # value ending in punctuation — "85+", "20+", "$200k+", "Fluent (C1-C2)" —
    # never matched, so a context.md naming exactly that value passed this guard
    # and was then injected into the simulator prompt.
    # COMMON-WORD PROBLEM — read this before flipping `named` to rep.bad.
    # The needle is the dimension VALUE, so a value that is also an everyday
    # English word matches ordinary scenario prose. In skyve2012's 2026-09-10
    # sweep of main, six of this pass's fourteen hits were prose, not leaks:
    #   commstyle-chat          'Never'   <- "it never asks"
    #   mindful-meditator-chat  'Daily'   <- "daily rhythm"
    #   morningkit-chat         'Daily'   <- "the daily kit"
    #   visual-chat             'Visual'  <- "visual-only view"
    #   cash-chat, youtube-chat           <- scenario lists every on-screen option
    # The other eight were real leaks. The boundaries are not the bug —
    # _value_mention_re is already endpoint-correct — so tightening them fixes
    # nothing; separating a named VALUE from the same word used as prose does.
    # Until that exists this half stays a WARN a human reads.
    # Known blind spot in the other direction: a negation pointer that names no
    # value at all ("this survey never mentions alcohol") is outside both this
    # pass and _SIM_COACHING_RE. never-bar-chat is caught only by accident,
    # because its value happens to be 'Never'.
    named = [f"{val!r} ({dim})" for dim, val in _check_values(meta)
             if len(val.strip()) >= 3
             and _value_mention_re(val.strip().lower()).search(low)]
    coaching = sorted({m.group(0).strip() for m in _SIM_COACHING_RE.finditer(text)})

    # WARN, not FAIL, until the merged chat suites are de-leaked: shipping this
    # as FAIL would turn main red on tasks nobody in this PR touched, and a check
    # that cannot be merged protects nothing. Flip `coaching` to rep.bad once #34
    # and a companion cleanup have landed; `named` additionally needs the
    # common-word problem above solved first.
    if named:
        rep.warn(f"input/context.md names the tested value {', '.join(named)} — "
                f"chat_harness passes this file into the persona simulator's "
                f"prompt, so the acting model is told the answer")
    if coaching:
        rep.warn(f"input/context.md coaches the persona simulator: {coaching[:4]} — "
                f"describe only the scenario and the opening message")
    if not named and not coaching:
        rep.ok("input/context.md does not coach the persona simulator")


# output-path agreement -------------------------------------------------------
# grep the path instruction.md tells the agent to write, and the path
# verifier.py reads, and warn if they visibly disagree. Best-effort: filenames
# are the load-bearing token (dir prefixes differ container vs host).
_PATH_RE = re.compile(r"[\w./-]*?([\w-]+\.json)")


def check_output_paths(task_dir: Path, rep: Report) -> None:
    instr = task_dir / "instruction.md"
    verif = task_dir / "tests" / "verifier.py"
    if not (instr.is_file() and verif.is_file()):
        return  # already reported as missing
    itext = instr.read_text(encoding="utf-8")
    vtext = verif.read_text(encoding="utf-8")

    # what instruction.md tells the agent to WRITE (look near "write"/output path)
    instr_files = set()
    for m in re.finditer(r"[`/][\w./-]*?([\w-]+\.json)", itext):
        instr_files.add(m.group(1))
    # what verifier.py READS (any *.json filename literal it references)
    verif_files = set(re.findall(r"['\"][\w./-]*?([\w-]+\.json)['\"]", vtext))
    # also catch `/ "name.json"` path-join style
    verif_files |= set(re.findall(r"/\s*['\"]([\w-]+\.json)['\"]", vtext))

    if not instr_files:
        rep.warn("could not find an output .json path in instruction.md "
                 "(chat tasks write no file — ignore if so)")
        return
    if not verif_files:
        rep.warn("could not find a .json filename in verifier.py to compare")
        return
    common = instr_files & verif_files
    if common:
        rep.ok(f"output path agrees: instruction writes and verifier reads "
               f"{sorted(common)}")
    else:
        rep.warn(f"output path may disagree: instruction.md mentions "
                 f"{sorted(instr_files)} but verifier.py reads {sorted(verif_files)} "
                 f"— confirm the agent writes the file the verifier reads")


# --------------------------------------------------------------------------- #
def main() -> int:
    ap = argparse.ArgumentParser(
        description="Validate a PersonaBench task dir for contract compliance "
                    "before opening a PR.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="example:\n  python evaluation/src/tools/task_doctor.py "
               "health-lifestyle/diet-type/vegan/vegan-survey",
    )
    ap.add_argument("task", help="task path relative to tasks/ "
                                 "(same form as run_task.py)")
    args = ap.parse_args()

    task_dir, root_name = _resolve_task_dir(args.task)
    if task_dir is None:
        roots = ", ".join(str(r.relative_to(REPO)) for r in TASK_ROOTS)
        print(f"{_R}error{_0}: no task.toml for {args.task!r} under {roots}",
              file=sys.stderr)
        return 2

    print(f"{_B}task-doctor{_0}: {root_name}/{args.task}")
    print(f"  dir: {task_dir}")
    print()

    rep = Report()
    meta = check_task_toml(task_dir, rep)
    if meta is not None:
        check_instruction(task_dir, meta, rep)
        check_persona(task_dir, meta, rep)
    check_solve(task_dir, rep)
    check_verifier(task_dir, rep)
    check_test_sh(task_dir, rep)
    if meta is not None:
        check_app_launcher(task_dir, meta, rep)
    check_input_no_labels(task_dir, rep)
    check_sim_context(task_dir, meta or {}, rep)
    check_output_paths(task_dir, rep)
    check_no_todos(task_dir, rep)
    # App tasks ship a GUI the agent drives from screenshots. Two of its defects
    # — content no action can scroll to, a window wider than the framebuffer —
    # leave every other check green while making the task unsolvable, so they
    # are checked here rather than discovered in a paid run.
    if (meta or {}).get("metadata", {}).get("type") == "app":
        app_env_check.run(task_dir, rep)

    rep.render()
    print()
    n_fail = sum(1 for s, _ in rep.rows if s == "FAIL")
    n_warn = sum(1 for s, _ in rep.rows if s == "WARN")
    if rep.failed:
        print(f"{_R}{_B}FAIL{_0} — {n_fail} problem(s), {n_warn} warning(s). "
              f"Fix the FAILs above before opening a PR.")
        return 1
    print(f"{_G}{_B}PASS{_0} — contract looks good"
          + (f" ({n_warn} warning(s) to eyeball)." if n_warn else "."))
    return 0


if __name__ == "__main__":
    sys.exit(main())
