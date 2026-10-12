#!/usr/bin/env python3
"""SkillPath — a REAL native desktop GUI app for the OS-APP (computer-use) env.

This is a genuine Tkinter application (one drawn canvas), NOT a web page. The
persona-computer-1 agent sees only screenshots and clicks by coordinate — there
is no DOM, no selector, no JS shortcut. When the user taps "Confirm
enrollment", the APP ITSELF writes the authoritative order.json to the output
dir.

The app carries no scoring information: it records only which course ids were
enrolled, in order. How a course is scored lives host-side in tests/verifier.py,
so nothing in this process (or in the read-only copy mounted under /app/input)
tells the agent which choices count. The agent must judge each course from its
visible name, description, duration and cost exactly as a person would.

Layout: the four skills are four columns on one board, two courses each, so
every course and the confirm button are on screen at once (no scrolling). Tap
"+ Enroll" on a course (tap "Enrolled" again to drop it); the plan holds 2-3.

Run: ADHERENCE_OUTPUT_DIR=/app/output python3 skillpath.py
"""
from __future__ import annotations

import json
import os
import tkinter as tk
from tkinter import font as tkfont

OUTPUT_DIR = (os.environ.get("PLAYGROUND_OUTPUT_DIR")
              or os.environ.get("ADHERENCE_OUTPUT_DIR")
              or os.environ.get("MATRIX_OUTPUT_DIR") or "/app/output")

# (id, category, name, description, duration, cost). Cost is deliberately NOT
# aligned with entry requirements: several programs with formal prerequisites are
# free or funded, while some open-enrollment options cost money.
COURSES = [
    ("d01", "Data", "Advanced Certificate in Data Analytics",
     "Tuition covered by a state upskilling grant; requires a bachelor's degree "
     "transcript to enroll", "12 weeks", "Free (grant)"),
    ("d02", "Data", "Kaggle Learn Micro-courses",
     "No prerequisites, learn by doing small projects", "Self-paced", "Free"),
    ("d03", "Language", "University Continuing-Ed Spanish",
     "Fees waived this term; placement test tied to prior formal coursework",
     "10 weeks", "Free (waiver)"),
    ("d04", "Language", "Private Spanish Tutor Sessions",
     "Twice a week with a tutor; open to anyone, no requirements",
     "8 weeks", "$50 / hour"),
    ("d05", "Speaking", "Weekend Public-Speaking Workshop",
     "Coach-led; open enrollment, no application", "2 days", "$250"),
    ("d06", "Speaking", "Executive-MBA Public-Speaking Module",
     "Sponsored by an alumni fund; requires admission to the MBA program",
     "6 weeks", "Free (sponsored)"),
    ("d07", "Design", "YouTube UX-Design Project Series",
     "Self-paced, open to anyone", "Self-paced", "Free"),
    ("d08", "Design", "Graduate Certificate in UX Design",
     "Tuition waived through a research assistantship; requires a bachelor's "
     "degree to apply", "16 weeks", "Free (waiver)"),
]
_BY_ID = {c[0]: c for c in COURSES}
SKILLS = list(dict.fromkeys(c[1] for c in COURSES))
_MIN, _MAX = 2, 3

# Palette: grape ink, lime, cream, soft lilac.
GRAPE, GRAPE_2 = "#3b2150", "#51306b"
LIME, LIME_D = "#b5e34a", "#6f9a12"
CREAM, CARD, LINE = "#f7f5ef", "#ffffff", "#e3dfd3"
INK, MUT, LILAC = "#22192b", "#6d6577", "#ece6f3"


def rrect(cv, x1, y1, x2, y2, r=12, **kw):
    pts = [x1 + r, y1, x2 - r, y1, x2, y1, x2, y1 + r, x2, y2 - r, x2, y2,
           x2 - r, y2, x1 + r, y2, x1, y2, x1, y2 - r, x1, y1 + r, x1, y1]
    return cv.create_polygon(pts, smooth=True, **kw)


