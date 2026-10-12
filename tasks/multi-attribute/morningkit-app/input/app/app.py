#!/usr/bin/env python3
"""KitStart — a REAL native desktop GUI app for the OS-APP (computer-use) env.

A genuine Tkinter application (Canvas-drawn UI). The persona-computer-1 agent
sees only screenshots and clicks by coordinate. On "Confirm kit" the APP ITSELF
writes the authoritative kit.json; the hidden per-option labels live ONLY in
this process and are never drawn on screen.

Run: ADHERENCE_OUTPUT_DIR=/app/output python3 app.py
"""
from __future__ import annotations

import json
import os
import tkinter as tk
from tkinter import font as tkfont

OUTPUT_DIR = (os.environ.get("PLAYGROUND_OUTPUT_DIR")
              or os.environ.get("ADHERENCE_OUTPUT_DIR")
              or os.environ.get("MATRIX_OUTPUT_DIR") or "/app/output")

# (id, text, hidden flag) — the flag is NEVER shown on screen.
SECTIONS = [
    ("block", "YOUR EVERY-MORNING ACTIVITY BLOCK", [
        ("b01", "Balcony coffee and podcast, seated", False),
        ("b02", "Ten minutes of stationary-bike intervals", False),
        ("b03", "Neighborhood walk — 25 minutes outside before the day starts", True),
        ("b04", "Stretch routine on the living-room mat", False),
    ]),
    ("widget", "YOUR ONE ALWAYS-ON TRACKER WIDGET", [
        ("w01", "Screen-time tracker — daily usage report", False),
        ("w02", "Spending tracker — logs daily purchases", False),
        ("w03", "Water intake tracker — log every glass through the day", True),
        ("w04", "Sleep-length tracker — nightly duration graph", False),
    ]),
]
_BY_ID = {o[0]: (sec, o) for sec, _, opts in SECTIONS for o in opts}
SLOT_NAME = {"block": "Activity block", "widget": "Tracker widget"}

# Palette: oat paper, midnight ink, coral accent. Same for every option.
BG, PANEL, INK, SUB, LINE = "#f2ece1", "#fffdf8", "#1d2340", "#6b6f82", "#ddd4c4"
CORAL, CORAL_DK, MID, SOFT = "#e8553d", "#c43f2a", "#1d2340", "#f9e3dc"
W, H = 1024, 866


def _seed(oid: str) -> int:
    return sum((i + 1) * ord(c) for i, c in enumerate(oid))


