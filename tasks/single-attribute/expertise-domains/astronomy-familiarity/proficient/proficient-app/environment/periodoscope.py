#!/usr/bin/env python3
"""PeriodoScope — a native desktop app for vetting transit-search results.

A Tk "phosphor console" for the 1024x900 desktop: a status line, a peak-power
chart, the candidate table with per-row PROMOTE keys and a queue bar. Promote
the candidates you want observed and press "Submit follow-up list" — the APP
ITSELF then writes submission.json to the output directory.

The app only knows periods and powers.

Run: ADHERENCE_OUTPUT_DIR=/app/output python3 periodoscope.py
"""
from __future__ import annotations

import json
import os
import time
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

# ---- palette: phosphor green on black, amber queue ------------------------- #
BG = "#0b100c"
PANEL = "#111913"
PANEL2 = "#16211a"
LINE = "#26402e"
GREEN = "#7cf29a"
GREEN_MID = "#4fb56e"
DIM = "#5f8f6c"
AMBER = "#ffb347"
AMBER_BG = "#2e2210"
RED = "#ff7a6b"
COLS = (70, 170, 140, 140)  # table column widths, px


class PeriodoScope:
    def __init__(self, root: tk.Tk):
        self.root = root
        self.promoted: list[str] = []
        self.submitted = False
        self.log = "READY  select candidates with PROMOTE"
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
        m = "DejaVu Sans Mono"
        self.f_logo = tkfont.Font(family=m, size=18, weight="bold")
        self.f_h = tkfont.Font(family=m, size=13, weight="bold")
        self.f_ui = tkfont.Font(family=m, size=12)
        self.f_uib = tkfont.Font(family=m, size=12, weight="bold")
        self.f_big = tkfont.Font(family=m, size=15, weight="bold")
        self.f_sm = tkfont.Font(family=m, size=10)

        self._statusline()
        tk.Label(root, text="> " + NOTE, bg=BG, fg=GREEN, font=self.f_ui,
                 wraplength=960, justify="left", anchor="w").pack(
            fill="x", padx=24, pady=(14, 10))
        self._chart()
        self.table = tk.Frame(root, bg=PANEL, highlightbackground=LINE,
                              highlightthickness=1)
        self.table.pack(fill="x", padx=24, pady=(12, 0))
        self.bar = tk.Frame(root, bg=PANEL2, highlightbackground=LINE,
                            highlightthickness=1)
        self.bar.pack(fill="x", padx=24, pady=(12, 0))
        self.render()
        # Keyboard fallback: Return submits (coordinate clicks on small buttons
        # are the flakiest CUA action; give agents a reliable alternative).
        root.bind("<Return>", lambda _e: self.submit())

    # ---- chrome ------------------------------------------------------------- #
    def _statusline(self):
        s = tk.Frame(self.root, bg=PANEL2, height=58)
        s.pack(fill="x")
        s.pack_propagate(False)
        c = tk.Canvas(s, width=40, height=40, bg=PANEL2, highlightthickness=0)
        c.pack(side="left", padx=(20, 10))
        c.create_rectangle(2, 2, 38, 38, outline=GREEN, width=2)
        pts = [4, 20, 10, 20, 13, 10, 16, 30, 19, 14, 22, 24, 25, 20, 36, 20]
        c.create_line(*pts, fill=GREEN, width=2)
        tk.Label(s, text="PeriodoScope", bg=PANEL2, fg=GREEN,
                 font=self.f_logo).pack(side="left")
        tk.Label(s, text="  console", bg=PANEL2, fg=DIM,
                 font=self.f_ui).pack(side="left")
        for t in ("SEARCH: BLS", "TARGET: ST-8842"):
            tk.Label(s, text=t, bg=PANEL2, fg=GREEN_MID, font=self.f_uib,
                     padx=12).pack(side="right", padx=(0, 12 if t == "SEARCH: BLS" else 0))
        tk.Frame(self.root, bg=GREEN_MID, height=1).pack(fill="x")

    def _chart(self):
        box = tk.Frame(self.root, bg=PANEL, highlightbackground=LINE,
                       highlightthickness=1)
        box.pack(fill="x", padx=24)
        tk.Label(box, text="PEAK POWER  (rank order, linear scale)", bg=PANEL,
                 fg=DIM, font=self.f_sm).pack(anchor="w", padx=14,
                                               pady=(10, 0))
        W, H = 972, 190
        c = tk.Canvas(box, width=W, height=H, bg=PANEL, highlightthickness=0)
        c.pack(padx=0, pady=(0, 8))
        x0, y0, y1 = 70, H - 36, 14
        top = max(float(p) for _i, _pd, p in CANDIDATES)
        for k in range(5):
            y = y0 - (y0 - y1) * k / 4
            c.create_line(x0, y, W - 20, y, fill=LINE, dash=(2, 4))
            c.create_text(x0 - 8, y, text=f"{top * k / 4:.4f}", fill=DIM,
                          font=self.f_sm, anchor="e")
        c.create_line(x0, y0, W - 20, y0, fill=GREEN_MID)
        step = (W - 20 - x0) / len(CANDIDATES)
        for i, (_cid, period, power) in enumerate(CANDIDATES):
            x = x0 + step * (i + 0.5)
            y = y0 - (y0 - y1) * float(power) / top
            c.create_line(x, y0, x, y, fill=GREEN, width=3)
            c.create_oval(x - 5, y - 5, x + 5, y + 5, fill=BG, outline=GREEN,
                          width=2)
            c.create_text(x, y0 + 12, text=f"#{i + 1}", fill=GREEN,
                          font=self.f_sm)
            c.create_text(x, y0 + 26, text=f"{period} d", fill=DIM,
                          font=self.f_sm)

    def key(self, parent, text, cmd, name, hot=False):
        fg = BG if hot else GREEN
        bg = AMBER if hot else PANEL
        b = tk.Label(parent, text=text, bg=bg, fg=fg, font=self.f_uib,
                     padx=14, pady=6, cursor="hand2", name=name,
                     highlightthickness=1,
                     highlightbackground=AMBER if hot else GREEN_MID)
        b.bind("<Button-1>", lambda _e: cmd())
        b.bind("<Enter>", lambda _e: b.configure(
            bg="#ffc56d" if hot else PANEL2))
        b.bind("<Leave>", lambda _e: b.configure(bg=bg))
        return b

    # ---- render ------------------------------------------------------------- #
    def render(self):
        for pane in (self.table, self.bar):
            for w in pane.winfo_children():
                w.destroy()
        hdr = tk.Frame(self.table, bg=PANEL)
        hdr.pack(fill="x", padx=14, pady=(10, 4))
        for k, txt in enumerate(("RANK", "PERIOD [d]", "POWER", "STATUS")):
            hdr.grid_columnconfigure(k, minsize=COLS[k])
            tk.Label(hdr, text=txt, bg=PANEL, fg=DIM, font=self.f_sm,
                     anchor="w").grid(row=0, column=k, sticky="w", padx=(12, 0))
        tk.Frame(self.table, bg=LINE, height=1).pack(fill="x", padx=14)
        for i, (cid, period, power) in enumerate(CANDIDATES):
            on = cid in self.promoted
            bg = AMBER_BG if on else PANEL
            row = tk.Frame(self.table, bg=bg)
            row.pack(fill="x", padx=14, pady=1)
            fg = AMBER if on else GREEN
            for k, (txt, f) in enumerate(((str(i + 1), self.f_ui),
                                          (period, self.f_big),
                                          (power, self.f_ui),
                                          ("QUEUED" if on else "--",
                                           self.f_uib))):
                row.grid_columnconfigure(k, minsize=COLS[k])
                tk.Label(row, text=txt, bg=bg, fg=fg, font=f,
                         anchor="w").grid(row=0, column=k, sticky="w",
                                          padx=(12, 0), pady=5)
            row.grid_columnconfigure(4, weight=1)
            if not self.submitted:
                self.key(row, "[ REMOVE  ]" if on else "[ PROMOTE ]",
                         lambda c=cid: self.toggle(c),
                         name=f"promote_{cid}").grid(row=0, column=4,
                                                     sticky="e", padx=6,
                                                     pady=4)
        tk.Frame(self.table, bg=PANEL, height=8).pack()
        # queue bar
        by_id = {c[0]: c for c in CANDIDATES}
        q = " ".join(f"{by_id[c][1]}d" for c in self.promoted) or "(empty)"
        left = tk.Frame(self.bar, bg=PANEL2)
        left.pack(side="left", fill="x", expand=True, padx=14, pady=10)
        tk.Label(left, text=f"follow-up queue [{len(self.promoted)}]: {q}",
                 bg=PANEL2, fg=AMBER, font=self.f_uib, anchor="w",
                 wraplength=620, justify="left").pack(fill="x")
        tk.Label(left, text="$ " + self.log, bg=PANEL2,
                 fg=RED if self.log.startswith("ERR") else DIM,
                 font=self.f_sm, anchor="w", wraplength=620,
                 justify="left").pack(fill="x", pady=(4, 0))
        if self.submitted:
            tk.Label(self.bar, text="\u2713 SUBMITTED", bg=GREEN, fg=BG,
                     font=self.f_uib, padx=14, pady=6).pack(side="right",
                                                             padx=14)
        else:
            self.key(self.bar, "Submit follow-up list", self.submit,
                     name="submit", hot=True).pack(side="right", padx=14)

    # ---- state -------------------------------------------------------------- #
    def toggle(self, cid: str) -> None:
        if self.submitted:
            return
        by_id = {c[0]: c for c in CANDIDATES}
        if cid in self.promoted:
            self.promoted.remove(cid)
            self.log = f"dequeued P={by_id[cid][1]} d"
        else:
            self.promoted.append(cid)
            self.log = f"queued P={by_id[cid][1]} d"
        self.render()

    def submit(self) -> None:
        if self.submitted:
            return
        if not self.promoted:
            # Refuse empty submissions: prevents an accidental Return keypress
            # from ending the trial with no selection.
            self.log = ("ERR follow-up list is empty - promote at least one "
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
        self.log = (f"{time.strftime('%H:%M:%S')}  follow-up list submitted "
                    "- you can close the app.")
        self.render()


def main() -> None:
    root = tk.Tk()
    PeriodoScope(root)
    root.mainloop()


if __name__ == "__main__":
    main()