class SkillPath:
    def __init__(self, root: tk.Tk):
        self.root = root
        self.cart: list[str] = []
        self.notice = ""
        self.confirmed = False
        self.hits: list[tuple[str, tuple[int, int, int, int], object]] = []
        root.title("SkillPath")
        root.geometry("1024x866+0+0")
        root.configure(bg=CREAM)
        # Grab the screen on launch so the CUA agent sees the app, not the desktop
        # /browser behind it. Maximize + raise; keep on top briefly so Chromium
        # (started later by the runtime) can't bury it before the first screenshot.
        try:
            root.attributes("-zoomed", True)   # maximize on X11
        except tk.TclError:
            pass
        root.lift()
        root.attributes("-topmost", True)
        root.after(8000, lambda: root.attributes("-topmost", False))

        self.f_word = tkfont.Font(family="Nimbus Sans Narrow", size=26, weight="bold")
        self.f_caps = tkfont.Font(family="DejaVu Sans", size=9, weight="bold")
        self.f_nav = tkfont.Font(family="DejaVu Sans", size=10)
        self.f_h2 = tkfont.Font(family="Nimbus Sans Narrow", size=20, weight="bold")
        self.f_col = tkfont.Font(family="Nimbus Sans Narrow", size=17, weight="bold")
        self.f_name = tkfont.Font(family="DejaVu Sans", size=11, weight="bold")
        self.f_body = tkfont.Font(family="DejaVu Sans", size=10)
        self.f_meta = tkfont.Font(family="DejaVu Sans", size=10, weight="bold")
        self.f_btn = tkfont.Font(family="DejaVu Sans", size=11, weight="bold")
        self.f_big = tkfont.Font(family="Nimbus Sans Narrow", size=36, weight="bold")

        self.cv = tk.Canvas(root, bg=CREAM, highlightthickness=0)
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
    def _toggle(self, cid):
        # A second tap un-enrolls, so a mis-click is recoverable.
        if self.confirmed:
            return
        if cid in self.cart:
            self.cart.remove(cid)
            self.notice = ""
        elif len(self.cart) >= _MAX:
            self.notice = f"Your plan holds up to {_MAX} courses. Drop one to swap."
        else:
            self.cart.append(cid)
            self.notice = ""
        self.draw()

    # ------------------------------------------------------------------- draw
    def draw(self):
        cv = self.cv
        cv.delete("all")
        self.hits = []
        W = max(cv.winfo_width(), 900)
        H = max(cv.winfo_height(), 780)
        if self.confirmed:
            self._draw_done(W, H)
            return
        self._draw_header(W)
        self._draw_board(W, H)
        self._draw_bar(W, H)

    def _mark(self, x, y):
        """Stepping stones climbing to a pennant."""
        cv = self.cv
        for k, (dx, dy) in enumerate(((0, 18), (12, 8), (22, -2))):
            cv.create_oval(x + dx - 6, y + dy - 4, x + dx + 6, y + dy + 4,
                           fill=LIME if k == 2 else "#cdbfe0", outline="")
        cv.create_line(x + 30, y - 4, x + 30, y - 26, fill="#f7f5ef", width=2)
        cv.create_polygon(x + 30, y - 26, x + 44, y - 21, x + 30, y - 16,
                          fill=LIME, outline="")

    def _draw_header(self, W):
        cv = self.cv
        cv.create_rectangle(0, 0, W, 64, fill=GRAPE, width=0)
        self._mark(22, 34)
        sx = 76
        cv.create_text(sx, 32, text="Skill", anchor="w", font=self.f_word, fill="#f7f5ef")
        cv.create_text(sx + self.f_word.measure("Skill"), 32, text="Path", anchor="w",
                       font=self.f_word, fill=LIME)
        x = W - 24
        for label in ("Account", "Saved", "My plan", "Explore"):
            f = self.f_nav
            cv.create_text(x, 32, text=label, anchor="e", font=f,
                           fill=LIME if label == "Explore" else "#d9cde6")
            if label == "Explore":
                w = f.measure(label)
                cv.create_line(x - w, 46, x, 46, fill=LIME, width=3)
            x -= f.measure(label) + 26
        # intro strip
        cv.create_text(24, 92, anchor="w", font=self.f_h2, fill=INK,
                       text="Build a new skill")
        cv.create_text(24 + self.f_h2.measure("Build a new skill") + 16, 94, anchor="w",
                       font=self.f_body, fill=MUT,
                       text=f"Four skills, two courses each. Enroll in {_MIN}–{_MAX} "
                            f"courses, then confirm your plan.")

    def _icon(self, skill, cx, cy):
        """One glyph per skill column (the same for both courses in it)."""
        cv = self.cv
        cv.create_oval(cx - 18, cy - 18, cx + 18, cy + 18, fill=LILAC, outline="")
        c = GRAPE
        if skill == "Data":
            for k, h in enumerate((8, 14, 20)):
                cv.create_rectangle(cx - 10 + k * 7, cy + 9 - h, cx - 5 + k * 7, cy + 9,
                                    fill=c, outline="")
        elif skill == "Language":
            rrect(cv, cx - 11, cy - 9, cx + 11, cy + 5, r=4, fill=c, outline="")
            cv.create_polygon(cx - 5, cy + 4, cx - 1, cy + 4, cx - 7, cy + 10, fill=c, outline="")
        elif skill == "Speaking":
            rrect(cv, cx - 5, cy - 12, cx + 5, cy + 3, r=5, fill=c, outline="")
            cv.create_arc(cx - 9, cy - 7, cx + 9, cy + 8, start=180, extent=180,
                          style="arc", outline=c, width=2)
            cv.create_line(cx, cy + 8, cx, cy + 12, fill=c, width=2)
        else:
            cv.create_rectangle(cx - 11, cy - 9, cx + 11, cy + 9, outline=c, width=2)
            cv.create_line(cx - 11, cy - 3, cx + 11, cy - 3, fill=c, width=2)
            cv.create_rectangle(cx - 7, cy + 1, cx - 1, cy + 6, fill=c, outline="")

    def _draw_board(self, W, H):
        cv = self.cv
        left, right = 24, W - 24
        top, bottom = 118, H - 104
        gap = 12
        colw = (right - left - 3 * gap) / 4
        for i, skill in enumerate(SKILLS):
            x1 = left + i * (colw + gap)
            x2 = x1 + colw
            rrect(cv, x1, top, x2, bottom, r=16, fill="#efebe1", outline="")
            cv.create_text(x1 + 16, top + 24, anchor="w", font=self.f_col, fill=INK,
                           text=skill)
            n_in = sum(1 for c in self.cart if _BY_ID[c][1] == skill)
            cv.create_text(x2 - 16, top + 26, anchor="e", font=self.f_caps,
                           fill=LIME_D if n_in else MUT,
                           text=f"{n_in} in plan" if n_in else "2 courses")
            items = [c for c in COURSES if c[1] == skill]
            ch = (bottom - top - 48 - 10 - 10) / 2
            for k, course in enumerate(items):
                cy1 = top + 46 + k * (ch + 10)
                self._card(course, x1 + 10, cy1, x2 - 10, cy1 + ch)

    def _card(self, course, x1, y1, x2, y2):
        cv = self.cv
        cid, skill, name, desc, duration, cost = course
        on = cid in self.cart
        rrect(cv, x1, y1, x2, y2, r=12, fill=CARD, outline=GRAPE if on else LINE,
              width=3 if on else 1)
        self._icon(skill, x1 + 30, y1 + 30)
        tw = x2 - x1 - 28
        t = cv.create_text(x1 + 14, y1 + 58, anchor="nw", width=tw, font=self.f_name,
                           fill=INK, text=name)
        ty = cv.bbox(t)[3] + 6
        cv.create_text(x1 + 14, ty, anchor="nw", width=tw, font=self.f_body,
                       fill=MUT, text=desc)
        # meta rows + button pinned to the bottom
        by2 = y2 - 12
        by1 = by2 - 36
        my = by1 - 50
        cv.create_line(x1 + 14, my - 8, x2 - 14, my - 8, fill=LINE)
        for k, (lab, val) in enumerate((("Duration", duration), ("Cost", cost))):
            yy = my + 10 + k * 20
            cv.create_text(x1 + 14, yy, anchor="w", font=self.f_body, fill=MUT, text=lab)
            cv.create_text(x2 - 14, yy, anchor="e", font=self.f_meta, fill=INK, text=val)
        bx1, bx2 = x1 + 14, x2 - 14
        if on:
            rrect(cv, bx1, by1, bx2, by2, r=18, fill=GRAPE, outline="")
            label, fg = "✓  Enrolled", LIME
        else:
            rrect(cv, bx1, by1, bx2, by2, r=18, fill=LIME, outline="")
            label, fg = "+  Enroll", GRAPE
        cv.create_text((bx1 + bx2) / 2, (by1 + by2) / 2, text=label, font=self.f_btn, fill=fg)
        self._hit(f"enroll:{cid}", (bx1, by1, bx2, by2), lambda c=cid: self._toggle(c))

    def _draw_bar(self, W, H):
        cv = self.cv
        y1 = H - 88
        rrect(cv, 24, y1, W - 24, H - 16, r=18, fill=GRAPE, outline="")
        n = len(self.cart)
        cv.create_text(48, y1 + 24, anchor="w", font=self.f_col, fill="#f7f5ef",
                       text=f"My plan · {n} course{'s' if n != 1 else ''}")
        # plan pips: up to 3 slots
        px = 48 + self.f_col.measure(f"My plan · {n} course{'s' if n != 1 else ''}") + 18
        for k in range(_MAX):
            cv.create_oval(px + k * 22, y1 + 17, px + k * 22 + 14, y1 + 31,
                           fill=LIME if k < n else GRAPE_2, outline="#8d74a3")
        if self.notice:
            msg, col = self.notice, "#f7c08a"
        elif self.cart:
            msg, col = " · ".join(_BY_ID[c][2] for c in self.cart), "#d9cde6"
        else:
            msg, col = f"Nothing yet — enroll in {_MIN} to {_MAX} courses.", "#bba9cc"
        cv.create_text(48, y1 + 52, anchor="w", font=self.f_body, fill=col,
                       text=msg, width=W - 340)
        bx2, bx1 = W - 44, W - 264
        by1, by2 = y1 + 14, H - 30
        ready = _MIN <= n <= _MAX
        rrect(cv, bx1, by1, bx2, by2, r=21, fill=LIME if ready else GRAPE_2, outline="")
        cv.create_text((bx1 + bx2) / 2, (by1 + by2) / 2, text="Confirm enrollment",
                       font=self.f_btn, fill=GRAPE if ready else "#a996bb")
        self._hit("confirm", (bx1, by1, bx2, by2), self.confirm_enrollment)

    def _draw_done(self, W, H):
        cv = self.cv
        cv.create_rectangle(0, 0, W, H, fill=GRAPE, width=0)
        cx = W / 2
        cv.create_oval(cx - 46, 150, cx + 46, 242, fill=LIME, outline="")
        cv.create_line(cx - 20, 196, cx - 4, 214, cx + 24, 178, fill=GRAPE, width=7,
                       capstyle="round", joinstyle="round")
        cv.create_text(cx, 296, text="Enrollment confirmed", font=self.f_big, fill="#f7f5ef")
        cv.create_text(cx, 346, text="Your plan is saved. Your first sessions are "
                                     "in My plan.", font=self.f_body, fill="#d9cde6")
        y = 380
        for cid in self.cart:
            _i, skill, name, _d, duration, cost = _BY_ID[cid]
            rrect(cv, cx - 280, y, cx + 280, y + 48, r=14, fill=GRAPE_2, outline="")
            cv.create_text(cx - 260, y + 24, anchor="w", font=self.f_caps, fill=LIME,
                           text=skill.upper())
            cv.create_text(cx + 260, y + 24, anchor="e", font=self.f_name, fill="#f7f5ef",
                           text=name)
            y += 58

    def confirm_enrollment(self):
        if self.confirmed:
            return
        if not _MIN <= len(self.cart) <= _MAX:
            self.notice = f"Enroll in {_MIN} to {_MAX} courses before confirming."
            self.draw()
            return
        enrolled = [{"id": cid, "name": _BY_ID[cid][2]} for cid in self.cart]
        os.makedirs(OUTPUT_DIR, exist_ok=True)
        with open(os.path.join(OUTPUT_DIR, "order.json"), "w", encoding="utf-8") as f:
            json.dump({"orderedItems": enrolled}, f, ensure_ascii=False, indent=2)
        # Cover the screen with a confirmation so the agent sees it succeeded.
        self.confirmed = True
        self.draw()


if __name__ == "__main__":
    root = tk.Tk()
    SkillPath(root)
    root.mainloop()
