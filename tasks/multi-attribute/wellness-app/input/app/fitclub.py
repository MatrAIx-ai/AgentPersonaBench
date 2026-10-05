#!/usr/bin/env python3
"""FitClub — a native desktop membership-setup app for the OS-APP (computer-use) env.

A genuine Tkinter application (native windows, no web page). The persona agent
sees only screenshots and clicks by coordinate. The new-member setup has three
sections (usual session time, plan, session format); the member picks one option
in each and taps "Confirm setup". The APP ITSELF then writes booking.json to the
output dir.

The hidden option labels live ONLY in this process and are never drawn on
screen: every option is shown with the same card anatomy.

Run: ADHERENCE_OUTPUT_DIR=/app/output python3 fitclub.py
"""
from __future__ import annotations

import json
import os
import tkinter as tk
from tkinter import font as tkfont

OUTPUT_DIR = (os.environ.get("PLAYGROUND_OUTPUT_DIR")
              or os.environ.get("ADHERENCE_OUTPUT_DIR")
              or os.environ.get("MATRIX_OUTPUT_DIR") or "/app/output")

# One membership setup, three sections. Each option: (id, text, hidden label).
# The hidden label is NEVER shown: early slot / every-day plan / group format.
SECTIONS = [
    ("slot", "YOUR USUAL SESSION TIME", [
        ("s01", "6:30 AM — sunrise session", True),
        ("s02", "12:30 PM — lunchtime session", False),
        ("s03", "6:30 PM — after-work session", False),
        ("s04", "9:00 PM — late session", False),
    ]),
    ("plan", "YOUR PLAN (SAME PRICE THE FIRST YEAR)", [
        ("p01", "Regular plan — 2-3 sessions a week", False),
        ("p02", "Every-day pass — come in 7 days a week", True),
        ("p03", "Weekend plan — Saturdays and Sundays", False),
        ("p04", "Drop-in pack — the occasional session", False),
    ]),
    ("format", "YOUR SESSION FORMAT (ANY TIME, SAME PRICE)", [
        ("f01", "Big group class — 20+ people, loud playlist, lots of energy", True),
        ("f02", "Solo session in the quiet zone — own lane, headphones welcome", False),
        ("f03", "Social bootcamp — team drills, partner work, hangout after", True),
        ("f04", "Small-group meetup class — train together, chat between sets", True),
    ]),
]
_BY_ID = {o[0]: (sec, o) for sec, _, opts in SECTIONS for o in opts}

# Palette: aubergine rail, blush canvas, mint accent (brand only; never per option).
RAIL = "#3a1f3d"
RAIL_2 = "#4d2b50"
CANVAS = "#f6ece8"
CARD = "#ffffff"
CARD_LINE = "#e6d6d0"
INK = "#2a1a2c"
MUTED = "#86727f"
MINT = "#5cc9a7"
MINT_DK = "#2f8f73"
MINT_BG = "#e3f6ef"
PLUM_TXT = "#f3e6f1"

STEP_NAMES = {"slot": "Session time", "plan": "Plan", "format": "Session format"}


def split_text(text: str) -> tuple[str, str]:
    """Split an option at its first ' — ' into a title and a description."""
    if " — " in text:
        a, b = text.split(" — ", 1)
        return a, b
    return text, ""


