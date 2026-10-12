#!/usr/bin/env python3
"""MealWeek — a native Tk weekly dinner-kit planner board.

Four night columns side by side; each column holds its dinner kits as
Canvas-drawn tiles. Pick one kit per night, then CONFIRM CHOICES. The app
itself writes selection.json to the output directory.
"""

from __future__ import annotations

import json
import os
import tkinter as tk
from tkinter import font as tkfont

OUTPUT_DIR = (
    os.environ.get("PLAYGROUND_OUTPUT_DIR")
    or os.environ.get("ADHERENCE_OUTPUT_DIR")
    or "/app/output"
)
QUESTIONS = (
    (
        "q1",
        "Monday dinner",
        (
            ("q1a", "Lemon cod and vegetables"),
            ("q1b", "Chicken and vegetables"),
            ("q1c", "Lamb tagine"),
            ("q1d", "Chickpea tagine"),
        ),
    ),
    (
        "q2",
        "Tuesday dinner",
        (
            ("q2a", "Pork noodles"),
            ("q2b", "Prawn noodles"),
            ("q2c", "Tofu noodles"),
            ("q2d", "Chicken noodles"),
        ),
    ),
    (
        "q3",
        "Thursday dinner",
        (
            ("q3a", "Salmon rice bowl"),
            ("q3b", "Beef rice bowl"),
            ("q3c", "Mushroom rice bowl"),
            ("q3d", "Turkey rice bowl"),
        ),
    ),
    (
        "q4",
        "Saturday dinner",
        (
            ("q4a", "Chicken tacos"),
            ("q4b", "Fish tacos"),
            ("q4c", "Pork tacos"),
            ("q4d", "Bean tacos"),
        ),
    ),
)

# Palette: paprika + oat paper + ink, with slate for plate art.
PAPER = "#f4ecdf"
OAT = "#e9dcc8"
INK = "#2b2522"
MUTE = "#7a6f66"
PAPRIKA = "#c4502f"
PAPRIKA_DK = "#9e3c20"
TILE = "#fffaf2"
LINE = "#dccbb3"
SLATE = ("#8d8a86", "#a7a39d", "#6f6c69", "#bdb8b0")

W, H = 1024, 866


def _seed(text: str) -> int:
    value = 7
    for ch in text:
        value = (value * 31 + ord(ch)) % 100003
    return value


def rounded(cv: tk.Canvas, x0, y0, x1, y1, r, **kw):
    pts = [
        x0 + r, y0, x1 - r, y0, x1, y0, x1, y0 + r, x1, y1 - r, x1, y1,
        x1 - r, y1, x0 + r, y1, x0, y1, x0, y1 - r, x0, y0 + r, x0, y0,
    ]
    return cv.create_polygon(pts, smooth=True, **kw)


