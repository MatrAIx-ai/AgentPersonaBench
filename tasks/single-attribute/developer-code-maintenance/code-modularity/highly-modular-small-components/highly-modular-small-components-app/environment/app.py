#!/usr/bin/env python3
"""LedgerDesk — a REAL native desktop coding app for the OS-APP (computer-use) env.

A genuine Tkinter app (native window + code editor + Submit button), NOT a web
page. The persona-computer-1 agent reads the exercise on screen, clicks into the
editor, types a Python solution, and clicks Submit. On submit the APP writes
<output>/solution/solution.py itself from the editor text. No DOM/JS shortcut.

Layout: bottle-green masthead with a gold rule, the brief on a ruled ledger
card across the top, a deep-green code editor with a gold line gutter below,
and a submit bar along the bottom.
"""
from __future__ import annotations

import os
import tkinter as tk
from tkinter import font as tkfont

OUTPUT_DIR = (os.environ.get("PLAYGROUND_OUTPUT_DIR")
              or os.environ.get("ADHERENCE_OUTPUT_DIR")
              or os.environ.get("MATRIX_OUTPUT_DIR") or "/app/output")

TASK = (
    "Write a batch transaction processor: take a list of raw transaction dicts "
    "(keys: tx_id, amount, timestamp, currency) and produce a summarized audit "
    "ledger — validate each record, compute fees, flag anomalies, format "
    "entries. One straightforward pass is probably fine. Treat it as production "
    "code going into a team repo. Keep it quick and lightweight."
)
PLACEHOLDER = "# type your solution here"

# palette — bottle green, ledger paper, brass gold, oxblood margin
GREEN = "#173d2f"
GREEN2 = "#0f2a20"
CODE_BG = "#10241c"
CODE_FG = "#e8efe6"
GOLD = "#d4a93f"
GOLD_DIM = "#8f7a45"
PAPER = "#f7f3e3"
RULE = "#c9dccf"
MARGIN = "#a3373a"
INK = "#1f2a24"
MUT = "#66756c"
BG = "#e9e4d0"


