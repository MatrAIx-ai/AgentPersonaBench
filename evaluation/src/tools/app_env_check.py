#!/usr/bin/env python3
"""app_env_check — static checks on an app task's GUI before it costs a run.

App tasks ship a Tkinter GUI under ``environment/`` that the computer-use agent
drives from screenshots. Two defects in that GUI are invisible to every other
check we have, because the task builds, launches, and looks fine — the agent
simply cannot finish it:

**The list scrolls in principle but nothing can scroll it.** The usual pattern
is a ``tk.Canvas`` holding a taller frame, with ``scrollregion`` set from
``bbox("all")``. That configures *how far* the view may move; it supplies no way
to move it. Without a scrollbar, a wheel binding, or a key binding, everything
past the first viewport is unreachable — and it is not a small tail: a measured
SmartCart put 1392px of cards in a 650px viewport, so 53% of the items could not
be clicked at all. Tasks whose instructions say "scroll to see all the options"
were shipping exactly this.

**The window is bigger than the screen.** The CUA desktop is 1024x900 (see
``computer_1.py``'s ``desktop_width``/``desktop_height``). A window wider or
taller than that is clipped by the framebuffer, and the agent never sees the
part that is cut off — including, often, the submit button.

Both are cheap to check in the source and expensive to discover in a run, so
they are checked here rather than left to review. ``task_doctor`` calls this for
every app task; it also runs standalone:

    python evaluation/src/tools/app_env_check.py <task-path>

Exit code: 0 if every check PASSes (WARNs are allowed), 1 otherwise.

Dependencies: stdlib only. No Tk, no display, no container — this reads source.
"""
from __future__ import annotations

import argparse
import ast
import re
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[3]
TASK_ROOTS = [REPO / "tasks" / "single-attribute", REPO / "tasks" / "multi-attribute"]

# The desktop persona-computer-1 brings up. Keep in sync with computer_1.py's
# desktop_width / desktop_height defaults.
DESKTOP_W, DESKTOP_H = 1024, 900
# xfwm4 draws a title bar above the client area; a window sized to the full
# desktop height loses its bottom edge to it.
TITLEBAR_H = 32

# Anything that can actually move a canvas's view.
_SCROLL_AFFORDANCES = (
    ("a scrollbar", re.compile(r"\bScrollbar\b")),
    ("a wheel binding", re.compile(r"<Button-4>|<Button-5>|<MouseWheel>")),
    ("a key binding", re.compile(r"<Prior>|<Next>|<Up>|<Down>|<Home>|<End>")),
    ("a scroll call", re.compile(r"\byview_scroll\b|\byview_moveto\b")),
)


def gui_sources(task_dir: Path) -> list[Path]:
    """The Python files under environment/ — the GUI the agent will drive."""
    env = task_dir / "environment"
    return sorted(p for p in env.glob("*.py")) if env.is_dir() else []


def _geometries(tree: ast.AST) -> list[tuple[int, int, int]]:
    """(width, height, lineno) for every literal ``.geometry("WxH")`` call."""
    found = []
    for node in ast.walk(tree):
        if not (isinstance(node, ast.Call)
                and isinstance(node.func, ast.Attribute)
                and node.func.attr == "geometry"
                and node.args
                and isinstance(node.args[0], ast.Constant)
                and isinstance(node.args[0].value, str)):
            continue
        m = re.match(r"^(\d+)x(\d+)", node.args[0].value)
        if m:
            found.append((int(m.group(1)), int(m.group(2)), node.lineno))
    return found


def check_window_size(path: Path, src: str, rep) -> None:
    """The window must fit the 1024x900 framebuffer the agent screenshots."""
    name = path.name
    try:
        tree = ast.parse(src)
    except SyntaxError as exc:
        rep.bad(f"{name} does not parse: {exc}")
        return
    sizes = _geometries(tree)
    if not sizes:
        rep.warn(f"{name}: no literal .geometry(\"WxH\") — confirm by hand that "
                 f"the window fits {DESKTOP_W}x{DESKTOP_H}")
        return
    for w, h, line in sizes:
        where = f"{name}:{line}"
        if w > DESKTOP_W or h > DESKTOP_H:
            rep.bad(f"{where}: window {w}x{h} is larger than the "
                    f"{DESKTOP_W}x{DESKTOP_H} desktop — the overflow is cut off "
                    f"the framebuffer and the agent never sees it")
        elif h > DESKTOP_H - TITLEBAR_H:
            rep.warn(f"{where}: window {w}x{h} leaves no room for the title bar "
                     f"(~{TITLEBAR_H}px) on a {DESKTOP_W}x{DESKTOP_H} desktop — "
                     f"the bottom edge is likely clipped")
        else:
            rep.ok(f"{where}: window {w}x{h} fits the "
                   f"{DESKTOP_W}x{DESKTOP_H} desktop")


