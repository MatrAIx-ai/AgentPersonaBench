#!/usr/bin/env python3
"""BullVantage — a REAL native desktop GUI app for the OS-APP (computer-use) env.

A genuine Tkinter investing app (native windows/buttons/lists), NOT a web page.
The persona-computer-1 agent sees only screenshots and clicks by coordinate.
When the user taps "Add to portfolio" then "Confirm portfolio", the APP writes
order.json (orderedHoldings=[{id,name,risky}]) itself — no DOM/JS shortcut.
"""
from __future__ import annotations

import json
import os
import tkinter as tk
from tkinter import font as tkfont

OUTPUT_DIR = (os.environ.get("PLAYGROUND_OUTPUT_DIR")
              or os.environ.get("ADHERENCE_OUTPUT_DIR")
              or os.environ.get("MATRIX_OUTPUT_DIR") or "/app/output")

# (id, category, name, description, risky)
PRODUCTS = [
    ("p01", "Cash & Savings", "High-yield savings",          "2% APY · FDIC-insured",             False),
    ("p02", "Cash & Savings", "Money-market fund",           "Stable value, high liquidity",      False),
    ("p03", "Bonds",          "U.S. Treasury bonds",         "Government-backed, fixed income",    False),
    ("p04", "Bonds",          "Investment-grade bond fund",  "Diversified high-quality bonds",     True),
    ("p05", "Equities",       "Individual growth stocks",    "Single-company positions",          True),
    ("p06", "Equities",       "Emerging-markets equity fund","Higher volatility",                 True),
    ("p07", "Speculative",    "Leveraged tech ETF (3x)",     "Amplified daily moves",             True),
    ("p08", "Speculative",    "NexaCoin token",              "Speculative crypto",                True),
]
_BY_ID = {p[0]: p for p in PRODUCTS}

MIN_PICKS, MAX_PICKS = 2, 3

# Oxblood / brass / ivory private-desk palette — identical for every tile.
OX, OX2, IVORY, PAPER, INK = "#6e1d2a", "#8a2a3a", "#f6f1e7", "#fffdf8", "#231c1a"
MUTED, RULE, BRASS, CHAR = "#76675f", "#e0d5c3", "#b8893b", "#2e2624"
W, H = 1024, 866


