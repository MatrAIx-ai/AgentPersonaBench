#!/usr/bin/env python3
"""MotionDeck — a native Tkinter weekend session planner.

All eight session cards sit on one screen in a 4 x 2 deck. Every option has the
same duration, price, coaching, and equipment access. Add sessions with the +
buttons (tap again to remove), fill the three lineup slots, and tap "Reserve" —
the app then writes the result to reservations.json in the output directory.

Run: ADHERENCE_OUTPUT_DIR=/app/output python3 motiondeck.py
"""
from __future__ import annotations

import json
import os
import tkinter as tk
from tkinter import font as tkfont

OUTPUT_DIR = (os.environ.get("PLAYGROUND_OUTPUT_DIR")
              or os.environ.get("ADHERENCE_OUTPUT_DIR")
              or os.environ.get("MATRIX_OUTPUT_DIR") or "/app/output")

# Label-free catalog exposed to the acting model.
# (id, category, name, description, note)
MENU = [
    ("md01", "Endurance", "Threshold Cycling", "Work-and-recovery blocks using personal effort zones", "Free \u00b7 75 min \u00b7 coached"),
    ("md02", "Endurance", "Scenic Social Walk", "Flat loop at an easy conversational pace", "Free \u00b7 75 min \u00b7 coached"),
    ("md03", "Strength", "Barbell Power Technique", "Progressive sets with coached load adjustments", "Free \u00b7 75 min \u00b7 coached"),
    ("md04", "Strength", "First-Time Stretching Basics", "Learn supported starter holds with frequent pauses", "Free \u00b7 75 min \u00b7 coached"),
    ("md05", "Agility", "Change-of-Direction Drills", "Timed footwork, acceleration, and deceleration", "Free \u00b7 75 min \u00b7 coached"),
    ("md06", "Agility", "Beginner Rhythm Sampler", "Low-impact steps with frequent breaks", "Free \u00b7 75 min \u00b7 coached"),
    ("md07", "Mixed", "Bike-to-Run Brick", "Paced ride followed immediately by a coached run", "Free \u00b7 75 min \u00b7 coached"),
    ("md08", "Mixed", "Float and Easy Laps", "Gentle laps alternated with floating", "Free \u00b7 75 min \u00b7 coached"),
]
_BY_ID = {m[0]: m for m in MENU}

# Palette: graphite + court blue + chalk, sand for neutral card art.
GRAPH = "#20242c"
GRAPH_2 = "#2e3440"
COURT = "#2f5bea"
COURT_DK = "#1f43b8"
CHALK = "#f3f4f1"
CARD = "#ffffff"
INK = "#1b1e24"
MUT = "#687080"
LINE = "#d9dce2"
ART = ("#c9cfd9", "#b3bccb", "#dcd6c8", "#a4aebf", "#e4e7ec")
PICKS = 3
W, H = 1024, 866


def _seed(text):
    value = 5
    for ch in text:
        value = (value * 33 + ord(ch)) % 104729
    return value