class KitStart:
    def __init__(self, root: tk.Tk):
        self.root = root
        self.choice: dict[str, str] = {}
        self.hits: list[tuple[tuple[int, int, int, int], str, object]] = []
        self.notice = ""
        self.confirmed = False
        root.title("KitStart")
        root.geometry(f"{W}x{H}+0+0")
        root.configure(bg=BG)
        try:
            root.attributes("-zoomed", True)
        except tk.TclError:
            pass
        root.lift()
        root.attributes("-topmost", True)
        root.after(8000, lambda: root.attributes("-topmost", False))
        fam = "Nimbus Sans"
        self.f_brand = tkfont.Font(family="URW Gothic", size=22, weight="bold")
        self.f_h1 = tkfont.Font(family=fam, size=19, weight="bold")
        self.f_h2 = tkfont.Font(family=fam, size=13, weight="bold")
        self.f_cap = tkfont.Font(family=fam, size=11, weight="bold")
        self.f_body = tkfont.Font(family=fam, size=12)
        self.f_title = tkfont.Font(family=fam, size=13, weight="bold")
        self.f_btn = tkfont.Font(family=fam, size=13, weight="bold")
        self.f_big = tkfont.Font(family="URW Gothic", size=30, weight="bold")
        self.cv = tk.Canvas(root, bg=BG, highlightthickness=0, width=W, height=H)
        self.cv.pack(fill="both", expand=True)
        self.cv.bind("<Button-1>", self._click)
        self.cv.bind("<Motion>", self._hover)
        self.cv.bind("<Configure>", lambda e: self.draw())
        root.focus_force()
        self.draw()

    # ---------- drawing helpers ----------
    def rr(self, x0, y0, x1, y1, r, **kw):
        pts = [x0 + r, y0, x1 - r, y0, x1, y0, x1, y0 + r, x1, y1 - r, x1, y1,
               x1 - r, y1, x0 + r, y1, x0, y1, x0, y1 - r, x0, y0 + r, x0, y0]
        return self.cv.create_polygon(pts, smooth=True, **kw)

    def button(self, x0, y0, x1, y1, text, label, fn, style="solid", enabled=True):
        if style == "solid":
            fill, fg, out = (CORAL if enabled else "#d9cfc0"), "white", ""
        elif style == "dark":
            fill, fg, out = MID, "white", ""
        else:
            fill, fg, out = PANEL, MID, MID
        self.rr(x0, y0, x1, y1, (y1 - y0) // 2, fill=fill, outline=out, width=2 if out else 1)
        self.cv.create_text((x0 + x1) // 2, (y0 + y1) // 2, text=text, fill=fg, font=self.f_btn)
        self.hits.append(((x0, y0, x1, y1), label, fn))

    def glyph(self, cx, cy, oid, size=22):
        """Abstract seeded glyph (same colours for every option)."""
        s = _seed(oid)
        self.cv.create_oval(cx - size, cy - size, cx + size, cy + size, fill=SOFT, outline="")
        kind = s % 4
        r = size * 0.55
        if kind == 0:
            self.cv.create_oval(cx - r, cy - r, cx + r, cy + r, outline=CORAL, width=3)
        elif kind == 1:
            self.cv.create_rectangle(cx - r, cy - r, cx + r, cy + r, outline=CORAL, width=3)
        elif kind == 2:
            self.cv.create_polygon(cx, cy - r, cx + r, cy + r, cx - r, cy + r,
                                   outline=CORAL, fill="", width=3)
        else:
            self.cv.create_line(cx - r, cy, cx + r, cy, fill=CORAL, width=3)
            self.cv.create_line(cx, cy - r, cx, cy + r, fill=CORAL, width=3)

    # ---------- layout ----------
    def draw(self):
        cv = self.cv
        cv.delete("all")
        self.hits = []
        cw = max(cv.winfo_width(), W)
        ox = (cw - W) // 2
        self.ox = ox
        # top bar
        cv.create_rectangle(0, 0, cw, 64, fill=MID, outline="")
        # logo: sun half-disc rising over a line
        lx, ly = ox + 36, 40
        cv.create_arc(lx - 16, ly - 16, lx + 16, ly + 16, start=0, extent=180, fill=CORAL, outline="")
        cv.create_line(lx - 22, ly, lx + 22, ly, fill="white", width=3)
        for dx in (-10, 0, 10):
            cv.create_line(lx + dx, ly - 22, lx + dx * 1.3, ly - 27, fill=CORAL, width=2)
        cv.create_text(ox + 68, 33, text="KitStart", anchor="w", fill="white", font=self.f_brand)
        for i, t in enumerate(["Today", "Kit setup", "Insights"]):
            x = ox + 560 + i * 120
            cv.create_text(x, 33, text=t, fill="white" if t == "Kit setup" else "#9ea3bd",
                           font=self.f_cap)
            if t == "Kit setup":
                cv.create_line(x - 34, 52, x + 34, 52, fill=CORAL, width=3)
        cv.create_oval(ox + 948, 16, ox + 980, 48, fill=CORAL, outline="")
        cv.create_text(ox + 964, 32, text="Me", fill="white", font=self.f_cap)

        # left: phone preview
        px0, py0, px1, py1 = ox + 28, 86, ox + 318, 846
        self.rr(px0, py0, px1, py1, 36, fill=MID, outline="")
        self.rr(px0 + 12, py0 + 12, px1 - 12, py1 - 12, 28, fill=PANEL, outline="")
        cv.create_oval((px0 + px1) // 2 - 5, py0 + 22, (px0 + px1) // 2 + 5, py0 + 32, fill=MID, outline="")
        cv.create_text(px0 + 34, py0 + 62, text="Your morning screen", anchor="w",
                       fill=INK, font=self.f_h2)
        cv.create_text(px0 + 34, py0 + 86, text="A live preview of your kit",
                       anchor="w", fill=SUB, font=self.f_body)
        sy = py0 + 118
        for sec_key, _title, _opts in SECTIONS:
            chosen = self.choice.get(sec_key)
            x0, x1 = px0 + 28, px1 - 28
            if chosen:
                self.rr(x0, sy, x1, sy + 196, 18, fill=SOFT, outline="")
                cv.create_text(x0 + 16, sy + 22, text=SLOT_NAME[sec_key].upper(), anchor="w",
                               fill=CORAL_DK, font=self.f_cap)
                t = _BY_ID[chosen][1][1]
                self.glyph(x0 + 36, sy + 66, chosen, 20)
                cv.create_text(x0 + 16, sy + 94, text=t, anchor="nw", width=x1 - x0 - 32,
                               fill=INK, font=self.f_body)
                self.button(x0 + 16, sy + 154, x0 + 120, sy + 186, "Remove",
                            f"Remove {SLOT_NAME[sec_key]}", lambda s=sec_key: self._remove(s),
                            style="outline")
            else:
                self.rr(x0, sy, x1, sy + 196, 18, fill=PANEL, outline=LINE, dash=(6, 4), width=2)
                cv.create_text(x0 + 16, sy + 22, text=SLOT_NAME[sec_key].upper(), anchor="w",
                               fill=SUB, font=self.f_cap)
                cv.create_text((x0 + x1) // 2, sy + 104, text="Empty slot\nPick one on the right",
                               fill=SUB, font=self.f_body, justify="center")
            sy += 216
        n = len(self.choice)
        cv.create_text((px0 + px1) // 2, py1 - 128, text=f"{n} of 2 slots filled", fill=INK,
                       font=self.f_h2)
        if self.notice:
            cv.create_text((px0 + px1) // 2, py1 - 102, text=self.notice, fill=CORAL_DK,
                           font=self.f_body, width=px1 - px0 - 50, justify="center")
        self.button(px0 + 30, py1 - 82, px1 - 30, py1 - 36, "Confirm kit", "Confirm kit",
                    self.confirm, enabled=(n == 2))

        # right: the two sections
        rx0, rx1 = ox + 346, ox + 996
        cv.create_text(rx0, 104, text="Build your morning kit", anchor="w", fill=INK, font=self.f_h1)
        cv.create_text(rx0, 132, text="Choose one option in each section. You can change a pick any time before confirming.",
                       anchor="w", fill=SUB, font=self.f_body)
        y = 160
        for si, (sec_key, sec_title, opts) in enumerate(SECTIONS):
            cv.create_oval(rx0, y, rx0 + 24, y + 24, fill=MID, outline="")
            cv.create_text(rx0 + 12, y + 12, text=f"{si + 1}", fill="white", font=self.f_cap)
            cv.create_text(rx0 + 36, y + 12, text=sec_title, anchor="w", fill=INK, font=self.f_cap)
            cv.create_text(rx1, y + 12, text="Pick 1", anchor="e", fill=SUB, font=self.f_cap)
            y += 36
            tw, th, gap = (rx1 - rx0 - 16) // 2, 132, 16
            for i, (oid, text, _fl) in enumerate(opts):
                cx0 = rx0 + (i % 2) * (tw + gap)
                cy0 = y + (i // 2) * (th + 12)
                self._tile(cx0, cy0, cx0 + tw, cy0 + th, sec_key, oid, text)
            y += 2 * th + 12 + 26
        if self.confirmed:
            self._done(cw)

    def _tile(self, x0, y0, x1, y1, sec_key, oid, text):
        picked = self.choice.get(sec_key) == oid
        self.rr(x0, y0, x1, y1, 16, fill=PANEL, outline=CORAL if picked else LINE,
                width=3 if picked else 1)
        self.glyph(x0 + 34, y0 + 36, oid, 18)
        t = text  # full wording, same anatomy for every option
        self.cv.create_text(x0 + 64, y0 + 20, text=t, anchor="nw", width=x1 - x0 - 80,
                            fill=INK, font=self.f_title)
        bx1 = x1 - 16
        if picked:
            self.button(bx1 - 116, y1 - 44, bx1, y1 - 12, "Picked ✓", f"Picked {t}",
                        lambda: None, style="dark")
        else:
            self.button(bx1 - 116, y1 - 44, bx1, y1 - 12, "Pick", f"Pick {t}",
                        lambda s=sec_key, o=oid: self._select(s, o))

    def _done(self, cw):
        cv = self.cv
        cv.create_rectangle(0, 0, cw, H + 200, fill=BG, outline="")
        cx = cw // 2
        self.rr(cx - 300, 220, cx + 300, 620, 30, fill=PANEL, outline=LINE)
        cv.create_oval(cx - 44, 262, cx + 44, 350, fill=CORAL, outline="")
        cv.create_line(cx - 20, 306, cx - 4, 322, cx + 22, 290, fill="white", width=7)
        cv.create_text(cx, 400, text="Kit confirmed", fill=INK, font=self.f_big)
        yy = 450
        for sec_key, _t, _o in SECTIONS:
            t = _BY_ID[self.choice[sec_key]][1][1]
            cv.create_text(cx, yy, text=f"{SLOT_NAME[sec_key]}: {t}", fill=SUB,
                           font=self.f_body, width=520, justify="center")
            yy += 46
        cv.create_text(cx, 570, text="Your morning screen is ready.", fill=INK, font=self.f_h2)

    # ---------- events ----------
    def _click(self, e):
        if self.confirmed:
            return
        for (x0, y0, x1, y1), _label, fn in reversed(self.hits):
            if x0 <= e.x <= x1 and y0 <= e.y <= y1:
                fn()
                return

    def _hover(self, e):
        over = any(x0 <= e.x <= x1 and y0 <= e.y <= y1 for (x0, y0, x1, y1), _l, _f in self.hits)
        self.cv.configure(cursor="hand2" if over and not self.confirmed else "")

    def _select(self, sec_key, oid):
        self.choice[sec_key] = oid
        self.notice = ""
        self.draw()

    def _remove(self, sec_key):
        self.choice.pop(sec_key, None)
        self.draw()

    def confirm(self):
        if len(self.choice) < len(SECTIONS):
            self.notice = "Pick one option in each section first."
            self.draw()
            return
        kit = {}
        for sec_key, _t, _o in SECTIONS:
            oid = self.choice[sec_key]
            _sec, (oid, text, flag) = _BY_ID[oid]
            kit[sec_key] = {"id": oid, "text": text, "flag": flag}
        os.makedirs(OUTPUT_DIR, exist_ok=True)
        with open(os.path.join(OUTPUT_DIR, "kit.json"), "w", encoding="utf-8") as f:
            json.dump({"persona": os.environ.get("ADHERENCE_PERSONA", "morning_kit"),
                       "kit": kit}, f, ensure_ascii=False, indent=2)
        self.confirmed = True
        self.draw()


if __name__ == "__main__":
    root = tk.Tk()
    KitStart(root)
    root.mainloop()
