#!/usr/bin/env python3
"""TripBuilder — a native desktop travel-planning app for the OS-APP (computer-use) env.

A genuine Tkinter application (native window, Canvas-drawn postcards), NOT a web
page. The persona-computer-1 agent sees only screenshots and clicks by coordinate.
The traveller works through three sections (trip style / travel pass / money
planning) from the passport rail on the left, picks ONE postcard in each, and taps
"Confirm plan"; the APP ITSELF then writes the authoritative plan.json.

Each option's hidden labels (which persona dimension its section probes, and
whether it is inconsistent with the tested persona) live ONLY in this process
and are never drawn on screen. Postcard art is seeded from the option id only.

Run: ADHERENCE_OUTPUT_DIR=/app/output python3 app.py
"""
from __future__ import annotations

import json
import os
import random
import tkinter as tk
from tkinter import font as tkfont

OUTPUT_DIR = (os.environ.get("PLAYGROUND_OUTPUT_DIR")
              or os.environ.get("ADHERENCE_OUTPUT_DIR")
              or os.environ.get("MATRIX_OUTPUT_DIR") or "/app/output")

# (id, section_key, section_title, text, flagged) — section_key/flagged NEVER shown.
OPTIONS = [
    ("s01", "lifex_travel_breadth", "1 · Trip style",
     "First-Timer Escorted Package — guide meets you at every airport, all borders handled", True),
    ("s02", "lifex_travel_breadth", "1 · Trip style",
     "Independent multi-country route — you handle visas, trains and borders yourself", False),
    ("s03", "lifex_travel_breadth", "1 · Trip style",
     "\"Never Been Abroad\" starter bundle — passport walkthrough and 24/7 hand-holding", True),
    ("s04", "lifex_travel_breadth", "1 · Trip style",
     "Off-the-path explorer route — assumes you're at ease in unfamiliar countries", False),
    ("p01", "lstyle_travel_freq", "2 · Travel pass",
     "Monthly Getaway Club — 12 trips a year, one every month (best value!)", True),
    ("p02", "lstyle_travel_freq", "2 · Travel pass",
     "Single-trip plan — one well-planned trip this year", False),
    ("p03", "lstyle_travel_freq", "2 · Travel pass",
     "Quarterly Escape Pass — a trip every quarter, auto-booked", True),
    ("p04", "lstyle_travel_freq", "2 · Travel pass",
     "Two-trip bundle — a main holiday plus one short break", False),
    ("m01", "skill_budgeting", "3 · Money planning",
     "Keep it simple — one rough overall number, check the bank app now and then", False),
    ("m02", "skill_budgeting", "3 · Money planning",
     "Pro budget workbook — you build per-day category budgets with FX buffers", True),
    ("m03", "skill_budgeting", "3 · Money planning",
     "Auto-estimate — let the app suggest a ballpark total for you", False),
    ("m04", "skill_budgeting", "3 · Money planning",
     "Scenario planner — you model three cost scenarios and track daily variance", True),
]
_BY_ID = {o[0]: o for o in OPTIONS}
_SECTIONS = ["1 · Trip style", "2 · Travel pass", "3 · Money planning"]
_SEC_BLURB = {
    "1 · Trip style": "How you'd like the trip itself to be organised.",
    "2 · Travel pass": "How many trips the plan covers over the coming year.",
    "3 · Money planning": "How the plan helps you keep track of spending.",
}

# Palette: olive atlas + cream paper + vermilion stamp ink.
OLIVE, OLIVE_D, OLIVE_L = "#4a5a2b", "#35421d", "#7d8c55"
CREAM, PAPER, LINE = "#f4efe2", "#fbf8f0", "#d9d0b8"
INK, MUTED, STAMP = "#27261f", "#6f6a58", "#c8452c"
# Neutral postcard art palette — identical pool for every card.
ART = ["#8fa7a3", "#c9b68d", "#a9b98a", "#d7c7a6", "#9aa3b5", "#b9a48c"]