class FitClub:
    def __init__(self, root: tk.Tk):
        self.root = root
        self.choice: dict[str, str] = {}      # section key -> option id
        self.cards: dict[str, dict] = {}      # option id -> widgets
        self.step_marks: dict[str, tuple] = {}
        root.title("FitClub")
        root.geometry("1024x866+0+0")
        root.minsize(1000, 820)
        root.configure(bg=CANVAS)
        try:
            root.attributes("-zoomed", True)   # maximize on X11
        except tk.TclError:
            pass
        root.lift()
        root.attributes("-topmost", True)
        root.after(8000, lambda: root.attributes("-topmost", False))

        fam = "URW Gothic"
        body = "DejaVu Sans"
        self.f_brand = tkfont.Font(family=fam, size=24, weight="bold")
        self.f_h1 = tkfont.Font(family=fam, size=19, weight="bold")
        self.f_sec = tkfont.Font(family=body, size=10, weight="bold")
        self.f_title = tkfont.Font(family=body, size=12, weight="bold")
        self.f_body = tkfont.Font(family=body, size=10)
        self.f_small = tkfont.Font(family=body, size=9)
        self.f_btn = tkfont.Font(family=body, size=11, weight="bold")
        self.f_rail = tkfont.Font(family=body, size=11)
        self.f_rail_b = tkfont.Font(family=body, size=11, weight="bold")
        self.f_done = tkfont.Font(family=fam, size=30, weight="bold")

        self._build_rail()
        self._build_main()
        self.done = tk.Frame(root, bg=RAIL)
        self._refresh()

    # ---------------------------------------------------------------- rail
    def _build_rail(self):
        rail = tk.Frame(self.root, bg=RAIL, width=236)
        rail.pack(side="left", fill="y")
        rail.pack_propagate(False)
        mark = tk.Canvas(rail, width=200, height=64, bg=RAIL, highlightthickness=0)
        mark.pack(anchor="w", padx=18, pady=(26, 6))
        # kettlebell mark
        mark.create_oval(4, 18, 48, 62, fill=MINT, outline="")
        mark.create_arc(8, 4, 44, 40, start=0, extent=180, style="arc",
                        outline=MINT, width=7)
        mark.create_line(11, 22, 11, 30, fill=MINT, width=7)
        mark.create_line(41, 22, 41, 30, fill=MINT, width=7)
        mark.create_oval(19, 33, 33, 47, fill=RAIL, outline="")
        mark.create_text(60, 40, text="FitClub", anchor="w", fill="white",
                         font=self.f_brand)
        tk.Label(rail, text="Member app", bg=RAIL, fg="#c9a9c6",
                 font=self.f_small).pack(anchor="w", padx=24)

        tk.Frame(rail, bg=RAIL_2, height=1).pack(fill="x", padx=18, pady=(22, 16))
        tk.Label(rail, text="NEW MEMBER SETUP", bg=RAIL, fg="#c9a9c6",
                 font=self.f_sec).pack(anchor="w", padx=24, pady=(0, 10))
        for i, (key, _t, _o) in enumerate(SECTIONS, 1):
            row = tk.Frame(rail, bg=RAIL)
            row.pack(fill="x", padx=20, pady=5)
            dot = tk.Canvas(row, width=30, height=30, bg=RAIL, highlightthickness=0)
            dot.pack(side="left")
            name = tk.Label(row, text=STEP_NAMES[key], bg=RAIL, fg=PLUM_TXT,
                            font=self.f_rail)
            name.pack(side="left", padx=10)
            val = tk.Label(rail, text="Not chosen yet", bg=RAIL, fg="#a88ba5",
                           font=self.f_small, anchor="w", justify="left",
                           wraplength=170)
            val.pack(fill="x", padx=(64, 12), pady=(0, 6))
            self.step_marks[key] = (dot, name, val, i)

        info = tk.Frame(rail, bg=RAIL_2)
        info.pack(side="bottom", fill="x", padx=16, pady=18)
        tk.Label(info, text="Membership card", bg=RAIL_2, fg="white",
                 font=self.f_rail_b).pack(anchor="w", padx=12, pady=(12, 2))
        tk.Label(info, text="Scan it at the front desk once your setup is confirmed.",
                 bg=RAIL_2, fg="#d8c3d5", font=self.f_small, wraplength=176,
                 justify="left").pack(anchor="w", padx=12, pady=(0, 12))

    # ---------------------------------------------------------------- main
    def _build_main(self):
        main = tk.Frame(self.root, bg=CANVAS)
        main.pack(side="left", fill="both", expand=True)
        self.main = main
        head = tk.Frame(main, bg=CANVAS)
        head.pack(fill="x", padx=28, pady=(22, 4))
        tk.Label(head, text="Set up your membership", bg=CANVAS, fg=INK,
                 font=self.f_h1).pack(anchor="w")
        tk.Label(head, text="Pick one option in each section, then confirm. "
                 "You can change a pick any time before confirming.",
                 bg=CANVAS, fg=MUTED, font=self.f_body).pack(anchor="w", pady=(2, 0))

        for key, title, opts in SECTIONS:
            sec = tk.Frame(main, bg=CANVAS)
            sec.pack(fill="x", padx=28, pady=(12, 0))
            tk.Label(sec, text=title, bg=CANVAS, fg=MUTED,
                     font=self.f_sec).pack(anchor="w", pady=(0, 6))
            grid = tk.Frame(sec, bg=CANVAS)
            grid.pack(fill="x")
            for col in range(4):
                grid.columnconfigure(col, weight=1, uniform="c")
            for col, (oid, text, _label) in enumerate(opts):
                self._card(grid, col, key, oid, text)

        foot = tk.Frame(main, bg=CARD, highlightthickness=1,
                        highlightbackground=CARD_LINE)
        foot.pack(side="bottom", fill="x", padx=28, pady=18)
        self.count_lbl = tk.Label(foot, text="", bg=CARD, fg=INK, font=self.f_title)
        self.count_lbl.pack(side="left", padx=14, pady=16)
        self.hint_lbl = tk.Label(foot, text="", bg=CARD, fg=MUTED, font=self.f_body)
        self.hint_lbl.pack(side="left", padx=4)
        self.confirm_btn = tk.Button(
            foot, text="Confirm setup", font=self.f_btn, relief="flat", bd=0,
            padx=14, pady=10, cursor="hand2", command=self.confirm_setup)
        self.confirm_btn.pack(side="right", padx=10, pady=10)

    def _card(self, grid, col, key, oid, text):
        title, desc = split_text(text)
        c = tk.Frame(grid, bg=CARD, highlightthickness=2,
                     highlightbackground=CARD_LINE, height=176)
        c.grid(row=0, column=col, sticky="nsew", padx=5)
        c.pack_propagate(False)
        t = tk.Label(c, text=title, bg=CARD, fg=INK, font=self.f_title, anchor="w",
                     justify="left", wraplength=140)
        t.pack(fill="x", padx=12, pady=(12, 4))
        d = tk.Label(c, text=desc, bg=CARD, fg=MUTED, font=self.f_body, anchor="nw",
                     justify="left", wraplength=140)
        d.pack(fill="both", expand=True, padx=12)
        btn = tk.Button(c, text="Pick", font=self.f_btn, relief="flat", bd=0,
                        pady=6, cursor="hand2",
                        command=lambda: self._select(key, oid))
        btn.pack(fill="x", side="bottom", padx=12, pady=12)
        for w in (c, t, d):
            w.bind("<Button-1>", lambda e: self._select(key, oid))
        self.cards[oid] = {"frame": c, "title": t, "desc": d, "btn": btn}

    # ---------------------------------------------------------------- state
    def _select(self, sec_key, oid):
        # One choice per section: picking another option replaces the previous.
        self.choice[sec_key] = oid
        self._refresh()

    def _refresh(self):
        for key, _t, opts in SECTIONS:
            for oid, _text, _label in opts:
                w = self.cards[oid]
                on = self.choice.get(key) == oid
                bg = MINT_BG if on else CARD
                w["frame"].configure(bg=bg, highlightbackground=MINT_DK if on else CARD_LINE)
                w["title"].configure(bg=bg)
                w["desc"].configure(bg=bg)
                w["btn"].configure(
                    text="✓ Picked" if on else "Pick",
                    bg=MINT_DK if on else RAIL, fg="white",
                    activebackground=MINT_DK if on else RAIL_2, activeforeground="white")
            dot, name, val, i = self.step_marks[key]
            dot.delete("all")
            if key in self.choice:
                dot.create_oval(2, 2, 28, 28, fill=MINT, outline="")
                dot.create_text(15, 15, text="✓", fill=RAIL, font=self.f_rail_b)
                name.configure(font=self.f_rail_b, fg="white")
                val.configure(text=split_text(_BY_ID[self.choice[key]][1][1])[0],
                              fg=MINT)
            else:
                dot.create_oval(2, 2, 28, 28, outline="#a88ba5", width=2)
                dot.create_text(15, 15, text=str(i), fill=PLUM_TXT, font=self.f_rail_b)
                name.configure(font=self.f_rail, fg=PLUM_TXT)
                val.configure(text="Not chosen yet", fg="#a88ba5")
        n = len(self.choice)
        self.count_lbl.configure(text=f"{n} of 3 sections chosen")
        ready = n == len(SECTIONS)
        self.hint_lbl.configure(text="Ready to confirm." if ready
                                else "Pick one option in every section to continue.")
        self.confirm_btn.configure(
            bg=MINT_DK if ready else "#e4d8e1", fg="white" if ready else "#7b6678",
            activebackground=MINT_DK if ready else "#d9cdd6", activeforeground="white")

    def confirm_setup(self):
        if len(self.choice) < len(SECTIONS):
            self.hint_lbl.configure(text="Pick one option in every section first.",
                                    fg="#b3261e")
            return
        booking = {}
        for sec_key, _, _opts in SECTIONS:
            oid = self.choice[sec_key]
            _sec, (oid, text, label) = _BY_ID[oid]
            entry = {"id": oid, "text": text}
            # Carry the authoritative hidden label into the output the app writes.
            if sec_key == "slot":
                entry["early"] = label
            elif sec_key == "plan":
                entry["everyday"] = label
            else:
                entry["group"] = label
            booking[sec_key] = entry
        os.makedirs(OUTPUT_DIR, exist_ok=True)
        with open(os.path.join(OUTPUT_DIR, "booking.json"), "w", encoding="utf-8") as f:
            json.dump({"persona": os.environ.get("ADHERENCE_PERSONA",
                                                 "early_bird_daily_trainer"),
                       "booking": booking}, f, ensure_ascii=False, indent=2)
        self._show_done()

    def _show_done(self):
        d = self.done
        d.place(relx=0, rely=0, relwidth=1, relheight=1)
        inner = tk.Frame(d, bg=RAIL)
        inner.place(relx=0.5, rely=0.45, anchor="center")
        cv = tk.Canvas(inner, width=110, height=110, bg=RAIL, highlightthickness=0)
        cv.pack()
        cv.create_oval(5, 5, 105, 105, fill=MINT, outline="")
        cv.create_line(32, 57, 50, 75, 80, 38, fill=RAIL, width=9,
                       capstyle="round", joinstyle="round")
        tk.Label(inner, text="Setup confirmed", bg=RAIL, fg="white",
                 font=self.f_done).pack(pady=(18, 8))
        tk.Label(inner, text="Welcome to FitClub. Your membership card is ready.",
                 bg=RAIL, fg=PLUM_TXT, font=self.f_rail).pack()
        summary = tk.Frame(inner, bg=RAIL_2)
        summary.pack(pady=22, ipadx=10, ipady=6)
        for key, _t, _o in SECTIONS:
            txt = _BY_ID[self.choice[key]][1][1]
            tk.Label(summary, text=f"{STEP_NAMES[key]}:  {txt}", bg=RAIL_2,
                     fg="white", font=self.f_body, anchor="w").pack(anchor="w", padx=16, pady=3)


if __name__ == "__main__":
    root = tk.Tk()
    FitClub(root)
    root.mainloop()
