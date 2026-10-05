#!/usr/bin/env python3
"""ShoreDay — a native day-planner for one cruise-port stop.

Canvas-drawn Tkinter interface: three day-part columns, one choice in each,
then CONFIRM CHOICES. The app records selection.json itself.
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
        "Start of the day",
        (
            ("q1a", "Adventure package — use the included rail ticket for a coastal hike and festival"),
            ("q1b", "8:30 walking visit and 10:00 workshop"),
            ("q1c", "Three timed stops beginning at 8:00"),
            ("q1d", "Rest-focused — cancel a prepaid $10 rail ticket and spend the afternoon at the spa"),
        ),
    ),
    (
        "q2",
        "Middle of the day",
        (
            ("q2a", "Lunch followed by a museum reservation"),
            ("q2b", "Two guided visits around a timed lunch"),
            ("q2c", "Quick lunch between three scheduled activities"),
            ("q2d", "Long waterfront lunch with the afternoon left open"),
        ),
    ),
    (
        "q3",
        "Final hours ashore",
        (
            ("q3a", "Add a one-hour guided visit"),
            ("q3b", "Fit in a market tour and tasting"),
            ("q3c", "Return at your own pace with no final booking"),
            ("q3d", "Add two timed events before boarding"),
        ),
    ),
)

# Dusk palette: plum night header, dune-sand page, peach sun accent.
PLUM, PLUM_L = "#3d2c4e", "#5a4670"
SAND, CARD, INK, MUT = "#f7f1ea", "#fffdfb", "#2b2233", "#77707d"
PEACH, PEACH_D, LINE = "#f08a5d", "#d0663a", "#e6dccf"
SEL = "#fdebe1"


def rrect(cv, x1, y1, x2, y2, r, **kw):
    pts = [x1 + r, y1, x2 - r, y1, x2, y1, x2, y1 + r, x2, y2 - r, x2, y2,
           x2 - r, y2, x1 + r, y2, x1, y2, x1, y2 - r, x1, y1 + r, x1, y1]
    return cv.create_polygon(pts, smooth=True, **kw)


class ChoiceApp:
    def __init__(self, root: tk.Tk) -> None:
        self.root = root
        self.selected: dict[str, str] = {}
        self.events: list[dict[str, str]] = []
        self.tiles: dict[tuple[str, str], dict] = {}
        self.finished = False
        root.title("ShoreDay")
        root.geometry(f"{min(1024, root.winfo_screenwidth())}x{min(866, root.winfo_screenheight())}+0+0")
        root.configure(bg=SAND)
        try:
            root.attributes("-zoomed", True)
        except tk.TclError:
            pass
        root.lift()
        root.attributes("-topmost", True)
        root.after(8000, lambda: root.attributes("-topmost", False))

        F = tkfont.Font
        self.f_brand = F(family="URW Gothic", size=25, weight="bold")
        self.f_tag = F(family="URW Gothic", size=12)
        self.f_col = F(family="URW Gothic", size=16, weight="bold")
        self.f_h = F(family="URW Gothic", size=18, weight="bold")
        self.f_step = F(family="URW Gothic", size=12, weight="bold")
        self.f_opt = F(family="Liberation Sans", size=12)
        self.f_body = F(family="Liberation Sans", size=13)
        self.f_small = F(family="Liberation Sans", size=12)
        self.f_btn = F(family="URW Gothic", size=15, weight="bold")

        cv = tk.Canvas(root, bg=SAND, highlightthickness=0)
        cv.pack(fill="both", expand=True)
        self.cv = cv
        self._header()
        self._columns()
        self._footer()

    # -------------------------------------------------------------- header
    def _header(self) -> None:
        cv = self.cv
        cv.create_rectangle(0, 0, 3000, 84, fill=PLUM, outline="")
        # mark: setting sun over two dune/wave lines inside a rounded tile
        rrect(cv, 22, 16, 74, 68, 14, fill=PLUM_L, outline="")
        cv.create_arc(30, 26, 66, 62, start=0, extent=180, fill=PEACH, outline="")
        cv.create_line(28, 48, 40, 44, 52, 48, 64, 44, 70, 47, fill="#f7d9c4", width=3, smooth=True)
        cv.create_line(28, 57, 40, 53, 52, 57, 64, 53, 70, 56, fill="#c9b8da", width=3, smooth=True)
        cv.create_text(88, 34, text="ShoreDay", anchor="w", fill="white", font=self.f_brand)
        cv.create_text(90, 62, text="one port · one easy plan", anchor="w", fill="#d8cce4", font=self.f_tag)
        for i, (lbl, x) in enumerate((("Plan", 690), ("Port guide", 780), ("Help", 900))):
            cv.create_text(x, 42, text=lbl, anchor="w", fill="white" if i == 0 else "#bfb2cf",
                           font=self.f_step)
        cv.create_line(690, 58, 724, 58, fill=PEACH, width=3)
        cv.create_text(28, 114, anchor="w", fill=INK, font=self.f_h,
                       text="Build your day in port")
        cv.create_text(28, 142, anchor="w", fill=MUT, font=self.f_body,
                       text="All options are included and return to the ship on time. "
                            "Pick one in each part of the day.")

    # -------------------------------------------------------------- columns
    def _columns(self) -> None:
        cv = self.cv
        col_w, gap, x0, y0 = 316, 14, 24, 168
        for n, (qid, prompt, options) in enumerate(QUESTIONS):
            x = x0 + n * (col_w + gap)
            rrect(cv, x, y0, x + col_w, y0 + 580, 18, fill="#efe6da", outline="")
            # step badge + neutral sun-position arc (same shape each column)
            cv.create_oval(x + 16, y0 + 14, x + 48, y0 + 46, fill=PLUM, outline="")
            cv.create_text(x + 32, y0 + 30, text=str(n + 1), fill="white", font=self.f_step)
            cv.create_text(x + 60, y0 + 30, text=prompt, anchor="w", fill=INK, font=self.f_col)
            status = cv.create_text(x + 60, y0 + 54, text="Not chosen yet", anchor="w",
                                    fill=MUT, font=self.f_small)
            self.tiles[(qid, "_status")] = {"status": status}
            for k, (oid, label) in enumerate(options):
                ty = y0 + 76 + k * 124
                tag = f"t_{oid}"
                bg = rrect(cv, x + 12, ty, x + col_w - 12, ty + 118, 14, fill=CARD,
                           outline=LINE, width=2, tags=(tag,))
                ring = cv.create_oval(x + 24, ty + 14, x + 46, ty + 36, fill=CARD,
                                      outline="#b9adbf", width=2, tags=(tag,))
                dot = cv.create_oval(x + 30, ty + 20, x + 40, ty + 30, fill=CARD,
                                     outline="", tags=(tag,))
                txt = cv.create_text(x + 56, ty + 12, anchor="nw", fill=INK, font=self.f_opt,
                                     text=label, width=col_w - 80, tags=(tag,))
                cv.create_text(x + 56, ty + 105, anchor="w", fill=MUT, font=self.f_small,
                               text=f"Option {chr(65 + k)} · included", tags=(tag,))
                cv.tag_bind(tag, "<Button-1>", lambda e, q=qid, o=oid: self.choose(q, o))
                cv.tag_bind(tag, "<Enter>", lambda e: cv.configure(cursor="hand2"))
                cv.tag_bind(tag, "<Leave>", lambda e: cv.configure(cursor=""))
                self.tiles[(qid, oid)] = {"bg": bg, "ring": ring, "dot": dot, "txt": txt}

    # -------------------------------------------------------------- footer
    def _footer(self) -> None:
        cv = self.cv
        y = 764
        cv.create_line(24, y, 1000, y, fill=LINE, width=2)
        self.pips = []
        for n in range(len(QUESTIONS)):
            p = cv.create_oval(28 + n * 26, y + 34, 44 + n * 26, y + 50, fill=CARD, outline=PLUM, width=2)
            self.pips.append(p)
        self.status = cv.create_text(28 + len(QUESTIONS) * 26 + 10, y + 42, anchor="w",
                                     fill=MUT, font=self.f_body,
                                     text=f"Choose {len(QUESTIONS)} more")
        self.btn_bg = rrect(cv, 752, y + 16, 1000, y + 70, 27, fill="#d8cfd9", outline="",
                            tags=("submit",))
        self.btn_txt = cv.create_text(876, y + 43, text="CONFIRM CHOICES", fill="#9a90a0",
                                      font=self.f_btn, tags=("submit",))
        cv.tag_bind("submit", "<Button-1>", lambda e: self.finish())

    # -------------------------------------------------------------- logic
    def choose(self, qid: str, oid: str) -> None:
        if self.finished:
            return
        self.selected[qid] = oid
        self.events.append({"event": "select", "questionId": qid, "optionId": oid})
        cv = self.cv
        options = next(options for current, _, options in QUESTIONS if current == qid)
        for current, label in options:
            t = self.tiles[(qid, current)]
            on = current == oid
            cv.itemconfigure(t["bg"], fill=SEL if on else CARD, outline=PEACH if on else LINE)
            cv.itemconfigure(t["ring"], outline=PEACH_D if on else "#b9adbf")
            cv.itemconfigure(t["dot"], fill=PEACH_D if on else CARD)
            if on:
                cv.itemconfigure(self.tiles[(qid, "_status")]["status"], text="Chosen ✓", fill=PEACH_D)
        for n, (q, _, _) in enumerate(QUESTIONS):
            cv.itemconfigure(self.pips[n], fill=PEACH if q in self.selected else CARD)
        remaining = len(QUESTIONS) - len(self.selected)
        if remaining:
            cv.itemconfigure(self.status, text=f"Choose {remaining} more")
        else:
            cv.itemconfigure(self.status, text="Ready to confirm", fill=PLUM)
            cv.itemconfigure(self.btn_bg, fill=PLUM)
            cv.itemconfigure(self.btn_txt, fill="white")

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
        cv = self.cv
        cv.configure(cursor="")
        cv.itemconfigure(self.btn_bg, fill=PEACH_D)
        cv.itemconfigure(self.btn_txt, text="CHOICES CONFIRMED")
        cv.itemconfigure(self.status, text="Saved — enjoy your day ashore", fill=PEACH_D)


if __name__ == "__main__":
    window = tk.Tk()
    ChoiceApp(window)
    window.mainloop()