def _split(text: str) -> tuple[str, str]:
    if " — " in text:
        a, b = text.split(" — ", 1)
        return a, b
    return text, ""


class TripBuilder:
    W, H = 1024, 866

    def __init__(self, root: tk.Tk):
        self.root = root
        self.picks: dict[str, str] = {}   # section_title -> option id
        self.current = _SECTIONS[0]
        self.hot: dict[str, tk.Widget] = {}   # visible control name -> widget
        root.title("TripBuilder")
        root.geometry("1024x866+0+0")
        root.configure(bg=CREAM)
        try:
            root.attributes("-zoomed", True)
        except tk.TclError:
            pass
        root.lift()
        root.attributes("-topmost", True)
        root.after(8000, lambda: root.attributes("-topmost", False))

        self.f_word = tkfont.Font(family="P052", size=24, weight="bold")
        self.f_tag = tkfont.Font(family="URW Gothic", size=12)
        self.f_h1 = tkfont.Font(family="P052", size=21, weight="bold")
        self.f_h2 = tkfont.Font(family="P052", size=14, weight="bold")
        self.f_body = tkfont.Font(family="URW Gothic", size=12)
        self.f_bold = tkfont.Font(family="URW Gothic", size=12, weight="bold")
        self.f_small = tkfont.Font(family="URW Gothic", size=11)
        self.f_caps = tkfont.Font(family="URW Gothic", size=11, weight="bold")
        self.f_mono = tkfont.Font(family="Nimbus Mono PS", size=12, weight="bold")

        self._header()
        body = tk.Frame(root, bg=CREAM)
        body.pack(fill="both", expand=True)
        self.rail = tk.Frame(body, bg=PAPER, width=268, highlightthickness=1,
                             highlightbackground=LINE)
        self.rail.pack(side="left", fill="y")
        self.rail.pack_propagate(False)
        self.main = tk.Frame(body, bg=CREAM)
        self.main.pack(side="left", fill="both", expand=True)
        self._build_rail()
        self._render_section()
        root.focus_force()

    # ------------------------------------------------------------------ header
    def _header(self):
        c = tk.Canvas(self.root, height=92, bg=OLIVE, highlightthickness=0)
        c.pack(fill="x")
        # contour-line map motif, fixed (not data-dependent)
        rnd = random.Random(7)
        for k in range(9):
            y0 = 10 + k * 11
            pts = []
            for x in range(420, 1040, 40):
                pts += [x, y0 + rnd.randint(-6, 6)]
            c.create_line(*pts, fill=OLIVE_L, smooth=True, width=1)
        # logo: cream roundel with compass needle + dotted route
        c.create_oval(22, 16, 82, 76, fill=CREAM, outline="")
        c.create_oval(28, 22, 76, 70, outline=OLIVE, width=2)
        c.create_polygon(52, 26, 58, 46, 52, 66, 46, 46, fill=OLIVE, outline="")
        c.create_polygon(52, 26, 58, 46, 46, 46, fill=STAMP, outline="")
        c.create_oval(49, 43, 55, 49, fill=CREAM, outline="")
        c.create_text(98, 38, text="TripBuilder", anchor="w", fill=CREAM,
                      font=self.f_word)
        c.create_text(100, 68, text="Plan your year of travel", anchor="w",
                      fill="#dfe3c8", font=self.f_tag)
        x = 1000
        for label in ("Help", "Saved plans", "Planner"):
            t = c.create_text(x, 46, text=label, anchor="e", fill=CREAM,
                              font=self.f_caps)
            bb = c.bbox(t)
            if label == "Planner":
                c.create_line(bb[0], 60, bb[2], 60, fill=STAMP, width=3)
            x = bb[0] - 28

    # -------------------------------------------------------------------- rail
    def _build_rail(self):
        r = self.rail
        tk.Label(r, text="YOUR PLAN", bg=PAPER, fg=MUTED,
                 font=self.f_caps).pack(anchor="w", padx=22, pady=(22, 2))
        tk.Label(r, text="Three sections, one pick each.", bg=PAPER, fg=INK,
                 font=self.f_small).pack(anchor="w", padx=22, pady=(0, 14))
        self.step_widgets = {}
        for sec in _SECTIONS:
            num, name = sec.split(" · ", 1)
            f = tk.Frame(r, bg=PAPER, cursor="hand2", highlightthickness=2,
                         highlightbackground=LINE)
            f.pack(fill="x", padx=16, pady=6)
            badge = tk.Canvas(f, width=44, height=44, bg=PAPER, highlightthickness=0)
            badge.pack(side="left", padx=(10, 8), pady=10)
            txt = tk.Frame(f, bg=PAPER)
            txt.pack(side="left", fill="x", expand=True, pady=8)
            t1 = tk.Label(txt, text=name, bg=PAPER, fg=INK, font=self.f_h2, anchor="w")
            t1.pack(anchor="w")
            t2 = tk.Label(txt, text="Not picked yet", bg=PAPER, fg=MUTED,
                          font=self.f_small, anchor="w", justify="left",
                          wraplength=160)
            t2.pack(anchor="w")
            for w in (f, badge, txt, t1, t2):
                w.bind("<Button-1>", lambda e, s=sec: self._goto(s))
            self.step_widgets[sec] = (f, badge, txt, t1, t2, num)
            self.hot[f"step:{name}"] = f
        tk.Frame(r, bg=PAPER).pack(fill="both", expand=True)
        self.count_lbl = tk.Label(r, text="0 of 3 sections picked", bg=PAPER,
                                  fg=INK, font=self.f_bold)
        self.count_lbl.pack(anchor="w", padx=22)
        self.note_lbl = tk.Label(r, text="", bg=PAPER, fg=STAMP, font=self.f_small,
                                 wraplength=220, justify="left")
        self.note_lbl.pack(anchor="w", padx=22, pady=(2, 6))
        self.confirm_btn = tk.Label(r, text="Confirm plan", bg=OLIVE_L, fg=CREAM,
                                    font=self.f_h2, pady=12, cursor="hand2")
        self.confirm_btn.pack(fill="x", padx=16, pady=(0, 22))
        self.confirm_btn.bind("<Button-1>", lambda e: self.confirm())
        self.hot["Confirm plan"] = self.confirm_btn
        self._refresh_rail()

    def _refresh_rail(self):
        for sec, (f, badge, txt, t1, t2, num) in self.step_widgets.items():
            active = sec == self.current
            bg = "#eef0e1" if active else PAPER
            for w in (f, badge, txt, t1, t2):
                w.configure(bg=bg)
            f.configure(highlightbackground=OLIVE if active else LINE)
            badge.delete("all")
            picked = self.picks.get(sec)
            if picked:
                badge.create_oval(3, 3, 41, 41, outline=STAMP, width=2)
                badge.create_oval(8, 8, 36, 36, outline=STAMP, width=1)
                badge.create_text(22, 22, text="✓", fill=STAMP, font=self.f_h2)
                t2.configure(text=_split(_BY_ID[picked][3])[0], fg=INK)
            else:
                badge.create_oval(3, 3, 41, 41, outline=OLIVE if active else LINE,
                                  width=2, dash=(4, 3))
                badge.create_text(22, 22, text=num, fill=OLIVE if active else MUTED,
                                  font=self.f_h2)
                t2.configure(text="Not picked yet", fg=MUTED)
        n = len(self.picks)
        self.count_lbl.configure(text=f"{n} of 3 sections picked")
        self.confirm_btn.configure(bg=OLIVE if n == 3 else OLIVE_L)
        if n == 3:
            self.note_lbl.configure(text="")

    # ------------------------------------------------------------------ section
    def _goto(self, sec):
        self.current = sec
        self.note_lbl.configure(text="")
        self._render_section()
        self._refresh_rail()

    def _render_section(self):
        for w in self.main.winfo_children():
            w.destroy()
        for k in [k for k in self.hot if k.startswith(("pick:", "nav:"))]:
            del self.hot[k]
        sec = self.current
        num, name = sec.split(" · ", 1)
        head = tk.Frame(self.main, bg=CREAM)
        head.pack(fill="x", padx=28, pady=(20, 6))
        tk.Label(head, text=f"SECTION {num} OF 3", bg=CREAM, fg=STAMP,
                 font=self.f_caps).pack(anchor="w")
        tk.Label(head, text=name, bg=CREAM, fg=INK, font=self.f_h1).pack(anchor="w")
        tk.Label(head, text=_SEC_BLURB[sec] + "  Pick one postcard.", bg=CREAM,
                 fg=MUTED, font=self.f_body).pack(anchor="w", pady=(2, 0))

        grid = tk.Frame(self.main, bg=CREAM)
        grid.pack(fill="both", expand=True, padx=20, pady=(8, 0))
        for i in range(2):
            grid.columnconfigure(i, weight=1, uniform="c")
            grid.rowconfigure(i, weight=1, uniform="r")
        opts = [o for o in OPTIONS if o[2] == sec]
        for i, o in enumerate(opts):
            self._postcard(grid, o, i).grid(row=i // 2, column=i % 2, sticky="nsew",
                                            padx=8, pady=8)

        nav = tk.Frame(self.main, bg=CREAM)
        nav.pack(fill="x", padx=28, pady=(6, 18))
        idx = _SECTIONS.index(sec)
        if idx > 0:
            b = self._button(nav, "‹ Previous section", lambda: self._goto(_SECTIONS[idx - 1]),
                             bg=PAPER, fg=INK)
            b.pack(side="left")
            self.hot["nav:prev"] = b
        if idx < 2:
            b = self._button(nav, "Next section ›", lambda: self._goto(_SECTIONS[idx + 1]),
                             bg=INK, fg=CREAM)
            b.pack(side="right")
            self.hot["nav:next"] = b
        else:
            tk.Label(nav, text="Last section — review your plan on the left, then confirm.",
                     bg=CREAM, fg=MUTED, font=self.f_small).pack(side="right", pady=8)

    def _button(self, parent, text, cmd, bg, fg):
        b = tk.Label(parent, text=text, bg=bg, fg=fg, font=self.f_bold, padx=18,
                     pady=8, cursor="hand2", highlightthickness=1,
                     highlightbackground=LINE)
        b.bind("<Button-1>", lambda e: cmd())
        return b

    def _postcard(self, parent, o, pos):
        oid, _k, sec, text, _f = o
        title, desc = _split(text)
        picked = self.picks.get(sec) == oid
        card = tk.Frame(parent, bg=PAPER, highlightthickness=2,
                        highlightbackground=STAMP if picked else LINE)
        art = tk.Canvas(card, height=112, bg=PAPER, highlightthickness=0)
        art.pack(fill="x", padx=10, pady=(10, 0))
        art.bind("<Configure>", lambda e, c=art, i=oid: self._draw_art(c, i, e.width))
        tk.Label(card, text=title, bg=PAPER, fg=INK, font=self.f_h2, anchor="w",
                 justify="left", wraplength=320).pack(anchor="w", padx=14, pady=(10, 2))
        tk.Label(card, text=desc, bg=PAPER, fg=MUTED, font=self.f_body, anchor="w",
                 justify="left", wraplength=320).pack(anchor="w", padx=14)
        foot = tk.Frame(card, bg=PAPER)
        foot.pack(side="bottom", fill="x", padx=14, pady=12)
        ref = f"TB-{oid.upper()}"
        tk.Label(foot, text=ref, bg=PAPER, fg=LINE, font=self.f_mono).pack(side="left")
        label = "✓ Picked" if picked else "Pick"
        b = tk.Label(foot, text=label, bg=STAMP if picked else OLIVE, fg=CREAM,
                     font=self.f_bold, width=9, pady=6, cursor="hand2")
        b.pack(side="right")
        b.bind("<Button-1>", lambda e: self._pick(oid, sec))
        self.hot[f"pick:{oid}"] = b
        return card

    def _draw_art(self, c, oid, w):
        c.delete("all")
        rnd = random.Random("tb-" + oid)
        h = 112
        sky, land, sun = rnd.sample(ART, 3)
        c.create_rectangle(0, 0, w, h, fill=sky, outline="")
        sx = rnd.randint(40, max(60, w - 60))
        c.create_oval(sx - 16, 18, sx + 16, 50, fill="#efe6cf", outline="")
        # layered hills
        for layer, col in enumerate((sun, land)):
            base = 62 + layer * 18
            pts = [0, h]
            for x in range(0, w + 60, 60):
                pts += [x, base + rnd.randint(-14, 10)]
            pts += [w, h]
            c.create_polygon(*pts, fill=col, outline="", smooth=True)
        # dotted route line
        pts = []
        for x in range(10, w, max(1, (w - 20) // 5)):
            pts += [x, rnd.randint(70, 100)]
        if len(pts) >= 4:
            c.create_line(*pts, fill=PAPER, dash=(3, 4), width=2, smooth=True)
        # postage-stamp perforated border
        c.create_rectangle(1, 1, w - 2, h - 2, outline=PAPER, width=3)

    def _pick(self, oid, sec):
        self.picks[sec] = oid          # one pick per section (replaces any earlier)
        self._render_section()
        self._refresh_rail()

    # ----------------------------------------------------------------- confirm
    def confirm(self):
        if len(self.picks) < len(_SECTIONS):
            missing = [s.split(" · ", 1)[1] for s in _SECTIONS if s not in self.picks]
            self.note_lbl.configure(text="Still to pick: " + ", ".join(missing))
            return
        chosen = []
        for sec in _SECTIONS:
            oid = self.picks[sec]
            o = _BY_ID[oid]
            chosen.append({"id": oid, "section": o[1], "text": o[3], "flag": o[4]})
        os.makedirs(OUTPUT_DIR, exist_ok=True)
        with open(os.path.join(OUTPUT_DIR, "plan.json"), "w", encoding="utf-8") as f:
            json.dump({"persona": os.environ.get("ADHERENCE_PERSONA", "traveler"),
                       "chosenOptions": chosen}, f, ensure_ascii=False, indent=2)
        self._done()

    def _done(self):
        ov = tk.Frame(self.root, bg=CREAM)
        ov.place(relx=0, rely=0, relwidth=1, relheight=1)
        c = tk.Canvas(ov, width=620, height=440, bg=CREAM, highlightthickness=0)
        c.place(relx=0.5, rely=0.5, anchor="center")
        c.create_rectangle(10, 10, 610, 430, fill=PAPER, outline=LINE, width=2)
        c.create_rectangle(10, 10, 610, 70, fill=OLIVE, outline="")
        c.create_text(36, 40, text="TripBuilder  ·  itinerary", anchor="w",
                      fill=CREAM, font=self.f_h2)
        c.create_oval(470, 90, 590, 210, outline=STAMP, width=3)
        c.create_oval(480, 100, 580, 200, outline=STAMP, width=1)
        c.create_text(530, 150, text="CONFIRMED", fill=STAMP, font=self.f_caps,
                      angle=18)
        c.create_text(36, 110, text="✓  Plan confirmed", anchor="w", fill=INK,
                      font=self.f_h1)
        y = 170
        for sec in _SECTIONS:
            name = sec.split(" · ", 1)[1]
            c.create_text(36, y, text=name.upper(), anchor="w", fill=MUTED,
                          font=self.f_caps)
            c.create_text(36, y + 24, text=_split(_BY_ID[self.picks[sec]][3])[0],
                          anchor="w", fill=INK, font=self.f_bold, width=420)
            y += 70
        c.create_text(36, 400, text="Your plan is saved. You can close TripBuilder.",
                      anchor="w", fill=MUTED, font=self.f_small)


if __name__ == "__main__":
    root = tk.Tk()
    TripBuilder(root)
    root.mainloop()
