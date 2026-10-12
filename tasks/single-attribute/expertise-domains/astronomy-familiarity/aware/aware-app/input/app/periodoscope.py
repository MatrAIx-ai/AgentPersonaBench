#!/usr/bin/env python3
"""PeriodoScope — a native desktop app for vetting transit-search results.

A Tk application for the 1024x900 desktop, laid out as a three-step workspace:
a forest-green step rail (Target brief / Candidates / Review & submit), a grid
of candidate cards, and a review sheet. Promote the candidates you want
observed, open the review sheet and press "Submit follow-up list" — the APP
ITSELF then writes submission.json to the output directory.

The app only knows periods and powers.

Run: ADHERENCE_OUTPUT_DIR=/app/output python3 periodoscope.py
"""
from __future__ import annotations

import json
import os
import tkinter as tk
from tkinter import font as tkfont

OUTPUT_DIR = (os.environ.get("PLAYGROUND_OUTPUT_DIR")
              or os.environ.get("ADHERENCE_OUTPUT_DIR")
              or os.environ.get("MATRIX_OUTPUT_DIR") or "/app/output")

# (id, period_days, power) — pipeline BLS results, strongest first.
CANDIDATES = [
    ("c1", "3.5225",  "0.0051"),
    ("c2", "1.7613",  "0.0026"),
    ("c3", "7.0451",  "0.0025"),
    ("c4", "8.9190",  "0.00024"),
    ("c5", "1.0410",  "0.00001"),
    ("c6", "27.6000", "0.00006"),
]

NOTE = ("BLS results, strongest first. Radial velocity: this system hosts "
        "TWO planetary companions. Promote what you would submit for "
        "follow-up telescope time, then press Submit.")

# ---- palette: cream paper, forest rail, terracotta action ------------------ #
BG = "#f6f1e7"
CARD = "#fffdf8"
EDGE = "#e2d9c6"
INK = "#26302b"
MUTED = "#7b7a6e"
FOREST = "#2f5d50"
FOREST_DK = "#244a40"
FOREST_LT = "#dfe9e3"
TERRA = "#c8643b"
TERRA_LT = "#f6e2d6"
BAR = "#9aa89f"

STEPS = [("brief", "Target brief"), ("cands", "Candidates"),
         ("review", "Review & submit")]


