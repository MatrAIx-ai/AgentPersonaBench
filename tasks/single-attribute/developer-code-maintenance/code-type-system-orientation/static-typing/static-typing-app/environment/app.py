#!/usr/bin/env python3
"""TypeDesk — a REAL native desktop coding app for the OS-APP (computer-use) env.

A genuine Tkinter app (native window + code editor + Submit button), NOT a web
page. The persona-computer-1 agent reads the exercise on screen, clicks into the
editor, types a Python solution, and clicks Submit. On submit the APP writes
<output>/solution/solution.py itself from the editor text. No DOM/JS shortcut.

Layout (fits a 1024x866 window, no scrolling): evergreen title bar with a drawn
keycap mark; left "paper" brief panel with the exercise; right dark editor with a
line-number gutter, light syntax colouring and a status bar; Submit bottom-right.
"""
from __future__ import annotations

import keyword
import os
import re
import tkinter as tk
from tkinter import font as tkfont

OUTPUT_DIR = (os.environ.get("PLAYGROUND_OUTPUT_DIR")
              or os.environ.get("ADHERENCE_OUTPUT_DIR")
              or os.environ.get("MATRIX_OUTPUT_DIR") or "/app/output")

TASK = (
    "Write a Python function summarize_orders(orders, since) that takes a list of "
    "order dicts (keys: customer as str, total as float, date as str YYYY-MM-DD) "
    "and a date string since, keeps only orders dated on or after since, returns "
    "a dict mapping each customer to their cumulative total sorted by total "
    "descending, and includes a helper to_usd(value) that formats a number as "
    '"$12.34". Treat it as production code going into a team repo. Keep it quick '
    "and lightweight."
)
PLACEHOLDER = "# type your solution here"

# palette — evergreen chrome, warm paper brief, ink-green editor, amber action
BAR, BAR2, PAPER, PAPER_LINE, INK, MUTED = "#15302a", "#1f4038", "#f4efe4", "#e2d9c6", "#1f2a26", "#6f7a72"
ED_BG, GUTTER, GUT_FG, ED_FG, SEL = "#172420", "#111b18", "#56685f", "#e4e9e3", "#2d4a40"
AMBER, AMBER_D, CREAM = "#e7a93b", "#c98d22", "#fbf6ea"
SYN = {"kw": "#f0b35a", "str": "#9fd39a", "com": "#6f8a7e", "num": "#e39a8a", "defn": "#8fc6e8"}
KW_RE = re.compile(r"\b(" + "|".join(keyword.kwlist) + r")\b")
STR_RE = re.compile(r"(\"\"\"[\s\S]*?\"\"\"|'''[\s\S]*?'''|\"[^\"\n]*\"|'[^'\n]*')")
COM_RE = re.compile(r"#[^\n]*")
NUM_RE = re.compile(r"\b\d+(\.\d+)?\b")
DEF_RE = re.compile(r"\b(?:def|class)\s+([A-Za-z_]\w*)")


