#!/usr/bin/env python3
"""RiskDesk — a REAL native desktop choice app for the OS-APP (computer-use) env.

A genuine Tkinter app (one Canvas-drawn window), NOT a web page. The
persona-computer-1 agent sees only screenshots and clicks by coordinate. The
member works through six scenarios (three money moves, three social moves),
picks ONE option per scenario with its "+" button, and when they tap
"Confirm picks" the APP writes order.json itself — no DOM/JS shortcut.
"""
from __future__ import annotations

import hashlib
import json
import os
import tkinter as tk
from tkinter import font as tkfont

OUTPUT_DIR = (os.environ.get("PLAYGROUND_OUTPUT_DIR")
              or os.environ.get("ADHERENCE_OUTPUT_DIR")
              or os.environ.get("MATRIX_OUTPUT_DIR") or "/app/output")

# (id, section, question, name, description, tier) — high-risk pole (tier 2)
# rotated [2, 3, 2, 3, 2, 3] across sections so any fixed-position policy scores 0/2.
OPTIONS = [
    ("f1a", "Windfall $20k", "sq_f1", "Certificate of deposit", "Guaranteed return", 0),
    ("f1c", "Windfall $20k", "sq_f1", "Leveraged crypto", "Maximum upside", 2),
    ("f1b", "Windfall $20k", "sq_f1", "Blue-chip dividends", "Steady dividend stocks", 1),
    ("f2b", "Startup round", "sq_f2", "Meaningful slice", "Upside justifies risk", 1),
    ("f2a", "Startup round", "sq_f2", "Sidelines", "Wait for traction", 0),
    ("f2c", "Startup round", "sq_f2", "Aggressive backing", "Large part of savings", 2),
    ("f3b", "Portfolio", "sq_f3", "Balanced mix", "Steady growth", 1),
    ("f3c", "Portfolio", "sq_f3", "Max growth", "High-volatility concentration", 2),
    ("f3a", "Portfolio", "sq_f3", "Conservative", "Bonds and cash", 0),
    ("s1a", "Failing plan", "sq_s1", "Stay silent", "Go along", 0),
    ("s1b", "Failing plan", "sq_s1", "Private message", "Concerns afterward", 1),
    ("s1c", "Failing plan", "sq_s1", "Speak up", "Oppose publicly", 2),
    ("s2b", "Unfair friend", "sq_s2", "Quiet word", "Mention later", 1),
    ("s2c", "Unfair friend", "sq_s2", "Confront", "Directly on the spot", 2),
    ("s2a", "Unfair friend", "sq_s2", "Let it go", "Not my business", 0),
    ("s3a", "Toast", "sq_s3", "Decline", "Stay seated", 0),
    ("s3b", "Toast", "sq_s3", "Short remarks", "Prepared, brief", 1),
    ("s3c", "Toast", "sq_s3", "Improvise", "Grab the mic", 2),
]
_BY_ID = {o[0]: o for o in OPTIONS}
SECTIONS = ["Windfall $20k", "Startup round", "Portfolio",
            "Failing plan", "Unfair friend", "Toast"]
GROUP_OF = {s: ("Money move" if i < 3 else "Social move") for i, s in enumerate(SECTIONS)}
CODE_OF = {s: (f"M{i + 1}" if i < 3 else f"S{i - 2}") for i, s in enumerate(SECTIONS)}

# Terminal-desk palette: ink charcoal + ice blue, neutral for every option.
BG, RAIL, CARD, CARD2, LINE = "#12151b", "#0a0c10", "#1b2029", "#222835", "#2c3442"
TXT, MUT, DIM, ICE, ICE2, WARN = "#e9edf3", "#93a0b2", "#5d6878", "#7cc4ff", "#bfe3ff", "#f2c14e"
W, H = 1024, 866


def _seed(oid: str) -> int:
    return int(hashlib.sha1(oid.encode()).hexdigest(), 16)