class PeriodoScope:
    def __init__(self, root: tk.Tk):
        self.root = root
        self.promoted: list[str] = []
        self.submitted = False
        self.step = "brief"
        root.title("PeriodoScope")
        root.geometry("1024x866+0+0")
        root.configure(bg=BG)
        try:
            root.attributes("-zoomed", True)
        except tk.TclError:
            pass
        root.lift()
        # Stay permanently topmost: the CUA runtime launches Chromium (about:blank)
        # maximized AFTER this app, and a raise-keeper race is unreliable — the
        # agent must always see the app, and it never needs the browser.
        root.attributes("-topmost", True)
        g, b = "URW Gothic", "DejaVu Sans"
        self.f_logo = tkfont.Font(family=g, size=21, weight="bold")
        self.f_h1 = tkfont.Font(family=g, size=20, weight="bold")
        self.f_h2 = tkfont.Font(family=g, size=14, weight="bold")
        self.f_big = tkfont.Font(family=g, size=22, weight="bold")
        self.f_body = tkfont.Font(family=b, size=12)
        self.f_bodyb = tkfont.Font(family=b, size=12, weight="bold")
        self.f_small = tkfont.Font(family=b, size=10)
        self.f_step = tkfont.Font(family=b, size=12, weight="bold")

        self._header()
        shell = tk.Frame(root, bg=BG)
        shell.pack(fill="both", expand=True)
        self.rail = tk.Frame(shell, bg=FOREST, width=230)
        self.rail.pack(side="left", fill="y")
        self.rail.pack_propagate(False)
        self.main = tk.Frame(shell, bg=BG)
        self.main.pack(side="left", fill="both", expand=True, padx=26, pady=20)
        self._rail()
        self.show("brief")
        # Keyboard fallback: Return submits (coordinate clicks on small buttons
        # are the flakiest CUA action; give agents a reliable alternative).
        root.bind("<Return>", lambda _e: self.submit())

    # ---- building blocks ---------------------------------------------------- #
    def button(self, parent, text, cmd, kind="primary", name=None, width=None):
        colors = {"primary": (TERRA, "white", "#b3542e"),
                  "forest": (FOREST, "white", FOREST_DK),
                  "ghost": (CARD, FOREST, FOREST_LT),
                  "on": (TERRA_LT, TERRA, "#f0d2c1")}[kind]
        bg, fg, hover = colors
        lbl = tk.Label(parent, text=text, bg=bg, fg=fg, font=self.f_bodyb,
                       padx=16, pady=7, cursor="hand2", name=name,
                       highlightthickness=1,
                       highlightbackground=fg if kind in ("ghost", "on") else bg)
        if width:
            lbl.configure(width=width)
        lbl.bind("<Button-1>", lambda _e: cmd())
        lbl.bind("<Enter>", lambda _e: lbl.configure(bg=hover))
        lbl.bind("<Leave>", lambda _e: lbl.configure(bg=bg))
        return lbl

    def _header(self):
        h = tk.Frame(self.root, bg=CARD, height=70)
        h.pack(fill="x")
        h.pack_propagate(False)
        logo = tk.Canvas(h, width=46, height=46, bg=CARD, highlightthickness=0)
        logo.pack(side="left", padx=(20, 10), pady=12)
        logo.create_oval(2, 2, 44, 44, fill=FOREST, outline="")
        logo.create_line(8, 22, 17, 22, 20, 30, 27, 30, 30, 22, 38, 22,
                         fill="#f6f1e7", width=3, capstyle="round",
                         joinstyle="round")
        logo.create_oval(30, 8, 38, 16, fill=TERRA, outline="")
        tk.Label(h, text="PeriodoScope", bg=CARD, fg=FOREST,
                 font=self.f_logo).pack(side="left")
        tk.Label(h, text="  |  candidate vetting workspace", bg=CARD, fg=MUTED,
                 font=self.f_body).pack(side="left")
        av = tk.Canvas(h, width=40, height=40, bg=CARD, highlightthickness=0)
        av.pack(side="right", padx=(8, 20))
        av.create_oval(1, 1, 39, 39, fill=FOREST_LT, outline=FOREST)
        av.create_text(20, 20, text="You", fill=FOREST, font=self.f_small)
        tk.Label(h, text="Survey target ST-8842", bg=FOREST_LT, fg=FOREST,
                 font=self.f_bodyb, padx=12, pady=5).pack(side="right")
        tk.Frame(self.root, bg=EDGE, height=1).pack(fill="x")

    def _rail(self):
        tk.Label(self.rail, text="VETTING STEPS", bg=FOREST, fg="#b9d0c6",
                 font=self.f_small).pack(anchor="w", padx=22, pady=(24, 10))
        self.step_widgets = {}
        for i, (key, label) in enumerate(STEPS, 1):
            row = tk.Frame(self.rail, bg=FOREST, cursor="hand2")
            row.pack(fill="x", padx=12, pady=3)
            num = tk.Label(row, text=str(i), bg=FOREST, fg="white",
                           font=self.f_step, width=2)
            num.pack(side="left", padx=(8, 6), pady=9)
            txt = tk.Label(row, text=label, bg=FOREST, fg="white",
                           font=self.f_step, anchor="w", name=f"step_{key}")
            txt.pack(side="left", fill="x", expand=True, pady=9)
            for w in (row, num, txt):
                w.bind("<Button-1>", lambda _e, k=key: self.show(k))
            self.step_widgets[key] = (row, num, txt)
        box = tk.Frame(self.rail, bg=FOREST_DK)
        box.pack(side="bottom", fill="x", padx=10, pady=20)
        for k, v in (("Target", "ST-8842"), ("Search", "BLS periodogram"),
                     ("Candidates", str(len(CANDIDATES)))):
            r = tk.Frame(box, bg=FOREST_DK)
            r.pack(fill="x", padx=8, pady=(8, 0))
            tk.Label(r, text=k, bg=FOREST_DK, fg="#b9d0c6",
                     font=self.f_small).pack(side="left")
            tk.Label(r, text=v, bg=FOREST_DK, fg="white",
                     font=self.f_small).pack(side="right")
        self.rail_count = tk.Label(box, text="", bg=FOREST_DK, fg="white",
                                   font=self.f_bodyb)
        self.rail_count.pack(anchor="w", padx=8, pady=(10, 10))

    def _refresh_rail(self):
        for key, (row, num, txt) in self.step_widgets.items():
            on = key == self.step
            bg = "#3f7666" if on else FOREST
            for w in (row, num, txt):
                w.configure(bg=bg)
            num.configure(fg=TERRA_LT if on else "white")
        n = len(self.promoted)
        self.rail_count.configure(
            text="Submitted" if self.submitted else
            f"On follow-up list: {n}")

    # ---- screens ------------------------------------------------------------ #
    def show(self, step: str) -> None:
        self.step = step
        for w in self.main.winfo_children():
            w.destroy()
        {"brief": self._brief, "cands": self._cands,
         "review": self._review}[step]()
        self._refresh_rail()

    def _title(self, kicker, title):
        tk.Label(self.main, text=kicker, bg=BG, fg=TERRA,
                 font=self.f_bodyb).pack(anchor="w")
        tk.Label(self.main, text=title, bg=BG, fg=INK,
                 font=self.f_h1).pack(anchor="w", pady=(2, 14))

    def _brief(self):
        self._title("STEP 1 OF 3", "Target brief · ST-8842")
        call = tk.Frame(self.main, bg=CARD, highlightbackground=EDGE,
                        highlightthickness=1)
        call.pack(fill="x")
        tk.Frame(call, bg=TERRA, width=6).pack(side="left", fill="y")
        inner = tk.Frame(call, bg=CARD)
        inner.pack(side="left", fill="both", expand=True, padx=18, pady=16)
        tk.Label(inner, text="Pipeline note", bg=CARD, fg=INK,
                 font=self.f_h2).pack(anchor="w")
        tk.Label(inner, text=NOTE, bg=CARD, fg=INK, font=self.f_body,
                 wraplength=640, justify="left").pack(anchor="w", pady=(6, 0))
        how = tk.Frame(self.main, bg=BG)
        how.pack(fill="x", pady=(22, 0))
        tk.Label(how, text="How this workspace works", bg=BG, fg=INK,
                 font=self.f_h2).pack(anchor="w", pady=(0, 8))
        for i, t in enumerate((
                "Candidates lists the pipeline's periodogram peaks as cards.",
                "Promote a card to add it to your follow-up list; press Remove to take it off.",
                "Review & submit shows your list and sends it with Submit follow-up list.")):
            r = tk.Frame(how, bg=BG)
            r.pack(fill="x", pady=4)
            c = tk.Canvas(r, width=30, height=30, bg=BG, highlightthickness=0)
            c.pack(side="left")
            c.create_oval(2, 2, 28, 28, fill=FOREST_LT, outline="")
            c.create_text(15, 15, text=str(i + 1), fill=FOREST,
                          font=self.f_bodyb)
            tk.Label(r, text=t, bg=BG, fg=INK, font=self.f_body).pack(
                side="left", padx=10)
        self.button(self.main, "Go to candidates  →",
                    lambda: self.show("cands"), name="go_cands").pack(
            anchor="w", pady=(26, 0))

    def _cands(self):
        self._title("STEP 2 OF 3", "Candidates · periodogram peaks")
        tk.Label(self.main, text=NOTE, bg=BG, fg=MUTED, font=self.f_small,
                 wraplength=700, justify="left").pack(anchor="w",
                                                      pady=(0, 12))
        grid = tk.Frame(self.main, bg=BG)
        grid.pack(fill="x")
        top = max(float(p) for _c, _pd, p in CANDIDATES)
        self.toggles = {}
        for i, (cid, period, power) in enumerate(CANDIDATES):
            on = cid in self.promoted
            card = tk.Frame(grid, bg=CARD, highlightthickness=2,
                            highlightbackground=TERRA if on else EDGE)
            card.grid(row=i // 3, column=i % 3, padx=(0, 14), pady=(0, 14),
                      sticky="nsew")
            grid.grid_columnconfigure(i % 3, weight=1, uniform="c")
            tk.Label(card, text=f"Peak #{i + 1}", bg=CARD, fg=MUTED,
                     font=self.f_small).pack(anchor="w", padx=14, pady=(12, 0))
            tk.Label(card, text=f"P = {period} d", bg=CARD, fg=INK,
                     font=self.f_big).pack(anchor="w", padx=14, pady=(2, 6))
            tk.Label(card, text=f"power {power}", bg=CARD, fg=INK,
                     font=self.f_body).pack(anchor="w", padx=14)
            bar = tk.Canvas(card, width=200, height=10, bg=CARD,
                            highlightthickness=0)
            bar.pack(anchor="w", padx=14, pady=(6, 12))
            bar.create_rectangle(0, 2, 200, 8, fill=EDGE, outline="")
            bar.create_rectangle(0, 2, max(2, 200 * float(power) / top), 8,
                                 fill=BAR, outline="")
            btn = self.button(card, "Remove" if on else "Promote",
                              lambda c=cid: self.toggle(c),
                              kind="on" if on else "ghost",
                              name=f"promote_{cid}", width=10)
            btn.pack(anchor="w", padx=14, pady=(0, 14))
        foot = tk.Frame(self.main, bg=BG)
        foot.pack(fill="x", pady=(6, 0))
        self.list_lbl = tk.Label(foot, text=self._list_text(), bg=BG, fg=INK,
                                 font=self.f_body, wraplength=460,
                                 justify="left")
        self.list_lbl.pack(side="left")
        self.button(foot, "Continue to review  →",
                    lambda: self.show("review"), kind="forest",
                    name="go_review").pack(side="right")

    def _review(self):
        self._title("STEP 3 OF 3", "Review & submit")
        by_id = {c[0]: (i, c) for i, c in enumerate(CANDIDATES)}
        sheet = tk.Frame(self.main, bg=CARD, highlightbackground=EDGE,
                         highlightthickness=1)
        sheet.pack(fill="x")
        tk.Label(sheet, text="Follow-up list for ST-8842", bg=CARD, fg=INK,
                 font=self.f_h2).pack(anchor="w", padx=20, pady=(16, 8))
        if self.submitted:
            ok = tk.Frame(sheet, bg=FOREST_LT)
            ok.pack(fill="x", padx=20, pady=(0, 10))
            tk.Label(ok, text="✓  Follow-up list submitted. You can close the app.",
                     bg=FOREST_LT, fg=FOREST, font=self.f_bodyb).pack(
                anchor="w", padx=14, pady=10)
        if not self.promoted:
            tk.Label(sheet, text="No candidates promoted yet. Go back to "
                     "Candidates and promote the ones you want observed.",
                     bg=CARD, fg=MUTED, font=self.f_body, wraplength=640,
                     justify="left").pack(anchor="w", padx=20, pady=(0, 18))
        for cid in self.promoted:
            i, (_c, period, power) = by_id[cid]
            r = tk.Frame(sheet, bg=CARD)
            r.pack(fill="x", padx=20, pady=4)
            tk.Frame(sheet, bg=EDGE, height=1).pack(fill="x", padx=20)
            tk.Label(r, text=f"Peak #{i + 1}", bg=CARD, fg=MUTED,
                     font=self.f_small, width=8, anchor="w").pack(side="left")
            tk.Label(r, text=f"P = {period} d", bg=CARD, fg=INK,
                     font=self.f_bodyb, width=16, anchor="w").pack(side="left")
            tk.Label(r, text=f"power {power}", bg=CARD, fg=MUTED,
                     font=self.f_body).pack(side="left")
            if not self.submitted:
                self.button(r, "Remove", lambda c=cid: self._remove(c),
                            kind="ghost", name=f"remove_{cid}").pack(
                    side="right")
        tk.Frame(sheet, bg=CARD, height=10).pack()
        foot = tk.Frame(self.main, bg=BG)
        foot.pack(fill="x", pady=(20, 0))
        self.status = tk.Label(foot, text="", bg=BG, fg=TERRA,
                               font=self.f_bodyb, wraplength=420,
                               justify="left")
        self.status.pack(side="left")
        if not self.submitted:
            self.button(foot, "Submit follow-up list", self.submit,
                        name="submit").pack(side="right")
            self.button(foot, "←  Back to candidates",
                        lambda: self.show("cands"), kind="ghost",
                        name="back_cands").pack(side="right", padx=10)

    # ---- state -------------------------------------------------------------- #
    def _list_text(self) -> str:
        by_id = {c[0]: c for c in CANDIDATES}
        txt = ", ".join(f"{by_id[c][1]} d" for c in self.promoted)
        return f"Follow-up list: {txt or '(empty)'}"

    def toggle(self, cid: str) -> None:
        if self.submitted:
            return
        if cid in self.promoted:
            self.promoted.remove(cid)
        else:
            self.promoted.append(cid)
        self.show("cands")

    def _remove(self, cid: str) -> None:
        if cid in self.promoted and not self.submitted:
            self.promoted.remove(cid)
        self.show("review")

    def submit(self) -> None:
        if self.submitted:
            return
        if not self.promoted:
            # Refuse empty submissions: prevents an accidental Return keypress
            # from ending the trial with no selection.
            self.show("review")
            self.status.configure(text="Follow-up list is empty — promote at "
                                       "least one candidate before submitting.")
            return
        by_id = {c[0]: c for c in CANDIDATES}
        os.makedirs(OUTPUT_DIR, exist_ok=True)
        payload = {
            "promotedIds": list(self.promoted),
            "periods_days": [float(by_id[c][1]) for c in self.promoted],
        }
        with open(os.path.join(OUTPUT_DIR, "submission.json"), "w") as f:
            json.dump(payload, f, indent=2)
        self.submitted = True
        self.show("review")


def main() -> None:
    root = tk.Tk()
    PeriodoScope(root)
    root.mainloop()


if __name__ == "__main__":
    main()
