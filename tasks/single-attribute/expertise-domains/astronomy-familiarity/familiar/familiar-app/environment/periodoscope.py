#!/usr/bin/env python3
"""PeriodoScope — a native desktop app for vetting transit-search results.

A Tk master/detail inspector for the 1024x900 desktop: a cobalt title bar, the
candidate list on the left, an inspector pane on the right (period, power dial,
promote switch) and a follow-up tray along the bottom. Promote the candidates
you want observed and press "Submit follow-up list" — the APP ITSELF then
writes submission.json to the output directory.

The app only knows periods and powers.

Run: ADHERENCE_OUTPUT_DIR=/app/output python3 periodoscope.py
"""
from __future__ import annotations

import json
import math
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

# ---- palette: ice white, cobalt, mint ------------------------------------- #
BG = "#eef3f8"
WHITE = "#ffffff"
LINE = "#d5dfeb"
INK = "#15213a"
MUTED = "#6a7892"
COBALT = "#2457d6"
COBALT_DK = "#1a43ab"
COBALT_LT = "#e3ebfc"
MINT = "#1fa98a"
MINT_LT = "#dcf5ee"
DIAL = "#8ea0bf"


class PeriodoScope:
    def __init__(self, root: tk.Tk):
        self.root = root
        self.promoted: list[str] = []
        self.sel = None
        self.submitted = False
        self.msg = ""
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
        f = "Nimbus Sans"
        self.f_logo = tkfont.Font(family=f, size=19, weight="bold")
        self.f_h = tkfont.Font(family=f, size=15, weight="bold")
        self.f_huge = tkfont.Font(family=f, size=34, weight="bold")
        self.f_ui = tkfont.Font(family=f, size=13)
        self.f_uib = tkfont.Font(family=f, size=13, weight="bold")
        self.f_sm = tkfont.Font(family=f, size=11)
        self.f_smb = tkfont.Font(family=f, size=11, weight="bold")

        self._titlebar()
        tk.Label(root, text=NOTE, bg=COBALT_LT, fg=COBALT_DK, font=self.f_ui,
                 wraplength=960, justify="left", anchor="w", padx=22,
                 pady=10).pack(fill="x")
        self.tray = tk.Frame(root, bg=WHITE, height=96,
                             highlightbackground=LINE, highlightthickness=1)
        self.tray.pack(fill="x", side="bottom")
        self.tray.pack_propagate(False)
        body = tk.Frame(root, bg=BG)
        body.pack(fill="both", expand=True, padx=18, pady=14)
        self.listpane = tk.Frame(body, bg=WHITE, width=360,
                                 highlightbackground=LINE, highlightthickness=1)
        self.listpane.pack(side="left", fill="y")
        self.listpane.pack_propagate(False)
        self.detail = tk.Frame(body, bg=WHITE, highlightbackground=LINE,
                               highlightthickness=1)
        self.detail.pack(side="left", fill="both", expand=True, padx=(14, 0))
        self.render()
        # Keyboard fallback: Return submits (coordinate clicks on small buttons
        # are the flakiest CUA action; give agents a reliable alternative).
        root.bind("<Return>", lambda _e: self.submit())

    # ---- chrome ------------------------------------------------------------- #
    def _titlebar(self):
        t = tk.Frame(self.root, bg=COBALT, height=62)
        t.pack(fill="x")
        t.pack_propagate(False)
        c = tk.Canvas(t, width=44, height=44, bg=COBALT, highlightthickness=0)
        c.pack(side="left", padx=(20, 10))
        c.create_oval(6, 6, 38, 38, outline="white", width=3)
        c.create_arc(0, 14, 44, 30, start=200, extent=140, style="arc",
                     outline=MINT_LT, width=2)
        c.create_oval(17, 17, 27, 27, fill="white", outline="")
        c.create_oval(34, 8, 42, 16, fill=MINT, outline="")
        tk.Label(t, text="PeriodoScope", bg=COBALT, fg="white",
                 font=self.f_logo).pack(side="left")
        tk.Label(t, text="Inspector", bg=COBALT_DK, fg="white",
                 font=self.f_smb, padx=8, pady=2).pack(side="left", padx=10)
        tk.Label(t, text="ST-8842  ·  transit candidate vetting",
                 bg=COBALT, fg="#c9d7f7", font=self.f_ui).pack(side="right",
                                                             padx=22)

    def button(self, parent, text, cmd, kind="primary", name=None):
        bg, fg, hov = {"primary": (COBALT, "white", COBALT_DK),
                       "mint": (MINT, "white", "#178a70"),
                       "soft": (COBALT_LT, COBALT_DK, "#d2dffa")}[kind]
        b = tk.Label(parent, text=text, bg=bg, fg=fg, font=self.f_uib,
                     padx=18, pady=8, cursor="hand2", name=name)
        b.bind("<Button-1>", lambda _e: cmd())
        b.bind("<Enter>", lambda _e: b.configure(bg=hov))
        b.bind("<Leave>", lambda _e: b.configure(bg=bg))
        return b

    # ---- render ------------------------------------------------------------- #
    def render(self):
        for pane in (self.listpane, self.detail, self.tray):
            for w in pane.winfo_children():
                w.destroy()
        self._list()
        self._detail()
        self._tray()

    def _list(self):
        hd = tk.Frame(self.listpane, bg=WHITE)
        hd.pack(fill="x", padx=16, pady=(14, 6))
        tk.Label(hd, text="Pipeline candidates", bg=WHITE, fg=INK,
                 font=self.f_h).pack(side="left")
        tk.Label(hd, text=f"{len(CANDIDATES)}", bg=BG, fg=MUTED,
                 font=self.f_smb, padx=8).pack(side="right")
        tk.Label(self.listpane, text="Select a row to inspect it.", bg=WHITE,
                 fg=MUTED, font=self.f_sm).pack(anchor="w", padx=16,
                                                pady=(0, 8))
        for i, (cid, period, power) in enumerate(CANDIDATES):
            sel = cid == self.sel
            bg = COBALT_LT if sel else WHITE
            row = tk.Frame(self.listpane, bg=bg, cursor="hand2", height=64,
                           name=f"row_{cid}")
            row.pack(fill="x", padx=8, pady=2)
            row.pack_propagate(False)
            tk.Frame(row, bg=COBALT if sel else bg, width=4).pack(
                side="left", fill="y")
            n = tk.Label(row, text=f"{i + 1}", bg=bg, fg=MUTED,
                         font=self.f_uib, width=3)
            n.pack(side="left")
            col = tk.Frame(row, bg=bg)
            col.pack(side="left", fill="both", expand=True)
            a = tk.Label(col, text=f"P = {period} d", bg=bg, fg=INK,
                         font=self.f_uib, anchor="w")
            a.pack(fill="x", pady=(10, 0))
            b = tk.Label(col, text=f"power {power}", bg=bg, fg=MUTED,
                         font=self.f_sm, anchor="w")
            b.pack(fill="x")
            on = cid in self.promoted
            s = tk.Label(row, text="✓ Promoted" if on else "", bg=bg,
                         fg=MINT, font=self.f_smb)
            s.pack(side="right", padx=12)
            for w in (row, n, col, a, b, s):
                w.bind("<Button-1>", lambda _e, c=cid: self.select(c))

    def _detail(self):
        if self.sel is None:
            d = self.detail
            c = tk.Canvas(d, width=120, height=120, bg=WHITE,
                          highlightthickness=0)
            c.pack(pady=(150, 12))
            c.create_oval(10, 10, 110, 110, outline=LINE, width=6)
            c.create_line(22, 60, 45, 60, 52, 76, 68, 76, 75, 60, 98, 60,
                          fill=DIAL, width=4, joinstyle="round")
            tk.Label(d, text="No candidate selected", bg=WHITE, fg=INK,
                     font=self.f_h).pack()
            tk.Label(d, text="Pick a row on the left to open it here, then "
                     "promote it if you want it observed.", bg=WHITE,
                     fg=MUTED, font=self.f_ui, wraplength=420).pack(pady=6)
            return
        i, (cid, period, power) = next(
            (i, c) for i, c in enumerate(CANDIDATES) if c[0] == self.sel)
        top = max(float(c[2]) for c in CANDIDATES)
        d = self.detail
        tk.Label(d, text=f"CANDIDATE {i + 1} OF {len(CANDIDATES)}", bg=WHITE,
                 fg=MUTED, font=self.f_smb).pack(anchor="w", padx=28,
                                                 pady=(24, 0))
        tk.Label(d, text=f"{period} d", bg=WHITE, fg=INK,
                 font=self.f_huge).pack(anchor="w", padx=28)
        tk.Label(d, text="period of this periodogram peak", bg=WHITE,
                 fg=MUTED, font=self.f_sm).pack(anchor="w", padx=28)
        # power dial
        c = tk.Canvas(d, width=300, height=170, bg=WHITE, highlightthickness=0)
        c.pack(anchor="w", padx=28, pady=(18, 0))
        cx, cy, r = 150, 150, 120
        c.create_arc(cx - r, cy - r, cx + r, cy + r, start=0, extent=180,
                     style="arc", outline=LINE, width=18)
        frac = float(power) / top
        c.create_arc(cx - r, cy - r, cx + r, cy + r, start=180,
                     extent=-max(1.5, 180 * frac), style="arc",
                     outline=DIAL, width=18)
        ang = math.pi * (1 - frac)
        c.create_line(cx, cy, cx + (r - 30) * math.cos(ang),
                      cy - (r - 30) * math.sin(ang), fill=INK, width=3,
                      capstyle="round")
        c.create_oval(cx - 7, cy - 7, cx + 7, cy + 7, fill=INK, outline="")
        c.create_text(cx, cy - 46, text=power, fill=INK, font=self.f_h)
        c.create_text(cx, cy - 24, text="BLS power", fill=MUTED,
                      font=self.f_sm)
        tk.Label(d, text="Dial scale: 0 to the strongest peak in this search.",
                 bg=WHITE, fg=MUTED, font=self.f_sm).pack(anchor="w", padx=28)
        # promote switch
        on = cid in self.promoted
        sw = tk.Frame(d, bg=BG)
        sw.pack(fill="x", padx=28, pady=(24, 0))
        tk.Label(sw, text="Include in follow-up list", bg=BG, fg=INK,
                 font=self.f_uib).pack(side="left", padx=16, pady=16)
        if not self.submitted:
            self.button(sw, "Remove" if on else "Promote",
                        lambda: self.toggle(cid),
                        kind="soft" if on else "primary",
                        name="promote_btn").pack(side="right", padx=14)
        tk.Label(sw, text="On the list" if on else "Not on the list", bg=BG,
                 fg=MINT if on else MUTED, font=self.f_smb).pack(
            side="right", padx=6)
        nav = tk.Frame(d, bg=WHITE)
        nav.pack(fill="x", padx=28, pady=(18, 0))
        if i > 0:
            self.button(nav, "‹ Previous", lambda: self.select(
                CANDIDATES[i - 1][0]), kind="soft", name="prev").pack(
                side="left")
        if i < len(CANDIDATES) - 1:
            self.button(nav, "Next ›", lambda: self.select(
                CANDIDATES[i + 1][0]), kind="soft", name="next").pack(
                side="right")

    def _tray(self):
        t = self.tray
        left = tk.Frame(t, bg=WHITE)
        left.pack(side="left", fill="both", expand=True, padx=20)
        tk.Label(left, text="FOLLOW-UP LIST", bg=WHITE, fg=MUTED,
                 font=self.f_smb).pack(anchor="w", pady=(12, 6))
        chips = tk.Frame(left, bg=WHITE)
        chips.pack(anchor="w")
        by_id = {c[0]: c for c in CANDIDATES}
        if self.submitted:
            tk.Label(chips, text="✓ Submitted: " + ", ".join(
                f"{by_id[c][1]} d" for c in self.promoted)
                + ". You can close the app.", bg=MINT_LT, fg="#11705b",
                font=self.f_uib, padx=12, pady=6).pack(side="left")
            return
        if not self.promoted:
            tk.Label(chips, text=getattr(self, "msg", "") or
                     "(empty) — promote candidates from the inspector",
                     bg=WHITE, fg=MUTED, font=self.f_ui).pack(side="left",
                                                               pady=6)
        for cid in self.promoted:
            ch = tk.Label(chips, text=f"{by_id[cid][1]} d   ×", bg=MINT_LT,
                          fg="#11705b", font=self.f_uib, padx=12, pady=6,
                          cursor="hand2", name=f"chip_{cid}")
            ch.pack(side="left", padx=(0, 8))
            ch.bind("<Button-1>", lambda _e, c=cid: self.toggle(c))
        self.button(t, "Submit follow-up list", self.submit, kind="mint",
                    name="submit").pack(side="right", padx=22)

    # ---- state -------------------------------------------------------------- #
    def select(self, cid: str) -> None:
        self.sel = cid
        self.render()

    def toggle(self, cid: str) -> None:
        if self.submitted:
            return
        self.msg = ""
        if cid in self.promoted:
            self.promoted.remove(cid)
        else:
            self.promoted.append(cid)
        self.render()

    def submit(self) -> None:
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


def main() -> None:
    root = tk.Tk()
    PeriodoScope(root)
    root.mainloop()


if __name__ == "__main__":
    main()