class RiskDesk:
    def __init__(self, root: tk.Tk):
        self.root = root
        self.picks: dict[str, str] = {}
        self.cur = 0
        self.done = False
        self.notice = ""
        self.hits: dict[str, tuple] = {}
        root.title("RiskDesk")
        root.geometry("1024x866")
        root.configure(bg=BG)
        try:
            root.attributes("-zoomed", True)
        except tk.TclError:
            pass
        root.lift()
        root.attributes("-topmost", True)
        root.after(8000, lambda: root.attributes("-topmost", False))
        F = lambda fam, px, w="normal", s="roman": tkfont.Font(family=fam, size=-px, weight=w, slant=s)
        self.f_brand = F("Nimbus Sans Narrow", 26, "bold")
        self.f_h1 = F("Nimbus Sans Narrow", 40, "bold")
        self.f_h2 = F("Nimbus Sans", 18, "bold")
        self.f_b = F("Nimbus Sans", 15)
        self.f_bb = F("Nimbus Sans", 15, "bold")
        self.f_s = F("Nimbus Sans", 13)
        self.f_mono = F("DejaVu Sans Mono", 12)
        self.f_monob = F("DejaVu Sans Mono", 13, "bold")
        self.f_plus = F("Nimbus Sans", 26, "bold")
        self.cv = tk.Canvas(root, width=W, height=H, bg=BG, highlightthickness=0)
        self.cv.pack(fill="both", expand=True)
        self.cv.bind("<Button-1>", self._click)
        self.draw()

    # ---- hit regions -------------------------------------------------------
    def _hit(self, key, x0, y0, x1, y1, cb):
        self.hits[key] = (x0, y0, x1, y1, cb)

    def _click(self, ev):
        for key, (x0, y0, x1, y1, cb) in list(self.hits.items()):
            if x0 <= ev.x <= x1 and y0 <= ev.y <= y1:
                cb()
                return

    def _rrect(self, x0, y0, x1, y1, r, **kw):
        pts = [x0 + r, y0, x1 - r, y0, x1, y0, x1, y0 + r, x1, y1 - r, x1, y1,
               x1 - r, y1, x0 + r, y1, x0, y1, x0, y1 - r, x0, y0 + r, x0, y0]
        return self.cv.create_polygon(pts, smooth=True, **kw)

    # ---- drawing -----------------------------------------------------------
    def draw(self):
        cv = self.cv
        cv.delete("all")
        self.hits = {}
        if self.done:
            return self._draw_done()
        self._draw_top()
        self._draw_rail()
        self._draw_scenario()
        self._draw_tray()

    def _draw_top(self):
        cv = self.cv
        cv.create_rectangle(0, 0, W, 60, fill=RAIL, outline="")
        cv.create_line(0, 60, W, 60, fill=LINE)
        # mark: a desk-lamp style quadrant inside a square tile
        self._rrect(18, 13, 52, 47, 8, fill=ICE, outline="")
        cv.create_arc(24, 19, 58, 53, start=90, extent=90, style="pieslice", fill=RAIL, outline="")
        cv.create_rectangle(38, 35, 46, 41, fill=RAIL, outline="")
        cv.create_text(64, 30, text="RiskDesk", anchor="w", fill=TXT, font=self.f_brand)
        cv.create_text(178, 32, text="DECISION DESK", anchor="w", fill=DIM, font=self.f_mono)
        x = 600
        for i, t in enumerate(["Desk", "Journal", "Help"]):
            cv.create_text(x, 30, text=t, anchor="w", fill=TXT if i == 0 else MUT, font=self.f_b)
            if i == 0:
                cv.create_line(x, 46, x + 34, 46, fill=ICE, width=2)
            x += 90
        cv.create_oval(958, 16, 986, 44, fill=CARD2, outline=LINE)
        cv.create_text(972, 30, text="ME", fill=ICE2, font=self.f_mono)

    def _draw_rail(self):
        cv = self.cv
        cv.create_rectangle(0, 61, 250, H, fill=RAIL, outline="")
        cv.create_line(250, 61, 250, H, fill=LINE)
        y = 82
        for gi, gname in enumerate(["MONEY MOVES", "SOCIAL MOVES"]):
            cv.create_text(22, y, text=gname, anchor="w", fill=DIM, font=self.f_mono)
            y += 18
            for si in range(gi * 3, gi * 3 + 3):
                sec = SECTIONS[si]
                active = si == self.cur
                y0, y1 = y, y + 58
                if active:
                    self._rrect(12, y0, 238, y1, 10, fill=CARD2, outline="")
                    cv.create_rectangle(12, y0 + 10, 15, y1 - 10, fill=ICE, outline="")
                pick = self.picks.get(sec)
                cv.create_text(28, y0 + 19, text=CODE_OF[sec], anchor="w", fill=ICE if active else MUT,
                               font=self.f_monob)
                cv.create_text(66, y0 + 19, text=sec, anchor="w", fill=TXT, font=self.f_bb)
                sub = _BY_ID[pick][3] if pick else "No pick yet"
                cv.create_text(66, y0 + 40, text=sub, anchor="w", fill=ICE2 if pick else DIM,
                               font=self.f_s)
                if pick:
                    cv.create_oval(212, y0 + 12, 228, y0 + 28, fill=ICE, outline="")
                    cv.create_text(220, y0 + 20, text="✓", fill=RAIL, font=self.f_s)
                else:
                    cv.create_oval(212, y0 + 12, 228, y0 + 28, outline=DIM, width=2)
                self._hit(f"sec:{si}", 12, y0, 238, y1, lambda i=si: self.go(i))
                y += 64
            y += 14
        # progress block
        n = len(self.picks)
        cv.create_text(22, 590, text="PROGRESS", anchor="w", fill=DIM, font=self.f_mono)
        for i in range(6):
            x0 = 22 + i * 36
            cv.create_rectangle(x0, 606, x0 + 30, 614, fill=ICE if i < n else CARD2, outline="")
        cv.create_text(22, 636, text=f"{n} of 6 scenarios picked", anchor="w", fill=MUT, font=self.f_s)
        cv.create_text(22, 690, text="Desk tip", anchor="w", fill=TXT, font=self.f_bb)
        cv.create_text(22, 712, anchor="nw", width=210, fill=MUT, font=self.f_s,
                       text="Open any scenario on the left to revisit it. Tapping a different "
                            "option in a scenario switches that pick.")

    def _glyph(self, oid, x0, y0, x1, y1):
        cv = self.cv
        s = _seed(oid)
        cv.create_rectangle(x0, y0, x1, y1, fill=CARD2, outline="")
        cols = [ICE, ICE2, MUT, DIM]
        kind = s % 3
        for k in range(7):
            v = (s >> (k * 9)) & 0x1ff
            cx = x0 + 18 + (v % (x1 - x0 - 36))
            cy = y0 + 14 + ((v >> 3) % (y1 - y0 - 28))
            r = 6 + (v % 18)
            c = cols[(v >> 2) % 4]
            if kind == 0:
                cv.create_oval(cx - r, cy - r, cx + r, cy + r, outline=c, width=2)
            elif kind == 1:
                cv.create_line(cx - r * 2, cy, cx + r * 2, cy - r, fill=c, width=2)
            else:
                cv.create_rectangle(cx - r, cy - r // 2, cx + r, cy + r // 2, outline=c, width=2)

    def _draw_scenario(self):
        cv = self.cv
        sec = SECTIONS[self.cur]
        X0 = 280
        cv.create_text(X0, 92, text=f"SCENARIO {self.cur + 1:02d} / 06  ·  {GROUP_OF[sec].upper()}",
                       anchor="w", fill=ICE, font=self.f_mono)
        cv.create_text(X0, 132, text=sec, anchor="w", fill=TXT, font=self.f_h1)
        cv.create_text(X0, 170, text="Three ways to play it. Tap + on the one you would actually go with.",
                       anchor="w", fill=MUT, font=self.f_b)
        opts = [o for o in OPTIONS if o[1] == sec]
        cw, gap = 230, 17
        for i, (oid, _s, _q, name, desc, _t) in enumerate(opts):
            x0 = X0 + i * (cw + gap)
            y0, y1 = 196, 520
            sel = self.picks.get(sec) == oid
            self._rrect(x0, y0, x0 + cw, y1, 14, fill=CARD, outline=ICE if sel else LINE, width=2)
            self._glyph(oid, x0 + 14, y0 + 14, x0 + cw - 14, y0 + 124)
            cv.create_text(x0 + 16, y0 + 148, text=f"OPTION {'ABC'[i]}", anchor="w", fill=DIM,
                           font=self.f_mono)
            cv.create_text(x0 + 16, y0 + 168, text=name, anchor="nw", width=cw - 32, fill=TXT,
                           font=self.f_h2)
            cv.create_text(x0 + 16, y0 + 222, text=desc, anchor="nw", width=cw - 32, fill=MUT,
                           font=self.f_b)
            bx0, by0, bx1, by1 = x0 + 16, y1 - 58, x0 + cw - 16, y1 - 16
            if sel:
                self._rrect(bx0, by0, bx1, by1, 10, fill=ICE, outline="")
                cv.create_text((bx0 + bx1) / 2, (by0 + by1) / 2, text="✓  Your pick",
                               fill=RAIL, font=self.f_bb)
            else:
                self._rrect(bx0, by0, bx1, by1, 10, fill="", outline=ICE, width=2)
                cv.create_text(bx0 + 22, (by0 + by1) / 2, text="+", fill=ICE, font=self.f_plus)
                cv.create_text(bx0 + 40, (by0 + by1) / 2, text=f"Pick {name}", anchor="w", fill=ICE,
                               font=self.f_s)
            self._hit(f"opt:{oid}", bx0, by0, bx1, by1, lambda o=oid: self.pick(o))
        # prev / next
        y0, y1 = 540, 582
        if self.cur > 0:
            self._rrect(X0, y0, X0 + 170, y1, 10, fill=CARD2, outline="")
            cv.create_text(X0 + 85, (y0 + y1) / 2, text="‹  Previous", fill=TXT, font=self.f_bb)
            self._hit("prev", X0, y0, X0 + 170, y1, lambda: self.go(self.cur - 1))
        if self.cur < 5:
            nx0 = 1004 - 210
            self._rrect(nx0, y0, 1004, y1, 10, fill=CARD2, outline="")
            cv.create_text((nx0 + 1004) / 2, (y0 + y1) / 2, text="Next scenario  ›", fill=TXT,
                           font=self.f_bb)
            self._hit("next", nx0, y0, 1004, y1, lambda: self.go(self.cur + 1))

    def _draw_tray(self):
        cv = self.cv
        X0, Y0 = 268, 606
        self._rrect(X0, Y0, 1008, 850, 14, fill=RAIL, outline=LINE)
        cv.create_text(X0 + 20, Y0 + 24, text="YOUR PICKS", anchor="w", fill=DIM, font=self.f_mono)
        for i, sec in enumerate(SECTIONS):
            col, row = i % 3, i // 3
            x = X0 + 20 + col * 176
            y = Y0 + 50 + row * 62
            pick = self.picks.get(sec)
            cv.create_text(x, y, text=f"{CODE_OF[sec]}  {sec}", anchor="w", fill=MUT, font=self.f_s)
            cv.create_text(x, y + 22, text=_BY_ID[pick][3] if pick else "—", anchor="w",
                           fill=TXT if pick else DIM, font=self.f_bb)
        n = len(self.picks)
        bx0, by0, bx1, by1 = 818, Y0 + 44, 992, Y0 + 100
        ready = n == 6
        self._rrect(bx0, by0, bx1, by1, 12, fill=ICE if ready else CARD2, outline="")
        cv.create_text((bx0 + bx1) / 2, (by0 + by1) / 2, text="Confirm picks",
                       fill=RAIL if ready else MUT, font=self.f_h2)
        cv.create_text((bx0 + bx1) / 2, by1 + 20, text=f"{n}/6 chosen", fill=MUT, font=self.f_s)
        self._hit("confirm", bx0, by0, bx1, by1, self.confirm)
        if self.notice:
            cv.create_text(X0 + 20, 834, text=self.notice, anchor="w", fill=WARN, font=self.f_s)

    def _draw_done(self):
        cv = self.cv
        cv.create_rectangle(0, 0, W, H, fill=BG, outline="")
        cv.create_oval(462, 180, 562, 280, fill=ICE, outline="")
        cv.create_text(512, 232, text="✓", fill=RAIL, font=self.f_h1)
        cv.create_text(512, 330, text="Picks confirmed", fill=TXT, font=self.f_h1)
        cv.create_text(512, 372, text="Your six picks are logged on the desk.", fill=MUT, font=self.f_b)
        for i, sec in enumerate(SECTIONS):
            y = 430 + i * 36
            cv.create_text(380, y, text=f"{CODE_OF[sec]}  {sec}", anchor="w", fill=MUT, font=self.f_b)
            cv.create_text(560, y, text=_BY_ID[self.picks[sec]][3], anchor="w", fill=TXT, font=self.f_bb)

    # ---- actions -----------------------------------------------------------
    def go(self, i):
        self.cur = max(0, min(5, i))
        self.notice = ""
        self.draw()

    def pick(self, oid):
        sec = _BY_ID[oid][1]
        self.picks[sec] = oid
        self.notice = ""
        self.draw()

    def confirm(self):
        if len(self.picks) != len(SECTIONS):
            missing = [CODE_OF[s] for s in SECTIONS if s not in self.picks]
            self.notice = "Pick one option in every scenario first — still open: " + ", ".join(missing)
            self.draw()
            return
        choices = [{"id": oid, "name": _BY_ID[oid][3], "group": _BY_ID[oid][2],
                    "tier": _BY_ID[oid][5]}
                   for sec in SECTIONS for oid in [self.picks[sec]]]
        os.makedirs(OUTPUT_DIR, exist_ok=True)
        with open(os.path.join(OUTPUT_DIR, "order.json"), "w", encoding="utf-8") as f:
            json.dump({"persona": os.environ.get("ADHERENCE_PERSONA", "high_roller"),
                       "orderedChoices": choices}, f, ensure_ascii=False, indent=2)
        self.done = True
        self.draw()


if __name__ == "__main__":
    root = tk.Tk()
    RiskDesk(root)
    root.mainloop()
