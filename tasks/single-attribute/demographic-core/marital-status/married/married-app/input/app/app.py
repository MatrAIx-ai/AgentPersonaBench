#!/usr/bin/env python3
"""Meridian — the desktop app you set your household accounts up in.

A Tkinter application drawn on one canvas: the four household needs sit on a
two-by-two board, each offering two lines. Tap "+ Add" on the line you want
under each need (tap it again to remove it), then tap "Confirm setup".
Confirming writes setup.json (the lines you chose) into the output directory,
so there is nothing else to save by hand.

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

# (id, category, name, description, price)
CATALOG = [
    ("a02", "Everyday account",   "Sole Everyday Account",         "In your name and no one else's: nobody else sees the statements, nothing needs a second signature, close it any afternoon, and no second name can ever be added to it", "$5/mo"),
    ("a01", "Everyday account",   "Joint Everyday Account",        "Both your names on one account: either of you can pay a bill or ring us without the other there, and one fee covers you both", "$7/mo"),
    ("a03", "Savings allowance",  "Spousal Allowance Transfer",    "What you do not use of your $12,000 shelter passes to your husband or wife instead of expiring, up to $24,000 between you on this one fee, with no second saver to open", "$5.50/mo"),
    ("a04", "Savings allowance",  "Sole Saver Allowance",          "The whole $12,000 shelter is yours, nobody else has a claim on it, and you can take the lot out the same day", "$6/mo"),
    ("a06", "If something happens", "Sole Estate Direction",       "The balance follows your will, so you can rewrite who receives it any afternoon, with nobody told and nobody automatically entitled to a share", "$3/mo"),
    ("a05", "If something happens", "Spousal Beneficiary Nomination", "Paid straight to your husband or wife with no probate wait, and the spousal exemption means no transfer-tax bill", "$4/mo"),
    ("a07", "Household bills",    "Two-Name Bills Account",        "You and your husband or wife both instruct it: one standing order instead of two, and either can stop a payment", "$4/mo"),
    ("a08", "Household bills",    "Own-Name Bills Account",        "Only you instruct it: nothing leaves that you did not set up, stopping one is a tap, nobody to consult first", "$6/mo"),
]
_BY_ID = {m[0]: m for m in CATALOG}
NEEDS = list(dict.fromkeys(m[1] for m in CATALOG))

# Setup size the instruction asks for — one line per need, four needs.
_MIN_ITEMS, _MAX_ITEMS = 4, 4

# Palette: deep lagoon teal, warm paper, terracotta-sand accent.
TEAL, TEAL_D = "#134e4a", "#0c3532"
SAND, SAND_D = "#d98f5c", "#b8703f"
PAPER, CARD, LINE = "#f4efe6", "#fffdf9", "#e0d7c6"
INK, MUT, MINT = "#1d2b2a", "#66706e", "#e3efe9"


def rrect(cv: tk.Canvas, x1, y1, x2, y2, r=10, **kw):
    """A rounded rectangle as a smoothed polygon."""
    pts = [x1 + r, y1, x2 - r, y1, x2, y1, x2, y1 + r, x2, y2 - r, x2, y2,
           x2 - r, y2, x1 + r, y2, x1, y2, x1, y2 - r, x1, y1 + r, x1, y1]
    return cv.create_polygon(pts, smooth=True, **kw)


class Meridian:
    def __init__(self, root: tk.Tk):
        self.root = root
        self.cart: list[str] = []
        self.notice = ""
        self.confirmed = False
        self.hits: list[tuple[str, tuple[int, int, int, int], object]] = []
        root.title("Meridian")
        root.geometry("1024x866+0+0")
        root.configure(bg=PAPER)
        try:
            root.attributes("-zoomed", True)   # maximize on X11
        except tk.TclError:
            pass
        root.lift()
        root.attributes("-topmost", True)
        root.after(8000, lambda: root.attributes("-topmost", False))

        self.f_word = tkfont.Font(family="C059", size=24, weight="bold")
        self.f_tag = tkfont.Font(family="DejaVu Sans", size=9, weight="bold")
        self.f_h2 = tkfont.Font(family="C059", size=17, weight="bold")
        self.f_need = tkfont.Font(family="DejaVu Sans", size=12, weight="bold")
        self.f_name = tkfont.Font(family="DejaVu Sans", size=12, weight="bold")
        self.f_body = tkfont.Font(family="DejaVu Sans", size=10)
        self.f_small = tkfont.Font(family="DejaVu Sans", size=9)
        self.f_btn = tkfont.Font(family="DejaVu Sans", size=11, weight="bold")
        self.f_big = tkfont.Font(family="C059", size=30, weight="bold")

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
    def _toggle(self, mid):
        if self.confirmed:
            return
        if mid in self.cart:
            self.cart.remove(mid)
            self.notice = ""
        else:
            need = _BY_ID[mid][1]
            other = [c for c in self.cart if _BY_ID[c][1] == need]
            if other:
                self.notice = (f"You already have a line for {need}. Tap "
                               f"“Added” on it to remove it first.")
            elif len(self.cart) >= _MAX_ITEMS:
                self.notice = "Your setup already holds four lines."
            else:
                self.cart.append(mid)
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
        self._draw_intro(W)
        self._draw_board(W, H)
        self._draw_bar(W, H)

    def _draw_header(self, W):
        cv = self.cv
        cv.create_rectangle(0, 0, W, 70, fill=TEAL, width=0)
        cv.create_rectangle(0, 70, W, 74, fill=SAND, width=0)
        # Mark: a globe with a single meridian line and a sand pole dot.
        cx, cy, r = 44, 35, 20
        cv.create_oval(cx - r, cy - r, cx + r, cy + r, outline="#f4efe6", width=2)
        cv.create_oval(cx - 8, cy - r, cx + 8, cy + r, outline="#f4efe6", width=2)
        cv.create_line(cx, cy - r, cx, cy + r, fill=SAND, width=3)
        cv.create_line(cx - r, cy, cx + r, cy, fill="#7fa6a2", width=1)
        cv.create_oval(cx - 4, cy - r - 4, cx + 4, cy - r + 4, fill=SAND, outline="")
        cv.create_text(76, 30, text="Meridian", anchor="w", font=self.f_word,
                       fill="#fbf7ef")
        cv.create_text(78, 54, text="HOUSEHOLD BANKING", anchor="w",
                       font=self.f_tag, fill="#b9d2cf")
        x = W - 24
        chip = "Opening today"
        tw = self.f_tag.measure(chip)
        rrect(cv, x - tw - 28, 22, x, 48, r=12, fill=TEAL_D, outline=SAND)
        cv.create_text(x - 14, 35, text=chip, anchor="e", font=self.f_tag, fill=SAND)
        x -= tw + 52
        for label in ("Help", "Statements", "Accounts"):
            cv.create_text(x, 35, text=label, anchor="e", font=self.f_body,
                           fill="#d5e5e2")
            x -= self.f_body.measure(label) + 26

    def _draw_intro(self, W):
        cv = self.cv
        cv.create_text(24, 102, text="Arrange your household accounts", anchor="w",
                       font=self.f_h2, fill=INK)
        cv.create_text(24, 128, anchor="w", font=self.f_body, fill=MUT,
                       text="Four needs, two lines under each. Add one line per need, "
                            "then confirm your setup at the bottom.")
        # progress pips, one per need
        covered = {_BY_ID[c][1] for c in self.cart}
        x = W - 24
        cv.create_text(x, 102, anchor="e", font=self.f_small, fill=MUT,
                       text=f"{len(covered)} of {len(NEEDS)} needs covered")
        for i, need in enumerate(reversed(NEEDS)):
            px = x - i * 26 - 10
            on = need in covered
            cv.create_oval(px - 8, 120, px + 8, 136, width=2, outline=TEAL,
                           fill=TEAL if on else PAPER)

    def _draw_board(self, W, H):
        cv = self.cv
        top, bottom = 148, H - 96
        gap = 14
        pw = (W - 48 - gap) / 2
        ph = (bottom - top - gap) / 2
        for n, need in enumerate(NEEDS):
            col, row = n % 2, n // 2
            x1 = 24 + col * (pw + gap)
            y1 = top + row * (ph + gap)
            self._draw_need(n, need, x1, y1, x1 + pw, y1 + ph)

    def _draw_need(self, n, need, x1, y1, x2, y2):
        cv = self.cv
        rrect(cv, x1, y1, x2, y2, r=14, fill="#ebe3d5", outline=LINE)
        # Need heading: number disc + name + what is chosen.
        cv.create_oval(x1 + 14, y1 + 10, x1 + 40, y1 + 36, fill=TEAL, outline="")
        cv.create_text(x1 + 27, y1 + 23, text=str(n + 1), font=self.f_need,
                       fill="#fbf7ef")
        cv.create_text(x1 + 50, y1 + 23, text=need, anchor="w", font=self.f_need,
                       fill=INK)
        chosen = [c for c in self.cart if _BY_ID[c][1] == need]
        cv.create_text(x2 - 16, y1 + 23, anchor="e", font=self.f_small,
                       fill=TEAL if chosen else MUT,
                       text="1 line chosen" if chosen else "Choose one")
        items = [m for m in CATALOG if m[1] == need]
        cg = 10
        cw = (x2 - x1 - 28 - cg) / 2
        for k, (mid, _cat, name, desc, price) in enumerate(items):
            cx1 = x1 + 14 + k * (cw + cg)
            self._draw_card(mid, name, desc, price, cx1, y1 + 46, cx1 + cw, y2 - 12)

    def _draw_card(self, mid, name, desc, price, x1, y1, x2, y2):
        cv = self.cv
        on = mid in self.cart
        rrect(cv, x1, y1, x2, y2, r=10, fill=CARD,
              outline=TEAL if on else LINE, width=2 if on else 1)
        tw = x2 - x1 - 24
        t = cv.create_text(x1 + 12, y1 + 12, text=name, anchor="nw", width=tw,
                           font=self.f_name, fill=INK)
        ty = cv.bbox(t)[3] + 6
        cv.create_text(x1 + 12, ty, text=desc, anchor="nw", width=tw,
                       font=self.f_body, fill=MUT)
        # footer: fee + add/remove button
        by2 = y2 - 10
        by1 = by2 - 34
        cv.create_line(x1 + 12, by1 - 8, x2 - 12, by1 - 8, fill=LINE)
        cv.create_text(x1 + 12, (by1 + by2) / 2, text=price, anchor="w",
                       font=self.f_btn, fill=INK)
        bx2, bx1 = x2 - 10, x2 - 118
        if on:
            rrect(cv, bx1, by1, bx2, by2, r=8, fill=TEAL, outline=TEAL)
            label, fg = "✓  Added", "#fbf7ef"
        else:
            rrect(cv, bx1, by1, bx2, by2, r=8, fill=CARD, outline=TEAL, width=2)
            label, fg = "+  Add", TEAL
        cv.create_text((bx1 + bx2) / 2, (by1 + by2) / 2, text=label,
                       font=self.f_btn, fill=fg)
        self._hit(f"add:{mid}", (bx1, by1, bx2, by2),
                  lambda m=mid: self._toggle(m))

    def _draw_bar(self, W, H):
        cv = self.cv
        y1 = H - 82
        cv.create_rectangle(0, y1, W, H, fill=INK, width=0)
        n = len(self.cart)
        cv.create_text(24, y1 + 24, anchor="w", font=self.f_need, fill="#fbf7ef",
                       text=f"Your setup · {n} of {_MAX_ITEMS} lines")
        if self.notice:
            cv.create_text(24, y1 + 54, anchor="w", font=self.f_body,
                           fill="#f2b48b", text=self.notice)
        else:
            names = [_BY_ID[c][2] for c in self.cart]
            cv.create_text(24, y1 + 54, anchor="w", font=self.f_body,
                           fill="#b9c6c4", width=W - 300,
                           text=" · ".join(names) if names
                           else "No lines added yet.")
        bx2, bx1 = W - 24, W - 224
        by1, by2 = y1 + 18, y1 + 64
        ready = n == _MAX_ITEMS
        rrect(cv, bx1, by1, bx2, by2, r=10, fill=SAND if ready else "#4a5655",
              outline="")
        cv.create_text((bx1 + bx2) / 2, (by1 + by2) / 2, text="Confirm setup",
                       font=self.f_btn, fill=INK if ready else "#c9d1cf")
        self._hit("confirm", (bx1, by1, bx2, by2), self.confirm_setup)

    def _draw_done(self, W, H):
        cv = self.cv
        cv.create_rectangle(0, 0, W, H, fill=TEAL, width=0)
        cx = W / 2
        cv.create_oval(cx - 44, 170, cx + 44, 258, fill=SAND, outline="")
        cv.create_line(cx - 20, 214, cx - 4, 232, cx + 24, 196, fill=TEAL,
                       width=7, capstyle="round", joinstyle="round")
        cv.create_text(cx, 310, text="Setup confirmed", font=self.f_big,
                       fill="#fbf7ef")
        cv.create_text(cx, 350, font=self.f_body, fill="#b9d2cf",
                       text="Your household accounts open with these lines:")
        y = 392
        for mid in self.cart:
            _m, cat, name, _d, price = _BY_ID[mid]
            rrect(cv, cx - 260, y, cx + 260, y + 44, r=10, fill=TEAL_D, outline="")
            cv.create_text(cx - 240, y + 22, anchor="w", font=self.f_small,
                           fill="#b9d2cf", text=cat.upper())
            cv.create_text(cx + 240, y + 22, anchor="e", font=self.f_name,
                           fill="#fbf7ef", text=name)
            y += 54

    # ---------------------------------------------------------------- confirm
    def confirm_setup(self):
        # The task asks for one line per need — four lines. Refusing to finalize
        # outside that range keeps a part-finished setup from being recorded.
        if not _MIN_ITEMS <= len(self.cart) <= _MAX_ITEMS:
            self.notice = (f"Add one line under each of the {_MAX_ITEMS} needs "
                           f"before confirming ({len(self.cart)} added).")
            self.draw()
            return
        chosen = [{"id": mid, "name": _BY_ID[mid][2]}
                  for mid in self.cart]
        os.makedirs(OUTPUT_DIR, exist_ok=True)
        with open(os.path.join(OUTPUT_DIR, "setup.json"), "w", encoding="utf-8") as f:
            json.dump({"persona": os.environ.get("ADHERENCE_PERSONA", "user"),
                       "selectedLines": chosen}, f, ensure_ascii=False, indent=2)
        self.confirmed = True
        self.draw()


if __name__ == "__main__":
    root = tk.Tk()
    Meridian(root)
    root.mainloop()