class LedgerDesk:
    def __init__(self, root: tk.Tk):
        self.root = root
        self.submitted = False
        root.title("LedgerDesk")
        root.geometry("1024x866+0+0")
        root.configure(bg=BG)
        try:
            root.attributes("-zoomed", True)
        except tk.TclError:
            pass
        root.lift()
        root.attributes("-topmost", True)
        root.after(8000, lambda: root.attributes("-topmost", False))

        self.f_word = tkfont.Font(family="P052", size=21, weight="bold")
        self.f_word2 = tkfont.Font(family="P052", size=21, slant="italic")
        self.f_caps = tkfont.Font(family="Nimbus Sans", size=10, weight="bold")
        self.f_h = tkfont.Font(family="P052", size=15, weight="bold")
        self.f_body = tkfont.Font(family="DejaVu Serif", size=12)
        self.f_small = tkfont.Font(family="DejaVu Sans", size=10)
        self.f_mono = tkfont.Font(family="Liberation Mono", size=12)
        self.f_btn = tkfont.Font(family="DejaVu Sans", size=12, weight="bold")

        self._masthead()
        self._footer()
        self._brief()
        self._editor()
        root.after(200, self._update_lines)

    # ------------------------------------------------------------------ chrome
    def _masthead(self):
        bar = tk.Frame(self.root, bg=GREEN, height=66)
        bar.pack(fill="x")
        bar.pack_propagate(False)
        mark = tk.Canvas(bar, width=44, height=44, bg=GREEN, highlightthickness=0)
        mark.pack(side="left", padx=(20, 10), pady=11)
        # an open ledger book: two ruled pages, oxblood spine ribbon, gold edge
        mark.create_polygon(2, 10, 21, 6, 21, 38, 2, 40, fill=PAPER, outline=GOLD)
        mark.create_polygon(23, 6, 42, 10, 42, 40, 23, 38, fill=PAPER, outline=GOLD)
        for y in (15, 21, 27, 33):
            mark.create_line(5, y + 1, 18, y - 1, fill=RULE, width=1)
            mark.create_line(26, y - 1, 39, y + 1, fill=RULE, width=1)
        mark.create_line(8, 12, 8, 37, fill=MARGIN)
        mark.create_polygon(20, 30, 24, 30, 24, 44, 22, 41, 20, 44, fill=MARGIN, outline="")
        tk.Label(bar, text="Ledger", bg=GREEN, fg=PAPER, font=self.f_word).pack(side="left")
        tk.Label(bar, text="Desk", bg=GREEN, fg=GOLD, font=self.f_word2).pack(side="left", padx=(2, 0))
        tk.Label(bar, text="CODE  WORKBOOK", bg=GREEN, fg=GOLD_DIM, font=self.f_caps).pack(side="left", padx=(16, 0), pady=(6, 0))
        for t in ("Help", "History", "Exercise"):
            tk.Label(bar, text=t, bg=GREEN, fg=PAPER if t == "Exercise" else "#a9c2b5",
                     font=self.f_small, padx=12).pack(side="right", padx=(0, 10) if t == "Help" else 0)
        tk.Frame(self.root, bg=GOLD, height=3).pack(fill="x")

    def _brief(self):
        outer = tk.Frame(self.root, bg=BG)
        outer.pack(fill="x", padx=22, pady=(16, 10))
        card = tk.Canvas(outer, height=150, bg=PAPER, highlightthickness=1, highlightbackground="#d3cbb0")
        card.pack(fill="x")
        self._card = card
        card.bind("<Configure>", lambda e: self._draw_card())

    def _draw_card(self):
        c = self._card
        c.delete("all")
        w, h = c.winfo_width(), c.winfo_height()
        ls = self.f_body.metrics("linespace")
        c.create_line(0, 34, w, 34, fill=RULE)
        for y in range(44 + ls, h, ls):
            c.create_line(0, y + 1, w, y + 1, fill=RULE)
        c.create_line(64, 0, 64, h, fill=MARGIN)
        c.create_line(68, 0, 68, h, fill=MARGIN)
        c.create_text(32, 20, text="No. 1", fill=MARGIN, font=self.f_small)
        c.create_text(84, 18, text="Exercise — batch ledger", anchor="w", fill=GREEN, font=self.f_h)
        c.create_text(84, 44, text=TASK, anchor="nw", fill=INK, font=self.f_body, width=w - 110)

    def _footer(self):
        bar = tk.Frame(self.root, bg=GREEN2, height=62)
        bar.pack(fill="x", side="bottom")
        bar.pack_propagate(False)
        self.status = tk.Label(bar, text="", bg=GREEN2, fg=PAPER, font=self.f_btn)
        self.status.pack(side="left", padx=22)
        self.submit_btn = tk.Label(bar, text="Submit", bg=GOLD, fg=GREEN2, font=self.f_btn,
                                   padx=30, pady=9, cursor="hand2")
        self.submit_btn.pack(side="right", padx=20)
        self.submit_btn.bind("<Button-1>", lambda e: self.submit())
        self.pos_lbl = tk.Label(bar, text="Ln 1, Col 1", bg=GREEN2, fg="#a9c2b5", font=self.f_small)
        self.pos_lbl.pack(side="right", padx=14)

    def _editor(self):
        frame = tk.Frame(self.root, bg=BG)
        frame.pack(fill="both", expand=True, padx=22, pady=(0, 16))
        tabs = tk.Frame(frame, bg=BG)
        tabs.pack(fill="x")
        tk.Label(tabs, text="  solution.py  ", bg=CODE_BG, fg=GOLD, font=self.f_mono, pady=6).pack(side="left")
        tk.Label(tabs, text="Your solution", bg=BG, fg=MUT, font=self.f_small).pack(side="left", padx=12)
        body = tk.Frame(frame, bg=CODE_BG)
        body.pack(fill="both", expand=True)
        self.gutter = tk.Canvas(body, width=54, bg=GREEN2, highlightthickness=0, takefocus=0)
        self.gutter.pack(side="left", fill="y")
        self.editor = tk.Text(body, bg=CODE_BG, fg=CODE_FG, insertbackground=GOLD, insertwidth=2,
                              font=self.f_mono, wrap="word", padx=14, pady=12, relief="flat",
                              highlightthickness=2, highlightbackground=CODE_BG, highlightcolor=GOLD_DIM,
                              selectbackground="#2e5a47", undo=True, tabs=(self.f_mono.measure("    "),))
        self.editor.pack(side="left", fill="both", expand=True)
        self.editor.insert("1.0", PLACEHOLDER + "\n")
        for ev in ("<KeyRelease>", "<ButtonRelease-1>", "<<Modified>>", "<Configure>", "<MouseWheel>",
                   "<Button-4>", "<Button-5>"):
            self.editor.bind(ev, lambda e: self.root.after_idle(self._update_lines), add="+")

    def _update_lines(self):
        self.editor.edit_modified(False)
        self.gutter.delete("all")
        n = int(self.editor.index("end-1c").split(".")[0])
        for i in range(1, n + 1):
            info = self.editor.dlineinfo(f"{i}.0")
            if info is None:
                continue
            self.gutter.create_text(42, info[1] + info[3] // 2, text=str(i), anchor="e",
                                    fill=GOLD_DIM, font=self.f_mono)
        line, col = self.editor.index("insert").split(".")
        self.pos_lbl.configure(text=f"Ln {line}, Col {int(col) + 1}   ·   Python 3")

    def submit(self):
        if self.submitted:
            return
        code = self.editor.get("1.0", "end").strip()
        if not code or code == PLACEHOLDER:
            self.status.configure(text="Editor is empty — type a solution first.", fg=GOLD)
            return
        d = os.path.join(OUTPUT_DIR, "solution")
        os.makedirs(d, exist_ok=True)
        with open(os.path.join(d, "solution.py"), "w", encoding="utf-8") as f:
            f.write(code + "\n")
        self.submitted = True
        self.status.configure(text="✓  Submitted", fg=GOLD)
        self.submit_btn.configure(text="✓ Submitted", bg=GOLD_DIM, fg=PAPER)
        self.editor.configure(state="disabled", fg="#b9c7be")


if __name__ == "__main__":
    root = tk.Tk()
    LedgerDesk(root)
    root.mainloop()
