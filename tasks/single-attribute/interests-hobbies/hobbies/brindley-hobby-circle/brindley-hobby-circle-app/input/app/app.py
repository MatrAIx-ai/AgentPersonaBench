#!/usr/bin/env python3
"""Brindley Hobby Circle: the members' season planner. Book one session for each of six months."""
from __future__ import annotations

import json
import math
import os
import tkinter as tk
from tkinter import font as tkfont

OUTPUT_DIR = (os.environ.get("PLAYGROUND_OUTPUT_DIR")
              or os.environ.get("ADHERENCE_OUTPUT_DIR")
              or os.environ.get("MATRIX_OUTPUT_DIR")
              or "/app/output")

TITLE = 'Brindley Hobby Circle'
UI = {
    'rail_heading': 'Your six months',
    'chosen': 'Chosen',
    'is_chosen': 'Chosen',
    'not_chosen': 'Not chosen yet',
    'save': 'Save',
    'saved': 'Your six bookings are saved.',
    'save_failed': 'Could not save the bookings:',
    'subtitle': 'Book one option for each of your six months',
    'note_plain': 'Choose one booking for this month.',
    'note_preset': 'Your membership already holds the booking marked Booked for you. Keep it or change it: click Choose on one card.',
    'choose': 'Choose',
    'keep': 'Choose',
}
OCCASIONS = (
    ('m1', 'Month 1'),
    ('m2', 'Month 2'),
    ('m3', 'Month 3'),
    ('m4', 'Month 4'),
    ('m5', 'Month 5'),
    ('m6', 'Month 6'),
)
# occasion id -> four options in display order: (option id, text, session lines, badges)
OPTIONS = {
    'm1': [
        ('m1-a', "Stamp collecting members' workshop: two hours, materials provided", (), ('Featured', 'Staff pick')),
        ('m1-b', "Pottery members' workshop: two hours, materials provided", (), ('Most booked',)),
        ('m1-c', "Bread baking members' workshop: two hours, materials provided", (), ()),
        ('m1-d', "Woodworking members' workshop: two hours, materials provided", (), ()),
    ],
    'm2': [
        ('m2-a', 'Stamp collecting club evening: a talk and a hands-on half hour', (), ('Featured', 'Most booked')),
        ('m2-b', 'Bread baking club evening: a talk and a hands-on half hour', (), ()),
        ('m2-c', 'Woodworking club evening: a talk and a hands-on half hour', (), ()),
        ('m2-d', 'Pottery club evening: a talk and a hands-on half hour', (), ('Staff pick',)),
    ],
    'm3': [
        ('m3-a', 'Woodworking guided session: two hours, small group', (), ('Featured', 'Most booked')),
        ('m3-b', 'Stamp collecting guided session: two hours, small group', (), ()),
        ('m3-c', 'Pottery guided session: two hours, small group', (), ('Booked for you',)),
        ('m3-d', 'Bread baking guided session: two hours, small group', (), ('Staff pick',)),
    ],
    'm4': [
        ('m4-a', 'Woodworking open table morning: three hours', (), ('Featured', 'Staff pick')),
        ('m4-b', 'Bread baking open table morning: three hours', (), ()),
        ('m4-c', 'Pottery open table morning: three hours', (), ()),
        ('m4-d', 'Stamp collecting open table morning: three hours', (), ('Most booked',)),
    ],
    'm5': [
        ('m5-a', 'Pottery Saturday session: two hours', (), ('Featured',)),
        ('m5-b', 'Stamp collecting Saturday session: two hours', (), ()),
        ('m5-c', 'Woodworking Saturday session: two hours', (), ('Staff pick',)),
        ('m5-d', 'Bread baking Saturday session: two hours', (), ('Most booked',)),
    ],
    'm6': [
        ('m6-a', 'Bread baking show and tell evening: bring one piece', (), ('Featured', 'Most booked', 'Booked for you')),
        ('m6-b', 'Woodworking show and tell evening: bring one piece', (), ()),
        ('m6-c', 'Stamp collecting show and tell evening: bring one piece', (), ()),
        ('m6-d', 'Pottery show and tell evening: bring one piece', (), ('Staff pick',)),
    ],
}

OCCASION_NAMES = dict(OCCASIONS)
PRESET_BADGE = "Booked for you"
BADGE_SEP = " · "
TICK = "✓"
LETTERS = "ABCD"

# Palette: moss and cream with a terracotta accent. Nothing is coloured by hobby.
MOSS, MOSS_DK, CREAM, PAPER, INK, MUTED, LINE = (
    "#2f4a3a", "#233a2d", "#f4efe3", "#fffdf7", "#23302a", "#6b7468", "#ddd5c2")
TERRA, TERRA_DK, SAGE, SAGE_LT, IDLE = "#c0643f", "#a4512f", "#8fa98f", "#e7eee3", "#b9b3a3"


