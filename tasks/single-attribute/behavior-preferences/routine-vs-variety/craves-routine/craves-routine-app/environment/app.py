#!/usr/bin/env python3
"""Native choice application for WeekFit.

A class-booking desktop app laid out like a pool: each booking section is a
lane with its own start block, and every plan in a lane is a tile. Pick one
plan per lane, then CONFIRM CHOICES; the app writes selection.json itself.
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
        "Monday warm-up bookings",
        (
            ("q1a", "New time and exercises each Monday + recovery drink"),
            ("q1b", "Rotate times, instructors and exercises + guest demos"),
            ("q1c", "Surprise time and exercises each week + friend pass"),
            ("q1d", "Rebook last month's 6 PM class, instructor and exercise order"),
        ),
    ),
    (
        "q2",
        "Wednesday warm-up bookings",
        (
            ("q2a", "New time and exercises each Wednesday + towel service"),
            ("q2b", "Rebook last month's 6 PM class, instructor and exercise order"),
            ("q2c", "Rotate times, instructors and exercises + guest demos"),
            ("q2d", "Surprise time and exercises each week + coaching clinic"),
        ),
    ),
    (
        "q3",
        "Saturday warm-up bookings",
        (
            ("q3a", "Rebook last month's 10 AM class, instructor and exercise order"),
            ("q3b", "New time and exercises each Saturday + snack voucher"),
            ("q3c", "Rotate times, instructors and exercises + guest demos"),
            ("q3d", "Surprise time and exercises each week + equipment trial"),
        ),
    ),
)
INTRO = ("Book four weeks of 45-minute warm-up classes. Each plan covers all four dates; every listed "
         "time fits your calendar, ability level, and membership.")

# pool palette: deep-water header, pale tile deck, lane ropes, white plan tiles
DEEP, DEEP2, WATER = "#0d3b5c", "#15507a", "#e8f3f6"
DECK, GROUT = "#f5f8f9", "#dbe7eb"
INK, MUTED = "#10222f", "#5a6b77"
ROPE_A, ROPE_B = "#ffffff", "#e45a4a"
TILE, TILE_EDGE, SEL = "#ffffff", "#b9ccd4", "#0d3b5c"
SIGNAL = "#f2c230"
W, H = 1024, 866
LANE_X, LANE_Y, LANE_H = 24, 196, 172
TILE_X0, TILE_W, TILE_H, TILE_GAP = 152, 202, 118, 10


def rrect(cv, x1, y1, x2, y2, r, **kw):
    pts = [x1 + r, y1, x2 - r, y1, x2, y1, x2, y1 + r, x2, y2 - r, x2, y2,
           x2 - r, y2, x1 + r, y2, x1, y2, x1, y2 - r, x1, y1 + r, x1, y1]
    return cv.create_polygon(pts, smooth=True, **kw)


def rope(cv, x1, x2, y):
    cv.create_line(x1, y, x2, y, fill="#8aa7b4", width=2)
    for i, x in enumerate(range(int(x1), int(x2), 16)):
        cv.create_oval(x, y - 4, x + 12, y + 4, fill=ROPE_B if (i // 4) % 2 else ROPE_A,
                       outline="#8aa7b4")


class ChoiceApp:
    def __init__(self, root: tk.Tk) -> None:
        self.root = root
        self.selected: dict[str, str] = {}
        self.events: list[dict[str, str]] = []
        self.tiles: dict[tuple[str, str], dict] = {}
        self.finished = False
        root.title("WeekFit")
        root.geometry("1024x866+0+0")
        root.resizable(False, False)
        root.configure(bg=DECK)
        self.f_word = tkfont.Font(family="Liberation Sans Narrow", size=28, weight="bold", slant="italic")
        self.f_caps = tkfont.Font(family="Liberation Sans Narrow", size=13, weight="bold")
        self.f_lane = tkfont.Font(family="Liberation Sans Narrow", size=34, weight="bold")
        self.f_title = tkfont.Font(family="Nimbus Sans", size=15, weight="bold")
        self.f_body = tkfont.Font(family="Nimbus Sans", size=12)
        self.f_small = tkfont.Font(family="Nimbus Sans", size=11)
        self.f_btn = tkfont.Font(family="Liberation Sans Narrow", size=17, weight="bold")
        self.cv = tk.Canvas(root, width=W, height=H, bg=DECK, highlightthickness=0)
        self.cv.pack(fill="both", expand=True)
        self.draw()

    # ------------------------------------------------------------------ drawing
    def draw(self) -> None:
        cv = self.cv
        # deck tiles
        for x in range(0, W, 32):
            cv.create_line(x, 90, x, H, fill=GROUT)
        for y in range(90, H, 32):
            cv.create_line(0, y, W, y, fill=GROUT)
        # header: deep water with wave lines + a lane-rope edge
        cv.create_rectangle(0, 0, W, 90, fill=DEEP, outline="")
        for k in range(4):
            y = 18 + k * 18
            pts = []
            for x in range(0, W + 20, 20):
                pts += [x, y + (4 if (x // 20) % 2 else -4)]
            cv.create_line(pts, fill=DEEP2, smooth=True, width=2)
        rope(cv, 0, W, 90)
        # mark: stopwatch roundel
        cv.create_oval(24, 20, 72, 68, fill=SIGNAL, outline="")
        cv.create_oval(31, 27, 65, 61, fill=DEEP, outline="")
        cv.create_rectangle(44, 12, 52, 20, fill=SIGNAL, outline="")
        cv.create_line(48, 44, 48, 32, fill="#ffffff", width=3, capstyle="round")
        cv.create_line(48, 44, 57, 49, fill=SIGNAL, width=3, capstyle="round")
        cv.create_text(86, 44, text="WeekFit", anchor="w", fill="#ffffff", font=self.f_word)
        cv.create_text(236, 50, text="WARM-UP  CLASS  BOOKING", anchor="w", fill="#9cc3d6", font=self.f_caps)
        for i, label in enumerate(("Classes", "Bookings", "Account")):
            cv.create_text(W - 280 + i * 90, 44, text=label, anchor="w", fill="#cfe2ea", font=self.f_small)

        # intro strip
        rrect(cv, 24, 108, W - 24, 176, 12, fill=WATER, outline=TILE_EDGE)
        cv.create_text(44, 126, text="FOUR-WEEK PLAN", anchor="w", fill=DEEP2, font=self.f_caps)
        cv.create_text(44, 144, text=INTRO, anchor="nw", fill=INK, font=self.f_small, width=W - 100)

        for n, (qid, prompt, options) in enumerate(QUESTIONS):
            top = LANE_Y + n * LANE_H
            rrect(cv, LANE_X, top, W - LANE_X, top + LANE_H - 14, 14, fill=WATER, outline=TILE_EDGE)
            # start block with lane number
            rrect(cv, LANE_X + 10, top + 10, LANE_X + 114, top + LANE_H - 24, 10, fill=DEEP, outline="")
            cv.create_text(LANE_X + 62, top + 52, text=str(n + 1), fill="#ffffff", font=self.f_lane)
            cv.create_text(LANE_X + 62, top + 92, text="LANE", fill="#9cc3d6", font=self.f_caps)
            self.tiles[("_check", qid)] = {"dot": cv.create_oval(LANE_X + 54, top + 110, LANE_X + 70, top + 126,
                                                                 fill=DEEP2, outline="#9cc3d6", width=2)}
            cv.create_text(TILE_X0, top + 20, text=prompt, anchor="w", fill=INK, font=self.f_title)
            cv.create_text(W - 44, top + 20, text="choose one", anchor="e", fill=MUTED, font=self.f_small)
            for col, (oid, label) in enumerate(options):
                x = TILE_X0 + col * (TILE_W + TILE_GAP)
                y = top + 36
                tag = f"t_{oid}"
                box = rrect(cv, x, y, x + TILE_W, y + TILE_H, 10, fill=TILE, outline=TILE_EDGE, width=2, tags=(tag,))
                ring = cv.create_oval(x + 12, y + 12, x + 30, y + 30, outline=TILE_EDGE, width=2, fill=TILE, tags=(tag,))
                tick = cv.create_text(x + 21, y + 21, text="", fill=DEEP, font=self.f_small, tags=(tag,))
                head = cv.create_text(x + 40, y + 21, text=f"PLAN {'ABCD'[col]}", anchor="w", fill=MUTED,
                                      font=self.f_caps, tags=(tag,))
                txt = cv.create_text(x + 12, y + 40, text=label, anchor="nw", fill=INK, font=self.f_body,
                                     width=TILE_W - 22, tags=(tag,))
                self.tiles[(qid, oid)] = {"box": box, "ring": ring, "tick": tick, "head": head, "txt": txt}
                cv.tag_bind(tag, "<ButtonRelease-1>", lambda _e, q=qid, o=oid: self.choose(q, o))
                cv.tag_bind(tag, "<Enter>", lambda _e: self.cv.configure(cursor="hand2"))
                cv.tag_bind(tag, "<Leave>", lambda _e: self.cv.configure(cursor=""))
            if n < len(QUESTIONS) - 1:
                rope(cv, LANE_X + 20, W - LANE_X - 20, top + LANE_H - 7)

        # footer
        fy = LANE_Y + len(QUESTIONS) * LANE_H + 6
        cv.create_rectangle(0, fy, W, H, fill="#ffffff", outline="")
        cv.create_line(0, fy, W, fy, fill=TILE_EDGE, width=2)
        self.pips = [cv.create_oval(28 + i * 26, fy + 36, 44 + i * 26, fy + 52, fill=GROUT, outline="")
                     for i in range(len(QUESTIONS))]
        self.status = cv.create_text(28 + len(QUESTIONS) * 26 + 10, fy + 44, anchor="w",
                                     text=f"Choose {len(QUESTIONS)} more", fill=MUTED, font=self.f_body)
        bx1, by1, bx2, by2 = W - 300, fy + 16, W - 28, fy + 72
        self.sub_box = rrect(cv, bx1, by1, bx2, by2, 14, fill="#c9d3d8", outline="", tags=("submit",))
        self.sub_txt = cv.create_text((bx1 + bx2) / 2, (by1 + by2) / 2, text="CONFIRM CHOICES",
                                      fill="#f4f7f8", font=self.f_btn, tags=("submit",))
        cv.tag_bind("submit", "<ButtonRelease-1>", lambda _e: self.finish())

    # ------------------------------------------------------------------ state
    def choose(self, qid: str, oid: str) -> None:
        if self.finished:
            return
        self.selected[qid] = oid
        self.events.append({"event": "select", "questionId": qid, "optionId": oid})
        options = next(options for current, _, options in QUESTIONS if current == qid)
        for current, _ in options:
            chosen = current == oid
            t = self.tiles[(qid, current)]
            self.cv.itemconfigure(t["box"], fill=SEL if chosen else TILE, outline=SEL if chosen else TILE_EDGE)
            self.cv.itemconfigure(t["ring"], fill=SIGNAL if chosen else TILE, outline=SIGNAL if chosen else TILE_EDGE)
            self.cv.itemconfigure(t["tick"], text="✓" if chosen else "")
            self.cv.itemconfigure(t["head"], fill="#9cc3d6" if chosen else MUTED)
            self.cv.itemconfigure(t["txt"], fill="#ffffff" if chosen else INK)
        self.cv.itemconfigure(self.tiles[("_check", qid)]["dot"], fill=SIGNAL, outline=SIGNAL)
        for i, pip in enumerate(self.pips):
            self.cv.itemconfigure(pip, fill=DEEP if i < len(self.selected) else GROUT)
        remaining = len(QUESTIONS) - len(self.selected)
        if remaining:
            self.cv.itemconfigure(self.status, text=f"Choose {remaining} more")
        else:
            self.cv.itemconfigure(self.status, text="Ready to confirm", fill=DEEP)
            self.cv.itemconfigure(self.sub_box, fill=DEEP)
            self.cv.itemconfigure(self.sub_txt, fill="#ffffff")

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
        self.cv.configure(cursor="")
        self.cv.itemconfigure(self.sub_box, fill=SIGNAL)
        self.cv.itemconfigure(self.sub_txt, text="CHOICES CONFIRMED", fill=DEEP)
        self.cv.itemconfigure(self.status, text="Saved", fill=DEEP)


if __name__ == "__main__":
    window = tk.Tk()
    ChoiceApp(window)
    window.mainloop()
