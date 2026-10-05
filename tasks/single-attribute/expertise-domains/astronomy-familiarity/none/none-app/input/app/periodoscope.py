#!/usr/bin/env python3
"""PeriodoScope — a native desktop app for vetting transit-search results.

A Tk triage board for the 1024x900 desktop: a charcoal header, the pipeline's
results column on the left and a follow-up list column on the right. Move the
candidates you want observed across with "Promote", then press "Submit
follow-up list" — the APP ITSELF then writes submission.json to the output
directory.

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

# ---- palette: sand board, charcoal, mustard -------------------------------- #
SAND = "#efe9dc"
COL = "#e3dccb"
CARD = "#fbf8f1"
EDGE = "#cfc6b0"
CHAR = "#2b2a28"
CHAR2 = "#3b3a36"
MUTED = "#7d776a"
MUSTARD = "#d9a21b"
MUSTARD_DK = "#b8860f"
MUSTARD_LT = "#f7e7b8"
GHOST = "#d8d0bd"


class PeriodoScope:
    def __init__(self, root: tk.Tk):
        self.root = root
        self.promoted: list[str] = []
        self.submitted = False
        self.msg = ""
        root.title("PeriodoScope")
        root.geometry("1024x866+0+0")
        root.configure(bg=SAND)
        try:
            root.attributes("-zoomed", True)
        except tk.TclError:
            pass
        root.lift()
        # Stay permanently topmost: the CUA runtime launches Chromium (about:blank)
        # maximized AFTER this app, and a raise-keeper race is unreliable — the
        # agent must always see the app, and it never needs the browser.
        root.attributes("-topmost", True)
        n, s = "Liberation Sans Narrow", "Liberation Sans"
        self.f_logo = tkfont.Font(family=n, size=22, weight="bold")
        self.f_col = tkfont.Font(family=n, size=16, weight="bold")
        self.f_per = tkfont.Font(family=n, size=19, weight="bold")
        self.f_ui = tkfont.Font(family=s, size=12)
        self.f_uib = tkfont.Font(family=s, size=12, weight="bold")
        self.f_sm = tkfont.Font(family=s, size=10)
        self.f_smb = tkfont.Font(family=s, size=10, weight="bold")

        self._header()
        brief = tk.Frame(root, bg=SAND)
        brief.pack(fill="x", padx=22, pady=(14, 4))
        pin = tk.Canvas(brief, width=26, height=26, bg=SAND,
                        highlightthickness=0)
        pin.pack(side="left", anchor="n", pady=2)
        pin.create_oval(3, 3, 23, 23, fill=MUSTARD, outline="")
        pin.create_text(13, 13, text="i", fill=CHAR, font=self.f_uib)
        tk.Label(brief, text=NOTE, bg=SAND, fg=CHAR, font=self.f_ui,
                 wraplength=900, justify="left").pack(side="left", padx=10)
        self.board = tk.Frame(root, bg=SAND)
        self.board.pack(fill="both", expand=True, padx=22, pady=(8, 16))
        self.render()
        # Keyboard fallback: Return submits (coordinate clicks on small buttons
        # are the flakiest CUA action; give agents a reliable alternative).
        root.bind("<Return>", lambda _e: self.submit())

    def _header(self):
        h = tk.Frame(self.root, bg=CHAR, height=64)
        h.pack(fill="x")
        h.pack_propagate(False)
        c = tk.Canvas(h, width=44, height=40, bg=CHAR, highlightthickness=0)
        c.pack(side="left", padx=(22, 10))
        for i, (x0, x1) in enumerate(((2, 13), (16, 27), (30, 41))):
            c.create_rectangle(x0, 4, x1, 36, fill=CHAR2, outline="")
            c.create_rectangle(x0, 4 + i * 9, x1, 12 + i * 9,
                               fill=MUSTARD if i == 2 else "#8c8577",
                               outline="")
        tk.Label(h, text="PeriodoScope", bg=CHAR, fg="white",
                 font=self.f_logo).pack(side="left")
        tk.Label(h, text="TRIAGE BOARD", bg=CHAR, fg=MUSTARD,
                 font=self.f_smb).pack(side="left", padx=12, pady=(8, 0))
        for t in ("ST-8842", "BLS search"):
            tk.Label(h, text=t, bg=CHAR2, fg="#e9e4d8", font=self.f_smb,
                     padx=10, pady=4).pack(side="right", padx=(0, 22 if t == "ST-8842" else 10))
        tk.Frame(self.root, bg=MUSTARD, height=4).pack(fill="x")

    def button(self, parent, text, cmd, kind="dark", name=""):
        bg, fg, hov = {"dark": (CHAR, "white", CHAR2),
                       "mustard": (MUSTARD, CHAR, MUSTARD_DK),
                       "line": (CARD, CHAR, MUSTARD_LT)}[kind]
        b = tk.Label(parent, text=text, bg=bg, fg=fg, font=self.f_uib,
                     padx=14, pady=7, cursor="hand2", **({"name": name} if name else {}),
                     highlightthickness=1, highlightbackground=CHAR)
        b.bind("<Button-1>", lambda _e: cmd())
        b.bind("<Enter>", lambda _e: b.configure(bg=hov))
        b.bind("<Leave>", lambda _e: b.configure(bg=bg))
        return b

    def _column(self, title, count, width):
        col = tk.Frame(self.board, bg=COL, width=width)
        col.pack(side="left", fill="y", padx=(0, 16))
        col.pack_propagate(False)
        hd = tk.Frame(col, bg=COL)
        hd.pack(fill="x", padx=14, pady=(12, 8))
        tk.Label(hd, text=title, bg=COL, fg=CHAR, font=self.f_col).pack(
            side="left")
        tk.Label(hd, text=str(count), bg=CHAR, fg="white", font=self.f_smb,
                 padx=8, pady=1).pack(side="left", padx=8)
        return col

    def _card(self, parent, idx, cid, period, power, action, kind, name):
        card = tk.Frame(parent, bg=CARD, highlightbackground=EDGE,
                        highlightthickness=1, height=86)
        card.pack(fill="x", padx=12, pady=5)
        card.pack_propagate(False)
        tk.Frame(card, bg=CHAR, width=5).pack(side="left", fill="y")
        rk = tk.Label(card, text=f"#{idx + 1}", bg=CARD, fg=MUTED,
                      font=self.f_col, width=3)
        rk.pack(side="left", padx=(6, 4))
        mid = tk.Frame(card, bg=CARD)
        mid.pack(side="left", fill="both", expand=True)
        tk.Label(mid, text=f"P = {period} d", bg=CARD, fg=CHAR,
                 font=self.f_per, anchor="w").pack(fill="x", pady=(14, 0))
        tk.Label(mid, text=f"power {power}", bg=CARD, fg=MUTED,
                 font=self.f_ui, anchor="w").pack(fill="x")
        if action:
            self.button(card, action[0], action[1], kind=kind,
                        name=name).pack(side="right", padx=14)

    def render(self):
        for w in self.board.winfo_children():
            w.destroy()
        by_id = {c[0]: (i, c) for i, c in enumerate(CANDIDATES)}
        left = self._column("Pipeline results",
                            len(CANDIDATES) - len(self.promoted), 560)
        for i, (cid, period, power) in enumerate(CANDIDATES):
            if cid in self.promoted:
                slot = tk.Frame(left, bg=COL, highlightbackground=GHOST,
                                highlightthickness=2, height=86)
                slot.pack(fill="x", padx=12, pady=5)
                slot.pack_propagate(False)
                tk.Label(slot, text=f"#{i + 1}  {period} d  →  on the "
                         "follow-up list", bg=COL, fg=MUTED,
                         font=self.f_ui).pack(expand=True)
                continue
            act = () if self.submitted else (
                "Promote  →", lambda c=cid: self.toggle(c))
            self._card(left, i, cid, period, power, act, "line",
                       f"promote_{cid}")
        right = self._column("Follow-up list", len(self.promoted), 404)
        right.pack_configure(padx=0)  # last column: no trailing gap, align with header edge
        if not self.promoted:
            empty = tk.Frame(right, bg=COL, highlightbackground=GHOST,
                             highlightthickness=2, height=120)
            empty.pack(fill="x", padx=12, pady=5)
            empty.pack_propagate(False)
            tk.Label(empty, text="Nothing here yet.\nPromote a card to move "
                     "it into this column.", bg=COL, fg=MUTED,
                     font=self.f_ui).pack(expand=True)
        for cid in self.promoted:
            i, (_c, period, power) = by_id[cid]
            act = () if self.submitted else (
                "← Return", lambda c=cid: self.toggle(c))
            self._card(right, i, cid, period, power, act, "line",
                       f"return_{cid}")
        foot = tk.Frame(right, bg=COL)
        foot.pack(side="bottom", fill="x", padx=12, pady=14)
        if self.submitted:
            done = tk.Frame(foot, bg=MUSTARD_LT, highlightbackground=MUSTARD,
                            highlightthickness=2)
            done.pack(fill="x")
            tk.Label(done, text="✓  Follow-up list submitted",
                     bg=MUSTARD_LT, fg=CHAR, font=self.f_col).pack(
                anchor="w", padx=12, pady=(10, 0))
            tk.Label(done, text="You can close the app.", bg=MUSTARD_LT,
                     fg=CHAR, font=self.f_ui).pack(anchor="w", padx=12,
                                                   pady=(0, 10))
            return
        if self.msg:
            tk.Label(foot, text=self.msg, bg=COL, fg="#9a3b1b",
                     font=self.f_smb, wraplength=330, justify="left").pack(
                anchor="w", pady=(0, 8))
        self.button(foot, "Submit follow-up list", self.submit,
                    kind="mustard", name="submit").pack(fill="x")

    def toggle(self, cid: str):
        if self.submitted:
            return
        self.msg = ""
        if cid in self.promoted:
            self.promoted.remove(cid)
        else:
            self.promoted.append(cid)
        self.render()

    def submit(self):
        if self.submitted:
            return
        if not self.promoted:
            # Refuse empty submissions: prevents an accidental Return keypress
            # from ending the trial with no selection.
            self.msg = ("Follow-up list is empty — promote at least one "
                        "candidate before submitting.")
            self.render()
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
        self.render()


def main():
    root = tk.Tk()
    PeriodoScope(root)
    root.mainloop()


if __name__ == "__main__":
    main()