class BookingApp:
    def __init__(self, root: tk.Tk):
        self.root = root
        self.current = OCCASIONS[0][0]
        self.choices: dict[str, str] = {}
        self.events: list[dict] = []
        self.saved = False
        self.month_buttons: dict[str, tk.Button] = {}
        self.option_buttons: dict[str, tk.Button] = {}
        root.title(TITLE)
        root.geometry("1024x866")
        root.minsize(980, 820)
        root.configure(bg=CREAM)
        root.lift()
        root.attributes("-topmost", True)
        root.after(8000, lambda: root.attributes("-topmost", False))
        serif, sans = "URW Bookman", "Nimbus Sans"
        self.f_brand = tkfont.Font(family=serif, size=20, weight="bold")
        self.f_brand2 = tkfont.Font(family=serif, size=14, slant="italic")
        self.f_head = tkfont.Font(family=serif, size=19, weight="bold")
        self.f_card = tkfont.Font(family=sans, size=13, weight="bold")
        self.f_month = tkfont.Font(family=sans, size=12, weight="bold")
        self.f_body = tkfont.Font(family=sans, size=11)
        self.f_small = tkfont.Font(family=sans, size=10)
        self.f_caps = tkfont.Font(family=sans, size=10, weight="bold")
        self.f_letter = tkfont.Font(family=serif, size=16, weight="bold")

        self._header()
        self._timeline()
        body = tk.Frame(root, bg=CREAM)
        body.pack(side="top", fill="both", expand=True, padx=18, pady=(4, 14))
        self._sidebar(body)
        self.centre = tk.Frame(body, bg=CREAM)
        self.centre.pack(side="left", fill="both", expand=True, padx=(0, 16))
        self.refresh()

    # ---- chrome -------------------------------------------------------------------------------------
    def _header(self):
        head = tk.Frame(self.root, bg=MOSS, height=70)
        head.pack(side="top", fill="x")
        head.pack_propagate(False)
        mark = tk.Canvas(head, width=50, height=50, bg=MOSS, highlightthickness=0)
        mark.pack(side="left", padx=(20, 10), pady=10)
        mark.create_oval(4, 4, 46, 46, outline=CREAM, width=2)
        for i in range(6):
            ang = math.radians(-90 + 60 * i)
            x, y = 25 + 14 * math.cos(ang), 25 + 14 * math.sin(ang)
            mark.create_oval(x - 4, y - 4, x + 4, y + 4, fill=TERRA if i == 0 else CREAM, outline="")
        mark.create_oval(21, 21, 29, 29, fill=SAGE, outline="")
        words = tk.Frame(head, bg=MOSS)
        words.pack(side="left")
        tk.Label(words, text="Brindley", bg=MOSS, fg=CREAM, font=self.f_brand).pack(side="left")
        tk.Label(words, text=" Hobby Circle", bg=MOSS, fg="#e9c9a8", font=self.f_brand2).pack(side="left", pady=(6, 0))
        chip = tk.Label(head, text="Member 0417  ·  Season planner", bg=MOSS_DK, fg=CREAM, font=self.f_small,
                        padx=12, pady=6)
        chip.pack(side="right", padx=20)
        for word in ("Help", "Club notices", "Programme"):
            tk.Label(head, text=word, bg=MOSS, fg="#c9d6c8", font=self.f_body).pack(side="right", padx=10)
        tk.Frame(self.root, bg=TERRA, height=3).pack(side="top", fill="x")

    def _timeline(self):
        band = tk.Frame(self.root, bg=PAPER, highlightbackground=LINE, highlightthickness=1)
        band.pack(side="top", fill="x", padx=18, pady=(14, 10))
        top = tk.Frame(band, bg=PAPER)
        top.pack(fill="x", padx=16, pady=(10, 2))
        tk.Label(top, text=UI["rail_heading"].upper(), bg=PAPER, fg=TERRA, font=self.f_caps).pack(side="left")
        tk.Label(top, text=UI["subtitle"], bg=PAPER, fg=MUTED, font=self.f_small).pack(side="left", padx=12)
        self.track = tk.Canvas(band, height=78, bg=PAPER, highlightthickness=0)
        self.track.pack(fill="x", padx=10, pady=(0, 8))
        self.track.bind("<Configure>", lambda e: self._layout_track())
        for occ, name in OCCASIONS:
            b = tk.Button(self.track, text=name, relief="flat", bd=0, font=self.f_month, cursor="hand2",
                          padx=6, pady=6, width=11, command=lambda o=occ: self.show(o))
            self.month_buttons[occ] = b
        self.track_windows = []

    def _layout_track(self):
        self.track.delete("all")
        w = max(self.track.winfo_width(), 900)
        step = w / len(OCCASIONS)
        y = 40
        self.track.create_line(step / 2, y, w - step / 2, y, fill=LINE, width=3)
        for i, (occ, _) in enumerate(OCCASIONS):
            x = step / 2 + i * step
            self.track.create_window(x, y, window=self.month_buttons[occ], width=step - 22, height=58)

    def _sidebar(self, body):
        side = tk.Frame(body, bg=CREAM, width=300)
        side.pack(side="right", fill="y")
        side.pack_propagate(False)
        card = tk.Frame(side, bg=MOSS, padx=16, pady=14)
        card.pack(fill="both", expand=True)
        tk.Label(card, text="YOUR PROGRAMME", bg=MOSS, fg="#e9c9a8", font=self.f_caps).pack(anchor="w")
        tk.Label(card, text="Brindley Hobby Circle · this season", bg=MOSS, fg="#c9d6c8",
                 font=self.f_small).pack(anchor="w", pady=(2, 8))
        self.summary = tk.Frame(card, bg=MOSS)
        self.summary.pack(fill="x")
        foot = tk.Frame(card, bg=MOSS)
        foot.pack(side="bottom", fill="x")
        self.count = tk.Label(foot, text="", bg=MOSS, fg=CREAM, font=self.f_card)
        self.count.pack(anchor="w", pady=(0, 8))
        self.save_button = tk.Button(foot, text=UI["save"], bg=IDLE, fg="white", activebackground=TERRA_DK,
                                     activeforeground="white", disabledforeground="#efeadf", relief="flat", bd=0,
                                     font=self.f_card, pady=10, cursor="hand2", command=self.save, state="disabled")
        self.save_button.pack(fill="x")
        tk.Label(foot, text="Circle hall, Brindley Lane · desk open before every session", bg=MOSS,
                 fg="#a9bba8", font=self.f_small, wraplength=260, justify="left").pack(anchor="w", pady=(10, 0))

    # ---- state views --------------------------------------------------------------------------------
    def refresh(self):
        self.refresh_count()
        self.show(self.current)

    def refresh_months(self):
        for occ, button in self.month_buttons.items():
            here = occ == self.current
            done = occ in self.choices
            label = OCCASION_NAMES[occ] + ("\n" + TICK + " " + UI["is_chosen"] if done else "\n" + UI["not_chosen"])
            button.configure(text=label,
                             bg=MOSS if here else (SAGE_LT if done else "#f1ece0"),
                             fg=CREAM if here else INK,
                             activebackground=MOSS_DK, activeforeground=CREAM,
                             highlightthickness=0)
        for child in self.summary.winfo_children():
            child.destroy()
        names = {o[0]: o[1] for occ, _ in OCCASIONS for o in OPTIONS[occ]}
        for occ, name in OCCASIONS:
            row = tk.Frame(self.summary, bg=MOSS)
            row.pack(fill="x", pady=3)
            done = occ in self.choices
            tk.Label(row, text=TICK if done else "○", bg=MOSS, fg="#e9c9a8" if done else "#8da08d",
                     font=self.f_card, width=2).pack(side="left", anchor="n")
            col = tk.Frame(row, bg=MOSS)
            col.pack(side="left", fill="x")
            tk.Label(col, text=name, bg=MOSS, fg=CREAM, font=self.f_caps).pack(anchor="w")
            tk.Label(col, text=names[self.choices[occ]] if done else UI["not_chosen"], bg=MOSS,
                     fg="#dfe7dc" if done else "#8da08d", font=self.f_small, wraplength=230,
                     justify="left").pack(anchor="w")

    def show(self, occ: str):
        self.current = occ
        self.refresh_months()
        for child in self.centre.winfo_children():
            child.destroy()
        self.option_buttons = {}
        chosen = occ in self.choices
        head = tk.Frame(self.centre, bg=CREAM)
        head.pack(fill="x")
        tk.Label(head, text=OCCASION_NAMES[occ], bg=CREAM, fg=INK, font=self.f_head).pack(side="left")
        tk.Label(head, text=(TICK + " " + UI["is_chosen"]) if chosen else UI["not_chosen"],
                 bg=MOSS if chosen else "#efe1cf", fg=CREAM if chosen else TERRA_DK, font=self.f_caps,
                 padx=10, pady=3).pack(side="left", padx=14, pady=(4, 0))
        booked_already = any(PRESET_BADGE in option[3] for option in OPTIONS[occ])
        tk.Label(self.centre, text=UI["note_preset"] if booked_already else UI["note_plain"], bg=CREAM, fg=MUTED,
                 font=self.f_body, wraplength=640, justify="left").pack(anchor="w", pady=(4, 10))
        for index, option in enumerate(OPTIONS[occ]):
            self.card(occ, index, option)

    def card(self, occ: str, index: int, option: tuple):
        oid, text, sessions, badges = option
        chosen = self.choices.get(occ) == oid
        fill = SAGE_LT if chosen else PAPER
        edge = MOSS if chosen else LINE
        box = tk.Frame(self.centre, bg=fill, highlightbackground=edge, highlightcolor=edge, highlightthickness=2)
        box.pack(fill="x", pady=5)
        disc = tk.Canvas(box, width=52, height=52, bg=fill, highlightthickness=0)
        disc.pack(side="left", padx=(14, 10), pady=16, anchor="n")
        disc.create_oval(3, 3, 49, 49, fill=MOSS if chosen else CREAM, outline=MOSS, width=2)
        disc.create_text(26, 27, text=LETTERS[index], fill=CREAM if chosen else MOSS, font=self.f_letter)
        button = tk.Button(box, text=UI["chosen"] if chosen else UI["choose"], width=9, relief="flat", bd=0,
                           bg=MOSS if chosen else TERRA, fg="white", activebackground=TERRA_DK,
                           activeforeground="white", font=self.f_card, pady=7, cursor="hand2",
                           command=lambda: self.choose(occ, oid))
        button.pack(side="right", padx=16)
        self.option_buttons[oid] = button
        col = tk.Frame(box, bg=fill)
        col.pack(side="left", fill="both", expand=True, pady=14)
        tk.Label(col, text=f"Option {LETTERS[index]}", bg=fill, fg=MUTED, font=self.f_caps).pack(anchor="w")
        if sessions:
            for line in sessions:
                tk.Label(col, text=line, bg=fill, fg=INK, font=self.f_body, wraplength=440,
                         justify="left").pack(anchor="w", pady=(2, 0))
        else:
            tk.Label(col, text=text, bg=fill, fg=INK, font=self.f_card, wraplength=440,
                     justify="left").pack(anchor="w", pady=(2, 0))
        tk.Label(col, text=BADGE_SEP.join(badges), bg=fill, fg=TERRA_DK, font=self.f_small, wraplength=440,
                 justify="left").pack(anchor="w", pady=(6, 0))

    def choose(self, occ: str, oid: str):
        if self.saved:
            return
        self.choices[occ] = oid
        self.events.append({"type": "select", "occasion": occ, "optionId": oid})
        self.refresh_count()
        # Redraw after the click handler returns, so the clicked button is not destroyed inside its own command.
        self.root.after_idle(lambda: self.show(occ))

    def refresh_count(self):
        done = sum(1 for occ, _ in OCCASIONS if occ in self.choices)
        ready = done == len(OCCASIONS)
        self.count.configure(text=f"{done} of {len(OCCASIONS)} chosen")
        self.save_button.configure(state="normal" if ready else "disabled", bg=TERRA if ready else IDLE)

    def save(self):
        if self.saved or any(occ not in self.choices for occ, _ in OCCASIONS):
            return
        events = [dict(e) for e in self.events] + [{"type": "submit"}]
        names = {option[0]: option[1] for occ, _ in OCCASIONS for option in OPTIONS[occ]}
        result = {
            "submitted": True,
            "selections": {occ: self.choices[occ] for occ, _ in OCCASIONS},
            "selectedItems": [{"occasion": occ, "optionId": self.choices[occ], "name": names[self.choices[occ]]}
                              for occ, _ in OCCASIONS],
            "events": events,
        }
        target = os.path.join(OUTPUT_DIR, "order_result.json")
        try:
            os.makedirs(OUTPUT_DIR, exist_ok=True)
            with open(target + ".part", "w", encoding="utf-8") as fh:
                json.dump(result, fh, ensure_ascii=False, indent=2)
            os.replace(target + ".part", target)
        except OSError as exc:
            self.count.configure(text=f"{UI['save_failed']} {exc}")
            return
        self.saved = True
        self.events = events
        self.save_button.configure(state="disabled", bg=IDLE)
        cover = tk.Frame(self.root, bg=CREAM)
        cover.place(relx=0, rely=0, relwidth=1, relheight=1)
        seal = tk.Canvas(cover, width=90, height=90, bg=CREAM, highlightthickness=0)
        seal.place(relx=0.5, rely=0.36, anchor="center")
        seal.create_oval(5, 5, 85, 85, fill=MOSS, outline="")
        seal.create_text(45, 46, text=TICK, fill=CREAM, font=self.f_head)
        tk.Label(cover, text=UI["saved"], bg=CREAM, fg=MOSS, font=self.f_head).place(
            relx=0.5, rely=0.47, anchor="center")
        tk.Label(cover, text="Brindley Hobby Circle · see you at the hall", bg=CREAM, fg=MUTED,
                 font=self.f_body).place(relx=0.5, rely=0.52, anchor="center")


if __name__ == "__main__":
    app_root = tk.Tk()
    BookingApp(app_root)
    app_root.mainloop()
