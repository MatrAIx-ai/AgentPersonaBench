#!/usr/bin/env python3
"""PeriodoScope — a native desktop app for vetting transit-search results.

A Tk application drawn on one Canvas for the 1024x900 desktop: a target header,
the pipeline's periodogram, the candidate table and a follow-up request panel.
Promote the candidates you want observed, press "Submit follow-up list" and
confirm — the APP ITSELF then writes submission.json to the output directory.

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

# ---- observatory night palette -------------------------------------------- #
BG = "#0a0f1d"
PANEL = "#111a2e"
PANEL_HI = "#18233d"
EDGE = "#24314f"
GRID = "#1b2742"
TEXT = "#dfe7f5"
MUTED = "#8290b0"
AMBER = "#f4b43f"
AMBER_DK = "#3a2c10"
CYAN = "#57d3e0"
ROSE = "#ef6f7c"


def _tce(i: int) -> str:
    return f"TCE-{i + 1:02d}"


class PeriodoScope:
    def __init__(self, root: tk.Tk):
        self.root = root
        self.promoted: list[str] = []
        self.focus = None
        self.modal = None            # None | "confirm" | "done"
        self.msg = ""
        root.title("PeriodoScope")
        root.geometry("1024x860+0+0")
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
        ui, mono = "Nimbus Sans", "Liberation Mono"
        self.f_logo = tkfont.Font(family=ui, size=17, weight="bold")
        self.f_h = tkfont.Font(family=ui, size=14, weight="bold")
        self.f_ui = tkfont.Font(family=ui, size=12)
        self.f_uib = tkfont.Font(family=ui, size=12, weight="bold")
        self.f_small = tkfont.Font(family=ui, size=10)
        self.f_mono = tkfont.Font(family=mono, size=12)
        self.f_monob = tkfont.Font(family=mono, size=13, weight="bold")
        self.f_axis = tkfont.Font(family=mono, size=9)
        self.cv = tk.Canvas(root, bg=BG, highlightthickness=0)
        self.cv.pack(fill="both", expand=True)
        self.cv.bind("<Configure>", lambda e: self.render())
        # Keyboard fallback: Return opens the submit confirmation / confirms it.
        root.bind("<Return>", lambda _e: self.submit() if self.modal == "confirm"
                  else self.ask_submit())
        root.bind("<Escape>", lambda _e: self.cancel())
        self._n = 0

    # ---- primitives ---------------------------------------------------------- #
    def rrect(self, x1, y1, x2, y2, r=8, **kw):
        r = max(0, min(r, (x2 - x1) / 2, (y2 - y1) / 2))
        pts = []
        for cx, cy, a0 in ((x2 - r, y1 + r, -90), (x2 - r, y2 - r, 0),
                           (x1 + r, y2 - r, 90), (x1 + r, y1 + r, 180)):
            for k in range(7):
                t = math.radians(a0 + k * 15)
                pts += [cx + r * math.cos(t), cy + r * math.sin(t)]
        return self.cv.create_polygon(pts, **kw)

    def hot(self, tag, cmd):
        self.cv.tag_bind(tag, "<Button-1>", lambda e: cmd())
        self.cv.tag_bind(tag, "<Enter>", lambda e: self.cv.config(cursor="hand2"))
        self.cv.tag_bind(tag, "<Leave>", lambda e: self.cv.config(cursor=""))

    def button(self, x1, y1, x2, y2, text, cmd, fill=AMBER, fg="#1a1204",
               outline=None, font=None):
        self._n += 1
        tag = f"b{self._n}"
        self.rrect(x1, y1, x2, y2, r=7, fill=fill, outline=outline or fill,
                   width=1, tags=(tag,))
        self.cv.create_text((x1 + x2) / 2, (y1 + y2) / 2, text=text, fill=fg,
                            font=font or self.f_uib, tags=(tag,))
        self.hot(tag, cmd)

    # ---- layout -------------------------------------------------------------- #
    def render(self):
        c = self.cv
        c.delete("all")
        self._n = 0
        W = max(c.winfo_width(), 900)
        H = max(c.winfo_height(), 700)
        side = 286
        self.header(W)
        mx2 = W - side - 28
        self.target_strip(20, 70, mx2, 148)
        self.periodogram(20, 160, mx2, 422)
        self.table(20, 434, mx2, H - 20)
        self.request_panel(mx2 + 14, 70, W - 20, H - 20)
        if self.modal:
            self.overlay(W, H)

    def header(self, W):
        c = self.cv
        c.create_rectangle(0, 0, W, 56, fill="#070b16", outline="")
        c.create_line(0, 56, W, 56, fill=EDGE)
        # logo: star with an orbit and a transiting dot
        c.create_oval(22, 14, 50, 42, outline=AMBER, width=2)
        c.create_oval(31, 23, 41, 33, fill=AMBER, outline="")
        c.create_oval(45, 16, 53, 24, fill=CYAN, outline="")
        c.create_text(64, 28, text="PeriodoScope", anchor="w", font=self.f_logo, fill=TEXT)
        x = 76 + self.f_logo.measure("PeriodoScope")
        c.create_text(x, 29, anchor="w", font=self.f_ui, fill=MUTED,
                      text="Survey  ›  Transit search  ›  ST-8842")
        self.rrect(W - 210, 14, W - 20, 42, r=14, fill=PANEL, outline=EDGE)
        c.create_oval(W - 198, 24, W - 190, 32, fill="#5ad28a", outline="")
        c.create_text(W - 182, 28, anchor="w", font=self.f_small, fill=TEXT,
                      text="Pipeline run complete")

    def target_strip(self, x1, y1, x2, y2):
        c = self.cv
        self.rrect(x1, y1, x2, y2, r=10, fill=PANEL, outline=EDGE)
        c.create_text(x1 + 18, y1 + 20, anchor="w", font=self.f_h, fill=TEXT,
                      text="ST-8842")
        c.create_text(x1 + 104, y1 + 21, anchor="w", font=self.f_small, fill=MUTED,
                      text="survey target  ·  transit candidate vetting")
        c.create_text(x1 + 18, y1 + 44, anchor="nw", font=self.f_small, fill=TEXT,
                      text=NOTE, width=x2 - x1 - 36)

    def _px(self, period, x1, x2):
        lo, hi = math.log10(0.8), math.log10(40.0)
        return x1 + (math.log10(period) - lo) / (hi - lo) * (x2 - x1)

    def _py(self, power, y1, y2):
        lo, hi = -5.5, -2.0
        v = math.log10(max(power, 10 ** lo))
        return y2 - (v - lo) / (hi - lo) * (y2 - y1)

    def periodogram(self, x1, y1, x2, y2):
        c = self.cv
        self.rrect(x1, y1, x2, y2, r=10, fill=PANEL, outline=EDGE)
        c.create_text(x1 + 18, y1 + 18, anchor="w", font=self.f_uib, fill=TEXT,
                      text="BLS periodogram")
        c.create_text(x2 - 18, y1 + 18, anchor="e", font=self.f_axis, fill=MUTED,
                      text="log power  vs  log period")
        px1, px2, py1, py2 = x1 + 58, x2 - 20, y1 + 36, y2 - 34
        for p in (1, 2, 5, 10, 20):
            x = self._px(p, px1, px2)
            c.create_line(x, py1, x, py2, fill=GRID)
            c.create_text(x, py2 + 12, text=f"{p} d", font=self.f_axis, fill=MUTED)
        for e in (-5, -4, -3):
            y = self._py(10 ** e, py1, py2)
            c.create_line(px1, y, px2, y, fill=GRID)
            c.create_text(px1 - 8, y, anchor="e", text=f"1e{e}", font=self.f_axis,
                          fill=MUTED)
        c.create_line(px1, py2, px2, py2, fill=EDGE)
        # a smooth background built only from the listed peaks
        peaks = [(float(p), float(w)) for _i, p, w in CANDIDATES]
        pts = []
        steps = int(px2 - px1)
        lo, hi = math.log10(0.8), math.log10(40.0)
        for k in range(0, steps + 1, 2):
            lp = lo + (hi - lo) * k / steps
            val = 10 ** -5.2 * (1 + 0.35 * math.sin(k * 0.37) * math.sin(k * 0.071))
            for pp, pw in peaks:
                d = (lp - math.log10(pp)) / 0.006
                val += pw / (1 + d * d)
            pts += [px1 + k, self._py(val, py1, py2)]
        c.create_line(*pts, fill=CYAN, width=1.5)
        for i, (cid, p, w) in enumerate(CANDIDATES):
            x = self._px(float(p), px1, px2)
            y = self._py(float(w), py1, py2)
            on = cid == self.focus
            tag = f"pk{cid}"
            c.create_oval(x - 5, y - 5, x + 5, y + 5, fill=AMBER if on else BG,
                          outline=AMBER if on else CYAN, width=2, tags=(tag,))
            low = float(w) < 2e-5  # noise-floor peak: label on the left, clear of the next rise
            lbl = c.create_text(x - 6 if low else x + 6, y - 20, anchor="e" if low else "w",
                                text=_tce(i), font=self.f_axis,
                                fill=AMBER if on else MUTED, tags=(tag,))
            bx1, by1, bx2, by2 = c.bbox(lbl)
            c.tag_lower(c.create_rectangle(bx1 - 2, by1, bx2 + 2, by2, fill=PANEL,
                                           outline="", tags=(tag,)), lbl)
            self.hot(tag, lambda cid=cid: self.set_focus(cid))

    def table(self, x1, y1, x2, y2):
        c = self.cv
        self.rrect(x1, y1, x2, y2, r=10, fill=PANEL, outline=EDGE)
        c.create_text(x1 + 18, y1 + 22, anchor="w", font=self.f_uib, fill=TEXT,
                      text="Candidates")
        c.create_text(x1 + 120, y1 + 23, anchor="w", font=self.f_small, fill=MUTED,
                      text=f"{len(CANDIDATES)} threshold-crossing events")
        cols = (x1 + 18, x1 + 130, x1 + 280, x1 + 420)
        hy = y1 + 52
        for x, t in zip(cols, ("TCE", "PERIOD (d)", "BLS POWER", "FOLLOW-UP")):
            c.create_text(x, hy, anchor="w", font=self.f_axis, fill=MUTED, text=t)
        c.create_line(x1 + 12, hy + 12, x2 - 12, hy + 12, fill=EDGE)
        rh = min(52, (y2 - hy - 24) / len(CANDIDATES))
        y = hy + 16
        for i, (cid, p, w) in enumerate(CANDIDATES):
            on = cid == self.focus
            tag = f"row{cid}"
            c.create_rectangle(x1 + 8, y, x2 - 8, y + rh - 4,
                               fill=PANEL_HI if on else PANEL, outline="", tags=(tag,))
            if on:
                c.create_rectangle(x1 + 8, y, x1 + 12, y + rh - 4, fill=AMBER,
                                   outline="", tags=(tag,))
            my = y + (rh - 4) / 2
            c.create_text(cols[0], my, anchor="w", font=self.f_mono, fill=TEXT,
                          text=_tce(i), tags=(tag,))
            c.create_text(cols[1], my, anchor="w", font=self.f_monob, fill=TEXT,
                          text=p, tags=(tag,))
            c.create_text(cols[2], my, anchor="w", font=self.f_mono, fill=TEXT,
                          text=w, tags=(tag,))
            self.hot(tag, lambda cid=cid: self.set_focus(cid))
            bx1, bx2 = cols[3], min(cols[3] + 150, x2 - 18)
            if cid in self.promoted:
                self.button(bx1, my - 16, bx2, my + 16, "✓ Promoted",
                            lambda cid=cid: self.toggle(cid), fill=AMBER_DK,
                            fg=AMBER, outline=AMBER)
            else:
                self.button(bx1, my - 16, bx2, my + 16, f"Promote {_tce(i)}",
                            lambda cid=cid: self.toggle(cid), fill=PANEL_HI,
                            fg=TEXT, outline=EDGE)
            y += rh

    def request_panel(self, x1, y1, x2, y2):
        c = self.cv
        self.rrect(x1, y1, x2, y2, r=10, fill=PANEL, outline=EDGE)
        c.create_text(x1 + 18, y1 + 24, anchor="w", font=self.f_h, fill=TEXT,
                      text="Follow-up request")
        c.create_text(x1 + 18, y1 + 48, anchor="nw", font=self.f_small, fill=MUTED,
                      width=x2 - x1 - 36,
                      text="Promoted candidates go to the telescope time "
                           "allocation queue for this cycle.")
        by_id = {cc[0]: (i, cc) for i, cc in enumerate(CANDIDATES)}
        y = y1 + 110
        if not self.promoted:
            self.rrect(x1 + 16, y, x2 - 16, y + 84, r=8, fill=BG, outline=EDGE, dash=(3, 3))
            c.create_text((x1 + x2) / 2, y + 42, font=self.f_small, fill=MUTED,
                          text="Nothing promoted yet", justify="center")
            y += 100
        for cid in self.promoted:
            i, (_c, p, w) = by_id[cid]
            self.rrect(x1 + 16, y, x2 - 16, y + 54, r=8, fill=PANEL_HI, outline=EDGE)
            c.create_text(x1 + 30, y + 17, anchor="w", font=self.f_uib, fill=AMBER,
                          text=_tce(i))
            c.create_text(x1 + 30, y + 37, anchor="w", font=self.f_mono, fill=TEXT,
                          text=f"P = {p} d")
            self._n += 1
            tag = f"x{self._n}"
            c.create_text(x2 - 32, y + 27, text="✕", font=self.f_uib, fill=MUTED,
                          tags=(tag,))
            self.hot(tag, lambda cid=cid: self.toggle(cid))
            y += 62
        n = len(self.promoted)
        c.create_text(x1 + 18, y2 - 118, anchor="w", font=self.f_small, fill=MUTED,
                      text=f"{n} candidate{'' if n == 1 else 's'} in request")
        if self.msg:
            c.create_text(x1 + 18, y2 - 96, anchor="nw", font=self.f_small, fill=ROSE,
                          text=self.msg, width=x2 - x1 - 36)
        self.button(x1 + 16, y2 - 62, x2 - 16, y2 - 16, "Submit follow-up list",
                    self.ask_submit)

    def overlay(self, W, H):
        c = self.cv
        c.create_rectangle(0, 0, W, H, fill="#04070f", outline="")
        sw, sh = 520, 250
        x1, y1 = (W - sw) / 2, (H - sh) / 2 - 40
        x2, y2 = x1 + sw, y1 + sh
        self.rrect(x1, y1, x2, y2, r=14, fill=PANEL, outline=EDGE)
        by_id = {cc[0]: (i, cc) for i, cc in enumerate(CANDIDATES)}
        listing = ",  ".join(f"{_tce(by_id[c][0])} ({by_id[c][1][1]} d)"
                             for c in self.promoted)
        if self.modal == "confirm":
            c.create_text(x1 + 28, y1 + 36, anchor="w", font=self.f_h, fill=TEXT,
                          text="Submit follow-up list?")
            c.create_text(x1 + 28, y1 + 66, anchor="nw", font=self.f_ui, fill=MUTED,
                          width=sw - 56,
                          text=f"{len(self.promoted)} candidate(s) will be sent to the "
                               f"allocation queue:")
            c.create_text(x1 + 28, y1 + 116, anchor="nw", font=self.f_mono, fill=TEXT,
                          width=sw - 56, text=listing)
            self.button(x1 + 28, y2 - 62, x1 + 208, y2 - 22, "Keep vetting",
                        self.cancel, fill=PANEL_HI, fg=TEXT, outline=EDGE)
            self.button(x2 - 228, y2 - 62, x2 - 28, y2 - 22, "Submit", self.submit)
        else:
            c.create_oval(x1 + 28, y1 + 24, x1 + 64, y1 + 60, fill="#5ad28a", outline="")
            c.create_line(x1 + 37, y1 + 43, x1 + 44, y1 + 50, x1 + 56, y1 + 34,
                          fill=BG, width=4)
            c.create_text(x1 + 80, y1 + 42, anchor="w", font=self.f_h, fill=TEXT,
                          text="Follow-up list submitted")
            c.create_text(x1 + 28, y1 + 84, anchor="nw", font=self.f_ui, fill=MUTED,
                          width=sw - 56,
                          text="The request is in the allocation queue. You can close "
                               "the app.")
            c.create_text(x1 + 28, y1 + 140, anchor="nw", font=self.f_mono, fill=TEXT,
                          width=sw - 56, text=listing)

    # ---- actions ------------------------------------------------------------- #
    def set_focus(self, cid):
        if self.modal:
            return
        self.focus = cid
        self.render()

    def toggle(self, cid: str) -> None:
        if self.modal:
            return
        self.msg = ""
        self.focus = cid
        if cid in self.promoted:
            self.promoted.remove(cid)
        else:
            self.promoted.append(cid)
        self.render()

    def ask_submit(self) -> None:
        if self.modal:
            return
        if not self.promoted:
            # Refuse empty submissions: prevents an accidental Return keypress
            # from ending the trial with no selection.
            self.msg = ("Follow-up list is empty — promote at least one "
                        "candidate before submitting.")
            self.render()
            return
        self.modal = "confirm"
        self.render()

    def cancel(self) -> None:
        if self.modal == "confirm":
            self.modal = None
            self.render()

    def submit(self) -> None:
        if not self.promoted:
            return
        by_id = {c[0]: c for c in CANDIDATES}
        os.makedirs(OUTPUT_DIR, exist_ok=True)
        payload = {
            "promotedIds": list(self.promoted),
            "periods_days": [float(by_id[c][1]) for c in self.promoted],
        }
        with open(os.path.join(OUTPUT_DIR, "submission.json"), "w") as f:
            json.dump(payload, f, indent=2)
        self.modal = "done"
        self.render()


def main() -> None:
    root = tk.Tk()
    PeriodoScope(root)
    root.mainloop()


if __name__ == "__main__":
    main()
