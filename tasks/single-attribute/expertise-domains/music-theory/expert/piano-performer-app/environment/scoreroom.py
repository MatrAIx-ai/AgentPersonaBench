#!/usr/bin/env python3
"""ScoreRoom — a native Tkinter music-practice app.

A genuine desktop application (native windows, buttons, lists). Every option has the same instrument, room, duration, and fee.
Browse the options, add items with the + buttons, and tap "Add to Plan" — the app
then writes the result to practice_plan.json in the output directory.

Run: ADHERENCE_OUTPUT_DIR=/app/output python3 scoreroom.py
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
    ("sr01", "Harmony", "Chord-Name Flashcards", "Name each printed chord without tracing its function", "Free \u00b7 60 min \u00b7 same room"),
    ("sr02", "Harmony", "Harmonic Route Map", "Mark pivots, tonicizations, cadences, and arrivals", "Free \u00b7 60 min \u00b7 same room"),
    ("sr03", "Texture", "Hard-Bars Motor Drill", "Repeat difficult hand shapes until automatic", "Free \u00b7 60 min \u00b7 same room"),
    ("sr04", "Texture", "Voice-Leading Reduction", "Trace active lines and structural tones", "Free \u00b7 60 min \u00b7 same room"),
    ("sr05", "Form", "Formal Return Comparison", "Chart changed harmony, register, and function", "Free \u00b7 60 min \u00b7 same room"),
    ("sr06", "Form", "Full-Movement Loop", "Use repeated uninterrupted run-throughs", "Free \u00b7 60 min \u00b7 same room"),
    ("sr07", "Sources", "Edition Evidence Table", "Compare readings through sources, syntax, and line direction", "Free \u00b7 60 min \u00b7 same room"),
    ("sr08", "Sources", "Favorite-Recording Shadow", "Copy one admired performance by ear", "Free \u00b7 60 min \u00b7 same room"),
]
_BY_ID = {m[0]: m for m in MENU}

# ---------------------------------------------------------------------------
# Look: "practice-room booking board" -- ivory manuscript paper, ebony keyboard
# band, verdigris + brass accents. Every card shares one anatomy; the small
# staff vignette is seeded from the card position only.
# ---------------------------------------------------------------------------
IVORY, PAPER, EBONY, EBONY_2 = "#f5efe2", "#fffbf2", "#17140f", "#2a251d"
INK, MUT, RULE = "#1d1a15", "#6f675b", "#ddd2bd"
VERD, VERD_DARK, VERD_SOFT, BRASS = "#2f7d6d", "#23604f", "#dcebe5", "#b8893b"
MAX_PICKS = 3


def _f(family, size, weight="normal", slant="roman"):
    return tkfont.Font(family=family, size=-size, weight=weight, slant=slant)


class ScoreRoom:
    def __init__(self, root: tk.Tk):
        self.root = root
        self.cart: list[str] = []
        self.events: list[dict] = []
        self.buttons: dict[str, tk.Button] = {}
        self.cards: dict[str, tuple] = {}
        root.title("ScoreRoom")
        root.geometry("1024x866+0+0")
        root.minsize(960, 800)
        root.configure(bg=IVORY)
        root.lift()
        root.attributes("-topmost", True)
        root.after(8000, lambda: root.attributes("-topmost", False))

        self.f_brand = _f("Nimbus Roman", 28, "bold")
        self.f_tag = _f("Nimbus Roman", 15, "normal", "italic")
        self.f_name = _f("Nimbus Roman", 19, "bold")
        self.f_body = _f("Liberation Sans", 13)
        self.f_small = _f("Liberation Sans", 12)
        self.f_small_b = _f("Liberation Sans", 12, "bold")
        self.f_col = _f("Liberation Sans", 12, "bold")
        self.f_btn = _f("Liberation Sans", 15, "bold")
        self.f_plus = _f("Liberation Sans", 20, "bold")
        self.f_slot = _f("Nimbus Roman", 16, "bold")
        self.f_done = _f("Nimbus Roman", 34, "bold")

        self._header()
        self._tray()
        self._grid()
        self._refresh()

    # ------------------------------------------------------------ header
    def _header(self):
        top = tk.Frame(self.root, bg=EBONY, height=66)
        top.pack(fill="x", side="top")
        top.pack_propagate(False)
        mark = tk.Canvas(top, width=44, height=44, bg=EBONY, highlightthickness=0)
        mark.pack(side="left", padx=(20, 12), pady=11)
        mark.create_oval(2, 2, 42, 42, fill=BRASS, outline="")
        for i in range(5):
            mark.create_line(9, 13 + i * 5, 35, 13 + i * 5, fill=EBONY, width=1)
        mark.create_oval(15, 24, 23, 30, fill=EBONY, outline="")
        mark.create_line(22, 27, 22, 9, fill=EBONY, width=2)
        tk.Label(top, text="ScoreRoom", bg=EBONY, fg=PAPER, font=self.f_brand).pack(side="left")
        tk.Label(top, text="   practice room planner", bg=EBONY, fg="#c9bda6", font=self.f_tag).pack(side="left", pady=(8, 0))
        chip = tk.Label(top, text="Room 4  ·  concert grand  ·  60-minute sessions", bg=EBONY_2, fg="#e7dcc6", font=self.f_small, padx=12, pady=6)
        chip.pack(side="right", padx=20)

        keys = tk.Canvas(self.root, height=26, bg=EBONY, highlightthickness=0)
        keys.pack(fill="x", side="top")
        white_w = 1024 / 52
        for i in range(52):
            x = i * white_w
            keys.create_rectangle(x, 0, x + white_w - 1, 26, fill="#f4efe4", outline="#b9ae99")
        pattern = (1, 1, 0, 1, 1, 1, 0)
        for i in range(51):
            if pattern[(i + 5) % 7]:
                x = (i + 1) * white_w - white_w * 0.3
                keys.create_rectangle(x, 0, x + white_w * 0.6, 16, fill=EBONY, outline="")

        intro = tk.Frame(self.root, bg=IVORY)
        intro.pack(fill="x", side="top", padx=24, pady=(12, 4))
        tk.Label(intro, text="Choose three practice hours", bg=IVORY, fg=INK, font=_f("Nimbus Roman", 22, "bold")).pack(side="left")
        tk.Label(intro, text="Every session is free, 60 minutes, in the same room on the same piano.", bg=IVORY, fg=MUT, font=self.f_body).pack(side="left", padx=14, pady=(6, 0))

    # -------------------------------------------------------------- grid
    def _grid(self):
        grid = tk.Frame(self.root, bg=IVORY)
        grid.pack(fill="both", expand=True, padx=18, pady=(4, 6))
        cats = []
        for row in MENU:
            if row[1] not in cats:
                cats.append(row[1])
        for c, cat in enumerate(cats):
            grid.columnconfigure(c, weight=1, uniform="col")
            head = tk.Frame(grid, bg=IVORY)
            head.grid(row=0, column=c, sticky="ew", padx=6, pady=(0, 6))
            tk.Label(head, text=cat.upper(), bg=IVORY, fg=VERD_DARK, font=self.f_col).pack(side="left")
            tk.Frame(head, bg=RULE, height=1).pack(side="left", fill="x", expand=True, padx=(8, 0), pady=(3, 0))
            r = 1
            for row in MENU:
                if row[1] == cat:
                    self._card(grid, row, r, c)
                    r += 1
        for r in (1, 2):
            grid.rowconfigure(r, weight=1, uniform="row")

    def _card(self, parent, row, r, c):
        mid, _cat, name, desc, note = row
        pos = [m[0] for m in MENU].index(mid)
        card = tk.Frame(parent, bg=PAPER, highlightthickness=1, highlightbackground=RULE)
        card.grid(row=r, column=c, sticky="nsew", padx=6, pady=(0, 10))
        staff = tk.Canvas(card, height=46, bg=PAPER, highlightthickness=0)
        staff.pack(fill="x", padx=14, pady=(12, 0))
        staff.bind("<Configure>", lambda e, cv=staff, p=pos: self._draw_staff(cv, e.width, p))
        tk.Label(card, text=f"Session {pos + 1:02d}", bg=PAPER, fg=MUT, font=self.f_small, anchor="w").pack(fill="x", padx=14, pady=(6, 0))
        tk.Label(card, text=name, bg=PAPER, fg=INK, font=self.f_name, anchor="w", justify="left", wraplength=196).pack(fill="x", padx=14)
        tk.Label(card, text=desc, bg=PAPER, fg="#3f392f", font=self.f_body, anchor="w", justify="left", wraplength=196).pack(fill="x", padx=14, pady=(4, 0))
        foot = tk.Frame(card, bg=PAPER)
        foot.pack(side="bottom", fill="x", padx=14, pady=12)
        tk.Label(foot, text=note, bg=PAPER, fg=MUT, font=self.f_small, anchor="w", justify="left", wraplength=140).pack(side="left", fill="x", expand=True)
        btn = tk.Button(foot, name=f"add_{mid}", text="+", width=2, font=self.f_plus, bg=VERD, fg="white",
                        activebackground=VERD_DARK, activeforeground="white", relief="flat", bd=0,
                        highlightthickness=0, cursor="hand2", command=lambda m=mid: self._toggle(m, self.buttons[m]))
        btn.pack(side="right")
        self.buttons[mid] = btn
        self.cards[mid] = (card,)

    def _draw_staff(self, cv, width, pos):
        cv.delete("all")
        for i in range(5):
            y = 6 + i * 8
            cv.create_line(0, y, width, y, fill="#cfc3aa")
        step = max(24, (width - 20) // 7)
        for k in range(7):
            level = (pos * 3 + k * 5) % 9
            x = 14 + k * step
            y = 38 - level * 4
            cv.create_oval(x - 5, y - 4, x + 5, y + 4, fill="#5a5245", outline="")
            cv.create_line(x + 4, y, x + 4, y - 22, fill="#5a5245")
        cv.create_line(width - 2, 6, width - 2, 38, fill="#cfc3aa", width=2)

    # -------------------------------------------------------------- tray
    def _tray(self):
        tray = tk.Frame(self.root, bg=EBONY, height=132)
        tray.pack(fill="x", side="bottom")
        tray.pack_propagate(False)
        left = tk.Frame(tray, bg=EBONY)
        left.pack(side="left", fill="y", padx=(22, 10), pady=14)
        tk.Label(left, text="YOUR PLAN", bg=EBONY, fg=BRASS, font=self.f_small_b, anchor="w").pack(fill="x")
        self.cart_lbl = tk.Label(left, text="", bg=EBONY, fg=PAPER, font=self.f_slot, anchor="w")
        self.cart_lbl.pack(fill="x", pady=(4, 0))
        self.hint = tk.Label(left, text="", bg=EBONY, fg="#c9bda6", font=self.f_small, anchor="w", justify="left", wraplength=150)
        self.hint.pack(fill="x", pady=(4, 0))
        self.slots = []
        for i in range(MAX_PICKS):
            slot = tk.Frame(tray, bg=EBONY_2, width=196, height=104, highlightthickness=1, highlightbackground="#4a4236")
            slot.pack(side="left", padx=6, pady=16)
            slot.pack_propagate(False)
            tk.Label(slot, text=f"HOUR {i + 1}", bg=EBONY_2, fg="#a89b84", font=self.f_small_b, anchor="w").pack(fill="x", padx=10, pady=(8, 0))
            title = tk.Label(slot, text="", bg=EBONY_2, fg=PAPER, font=self.f_body, anchor="w", justify="left", wraplength=176)
            title.pack(fill="x", padx=10, pady=(2, 0))
            remove = tk.Button(slot, name=f"remove_{i + 1}", text="Remove", bg=EBONY_2, fg="#e9c98f", activebackground="#3a3328",
                               activeforeground="#e9c98f", relief="flat", bd=0, highlightthickness=0, font=self.f_small_b, padx=6, pady=6,
                               cursor="hand2", command=lambda k=i: self._remove_slot(k))
            self.slots.append((slot, title, remove))
        self.place_btn = tk.Button(tray, name="add_to_plan", text="Add to Plan", bg=BRASS, fg=EBONY, activebackground="#a07630",
                                   activeforeground=EBONY, disabledforeground="#6d604a", relief="flat", bd=0,
                                   highlightthickness=0, font=self.f_btn, padx=22, pady=14, cursor="hand2",
                                   command=self.place_order)
        self.place_btn.pack(side="right", padx=22)

    def _remove_slot(self, k):
        if k < len(self.cart):
            mid = self.cart[k]
            self._toggle(mid, self.buttons[mid])

    # ------------------------------------------------------------- state
    def _toggle(self, mid, btn):
        # Tapping again removes the item, so a misclick is always correctable.
        if mid in self.cart:
            self.cart.remove(mid)
            self.events.append({"action": "deselect", "id": mid})
        else:
            if len(self.cart) >= MAX_PICKS:
                self.hint.configure(text="Plan is full — remove one to swap.", fg="#f0b27a")
                return
            self.cart.append(mid)
            self.events.append({"action": "select", "id": mid})
        self._refresh()

    def _refresh(self):
        n = len(self.cart)
        self.cart_lbl.configure(text=f"{n} of {MAX_PICKS} hours")
        self.hint.configure(text="Tap + on a card to add it." if n < MAX_PICKS else "Ready — tap Add to Plan.", fg="#c9bda6")
        for mid, btn in self.buttons.items():
            on = mid in self.cart
            full = n >= MAX_PICKS and not on
            btn.configure(text="✓" if on else "+", bg=BRASS if on else ("#9fb9b1" if full else VERD),
                          fg=EBONY if on else "white")
            self.cards[mid][0].configure(highlightbackground=BRASS if on else RULE, highlightthickness=2 if on else 1)
        for i, (slot, title, remove) in enumerate(self.slots):
            if i < n:
                title.configure(text=_BY_ID[self.cart[i]][2], fg=PAPER, font=self.f_slot)
                remove.pack(anchor="w", padx=4, pady=(0, 2), side="bottom")
                slot.configure(highlightbackground=BRASS)
            else:
                title.configure(text="Empty", fg="#7d7160", font=self.f_body)
                remove.pack_forget()
                slot.configure(highlightbackground="#4a4236")
        self.place_btn.configure(state="normal" if n == MAX_PICKS else "disabled",
                                 bg=BRASS if n == MAX_PICKS else "#5a5040")

    def place_order(self):
        if len(self.cart) != MAX_PICKS:
            return
        chosen = [{"id": mid, "name": _BY_ID[mid][2]} for mid in self.cart]
        os.makedirs(OUTPUT_DIR, exist_ok=True)
        with open(os.path.join(OUTPUT_DIR, "practice_plan.json"), "w", encoding="utf-8") as f:
            json.dump({"persona": os.environ.get("ADHERENCE_PERSONA", "p-268c55cd56"),
                       "plannedCards": chosen,
                       "events": [*self.events,
                                  {"action": "submit", "ids": list(self.cart)}]},
                      f, ensure_ascii=False, indent=2)
        cover = tk.Frame(self.root, bg=IVORY)
        cover.place(relx=0, rely=0, relwidth=1, relheight=1)
        box = tk.Frame(cover, bg=PAPER, highlightthickness=1, highlightbackground=RULE)
        box.place(relx=0.5, rely=0.45, anchor="center", width=560, height=250)
        tk.Frame(box, bg=VERD, height=6).pack(fill="x")
        tk.Label(box, text="♪", bg=PAPER, fg=BRASS, font=_f("Nimbus Roman", 44, "bold")).pack(pady=(18, 0))
        tk.Label(box, text="Practice plan saved", bg=PAPER, fg=INK, font=self.f_done).pack()
        for i, row in enumerate(chosen):
            tk.Label(box, text=f"Hour {i + 1}  ·  {row['name']}", bg=PAPER, fg=MUT, font=self.f_body).pack(pady=(6 if i == 0 else 1, 0))


if __name__ == "__main__":
    root = tk.Tk()
    ScoreRoom(root)
    root.mainloop()