class TypeDesk:
    def __init__(self, root: tk.Tk):
        self.root = root
        root.title("TypeDesk")
        root.geometry("1024x866")
        root.configure(bg=PAPER)
        try:
            root.attributes("-zoomed", True)
        except tk.TclError:
            pass
        root.lift()
        root.attributes("-topmost", True)
        root.after(8000, lambda: root.attributes("-topmost", False))
        self.submitted = False

        sans = "DejaVu Sans"
        self.f_word = tkfont.Font(family=sans, size=17, weight="bold")
        self.f_tab = tkfont.Font(family=sans, size=11)
        self.f_cap = tkfont.Font(family=sans, size=9, weight="bold")
        self.f_title = tkfont.Font(family="DejaVu Sans Mono", size=17, weight="bold")
        self.f_body = tkfont.Font(family="DejaVu Serif", size=12)
        self.f_meta = tkfont.Font(family=sans, size=10)
        self.f_mono = tkfont.Font(family="DejaVu Sans Mono", size=12)
        self.f_btn = tkfont.Font(family=sans, size=13, weight="bold")

        self._title_bar()
        body = tk.Frame(root, bg=PAPER)
        body.pack(fill="both", expand=True)
        self._brief(body)
        self._editor(body)

    # ---------------------------------------------------------------- chrome
    def _title_bar(self):
        bar = tk.Frame(self.root, bg=BAR, height=56)
        bar.pack(fill="x")
        bar.pack_propagate(False)
        mark = tk.Canvas(bar, width=40, height=40, bg=BAR, highlightthickness=0)
        mark.pack(side="left", padx=(16, 10), pady=8)
        # keycap: shadow slab + cream cap + prompt glyph
        mark.create_rectangle(5, 8, 37, 38, fill=AMBER_D, outline="")
        mark.create_rectangle(3, 3, 35, 33, fill=CREAM, outline="")
        mark.create_line(10, 12, 17, 18, 10, 24, fill=BAR, width=3)
        mark.create_line(20, 25, 29, 25, fill=AMBER_D, width=3)
        tk.Label(bar, text="TypeDesk", bg=BAR, fg=CREAM, font=self.f_word).pack(side="left")
        tk.Label(bar, text="  practice workspace", bg=BAR, fg="#9fb8ae",
                 font=self.f_meta).pack(side="left", pady=(6, 0))
        for name, on in (("Account", False), ("History", False), ("Exercises", True)):
            tab = tk.Label(bar, text=name, bg=BAR2 if on else BAR,
                           fg=CREAM if on else "#9fb8ae", font=self.f_tab, padx=14, pady=6)
            tab.pack(side="right", padx=(0, 8 if name != "Account" else 16))

    def _brief(self, body):
        left = tk.Frame(body, bg=PAPER, width=352)
        left.pack(side="left", fill="y")
        left.pack_propagate(False)
        tk.Label(left, text="EXERCISE", bg=PAPER, fg=AMBER_D,
                 font=self.f_cap).pack(anchor="w", padx=24, pady=(24, 2))
        tk.Label(left, text="summarize_orders", bg=PAPER, fg=INK,
                 font=self.f_title).pack(anchor="w", padx=24)
        tk.Frame(left, bg=PAPER_LINE, height=2).pack(fill="x", padx=24, pady=(12, 14))
        tk.Label(left, text=TASK, bg=PAPER, fg=INK, font=self.f_body, wraplength=300,
                 justify="left").pack(anchor="w", padx=24)
        tk.Frame(left, bg=PAPER_LINE, height=2).pack(fill="x", padx=24, pady=(18, 12))
        meta = tk.Frame(left, bg=PAPER)
        meta.pack(fill="x", padx=24)
        for i, (k, v) in enumerate((("Language", "Python 3"),
                                    ("File", "solution.py"),
                                    ("Attempts", "1 submission"))):
            tk.Label(meta, text=k, bg=PAPER, fg=MUTED, font=self.f_meta).grid(
                row=i, column=0, sticky="w", pady=3)
            tk.Label(meta, text=v, bg=PAPER, fg=INK, font=self.f_meta).grid(
                row=i, column=1, sticky="w", padx=(18, 0), pady=3)
        how = tk.Frame(left, bg="#ebe3d1")
        how.pack(side="bottom", fill="x", padx=24, pady=24)
        tk.Label(how, text="How it works", bg="#ebe3d1", fg=INK,
                 font=self.f_cap).pack(anchor="w", padx=14, pady=(12, 4))
        tk.Label(how, text="Click into the editor on the right, write your code, "
                           "then press Submit. Submitting sends solution.py as it is.",
                 bg="#ebe3d1", fg=INK, font=self.f_meta, wraplength=280,
                 justify="left").pack(anchor="w", padx=14, pady=(0, 12))
        tk.Frame(body, bg="#0e1a16", width=2).pack(side="left", fill="y")

    def _editor(self, body):
        right = tk.Frame(body, bg=ED_BG)
        right.pack(side="left", fill="both", expand=True)
        tabs = tk.Frame(right, bg=GUTTER, height=38)
        tabs.pack(fill="x")
        tabs.pack_propagate(False)
        tk.Label(tabs, text="  solution.py  ", bg=ED_BG, fg=CREAM,
                 font=self.f_tab).pack(side="left", fill="y")
        tk.Frame(tabs, bg=AMBER, width=3).place(x=0, y=0, relheight=1)

        # bottom: action row + status bar (packed first so the editor fills the rest)
        status = tk.Frame(right, bg=AMBER_D, height=26)
        status.pack(side="bottom", fill="x")
        status.pack_propagate(False)
        self.pos = tk.Label(status, text="Ln 1, Col 1", bg=AMBER_D, fg=BAR, font=self.f_meta)
        self.pos.pack(side="left", padx=12)
        tk.Label(status, text="Python   UTF-8   LF   Spaces: 4", bg=AMBER_D, fg=BAR,
                 font=self.f_meta).pack(side="right", padx=12)

        act = tk.Frame(right, bg=GUTTER, height=68)
        act.pack(side="bottom", fill="x")
        act.pack_propagate(False)
        self.status = tk.Label(act, text="Not submitted yet", bg=GUTTER, fg="#9fb8ae",
                               font=self.f_tab)
        self.status.pack(side="left", padx=18)
        self.btn = tk.Button(act, text="Submit", bg=AMBER, fg=BAR, activebackground=AMBER_D,
                             activeforeground=BAR, font=self.f_btn, relief="flat", bd=0,
                             padx=30, pady=8, cursor="hand2", command=self.submit)
        self.btn.pack(side="right", padx=16, pady=12)

        area = tk.Frame(right, bg=ED_BG)
        area.pack(fill="both", expand=True)
        self.gutter = tk.Text(area, width=4, bg=GUTTER, fg=GUT_FG, font=self.f_mono, bd=0,
                              highlightthickness=0, padx=8, pady=14, takefocus=0,
                              cursor="arrow", state="disabled")
        self.gutter.pack(side="left", fill="y")
        self.editor = tk.Text(area, bg=ED_BG, fg=ED_FG, insertbackground=AMBER,
                              insertwidth=2, selectbackground=SEL, font=self.f_mono,
                              wrap="char", undo=True, bd=0, highlightthickness=0,
                              padx=14, pady=14, tabs=(self.f_mono.measure("    "),))
        self.editor.pack(side="left", fill="both", expand=True)
        for tag, col in SYN.items():
            self.editor.tag_configure(tag, foreground=col)
        self.editor.tag_configure("ph", foreground="#5c7068")
        self.editor.insert("1.0", PLACEHOLDER, ("ph",))
        self.editor.bind("<FocusIn>", self._clear_placeholder)
        self.editor.bind("<Button-1>", self._clear_placeholder, add="+")
        self.editor.bind("<Tab>", self._tab)
        self.editor.bind("<KeyRelease>", self._refresh)
        self.editor.bind("<ButtonRelease-1>", self._refresh)
        self._refresh()

    # ---------------------------------------------------------------- editor
    def _clear_placeholder(self, _e=None):
        if self.editor.get("1.0", "end").strip() == PLACEHOLDER and not self.submitted:
            self.editor.delete("1.0", "end")

    def _tab(self, _e):
        self.editor.insert("insert", "    ")
        return "break"

    def _refresh(self, _e=None):
        text = self.editor.get("1.0", "end-1c")
        lines = text.count("\n") + 1
        self.gutter.configure(state="normal")
        self.gutter.delete("1.0", "end")
        rows = []
        for i in range(1, lines + 1):
            rows.append(f"{i:>3}")
            try:
                extra = self.editor.count(f"{i}.0", f"{i}.0 lineend", "displaylines")
                extra = extra[0] if isinstance(extra, tuple) else (extra or 0)
            except tk.TclError:
                extra = 0
            rows.extend([""] * int(extra))
        self.gutter.insert("1.0", "\n".join(rows))
        self.gutter.configure(state="disabled")
        self.gutter.yview_moveto(self.editor.yview()[0])
        ln, col = self.editor.index("insert").split(".")
        self.pos.configure(text=f"Ln {ln}, Col {int(col) + 1}")
        if text.strip() == PLACEHOLDER:
            return
        for tag in SYN:
            self.editor.tag_remove(tag, "1.0", "end")
        for rx, tag, grp in ((KW_RE, "kw", 0), (NUM_RE, "num", 0), (DEF_RE, "defn", 1),
                             (STR_RE, "str", 0), (COM_RE, "com", 0)):
            for m in rx.finditer(text):
                s, e = m.span(grp)
                if tag in ("str", "com"):
                    for t in SYN:
                        self.editor.tag_remove(t, f"1.0+{s}c", f"1.0+{e}c")
                self.editor.tag_add(tag, f"1.0+{s}c", f"1.0+{e}c")

    def submit(self):
        code = self.editor.get("1.0", "end").strip()
        if not code or code == PLACEHOLDER:
            self.status.configure(text="Editor is empty — type a solution first.", fg=AMBER)
            return
        d = os.path.join(OUTPUT_DIR, "solution")
        os.makedirs(d, exist_ok=True)
        with open(os.path.join(d, "solution.py"), "w", encoding="utf-8") as f:
            f.write(code + "\n")
        self.submitted = True
        self.status.configure(text="✓  Submitted — solution.py received", fg="#9fd39a")
        self.btn.configure(state="disabled", text="Submitted", disabledforeground=BAR,
                           bg="#8fb39f")
        self.editor.configure(state="disabled")


if __name__ == "__main__":
    root = tk.Tk()
    TypeDesk(root)
    root.mainloop()