class ChoiceApp:
    def __init__(self, root: tk.Tk) -> None:
        self.root = root
        self.selected: dict[str, str] = {}
        self.events: list[dict[str, str]] = []
        self.tiles: dict[tuple[str, str], tk.Canvas] = {}
        self.slots: dict[str, tk.Label] = {}
        self.finished = False
        root.title("MealWeek")
        root.geometry(f"{W}x{H}+0+0")
        root.resizable(False, False)
        root.configure(bg=PAPER)
        self.f_brand = tkfont.Font(family="URW Gothic", size=26, weight="bold")
        self.f_tag = tkfont.Font(family="Nimbus Sans", size=12)
        self.f_head = tkfont.Font(family="URW Gothic", size=17, weight="bold")
        self.f_sub = tkfont.Font(family="Nimbus Sans", size=12)
        self.f_title = tkfont.Font(family="Nimbus Sans", size=13, weight="bold")
        self.f_small = tkfont.Font(family="Nimbus Sans", size=12)
        self.f_btn = tkfont.Font(family="URW Gothic", size=14, weight="bold")
        self._header()
        self._board()
        self._footer()

    # ------------------------------------------------------------------ layout
    def _header(self) -> None:
        bar = tk.Canvas(self.root, width=W, height=86, bg=INK, highlightthickness=0)
        bar.pack(fill="x")
        # mark: a bowl with three steam curls on a paprika disc
        bar.create_oval(24, 15, 80, 71, fill=PAPRIKA, outline="")
        bar.create_arc(34, 22, 70, 60, start=180, extent=180, fill=PAPER, outline="")
        bar.create_line(34, 41, 70, 41, fill=PAPER, width=2)
        for dx in (-8, 0, 8):
            bar.create_line(52 + dx, 36, 49 + dx, 31, 53 + dx, 26, 50 + dx, 21,
                            smooth=True, fill=PAPER, width=2)
        bar.create_text(96, 34, text="Meal", anchor="w", font=self.f_brand, fill=PAPER)
        mw = self.f_brand.measure("Meal")
        bar.create_text(96 + mw, 34, text="Week", anchor="w", font=self.f_brand, fill="#e98a63")
        bar.create_text(97, 62, text="Your weekly dinner-kit board", anchor="w",
                        font=self.f_tag, fill="#cdbfae")
        # inert nav pills
        x = 640
        for label, active in (("Plan", True), ("Pantry", False), ("Deliveries", False)):
            wdt = self.f_sub.measure(label) + 28
            if active:
                rounded(bar, x, 29, x + wdt, 57, 13, fill="#4a403a", outline="")
            bar.create_text(x + wdt / 2, 43, text=label, font=self.f_sub,
                            fill=PAPER if active else "#a99c8e")
            x += wdt + 8
        bar.create_oval(W - 58, 26, W - 26, 58, fill="#4a403a", outline="")
        bar.create_text(W - 42, 42, text="MW", font=self.f_small, fill=PAPER)

        strip = tk.Frame(self.root, bg=OAT, height=44)
        strip.pack(fill="x")
        strip.pack_propagate(False)
        tk.Label(
            strip,
            text="Choose one dinner kit for each night. Kits are equal in price, nutrition, prep time, and rating.",
            bg=OAT, fg=INK, font=self.f_sub,
        ).pack(side="left", padx=24)

    def _board(self) -> None:
        board = tk.Frame(self.root, bg=PAPER)
        board.pack(fill="both", expand=True, padx=20, pady=(14, 0))
        col_w = (W - 40 - 3 * 12) // 4
        for number, (qid, prompt, options) in enumerate(QUESTIONS, start=1):
            col = tk.Frame(board, bg=PAPER, width=col_w)
            col.grid(row=0, column=number - 1, padx=(0 if number == 1 else 12, 0), sticky="n")
            head = tk.Canvas(col, width=col_w, height=58, bg=PAPER, highlightthickness=0)
            head.pack()
            head.create_oval(0, 8, 40, 48, fill=INK, outline="")
            head.create_text(20, 28, text=str(number), font=self.f_head, fill=PAPER)
            head.create_text(50, 20, text=prompt, anchor="w", font=self.f_head, fill=INK)
            head.create_text(50, 43, text=f"{len(options)} kits · pick one", anchor="w",
                             font=self.f_small, fill=MUTE)
            head.create_line(0, 56, col_w, 56, fill=LINE, width=2)
            for idx, (oid, label) in enumerate(options):
                cv = tk.Canvas(col, width=col_w, height=128, bg=PAPER,
                               highlightthickness=0, cursor="hand2")
                cv.pack(pady=(10, 0))
                cv.bind("<Button-1>", lambda _e, q=qid, o=oid: self.choose(q, o))
                self.tiles[(qid, oid)] = cv
                self._draw_tile(cv, col_w, oid, label, idx, False)

    def _footer(self) -> None:
        foot = tk.Frame(self.root, bg=INK, height=92)
        foot.pack(fill="x", side="bottom")
        foot.pack_propagate(False)
        left = tk.Frame(foot, bg=INK)
        left.pack(side="left", padx=22, pady=10)
        self.status = tk.Label(left, text=f"Choose {len(QUESTIONS)} more", bg=INK,
                               fg="#e98a63", font=self.f_title, anchor="w")
        self.status.pack(anchor="w")
        row = tk.Frame(left, bg=INK)
        row.pack(anchor="w", pady=(6, 0))
        for qid, prompt, _ in QUESTIONS:
            slot = tk.Label(row, text=f"{prompt.split()[0][:3]} · —", bg="#3d3531",
                            fg="#cdbfae", font=self.f_small, padx=10, pady=5,
                            width=17, anchor="w")
            slot.pack(side="left", padx=(0, 6))
            self.slots[qid] = slot
        self.submit = tk.Button(
            foot, text="CONFIRM CHOICES", command=self.finish, state="disabled",
            bg="#5a4f49", fg=PAPER, disabledforeground="#9b8f84",
            activebackground=PAPRIKA_DK, activeforeground=PAPER,
            relief="flat", bd=0, padx=22, pady=14, font=self.f_btn, cursor="hand2",
        )
        self.submit.pack(side="right", padx=22)

    # ------------------------------------------------------------------- tiles
    def _draw_tile(self, cv: tk.Canvas, w: int, oid: str, label: str, idx: int, chosen: bool) -> None:
        cv.delete("all")
        h = 128
        rounded(cv, 2, 2, w - 2, h - 2, 14, fill=TILE if not chosen else "#fbe3d6",
                outline=PAPRIKA if chosen else LINE, width=3 if chosen else 1)
        # plate art, seeded from the id only; one neutral slate palette for all
        s = _seed(oid)
        cx, cy, r = 50, 52, 34
        cv.create_oval(cx - r, cy - r, cx + r, cy + r, fill="#f7f3ec", outline="#cfc6ba", width=2)
        cv.create_oval(cx - r + 8, cy - r + 8, cx + r - 8, cy + r - 8, fill="#efe8dd", outline="")
        for k in range(3 + s % 3):
            a = (s * (k + 3)) % 360
            col = SLATE[(s + k) % len(SLATE)]
            rr = 8 + (s >> k) % 9
            ox = cx + ((s * (k + 1)) % 23) - 11
            oy = cy + ((s * (k + 5)) % 21) - 10
            if (s + k) % 2:
                cv.create_arc(ox - rr, oy - rr, ox + rr, oy + rr, start=a, extent=160,
                              fill=col, outline="")
            else:
                cv.create_oval(ox - rr / 2, oy - rr / 2, ox + rr / 2, oy + rr / 2,
                               fill=col, outline="")
        cv.create_text(cx, 104, text=f"Kit {oid[1:].upper()}", font=self.f_small, fill=MUTE)
        cv.create_text(98, 44, text=label, anchor="w", width=w - 110,
                       font=self.f_title, fill=INK)
        # pill
        px0, py0, px1, py1 = 98, 88, w - 12, 116
        if chosen:
            rounded(cv, px0, py0, px1, py1, 13, fill=PAPRIKA, outline="")
            cv.create_text((px0 + px1) / 2, (py0 + py1) / 2, text="✓ Planned",
                           font=self.f_title, fill="white")
        else:
            rounded(cv, px0, py0, px1, py1, 13, fill=TILE, outline=INK, width=1)
            cv.create_text((px0 + px1) / 2, (py0 + py1) / 2, text="Plan this kit",
                           font=self.f_small, fill=INK)

    def _label_of(self, qid: str, oid: str) -> str:
        options = next(opts for cur, _, opts in QUESTIONS if cur == qid)
        return next(label for cur, label in options if cur == oid)

    # ------------------------------------------------------------------ logic
    def choose(self, qid: str, oid: str) -> None:
        if self.finished:
            return
        self.selected[qid] = oid
        self.events.append({"event": "select", "questionId": qid, "optionId": oid})
        options = next(opts for cur, _, opts in QUESTIONS if cur == qid)
        for idx, (current, label) in enumerate(options):
            cv = self.tiles[(qid, current)]
            self._draw_tile(cv, int(cv.cget("width")), current, label, idx, current == oid)
        prompt = next(p for cur, p, _ in QUESTIONS if cur == qid)
        name = self._label_of(qid, oid)
        short = name if len(name) <= 13 else name[:12] + "…"
        self.slots[qid].configure(text=f"{prompt.split()[0][:3]} · {short}",
                                  bg="#5b3a2c", fg=PAPER)
        remaining = len(QUESTIONS) - len(self.selected)
        if remaining:
            self.status.configure(text=f"Choose {remaining} more")
        else:
            self.status.configure(text="Ready to confirm", fg="#9fd3b0")
            self.submit.configure(state="normal", bg=PAPRIKA)

    def finish(self) -> None:
        if self.finished or len(self.selected) != len(QUESTIONS):
            return
        self.finished = True
        self.events.append({"event": "submit"})
        answers = [
            {"questionId": qid, "optionId": self.selected[qid]}
            for qid, _, _ in QUESTIONS
        ]
        os.makedirs(OUTPUT_DIR, exist_ok=True)
        with open(
            os.path.join(OUTPUT_DIR, "selection.json"), "w", encoding="utf-8"
        ) as handle:
            json.dump(
                {"submitted": True, "answers": answers, "events": self.events},
                handle,
                ensure_ascii=False,
                indent=2,
            )
        for cv in self.tiles.values():
            cv.configure(cursor="arrow")
        self.submit.configure(state="disabled", text="CHOICES CONFIRMED",
                              bg="#2f6b4f", disabledforeground="white")
        self.status.configure(text="Saved — your week is planned", fg="#9fd3b0")


if __name__ == "__main__":
    window = tk.Tk()
    ChoiceApp(window)
    window.mainloop()