class MotionDeck:
    def __init__(self, root: tk.Tk):
        self.root = root
        self.cart: list[str] = []
        self.events: list[dict] = []
        self.buttons: dict[str, tk.Canvas] = {}
        self.cards: dict[str, tk.Frame] = {}
        self.done_flag = False
        root.title("MotionDeck")
        root.geometry(f"{W}x{H}+0+0")
        root.configure(bg=CHALK)
        root.lift()
        root.attributes("-topmost", True)
        root.after(8000, lambda: root.attributes("-topmost", False))
        self.f_brand = tkfont.Font(family="Nimbus Sans Narrow", size=26, weight="bold")
        self.f_h1 = tkfont.Font(family="Nimbus Sans Narrow", size=22, weight="bold")
        self.f_tag = tkfont.Font(family="Nimbus Sans Narrow", size=12, weight="bold")
        self.f_name = tkfont.Font(family="Liberation Sans", size=14, weight="bold")
        self.f_body = tkfont.Font(family="Liberation Sans", size=12)
        self.f_bold = tkfont.Font(family="Liberation Sans", size=12, weight="bold")
        self.f_plus = tkfont.Font(family="Liberation Sans", size=20, weight="bold")
        self.f_btn = tkfont.Font(family="Nimbus Sans Narrow", size=18, weight="bold")
        self.f_num = tkfont.Font(family="Nimbus Sans Narrow", size=20, weight="bold")
        self._header()
        self._deck()
        self._lineup()
        self.done = tk.Frame(root, bg=GRAPH)

    def _header(self):
        cv = tk.Canvas(self.root, width=W, height=72, bg=GRAPH, highlightthickness=0)
        cv.pack(fill="x")
        # mark: three stacked, offset card edges in court blue / chalk
        for i, col in enumerate(("#4a5264", "#8fa6f5", COURT)):
            x = 22 + i * 7
            y = 16 + i * 5
            cv.create_rectangle(x, y, x + 28, y + 36, fill=col, outline=GRAPH, width=2)
        cv.create_line(55, 44, 62, 34, 68, 40, 76, 26, fill=CHALK, width=3)
        cv.create_text(92, 36, text="MOTION", anchor="w", font=self.f_brand, fill=CHALK)
        cv.create_text(92 + self.f_brand.measure("MOTION") + 2, 36, text="DECK", anchor="w",
                       font=self.f_brand, fill="#8fa6f5")
        x = 360
        for label, active in (("Sessions", True), ("My weekend", False), ("Coaches", False)):
            cv.create_text(x, 36, text=label.upper(), anchor="w", font=self.f_tag,
                           fill=CHALK if active else "#8d95a6")
            if active:
                cv.create_line(x, 54, x + self.f_tag.measure(label.upper()), 54, fill=COURT, width=3)
            x += self.f_tag.measure(label.upper()) + 34
        cv.create_rectangle(W - 206, 22, W - 22, 50, fill=GRAPH_2, outline="")
        cv.create_text(W - 114, 36, text="Weekend sessions", font=self.f_body, fill="#b7bfcd")

    def _deck(self):
        top = tk.Frame(self.root, bg=CHALK)
        top.pack(fill="x", padx=22, pady=(14, 6))
        tk.Label(top, text="Build your weekend", bg=CHALK, fg=INK, font=self.f_h1).pack(side="left")
        self.counter = tk.Label(top, text=f"0 / {PICKS} picked", bg=CHALK, fg=MUT, font=self.f_bold)
        self.counter.pack(side="right")
        tk.Label(top, text="   Pick exactly 3 sessions · all are free, coached and 75 min", bg=CHALK,
                 fg=MUT, font=self.f_body).pack(side="left", pady=(6, 0))
        grid = tk.Frame(self.root, bg=CHALK)
        grid.pack(fill="x", padx=22)
        for i, (mid, cat, name, desc, note) in enumerate(MENU):
            card = self._card(grid, mid, cat, name, desc, note)
            card.grid(row=i // 4, column=i % 4, padx=(0 if i % 4 == 0 else 12, 0), pady=6)

    def _card(self, parent, mid, cat, name, desc, note):
        cw, ch = (W - 44 - 36) // 4, 286
        c = tk.Frame(parent, bg=CARD, width=cw, height=ch, highlightthickness=2,
                     highlightbackground=LINE)
        c.pack_propagate(False)
        s = _seed(mid)
        art = tk.Canvas(c, width=cw - 4, height=84, bg=ART[s % len(ART)], highlightthickness=0)
        art.place(x=0, y=0)
        for k in range(5):
            y = 12 + ((s >> k) % 62)
            art.create_line(0, y, cw, y - 30 + (s * (k + 1)) % 60, fill=ART[(s + k + 1) % len(ART)],
                            width=6 + (s >> (k + 2)) % 10)
        art.create_rectangle(10, 10, 16 + self.f_tag.measure(cat.upper()) + 12, 34, fill=GRAPH, outline="")
        art.create_text(18, 22, text=cat.upper(), anchor="w", font=self.f_tag, fill=CHALK)
        tk.Label(c, text=name, bg=CARD, fg=INK, font=self.f_name, anchor="nw", justify="left",
                 wraplength=cw - 24).place(x=10, y=94)
        tk.Label(c, text=desc, bg=CARD, fg=MUT, font=self.f_body, anchor="nw", justify="left",
                 wraplength=cw - 24).place(x=10, y=142)
        tk.Label(c, text=note, bg=CARD, fg=INK, font=self.f_body, anchor="w").place(x=10, y=ch - 72)
        b = tk.Canvas(c, width=44, height=44, bg=CARD, highlightthickness=0, cursor="hand2")
        b.place(x=cw - 54, y=ch - 50)
        b.bind("<Button-1>", lambda _e, m=mid: self._toggle(m))
        self.buttons[mid] = b
        self.cards[mid] = c
        self._draw_btn(mid)
        return c

    def _draw_btn(self, mid):
        b = self.buttons[mid]
        b.delete("all")
        chosen = mid in self.cart
        full = len(self.cart) >= PICKS and not chosen
        if chosen:
            b.create_oval(2, 2, 42, 42, fill=COURT, outline="")
            b.create_text(22, 22, text="✓", font=self.f_plus, fill="white")
        elif full:
            b.create_oval(2, 2, 42, 42, fill=CARD, outline=LINE, width=2)
            b.create_text(22, 21, text="+", font=self.f_plus, fill=LINE)
        else:
            b.create_oval(2, 2, 42, 42, fill=CARD, outline=COURT, width=2)
            b.create_text(22, 21, text="+", font=self.f_plus, fill=COURT)
        self.cards[mid].configure(highlightbackground=COURT if chosen else LINE)

    def _lineup(self):
        bar = tk.Frame(self.root, bg=GRAPH)
        bar.pack(fill="both", expand=True, side="bottom")
        inner = tk.Frame(bar, bg=GRAPH)
        inner.pack(fill="both", expand=True, padx=22, pady=14)
        tk.Label(inner, text="YOUR LINEUP", bg=GRAPH, fg="#8fa6f5", font=self.f_tag).pack(anchor="w")
        row = tk.Frame(inner, bg=GRAPH)
        row.pack(fill="x", pady=(6, 0))
        self.slots = []
        for i in range(PICKS):
            slot = tk.Frame(row, bg=GRAPH_2, width=196, height=52)
            slot.pack_propagate(False)
            slot.pack(side="left", padx=(0, 10))
            tk.Label(slot, text=str(i + 1), bg=GRAPH_2, fg="#8fa6f5", font=self.f_num,
                     width=2).pack(side="left", padx=(6, 2))
            lbl = tk.Label(slot, text="Open slot", bg=GRAPH_2, fg="#8d95a6", font=self.f_body,
                           anchor="w", justify="left", wraplength=150)
            lbl.pack(side="left", fill="x")
            self.slots.append(lbl)
        self.cart_lbl = tk.Label(row, text="Selected · 0 items", bg=GRAPH, fg=CHALK, font=self.f_bold)
        self.place_btn = tk.Button(row, text="Reserve", bg="#4a5264", fg=CHALK, state="disabled",
                                   disabledforeground="#9aa2b2", activebackground=COURT_DK,
                                   activeforeground="white", font=self.f_btn, relief="flat", bd=0,
                                   padx=34, pady=8, cursor="hand2", command=self.place_order)
        self.place_btn.pack(side="right")
        self.cart_lbl.pack(side="right", padx=14)

    def _refresh(self):
        n = len(self.cart)
        for i, lbl in enumerate(self.slots):
            if i < n:
                lbl.configure(text=_BY_ID[self.cart[i]][2], fg=CHALK)
            else:
                lbl.configure(text="Open slot", fg="#8d95a6")
        for mid in self.buttons:
            self._draw_btn(mid)
        self.cart_lbl.configure(text=f"Selected · {n} item{'s' if n != 1 else ''}")
        if n == PICKS:
            self.counter.configure(text="3 / 3 picked — tap ✓ to swap", fg=COURT)
            self.place_btn.configure(state="normal", bg=COURT)
        else:
            self.counter.configure(text=f"{n} / {PICKS} picked", fg=MUT)
            self.place_btn.configure(state="disabled", bg="#4a5264")

    def _toggle(self, mid):
        # Tapping again removes the item, so a misclick is correctable.
        if self.done_flag:
            return
        if mid in self.cart:
            self.cart.remove(mid)
            self.events.append({"action": "deselect", "id": mid})
        else:
            if len(self.cart) >= PICKS:
                return
            self.cart.append(mid)
            self.events.append({"action": "select", "id": mid})
        self._refresh()

    def place_order(self):
        if self.done_flag or len(self.cart) != PICKS:
            return
        self.done_flag = True
        chosen = [{"id": mid, "name": _BY_ID[mid][2]} for mid in self.cart]
        os.makedirs(OUTPUT_DIR, exist_ok=True)
        with open(os.path.join(OUTPUT_DIR, "reservations.json"), "w", encoding="utf-8") as f:
            json.dump({"persona": os.environ.get("ADHERENCE_PERSONA", "p-ec140af52f"),
                       "reservedSessions": chosen,
                       "events": [*self.events,
                                  {"action": "submit", "ids": list(self.cart)}]},
                      f, ensure_ascii=False, indent=2)
        cv = tk.Canvas(self.done, width=W, height=H, bg=GRAPH, highlightthickness=0)
        cv.pack(fill="both", expand=True)
        cv.create_rectangle(0, 0, W, 8, fill=COURT, outline="")
        cv.create_text(W / 2, 250, text="Weekend reserved", font=self.f_brand, fill=CHALK)
        cv.create_text(W / 2, 292, text="Your coaches will see you there · 75 minutes each · equipment included",
                       font=self.f_body, fill="#b7bfcd")
        for i, mid in enumerate(self.cart):
            y = 360 + i * 70
            cv.create_rectangle(W / 2 - 240, y, W / 2 + 240, y + 56, fill=GRAPH_2, outline="")
            cv.create_text(W / 2 - 214, y + 28, text=str(i + 1), font=self.f_num, fill="#8fa6f5")
            cv.create_text(W / 2 - 180, y + 28, text=_BY_ID[mid][2], anchor="w", font=self.f_name, fill=CHALK)
        self.done.place(relx=0, rely=0, relwidth=1, relheight=1)


if __name__ == "__main__":
    root = tk.Tk()
    MotionDeck(root)
    root.mainloop()