def check_scrollable(path: Path, src: str, rep) -> None:
    """A canvas with a scrollregion needs something that can actually scroll it."""
    name = path.name
    if "tk.Canvas" not in src and "Canvas(" not in src:
        rep.ok(f"{name}: no canvas — nothing to scroll")
        return
    if "scrollregion" not in src:
        rep.warn(f"{name}: has a canvas but sets no scrollregion — confirm the "
                 f"content is not taller than the canvas")
        return

    present = [label for label, pattern in _SCROLL_AFFORDANCES if pattern.search(src)]
    if not present:
        rep.bad(f"{name}: the canvas sets a scrollregion but has no scrollbar, "
                f"wheel binding or key binding — content below the first "
                f"viewport cannot be reached by any action the agent can take")
        return
    rep.ok(f"{name}: canvas scrolls via {', '.join(present)}")

    # A wheel-only canvas moves, but nothing on screen says so. The agent works
    # from screenshots and has no way to learn the list continues.
    if not _SCROLL_AFFORDANCES[0][1].search(src):
        rep.warn(f"{name}: scrolling works but there is no visible scrollbar — "
                 f"a screenshot-driven agent cannot tell the list continues")

    # A fixed inner width does not shrink when a scrollbar takes its strip, so
    # the right edge of every row (usually the button) is covered.
    fixed = re.search(r"create_window\([^)]*\bwidth\s*=\s*(\d+)", src)
    if fixed and _SCROLL_AFFORDANCES[0][1].search(src):
        rep.warn(f"{name}: create_window pins the inner frame to "
                 f"{fixed.group(1)}px while a scrollbar is present — bind the "
                 f"canvas's <Configure> to the frame width instead, or the "
                 f"scrollbar covers the right edge of every row")


def run(task_dir: Path, rep) -> None:
    """Every app-GUI check, appended to an existing task_doctor Report."""
    sources = gui_sources(task_dir)
    if not sources:
        rep.warn("environment/ holds no .py — if this task ships a GUI, its "
                 "source belongs here (a Dockerfile COPY reads from this dir)")
        return
    for path in sources:
        try:
            src = path.read_text(encoding="utf-8")
        except OSError as exc:
            rep.bad(f"{path.name} is unreadable: {exc}")
            continue
        check_window_size(path, src, rep)
        check_scrollable(path, src, rep)


# --------------------------------------------------------------------------- #
def _standalone_report():
    """A Report with task_doctor's interface, for running this file directly."""
    tty = sys.stdout.isatty()
    green, red, yellow, off = (("\033[32m", "\033[31m", "\033[33m", "\033[0m")
                               if tty else ("", "", "", ""))

    class Report:
        def __init__(self):
            self.rows = []
            self.failed = False

        def ok(self, msg):
            self.rows.append(("PASS", msg))

        def warn(self, msg):
            self.rows.append(("WARN", msg))

        def bad(self, msg):
            self.rows.append(("FAIL", msg))
            self.failed = True

        def render(self):
            icon = {"PASS": f"{green}PASS{off}", "WARN": f"{yellow}WARN{off}",
                    "FAIL": f"{red}FAIL{off}"}
            for status, msg in self.rows:
                print(f"  [{icon[status]}] {msg}")

    return Report()


def main() -> int:
    ap = argparse.ArgumentParser(
        description="Check an app task's GUI for defects that make it "
                    "unsolvable: unreachable content, an oversized window.",
        epilog="example: python evaluation/src/tools/app_env_check.py "
               "behavior-preferences/accessibility-needs/visual/visual-app",
    )
    ap.add_argument("task", help="task path relative to tasks/ "
                                 "(same form as run_task.py)")
    args = ap.parse_args()

    task_dir = next((root / args.task for root in TASK_ROOTS
                     if (root / args.task / "task.toml").is_file()), None)
    if task_dir is None:
        roots = ", ".join(str(r.relative_to(REPO)) for r in TASK_ROOTS)
        print(f"error: no task.toml for {args.task!r} under {roots}",
              file=sys.stderr)
        return 2

    print(f"app-env-check: {args.task}")
    print(f"  dir: {task_dir}")
    print()
    rep = _standalone_report()
    run(task_dir, rep)
    rep.render()
    print()
    if rep.failed:
        n = sum(1 for s, _ in rep.rows if s == "FAIL")
        print(f"FAIL — {n} problem(s). The agent cannot solve this task as it stands.")
        return 1
    print("PASS — the GUI is reachable and fits the screen.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
