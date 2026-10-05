#!/usr/bin/env python3
"""VetEntry — front-desk check-in app for a veterinary clinic (Tkinter).

The receptionist-style screen shows the three check-in sections on the right
as radio tiles (one choice per section) and a live visit slip on the left.
"CONFIRM CHOICES" becomes active once every section has a choice; the app
then records /app/output/selection.json itself.
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
        "Patient species",
        (
            ("q1a", "Dog"),
            ("q1b", "Small companion animal"),
            ("q1c", "No animal patient"),
            ("q1d", "Cat"),
        ),
    ),
    (
        "q2",
        "Waiting arrangement",
        (
            ("q2a", "Dog waiting bay with lead hook"),
            ("q2b", "Small-animal quiet habitat bay"),
            ("q2c", "Covered cat-carrier alcove"),
            ("q2d", "No pet waiting space"),
        ),
    ),
    (
        "q3",
        "Take-home care pack",
        (
            ("q3a", "Dog feeding and walking care pack"),
            ("q3b", "Cat feeding and litter care pack"),
            ("q3c", "Small-animal feeding and bedding pack"),
            ("q3d", "No animal care pack"),
        ),
    ),
)

# Palette: blueberry ink, peach accent, ice-blue page.
INK = "#2b3a8c"
INK2 = "#3c4da6"
PEACH = "#f6a57c"
PEACH_DK = "#e0875a"
ICE = "#eef1fb"
WHITE = "#ffffff"
TEXT = "#1f2437"
MUTED = "#687089"
EDGE = "#d5daee"
SLIP = "#fffdf8"
SEL_BG = "#e7ebff"


class ChoiceApp:
    def __init__(self, root: tk.Tk) -> None:
        self.root = root
        self.selected: dict[str, str] = {}
        self.events: list[dict[str, str]] = []
        self.buttons: dict[tuple[str, str], tk.Frame] = {}
        self.tile_parts: dict[tuple[str, str], list] = {}
        self.hooks: dict = {}
        self.finished = False
        root.title("VetEntry")
        w = min(1024, root.winfo_screenwidth())
        h = min(866, root.winfo_screenheight())
        root.geometry(f"{w}x{h}+0+0")
        root.configure(bg=ICE)
        root.lift()
        root.attributes("-topmost", True)
        root.after(8000, lambda: root.attributes("-topmost", False))

        self.f_word = tkfont.Font(family="C059", size=23, weight="bold")
        self.f_nav = tkfont.Font(family="DejaVu Sans", size=11)
        self.f_h2 = tkfont.Font(family="C059", size=17, weight="bold")
        self.f_h3 = tkfont.Font(family="C059", size=15, weight="bold")
        self.f_sec = tkfont.Font(family="DejaVu Sans", size=13, weight="bold")
        self.f_opt = tkfont.Font(family="DejaVu Sans", size=12)
        self.f_small = tkfont.Font(family="DejaVu Sans", size=10)
        self.f_mono = tkfont.Font(family="Liberation Mono", size=11)
        self.f_monob = tkfont.Font(family="Liberation Mono", size=12, weight="bold")
        self.f_big = tkfont.Font(family="Liberation Mono", size=30, weight="bold")
        self.f_btn = tkfont.Font(family="DejaVu Sans", size=12, weight="bold")
        self.f_badge = tkfont.Font(family="DejaVu Sans", size=11, weight="bold")

        self._header()
        body = tk.Frame(root, bg=ICE)
        body.pack(fill="both", expand=True, padx=18, pady=14)
        self._slip_panel(body)
        self._sections(body)
        self._redraw_slip()

    # --------------------------------------------------------------- header
    def _header(self) -> None:
        hd = tk.Canvas(self.root, height=70, bg=WHITE, highlightthickness=0)
        hd.pack(fill="x")
        # mark: blueberry rounded tile with a peach medical cross and a
        # check-in tick
        hd.create_oval(18, 13, 62, 57, fill=INK, outline="")
        hd.create_rectangle(35, 21, 45, 49, fill=PEACH, outline="")
        hd.create_rectangle(26, 30, 54, 40, fill=PEACH, outline="")
        hd.create_line(48, 50, 53, 55, 62, 44, fill=WHITE, width=3)
        hd.create_text(74, 35, text="VetEntry", fill=INK, font=self.f_word, anchor="w")
        hd.create_text(76 + self.f_word.measure("VetEntry") + 8, 37,
                       text="Front desk · Check-in", fill=MUTED, font=self.f_small, anchor="w")
        x = 640
        for label, active in (("Check-in", True), ("Appointments", False), ("Help", False)):
            hd.create_text(x, 35, text=label, fill=INK if active else MUTED,
                           font=self.f_nav, anchor="w")
            if active:
                hd.create_line(x, 52, x + self.f_nav.measure(label), 52, fill=PEACH, width=3)
            x += self.f_nav.measure(label) + 28
        hd.create_line(0, 69, 1100, 69, fill=EDGE)

    # ------------------------------------------------------------ left slip
    def _slip_panel(self, body: tk.Frame) -> None:
        left = tk.Frame(body, bg=ICE, width=300)
        left.pack(side="left", fill="y")
        left.pack_propagate(False)
        tk.Label(left, text="Visit slip", bg=ICE, fg=INK, font=self.f_h2,
                 anchor="w").pack(fill="x")
        tk.Label(left, text="Fills in as you choose", bg=ICE, fg=MUTED,
                 font=self.f_small, anchor="w").pack(fill="x", pady=(0, 8))
        self.slip = tk.Canvas(left, width=296, height=470, bg=ICE, highlightthickness=0)
        self.slip.pack()
        self.status = tk.Label(left, text="", bg=ICE, fg=MUTED, font=self.f_opt, anchor="w")
        self.status.pack(fill="x", side="bottom", pady=(0, 4))
        info = tk.Frame(left, bg=ICE)
        info.pack(fill="x", side="bottom", pady=(0, 10))
        tk.Label(info, text="Riverside Veterinary Clinic", bg=ICE, fg=TEXT,
                 font=self.f_badge, anchor="w").pack(fill="x")
        tk.Label(info, text="Open 8:00–19:00 · 01632 960 214", bg=ICE, fg=MUTED,
                 font=self.f_small, anchor="w").pack(fill="x")

    def _redraw_slip(self) -> None:
        c = self.slip
        c.delete("all")
        c.create_rectangle(5, 5, 291, 465, fill="#d9deef", outline="")
        c.create_rectangle(0, 0, 286, 460, fill=SLIP, outline=EDGE)
        # perforated top edge
        for x in range(8, 286, 16):
            c.create_oval(x - 3, -3, x + 3, 3, fill=ICE, outline="")
        c.create_text(143, 34, text="CHECK-IN", fill=MUTED, font=self.f_mono)
        c.create_text(143, 72, text="A-027", fill=INK, font=self.f_big)
        c.create_text(143, 106, text="queue ticket", fill=MUTED, font=self.f_small)
        c.create_line(18, 128, 268, 128, fill=EDGE, dash=(4, 3))
        y = 156
        for number, (qid, prompt, options) in enumerate(QUESTIONS, start=1):
            c.create_text(18, y, text=f"{number}. {prompt.upper()}", fill=MUTED,
                          font=self.f_small, anchor="w")
            oid = self.selected.get(qid)
            if oid:
                label = next(lbl for o, lbl in options if o == oid)
                c.create_text(18, y + 26, text=label, fill=TEXT, font=self.f_monob,
                              anchor="nw", width=250)
            else:
                c.create_text(18, y + 26, text="— not chosen yet", fill="#a6abbd",
                              font=self.f_mono, anchor="nw")
            y += 88
        c.create_line(18, 420, 268, 420, fill=EDGE, dash=(4, 3))
        done = len(self.selected)
        c.create_text(18, 440, text=f"{done} of {len(QUESTIONS)} sections", fill=MUTED,
                      font=self.f_small, anchor="w")
        if self.finished:
            c.create_rectangle(170, 428, 268, 452, fill=INK, outline="")
            c.create_text(219, 440, text="SAVED", fill=WHITE, font=self.f_badge)

    # ------------------------------------------------------------- sections
    def _sections(self, body: tk.Frame) -> None:
        right = tk.Frame(body, bg=ICE)
        right.pack(side="left", fill="both", expand=True, padx=(18, 0))
        tk.Label(right, text="Register today's patient and matching visit arrangements",
                 bg=ICE, fg=INK, font=self.f_h3, anchor="w").pack(fill="x")
        tk.Label(right, text="Choose one option in each section.", bg=ICE, fg=MUTED,
                 font=self.f_small, anchor="w").pack(fill="x", pady=(0, 6))
        for number, (qid, prompt, options) in enumerate(QUESTIONS, start=1):
            sec = tk.Frame(right, bg=WHITE, highlightthickness=1, highlightbackground=EDGE)
            sec.pack(fill="x", pady=5)
            top = tk.Frame(sec, bg=WHITE)
            top.pack(fill="x", padx=14, pady=(10, 6))
            num = tk.Canvas(top, width=28, height=28, bg=WHITE, highlightthickness=0)
            num.create_oval(1, 1, 27, 27, fill=INK, outline="")
            num.create_text(14, 14, text=str(number), fill=WHITE, font=self.f_badge)
            num.pack(side="left")
            tk.Label(top, text=prompt, bg=WHITE, fg=TEXT, font=self.f_sec).pack(
                side="left", padx=10)
            grid = tk.Frame(sec, bg=WHITE)
            grid.pack(fill="x", padx=12, pady=(0, 12))
            grid.columnconfigure(0, weight=1, uniform="o")
            grid.columnconfigure(1, weight=1, uniform="o")
            for i, (oid, label) in enumerate(options):
                r, col = divmod(i, 2)
                self._tile(grid, qid, oid, "ABCD"[i], label).grid(
                    row=r, column=col, sticky="nsew", padx=4, pady=4)
        foot = tk.Frame(right, bg=ICE)
        foot.pack(fill="x", side="bottom", pady=(6, 0))
        self.submit = tk.Button(
            foot, text="CONFIRM CHOICES", command=self.finish, state="disabled",
            bg="#c3c8da", fg=WHITE, disabledforeground="#eef0f7",
            activebackground=INK2, activeforeground=WHITE, relief="flat", bd=0,
            highlightthickness=0, padx=28, pady=13, font=self.f_btn, cursor="hand2")
        self.submit.pack(side="right")
        self.hooks["submit"] = self.submit
        self.hint = tk.Label(foot, text="All sections are required.", bg=ICE, fg=MUTED,
                             font=self.f_small)
        self.hint.pack(side="left")
        self._update_status()

    def _tile(self, parent, qid, oid, letter, label):
        t = tk.Frame(parent, bg=WHITE, highlightthickness=2, highlightbackground=EDGE,
                     cursor="hand2", height=52)
        t.pack_propagate(False)
        radio = tk.Canvas(t, width=26, height=26, bg=WHITE, highlightthickness=0)
        radio.pack(side="left", padx=(10, 6))
        badge = tk.Label(t, text=letter, bg=ICE, fg=INK, font=self.f_badge, width=2)
        badge.pack(side="left", padx=(0, 8))
        text = tk.Label(t, text=label, bg=WHITE, fg=TEXT, font=self.f_opt, anchor="w",
                        justify="left", wraplength=240)
        text.pack(side="left", fill="x", expand=True)
        for wdg in (t, radio, badge, text):
            wdg.bind("<Button-1>", lambda _e, q=qid, o=oid: self.choose(q, o))
        self.buttons[(qid, oid)] = t
        self.tile_parts[(qid, oid)] = [t, radio, text]
        self.hooks[oid] = t
        self._paint_tile(qid, oid, False)
        return t

    def _paint_tile(self, qid, oid, on) -> None:
        t, radio, text = self.tile_parts[(qid, oid)]
        bg = SEL_BG if on else WHITE
        t.configure(bg=bg, highlightbackground=INK if on else EDGE)
        text.configure(bg=bg)
        radio.configure(bg=bg)
        radio.delete("all")
        radio.create_oval(3, 3, 23, 23, outline=INK if on else "#9aa2bf", width=2, fill=WHITE)
        if on:
            radio.create_oval(8, 8, 18, 18, fill=INK, outline="")

    # ---------------------------------------------------------------- state
    def _update_status(self) -> None:
        remaining = len(QUESTIONS) - len(self.selected)
        if self.finished:
            self.status.configure(text="Saved", fg=INK)
        elif remaining:
            self.status.configure(text=f"Choose {remaining} more", fg=MUTED)
        else:
            self.status.configure(text="Ready to confirm", fg=INK)

    def choose(self, qid: str, oid: str) -> None:
        if self.finished:
            return
        self.selected[qid] = oid
        self.events.append({"event": "select", "questionId": qid, "optionId": oid})
        options = next(options for current, _, options in QUESTIONS if current == qid)
        for current, _ in options:
            self._paint_tile(qid, current, current == oid)
        if len(self.selected) == len(QUESTIONS):
            self.submit.configure(state="normal", bg=INK)
            self.hint.configure(text="Every section has a choice.")
        self._update_status()
        self._redraw_slip()

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
        for t, _radio, _text in self.tile_parts.values():
            t.configure(cursor="arrow")
        self.submit.configure(state="disabled", text="CHOICES CONFIRMED", bg=PEACH_DK,
                              disabledforeground=WHITE)
        self.hint.configure(text="Check-in recorded — please take a seat.")
        self._update_status()
        self._redraw_slip()


if __name__ == "__main__":
    window = tk.Tk()
    ChoiceApp(window)
    window.mainloop()