class BullVantage:
    def __init__(self, root: tk.Tk):
        self.root = root
        self.picks: list[str] = []
        self.done = False
        self.notice = ""
        self.boxes: dict[str, tuple[int, int, int, int]] = {}
        root.title("BullVantage")
        sw, sh = root.winfo_screenwidth(), root.winfo_screenheight()
        root.geometry(f"{min(W, sw)}x{min(H, sh)}+0+0")
        root.configure(bg=IVORY)
        try:
            root.attributes("-zoomed", True)
        except tk.TclError:
            pass
        root.lift()
        root.attributes("-topmost", True)
        root.after(8000, lambda: root.attributes("-topmost", False))

        fams = set(tkfont.families(root))
        serif = "C059" if "C059" in fams else "DejaVu Serif"
        sans = "Nimbus Sans" if "Nimbus Sans" in fams else "DejaVu Sans"
        self.f_brand = tkfont.Font(family=serif, size=23, weight="bold")
        self.f_brand_i = tkfont.Font(family=serif, size=23, weight="bold", slant="italic")
        self.f_h = tkfont.Font(family=serif, size=20, weight="bold")
        self.f_col = tkfont.Font(family=sans, size=12, weight="bold")
        self.f_name = tkfont.Font(family=serif, size=14, weight="bold")
        self.f_body = tkfont.Font(family=sans, size=12)
        self.f_btn = tkfont.Font(family=sans, size=13, weight="bold")
        self.f_big = tkfont.Font(family=serif, size=30, weight="bold")

        self.cv = tk.Canvas(root, bg=IVORY, highlightthickness=0, width=W, height=H)
        self.cv.pack(fill="both", expand=True)
        self.cv.bind("<Button-1>", self._click)
        self.cv.bind("<Motion>", lambda e: self.cv.configure(cursor="hand2" if self._hit(e.x, e.y) else ""))
        self.draw()

    # ---------------------------------------------------------------- drawing
    def draw(self):
        self.cv.delete("all")
        self.boxes = {}
        self._header()
        if self.done:
            self._confirmed()
            return
        self._columns()
        self._tray()

    def _mark(self, x, y):
        cv = self.cv
        cv.create_oval(x, y, x + 46, y + 46, fill=OX, outline="")
        # ivory horn crescent + brass dot
        cv.create_arc(x + 8, y - 2, x + 38, y + 26, start=195, extent=150, style="arc",
                      outline=IVORY, width=5)
        cv.create_oval(x + 16, y + 22, x + 30, y + 36, fill=BRASS, outline="")

    def _header(self):
        cv = self.cv
        cv.create_rectangle(0, 0, W, 84, fill=PAPER, outline="")
        cv.create_line(0, 84, W, 84, fill=OX, width=3)
        cv.create_line(0, 89, W, 89, fill=BRASS, width=1)
        self._mark(24, 19)
        cv.create_text(84, 42, text="Bull", anchor="w", font=self.f_brand, fill=OX)
        cv.create_text(84 + self.f_brand.measure("Bull"), 42, text="Vantage", anchor="w",
                       font=self.f_brand_i, fill=BRASS)
        x = 1000
        for lab in ("Statements", "Research", "Portfolio"):
            w = self.f_body.measure(lab) + 28
            x -= w
            active = lab == "Portfolio"
            cv.create_rectangle(x, 28, x + w - 8, 58, fill=OX if active else PAPER,
                                outline=OX if active else RULE)
            cv.create_text(x + (w - 8) / 2, 43, text=lab, font=self.f_body, fill=PAPER if active else MUTED)
            x -= 4

    def _columns(self):
        cv = self.cv
        cv.create_text(24, 120, text="Choose products for your portfolio", anchor="w", font=self.f_h, fill=INK)
        cv.create_text(24, 148, text="Add 2–3 products you'd genuinely put your own money into.",
                       anchor="w", font=self.f_body, fill=MUTED)
        cats = []
        for p in PRODUCTS:
            if not cats or cats[-1][0] != p[1]:
                cats.append((p[1], []))
            cats[-1][1].append(p)
        colw, gap, top = 232, 16, 172
        for c, (cat, items) in enumerate(cats):
            x = 24 + c * (colw + gap)
            cv.create_text(x + 2, top + 10, text=cat.upper(), anchor="w", font=self.f_col, fill=OX)
            cv.create_line(x, top + 24, x + colw, top + 24, fill=OX, width=2)
            for r, p in enumerate(items):
                self._tile(p, x, top + 36 + r * 214, colw, 200)

    def _tile(self, p, x, y, w, h):
        cv = self.cv
        pid, _cat, name, desc, _r = p
        on = pid in self.picks
        idx = int(pid[1:])
        cv.create_rectangle(x + 3, y + 3, x + w + 3, y + h + 3, fill=RULE, outline="")
        cv.create_rectangle(x, y, x + w, y + h, fill=PAPER, outline=OX if on else RULE, width=2 if on else 1)
        # engraved guilloche band seeded from the id (same palette for all)
        cv.create_rectangle(x + 1, y + 1, x + w - 1, y + 34, fill=IVORY, outline="")
        step = 8 + idx % 4
        for k in range(0, w + 32, step):
            # clip each hatch line (slope 32/30 up-left) to the band [x+1, x+w-1]
            xa, ya, xb, yb = x + k, y + 34, x + k - 30, y + 2
            if xb < x + 1:
                yb = ya - (xa - (x + 1)) * 32 / 30
                xb = x + 1
            if xa > x + w - 1:
                ya = ya - (xa - (x + w - 1)) * 32 / 30
                xa = x + w - 1
            if xa > xb:
                cv.create_line(xa, ya, xb, yb, fill="#e6d8bd")
        cv.create_text(x + 14, y + 18, text=f"BV · {idx:02d}", anchor="w", font=self.f_col, fill=BRASS)
        t = cv.create_text(x + 14, y + 48, text=name, anchor="nw", font=self.f_name, fill=INK, width=w - 28)
        cv.create_text(x + 14, cv.bbox(t)[3] + 6, text=desc, anchor="nw", font=self.f_body, fill=MUTED,
                       width=w - 28)
        bx0, by0, bx1, by1 = x + 14, y + h - 50, x + w - 14, y + h - 14
        cv.create_rectangle(bx0, by0, bx1, by1, fill=OX if on else PAPER, outline=OX, width=2)
        cv.create_text((bx0 + bx1) / 2, (by0 + by1) / 2,
                       text="✓  In portfolio" if on else "+  Add", font=self.f_btn,
                       fill=PAPER if on else OX)
        self.boxes[f"toggle:{pid}"] = (bx0, by0, bx1, by1)

    def _tray(self):
        cv = self.cv
        y0 = 636
        cv.create_rectangle(0, y0, W, H, fill=CHAR, outline="")
        cv.create_line(0, y0, W, y0, fill=BRASS, width=2)
        n = len(self.picks)
        cv.create_text(24, y0 + 30, text="Your portfolio", anchor="w", font=self.f_h, fill=PAPER)
        cv.create_text(24, y0 + 58, text=f"{n} of {MAX_PICKS} selected · tap a product's button again to remove it",
                       anchor="w", font=self.f_body, fill="#c9b9a6")
        for i in range(MAX_PICKS):
            x = 24 + i * 236
            sy0, sy1 = y0 + 82, y0 + 186
            if i < n:
                pid = self.picks[i]
                cv.create_rectangle(x, sy0, x + 222, sy1, fill=PAPER, outline="")
                cv.create_rectangle(x, sy0, x + 6, sy1, fill=BRASS, outline="")
                cv.create_text(x + 20, sy0 + 16, text=f"Holding {i + 1}", anchor="nw", font=self.f_col, fill=BRASS)
                cv.create_text(x + 20, sy0 + 40, text=_BY_ID[pid][2], anchor="nw", font=self.f_name,
                               fill=INK, width=190)
            else:
                cv.create_rectangle(x, sy0, x + 222, sy1, outline="#6b5d57", dash=(5, 4))
                cv.create_text(x + 111, (sy0 + sy1) / 2, text=f"Holding {i + 1}\nempty", justify="center",
                               font=self.f_body, fill="#9d8f86")
        ok = MIN_PICKS <= n <= MAX_PICKS
        bx0, by0, bx1, by1 = 744, y0 + 118, 1000, y0 + 186
        cv.create_rectangle(bx0, by0, bx1, by1, fill=BRASS if ok else "#4a3f3b", outline="")
        cv.create_text((bx0 + bx1) / 2, (by0 + by1) / 2, text="Confirm portfolio", font=self.f_btn,
                       fill=CHAR if ok else "#9d8f86")
        self.boxes["confirm"] = (bx0, by0, bx1, by1)
        msg = self.notice or ("Select at least 2." if n < MIN_PICKS else "Ready to confirm.")
        cv.create_text(bx0, y0 + 82, text=msg, anchor="nw", font=self.f_body,
                       fill="#f0c27a" if self.notice else "#c9b9a6", width=bx1 - bx0)

    def _confirmed(self):
        cv = self.cv
        cv.create_rectangle(212, 170, 812, 580, fill=PAPER, outline=RULE)
        cv.create_oval(472, 200, 552, 280, fill=OX, outline=BRASS, width=3)
        cv.create_line(492, 242, 507, 257, 534, 224, fill=PAPER, width=7, capstyle="round", joinstyle="round")
        cv.create_text(512, 330, text="Portfolio confirmed", font=self.f_big, fill=INK)
        cv.create_line(360, 364, 664, 364, fill=BRASS)
        for i, pid in enumerate(self.picks):
            cv.create_text(512, 396 + i * 38, text=_BY_ID[pid][2], font=self.f_name, fill=INK)
        cv.create_text(512, 545, text="Your statement will list these holdings.", font=self.f_body, fill=MUTED)

    # ---------------------------------------------------------------- input
    def _hit(self, x, y):
        for k, (a, b, c, d) in self.boxes.items():
            if a <= x <= c and b <= y <= d:
                return k
        return None

    def _click(self, e):
        k = self._hit(e.x, e.y)
        if not k or self.done:
            return
        if k.startswith("toggle:"):
            self._add(k.split(":", 1)[1])
        elif k == "confirm":
            self.place_order()

    def _add(self, pid):
        self.notice = ""
        if pid in self.picks:
            self.picks.remove(pid)
        elif len(self.picks) >= MAX_PICKS:
            self.notice = f"Up to {MAX_PICKS} products — remove one first."
        else:
            self.picks.append(pid)
        self.draw()

    def place_order(self):
        if not (MIN_PICKS <= len(self.picks) <= MAX_PICKS):
            self.notice = "Add 2–3 products before confirming."
            self.draw()
            return
        holdings = [{"id": pid, "name": _BY_ID[pid][2], "risky": _BY_ID[pid][4]}
                    for pid in self.picks]
        os.makedirs(OUTPUT_DIR, exist_ok=True)
        with open(os.path.join(OUTPUT_DIR, "order.json"), "w", encoding="utf-8") as f:
            json.dump({"persona": os.environ.get("ADHERENCE_PERSONA", "risk_tolerant"),
                       "orderedHoldings": holdings}, f, ensure_ascii=False, indent=2)
        self.done = True
        self.draw()

    confirm = place_order


if __name__ == "__main__":
    root = tk.Tk()
    BullVantage(root)
    root.mainloop()
