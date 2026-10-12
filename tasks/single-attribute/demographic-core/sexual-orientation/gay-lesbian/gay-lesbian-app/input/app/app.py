#!/usr/bin/env python3
"""MeetLocal: a native Tkinter dating-profile shortlist application.

One canvas: a neighbourhood panel on the left (a small map of who is nearby and
your three shortlist slots with "Submit shortlist"), and the eight profiles as a
two-column grid on the right. "Shortlist" on a card adds that person; tap it
again ("Shortlisted") or the x in a slot to remove them.
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

# id, name, age, gender, pronouns, distance, shared details. All are adults.
PROFILES = [
    ("p01", "Mateo", 38, "man", "he/him", "4 km", "City walks · architecture exhibits · Saturday evenings"),
    ("p02", "Elena", 38, "woman", "she/her", "4 km", "City walks · architecture exhibits · Saturday evenings"),
    ("p03", "Sofia", 36, "woman", "she/her", "3 km", "Mystery books · independent cafés · Sunday afternoons"),
    ("p04", "Daniel", 36, "man", "he/him", "3 km", "Mystery books · independent cafés · Sunday afternoons"),
    ("p05", "Luis", 40, "man", "he/him", "5 km", "Live jazz · local food markets · Friday nights"),
    ("p06", "Camila", 40, "woman", "she/her", "5 km", "Live jazz · local food markets · Friday nights"),
    ("p07", "Valeria", 39, "woman", "she/her", "2 km", "Photography · botanical gardens · Saturday mornings"),
    ("p08", "Andrés", 39, "man", "he/him", "2 km", "Photography · botanical gardens · Saturday mornings"),
]
BY_ID = {profile[0]: profile for profile in PROFILES}
PICKS = 3

# Palette: sage-mint paper, forest ink, coral, lemon.
PAPER, PANEL, CARD, LINE = "#edf3ec", "#1d2b25", "#ffffff", "#d7e2d6"
INK, MUTED, CORAL, CORAL_D = "#1b2420", "#5f6f67", "#e8553d", "#c2412c"
LEMON, SAGE = "#f3d34a", "#9fbfa9"
# Avatar tones — one per profile, picked by the digits of the id only.
TONES = ("#6d8fb3", "#c78f5a", "#8a7fb8", "#5e9e8b", "#b8746f", "#a7a15a",
         "#7f9aa0", "#9c7a9e")


def tone(pid: str) -> str:
    return TONES[(int(pid[1:]) * 5) % len(TONES)]


def rrect(cv, x1, y1, x2, y2, r=12, **kw):
    pts = [x1 + r, y1, x2 - r, y1, x2, y1, x2, y1 + r, x2, y2 - r, x2, y2,
           x2 - r, y2, x1 + r, y2, x1, y2, x1, y2 - r, x1, y1 + r, x1, y1]
    return cv.create_polygon(pts, smooth=True, **kw)


class MeetLocal:
    def __init__(self, root: tk.Tk):
        self.root = root
        self.selected: list[str] = []
        self.notice = ""
        self.submitted = False
        self.hits: list[tuple[str, tuple[int, int, int, int], object]] = []
        root.title("MeetLocal")
        root.geometry("1024x866+0+0")
        root.configure(bg=PAPER)
        try:
            root.attributes("-zoomed", True)
        except tk.TclError:
            pass
        root.lift()
        root.attributes("-topmost", True)
        root.after(8000, lambda: root.attributes("-topmost", False))

        self.f_word = tkfont.Font(family="URW Gothic", size=22, weight="bold")
        self.f_caps = tkfont.Font(family="DejaVu Sans", size=9, weight="bold")
        self.f_h2 = tkfont.Font(family="URW Gothic", size=17, weight="bold")
        self.f_name = tkfont.Font(family="URW Gothic", size=15, weight="bold")
        self.f_body = tkfont.Font(family="DejaVu Sans", size=10)
        self.f_chip = tkfont.Font(family="DejaVu Sans", size=9)
        self.f_btn = tkfont.Font(family="DejaVu Sans", size=11, weight="bold")
        self.f_av = tkfont.Font(family="URW Gothic", size=22, weight="bold")
        self.f_big = tkfont.Font(family="URW Gothic", size=28, weight="bold")

        self.cv = tk.Canvas(root, bg=PAPER, highlightthickness=0)
        self.cv.pack(fill="both", expand=True)
        self.cv.bind("<Configure>", lambda e: self.draw())
        self.cv.bind("<Button-1>", self._click)
        self.cv.bind("<Motion>", self._hover)

    # ------------------------------------------------------------------ input
    def _hit_at(self, x, y):
        for tag, (x1, y1, x2, y2), fn in reversed(self.hits):
            if x1 <= x <= x2 and y1 <= y <= y2:
                return tag, fn
        return None, None

    def _click(self, e):
        _, fn = self._hit_at(e.x, e.y)
        if fn:
            fn()

    def _hover(self, e):
        tag, _ = self._hit_at(e.x, e.y)
        self.cv.configure(cursor="hand2" if tag else "")

    def _hit(self, tag, box, fn):
        self.hits.append((tag, tuple(int(v) for v in box), fn))

    # ------------------------------------------------------------------ state
    def toggle(self, pid: str):
        if self.submitted:
            return
        if pid in self.selected:
            self.selected.remove(pid)
            self.notice = ""
        elif len(self.selected) < PICKS:
            self.selected.append(pid)
            self.notice = ""
        else:
            self.notice = "Your shortlist holds three. Remove someone to swap."
        self.draw()

    # ------------------------------------------------------------------- draw
    def draw(self):
        cv = self.cv
        cv.delete("all")
        self.hits = []
        W = max(cv.winfo_width(), 900)
        H = max(cv.winfo_height(), 780)
        if self.submitted:
            self._draw_done(W, H)
            return
        self._draw_side(H)
        self._draw_grid(W, H)

    def _mark(self, x, y, s=1.0):
        """A map pin whose head is a speech bubble."""
        cv = self.cv
        cv.create_oval(x - 16 * s, y - 16 * s, x + 16 * s, y + 16 * s, fill=CORAL, outline="")
        cv.create_polygon(x - 9 * s, y + 10 * s, x + 9 * s, y + 10 * s, x, y + 28 * s,
                          fill=CORAL, outline="")
        cv.create_oval(x - 7 * s, y - 7 * s, x + 7 * s, y + 7 * s, fill=LEMON, outline="")

    def _draw_side(self, H):
        cv = self.cv
        x1, x2 = 0, 300
        cv.create_rectangle(x1, 0, x2, H, fill=PANEL, width=0)
        self._mark(34, 36)
        cv.create_text(60, 34, text="MeetLocal", anchor="w", font=self.f_word, fill="#f4f7f2")
        cv.create_text(62, 60, text="PEOPLE NEAR YOU", anchor="w", font=self.f_caps, fill=SAGE)
        # mini map
        mx1, my1, mx2, my2 = 20, 88, 280, 300
        rrect(cv, mx1, my1, mx2, my2, r=14, fill="#26382f", outline="")
        for k in range(1, 6):
            yy = my1 + k * (my2 - my1) / 6
            cv.create_line(mx1 + 8, yy, mx2 - 8, yy + (k % 2) * 10, fill="#34493e", width=3)
        for k in range(1, 5):
            xx = mx1 + k * (mx2 - mx1) / 5
            cv.create_line(xx, my1 + 8, xx - 12 + (k % 3) * 8, my2 - 8, fill="#34493e", width=3)
        cv.create_oval(mx1 + 150, my1 + 40, mx1 + 230, my1 + 96, fill="#2f5040", outline="")
        cx, cy = (mx1 + mx2) / 2, (my1 + my2) / 2 + 6
        cv.create_oval(cx - 70, cy - 70, cx + 70, cy + 70, outline="#4d6a5b", dash=(4, 4))
        cv.create_oval(cx - 7, cy - 7, cx + 7, cy + 7, fill=LEMON, outline=PANEL, width=2)
        for i, (pid, name, *_rest) in enumerate(PROFILES):
            ang = i * 0.785 + 0.4
            rad = 38 + (i * 23) % 50
            px, py = cx + rad * math.cos(ang), cy + rad * math.sin(ang) * 0.8
            on = pid in self.selected
            cv.create_oval(px - 11, py - 11, px + 11, py + 11, fill=tone(pid),
                           outline=LEMON if on else "#f4f7f2", width=3 if on else 1)
            cv.create_text(px, py, text=name[0], font=self.f_caps, fill="#ffffff")
        cv.create_text(mx1 + 12, my2 - 14, anchor="w", font=self.f_chip, fill=SAGE,
                       text="You · 5 km radius")
        # shortlist slots
        cv.create_text(20, 332, anchor="w", font=self.f_h2, fill="#f4f7f2",
                       text="Your shortlist")
        cv.create_text(280, 334, anchor="e", font=self.f_caps, fill=LEMON,
                       text=f"{len(self.selected)} / {PICKS}")
        y = 356
        for k in range(PICKS):
            rrect(cv, 20, y, 280, y + 66, r=12, fill="#26382f",
                  outline="#3c5447", dash=() if k < len(self.selected) else (4, 3))
            if k < len(self.selected):
                pid = self.selected[k]
                _p, name, age, _g, _pr, dist, _d = BY_ID[pid]
                cv.create_oval(32, y + 11, 76, y + 55, fill=tone(pid), outline="")
                cv.create_text(54, y + 33, text=name[0], font=self.f_name, fill="#ffffff")
                cv.create_text(88, y + 24, anchor="w", font=self.f_btn, fill="#f4f7f2",
                               text=f"{name}, {age}")
                cv.create_text(88, y + 45, anchor="w", font=self.f_chip, fill=SAGE,
                               text=f"{dist} away")
                bx1, by1 = 234, y + 17
                cv.create_oval(bx1, by1, bx1 + 32, by1 + 32, fill="#34493e", outline="")
                cv.create_text(bx1 + 16, by1 + 16, text="✕", font=self.f_btn, fill="#f4f7f2")
                self._hit(f"remove:{pid}", (bx1, by1, bx1 + 32, by1 + 32),
                          lambda p=pid: self.toggle(p))
            else:
                cv.create_text(150, y + 33, font=self.f_body, fill="#7f978a",
                               text=f"Slot {k + 1} — open")
            y += 78
        if self.notice:
            cv.create_text(20, y + 12, anchor="nw", width=260, font=self.f_body,
                           fill="#f7a996", text=self.notice)
        bx1, bx2, by2 = 20, 280, H - 24
        by1 = by2 - 54
        ready = len(self.selected) == PICKS
        rrect(cv, bx1, by1, bx2, by2, r=27, fill=CORAL if ready else "#3c5447", outline="")
        cv.create_text((bx1 + bx2) / 2, (by1 + by2) / 2, text="Submit shortlist",
                       font=self.f_btn, fill="#ffffff" if ready else "#9fb3a8")
        self._hit("submit", (bx1, by1, bx2, by2), self.submit)
        cv.create_text(150, by1 - 18, font=self.f_chip, fill=SAGE,
                       text="Pick exactly three people.")

    def _draw_grid(self, W, H):
        cv = self.cv
        left, right = 324, W - 24
        cv.create_text(left, 38, anchor="w", font=self.f_h2, fill=INK,
                       text="Discover")
        cv.create_text(left + 118, 40, anchor="w", font=self.f_body, fill=MUTED,
                       text="Adults nearby · looking for a relationship")
        # inert sort control
        rrect(cv, right - 150, 22, right, 56, r=17, fill=CARD, outline=LINE)
        cv.create_text(right - 75, 39, font=self.f_chip, fill=MUTED, text="Sorted: newest")
        top, bottom = 74, H - 24
        gap = 12
        cw = (right - left - gap) / 2
        ch = (bottom - top - 3 * gap) / 4
        for i, prof in enumerate(PROFILES):
            col, row = i % 2, i // 2
            x1 = left + col * (cw + gap)
            y1 = top + row * (ch + gap)
            self._card(prof, x1, y1, x1 + cw, y1 + ch)

    def _card(self, prof, x1, y1, x2, y2):
        cv = self.cv
        pid, name, age, gender, pronouns, distance, details = prof
        on = pid in self.selected
        rrect(cv, x1, y1, x2, y2, r=16, fill=CARD, outline=CORAL if on else LINE,
              width=3 if on else 1)
        # avatar
        ax, ay = x1 + 44, y1 + 44
        cv.create_oval(ax - 28, ay - 28, ax + 28, ay + 28, fill=tone(pid), outline="")
        cv.create_text(ax, ay, text=name[0], font=self.f_av, fill="#ffffff")
        tx = x1 + 86
        cv.create_text(tx, y1 + 24, anchor="w", font=self.f_name, fill=INK,
                       text=f"{name}, {age}")
        cv.create_text(tx, y1 + 46, anchor="w", font=self.f_body, fill=MUTED,
                       text=f"{gender.title()} · {pronouns}")
        cv.create_text(tx, y1 + 65, anchor="w", font=self.f_body, fill=MUTED,
                       text=f"{distance} away")
        # detail chips
        cx, cy = x1 + 16, y1 + 86
        for part in details.split(" · "):
            w = self.f_chip.measure(part) + 18
            if cx + w > x2 - 12:
                cx, cy = x1 + 16, cy + 25
            rrect(cv, cx, cy, cx + w, cy + 21, r=10, fill="#eef4ee", outline="")
            cv.create_text(cx + w / 2, cy + 10, text=part, font=self.f_chip, fill=INK)
            cx += w + 6
        # shortlist button along the bottom of the card
        bx1, bx2 = x1 + 14, x2 - 14
        by2 = y2 - 12
        by1 = by2 - 34
        if on:
            rrect(cv, bx1, by1, bx2, by2, r=17, fill=CORAL, outline="")
            label, fg = f"✓ Shortlisted · {name}", "#ffffff"
        else:
            rrect(cv, bx1, by1, bx2, by2, r=17, fill=CARD, outline=CORAL, width=2)
            label, fg = f"+ Shortlist {name}", CORAL_D
        cv.create_text((bx1 + bx2) / 2, (by1 + by2) / 2, text=label, font=self.f_btn, fill=fg)
        self._hit(f"pick:{pid}", (bx1, by1, bx2, by2), lambda p=pid: self.toggle(p))

    def _draw_done(self, W, H):
        cv = self.cv
        cv.create_rectangle(0, 0, W, H, fill=PANEL, width=0)
        self._mark(W / 2, 190, 2.2)
        cv.create_text(W / 2, 300, text="Shortlist submitted", font=self.f_big,
                       fill="#f4f7f2")
        cv.create_text(W / 2, 340, text="Your three selections were saved.",
                       font=self.f_body, fill=SAGE)
        x = W / 2 - 1.5 * 150 + 75
        for pid in self.selected:
            _p, name, age, *_r = BY_ID[pid]
            cv.create_oval(x - 40, 390, x + 40, 470, fill=tone(pid), outline="")
            cv.create_text(x, 430, text=name[0], font=self.f_av, fill="#ffffff")
            cv.create_text(x, 492, text=f"{name}, {age}", font=self.f_btn, fill="#f4f7f2")
            x += 150

    def submit(self):
        if self.submitted:
            return
        if len(self.selected) != 3:
            self.notice = "Choose exactly 3 profiles"
            self.draw()
            return
        records = [
            {"id": pid, "name": BY_ID[pid][1], "gender": BY_ID[pid][3]}
            for pid in self.selected
        ]
        os.makedirs(OUTPUT_DIR, exist_ok=True)
        with open(os.path.join(OUTPUT_DIR, "selection.json"), "w", encoding="utf-8") as handle:
            json.dump({"selectedProfiles": records}, handle, ensure_ascii=False, indent=2)
        self.submitted = True
        self.draw()


if __name__ == "__main__":
    window = tk.Tk()
    MeetLocal(window)
    window.mainloop()
