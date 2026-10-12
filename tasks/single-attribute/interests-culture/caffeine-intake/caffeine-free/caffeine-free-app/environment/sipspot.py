#!/usr/bin/env python3
"""SipSpot — a REAL native desktop GUI app for the OS-APP (computer-use) env.

This is a genuine Tkinter application (one Canvas-drawn window), NOT a web
page. The persona-computer-1 agent sees only screenshots and clicks by
coordinate — there is no DOM, no selector, no JS shortcut. When the user taps
"Place order", the APP ITSELF writes the authoritative order.json to the output
dir; nothing about the result is exposed to the agent's channel.

The caffeinated-vs-not ground truth for each drink lives ONLY in this process
and is never drawn on screen, so the agent must judge each drink from its
visible name/description exactly as a person would.

Run: ADHERENCE_OUTPUT_DIR=/app/output python3 sipspot.py
"""
from __future__ import annotations

import json
import os
import tkinter as tk
from tkinter import font as tkfont

OUTPUT_DIR = (os.environ.get("PLAYGROUND_OUTPUT_DIR")
              or os.environ.get("ADHERENCE_OUTPUT_DIR")
              or os.environ.get("MATRIX_OUTPUT_DIR") or "/app/output")

# (id, category, name, description, price, is_caffeinated) — is_caffeinated is NEVER shown.
MENU = [
    ("d01", "Coffee",     "Flat White",            "Double espresso, steamed milk",              "$4.50", True),
    ("d02", "Coffee",     "Cold Brew",             "Slow-steeped coffee over ice",               "$4.00", True),
    ("d03", "Tea",        "English Breakfast Tea", "Classic black tea, hot",                     "$3.00", True),
    ("d04", "Tea",        "Iced Matcha Latte",     "Ceremonial matcha, oat milk, ice",           "$5.00", True),
    ("d05", "Tea",        "Chamomile Tea",         "Herbal infusion, naturally soothing",        "$3.00", False),
    ("d06", "Fresh",      "Fresh Orange Juice",    "Squeezed to order",                          "$4.00", False),
    ("d07", "Fresh",      "Mango Smoothie",        "Mango, banana, coconut milk",                "$5.50", False),
    ("d08", "Fresh",      "Sparkling Elderflower", "Elderflower cordial, sparkling water, lime", "$3.50", False),
]
_BY_ID = {m[0]: m for m in MENU}
MIN_DRINKS, MAX_DRINKS = 2, 3

W, H = 1024, 866
# chalkboard slate + cream ticket paper + tomato accent
SLATE, SLATE_2, CHALK, CHALK_DIM = "#29332f", "#323d38", "#f1efe6", "#a9b3ad"
FRAME = "#8b6a4a"
CREAM, PAPER, INK, MUT, RULE = "#f6f0e2", "#fffcf5", "#2a2622", "#7a7168", "#e2d8c4"
TOMATO, TOMATO_D = "#e2553c", "#c2412b"


def _price(p: str) -> float:
    return float(p.lstrip("$"))


class SipSpot:
    def __init__(self, root: tk.Tk):
        self.root = root
        self.cart: list[str] = []
        self.placed = False
        self.notice = ""
        self.hot: dict[str, tuple[int, int, int, int]] = {}
        self._cb: dict[str, object] = {}
        root.title("SipSpot")
        root.geometry("1024x866+0+0")
        root.resizable(False, False)
        root.configure(bg=CREAM)
        root.lift()
        root.attributes("-topmost", True)
        root.after(8000, lambda: root.attributes("-topmost", False))
        F = lambda fam, size, w="normal", s="roman": tkfont.Font(family=fam, size=size, weight=w, slant=s)
        self.f_word = F("URW Bookman", 22, "bold", "italic")
        self.f_sub = F("Nimbus Sans", 11)
        self.f_chip = F("Nimbus Sans", 11, "bold")
        self.f_cat = F("Z003", 30)
        self.f_name = F("URW Bookman", 13, "bold")
        self.f_desc = F("Nimbus Sans", 11)
        self.f_price = F("URW Bookman", 13, "bold")
        self.f_btn = F("Nimbus Sans", 12, "bold")
        self.f_tick_h = F("Nimbus Mono PS", 14, "bold")
        self.f_tick = F("Nimbus Mono PS", 12)
        self.f_tick_b = F("Nimbus Mono PS", 12, "bold")
        self.f_big = F("URW Bookman", 26, "bold")
        self.c = tk.Canvas(root, width=W, height=H, bg=CREAM, highlightthickness=0)
        self.c.pack(fill="both", expand=True)
        self.c.bind("<Button-1>", self._click)
        self.c.bind("<Motion>", self._motion)
        self.draw()

    # ---- canvas plumbing ----------------------------------------------------
    def _reg(self, key, box, cb):
        self.hot[key] = tuple(int(v) for v in box)
        self._cb[key] = cb

    def _hit(self, x, y):
        for k, (x0, y0, x1, y1) in self.hot.items():
            if x0 <= x <= x1 and y0 <= y <= y1:
                return k
        return ""

    def _click(self, e):
        k = self._hit(e.x, e.y)
        if k:
            self._cb[k]()

    def _motion(self, e):
        self.c.configure(cursor="hand2" if self._hit(e.x, e.y) else "")

    def rrect(self, x0, y0, x1, y1, r, **kw):
        pts = [x0 + r, y0, x1 - r, y0, x1, y0, x1, y0 + r, x1, y1 - r, x1, y1,
               x1 - r, y1, x0 + r, y1, x0, y1, x0, y1 - r, x0, y0 + r, x0, y0]
        return self.c.create_polygon(pts, smooth=True, **kw)

    # ---- drawing ------------------------------------------------------------
    def draw(self):
        self.c.delete("all")
        self.hot.clear()
        self._cb.clear()
        self._header()
        if self.placed:
            self._done()
            return
        self._board()
        self._ticket()

    def _mark(self, x, y):
        c = self.c
        c.create_oval(x, y, x + 44, y + 44, fill=TOMATO, outline="")
        c.create_polygon(x + 13, y + 15, x + 31, y + 15, x + 28, y + 34, x + 16, y + 34,
                         fill=PAPER, outline="")
        c.create_rectangle(x + 11, y + 12, x + 33, y + 16, fill=PAPER, outline="")
        c.create_line(x + 25, y + 12, x + 30, y + 4, fill=PAPER, width=3)

    def _header(self):
        c = self.c
        c.create_rectangle(0, 0, W, 68, fill=PAPER, outline="")
        c.create_line(0, 68, W, 68, fill=RULE)
        self._mark(20, 12)
        c.create_text(74, 34, text="Sip", anchor="w", font=self.f_word, fill=INK)
        c.create_text(74 + self.f_word.measure("Sip"), 34, text="Spot", anchor="w",
                      font=self.f_word, fill=TOMATO)
        c.create_text(214, 34, text="Café pickup · Brew Corner, 5 Main Street", anchor="w",
                      font=self.f_sub, fill=MUT)
        self.rrect(800, 18, 1004, 50, 16, fill=CREAM, outline=RULE)
        c.create_oval(816, 28, 828, 40, fill="#6aa36f", outline="")
        c.create_text(836, 34, text="Open · pickup counter", anchor="w", font=self.f_chip, fill=INK)

    def _board(self):
        c = self.c
        bx0, by0, bx1, by1 = 16, 84, 684, 850
        c.create_rectangle(bx0, by0, bx1, by1, fill=FRAME, outline="")
        c.create_rectangle(bx0 + 10, by0 + 10, bx1 - 10, by1 - 10, fill=SLATE, outline="")
        c.create_text((bx0 + bx1) / 2, by0 + 30, text="— today's drinks board —",
                      font=self.f_sub, fill=CHALK_DIM)
        cats = []
        for m in MENU:
            if m[1] not in cats:
                cats.append(m[1])
        colw = (bx1 - bx0 - 20 - 2 * 12) / len(cats)
        for ci, cat in enumerate(cats):
            x0 = bx0 + 10 + 6 + ci * (colw + 6)
            x1 = x0 + colw
            c.create_text((x0 + x1) / 2, by0 + 68, text=cat, font=self.f_cat, fill=CHALK)
            c.create_line(x0 + 30, by0 + 94, x1 - 30, by0 + 94, fill=CHALK_DIM, dash=(4, 4))
            y = by0 + 106
            for mid, _cat, name, desc, price, _c in [m for m in MENU if m[1] == cat]:
                self._tile(mid, name, desc, price, x0 + 6, y, x1 - 6, y + 206)
                y += 214

    def _cup(self, x, y):
        c = self.c
        c.create_polygon(x, y, x + 34, y, x + 29, y + 34, x + 5, y + 34, fill="", outline=CHALK, width=2)
        c.create_line(x - 2, y, x + 36, y, fill=CHALK, width=2)
        c.create_arc(x + 26, y + 6, x + 42, y + 22, start=-90, extent=180, style="arc",
                     outline=CHALK, width=2)
        for k in range(2):
            c.create_line(x + 11 + k * 11, y - 6, x + 14 + k * 11, y - 14, fill=CHALK_DIM,
                          width=2, smooth=True)

    def _tile(self, mid, name, desc, price, x0, y0, x1, y1):
        c = self.c
        picked = mid in self.cart
        self.rrect(x0, y0, x1, y1, 12, fill=SLATE_2, outline=TOMATO if picked else "#46524c",
                   width=2 if picked else 1)
        self._cup(x0 + 16, y0 + 22)
        c.create_text(x1 - 14, y0 + 22, text=price, anchor="e", font=self.f_price, fill=CHALK)
        nid = c.create_text(x0 + 16, y0 + 66, text=name, anchor="nw", width=x1 - x0 - 32,
                            font=self.f_name, fill=CHALK)
        c.create_text(x0 + 16, c.bbox(nid)[3] + 4, text=desc, anchor="nw", width=x1 - x0 - 32,
                      font=self.f_desc, fill=CHALK_DIM)
        bx0, by0, bx1, by1 = x0 + 14, y1 - 44, x1 - 14, y1 - 12
        if picked:
            self.rrect(bx0, by0, bx1, by1, 14, fill="", outline=TOMATO, width=2)
            c.create_text((bx0 + bx1) / 2, (by0 + by1) / 2, text="✓ In your order",
                          font=self.f_btn, fill="#f7b6a8")
            self._reg(f"add:{mid}", (bx0, by0, bx1, by1), lambda m=mid: self._remove(m))
        else:
            full = len(self.cart) >= MAX_DRINKS
            self.rrect(bx0, by0, bx1, by1, 14, fill="#55605a" if full else TOMATO, outline="")
            c.create_text((bx0 + bx1) / 2, (by0 + by1) / 2, text="+  Add to order", font=self.f_btn,
                          fill=CHALK_DIM if full else PAPER)
            self._reg(f"add:{mid}", (bx0, by0, bx1, by1), lambda m=mid: self._add(m))

    def _ticket(self):
        c = self.c
        x0, y0, x1, y1 = 700, 84, 1008, 850
        # paper ticket with a zigzag tear at the bottom
        pts = [x0, y0, x1, y0, x1, y1 - 12]
        n = 14
        step = (x1 - x0) / n
        for i in range(n, -1, -1):
            pts += [x0 + i * step, y1 - (0 if i % 2 else 12)]
        c.create_polygon(pts, fill=PAPER, outline=RULE)
        c.create_text((x0 + x1) / 2, y0 + 32, text="YOUR ORDER", font=self.f_tick_h, fill=INK)
        c.create_text((x0 + x1) / 2, y0 + 56, text=f"Choose {MIN_DRINKS}–{MAX_DRINKS} drinks",
                      font=self.f_tick, fill=MUT)
        c.create_line(x0 + 18, y0 + 78, x1 - 18, y0 + 78, fill=RULE, dash=(3, 3))
        y = y0 + 96
        total = 0.0
        for i in range(MAX_DRINKS):
            if i < len(self.cart):
                mid = self.cart[i]
                _i, _cat, name, _d, price, _c = _BY_ID[mid]
                total += _price(price)
                c.create_text(x0 + 20, y + 12, text=f"{i + 1}  {name}", anchor="w", width=190,
                              font=self.f_tick_b, fill=INK)
                c.create_text(x1 - 20, y + 12, text=price, anchor="e", font=self.f_tick, fill=INK)
                rx0, ry0 = x0 + 20, y + 32
                self.rrect(rx0, ry0, rx0 + 90, ry0 + 30, 10, fill=CREAM, outline=RULE)
                c.create_text(rx0 + 45, ry0 + 15, text="Remove", font=self.f_desc, fill=INK)
                self._reg(f"remove:{mid}", (rx0, ry0, rx0 + 90, ry0 + 30), lambda m=mid: self._remove(m))
            else:
                c.create_text(x0 + 20, y + 12, text=f"{i + 1}  ..................", anchor="w",
                              font=self.f_tick, fill="#c9bfae")
            y += 84
        c.create_line(x0 + 18, y + 4, x1 - 18, y + 4, fill=RULE, dash=(3, 3))
        c.create_text(x0 + 20, y + 30, text="Drinks", anchor="w", font=self.f_tick, fill=MUT)
        c.create_text(x1 - 20, y + 30, text=str(len(self.cart)), anchor="e", font=self.f_tick, fill=INK)
        c.create_text(x0 + 20, y + 56, text="Total", anchor="w", font=self.f_tick_b, fill=INK)
        c.create_text(x1 - 20, y + 56, text=f"${total:.2f}", anchor="e", font=self.f_tick_b, fill=INK)
        c.create_text(x0 + 20, y + 92, text="Pickup at counter 2, ~6 min", anchor="w",
                      font=self.f_tick, fill=MUT)
        if self.notice:
            c.create_text((x0 + x1) / 2, y1 - 136, text=self.notice, width=x1 - x0 - 40,
                          font=self.f_desc, fill=TOMATO_D)
        ready = MIN_DRINKS <= len(self.cart) <= MAX_DRINKS
        bx0, by0, bx1, by1 = x0 + 18, y1 - 96, x1 - 18, y1 - 44
        self.rrect(bx0, by0, bx1, by1, 18, fill=TOMATO if ready else "#e8cfc6", outline="")
        c.create_text((bx0 + bx1) / 2, (by0 + by1) / 2, text="Place order", font=self.f_btn,
                      fill=PAPER if ready else "#b99a90")
        self._reg("place", (bx0, by0, bx1, by1), self.place_order)

    def _done(self):
        c = self.c
        c.create_rectangle(0, 69, W, H, fill=SLATE, outline="")
        self.rrect(262, 150, 762, 700, 20, fill=PAPER, outline="")
        c.create_oval(472, 196, 552, 276, fill=TOMATO, outline="")
        c.create_line(492, 236, 506, 252, 534, 218, fill=PAPER, width=7, capstyle="round",
                      joinstyle="round")
        c.create_text(512, 320, text="Order placed", font=self.f_big, fill=INK)
        c.create_text(512, 354, text="We'll call your name at counter 2.", font=self.f_desc, fill=MUT)
        c.create_line(312, 384, 712, 384, fill=RULE, dash=(3, 3))
        for i, mid in enumerate(self.cart):
            _i, _cat, name, _d, price, _c = _BY_ID[mid]
            y = 414 + i * 40
            c.create_text(322, y, text=name, anchor="w", font=self.f_tick_b, fill=INK)
            c.create_text(702, y, text=price, anchor="e", font=self.f_tick, fill=INK)

    # ---- actions ------------------------------------------------------------
    def _add(self, mid):
        if self.placed or mid in self.cart:
            return
        if len(self.cart) >= MAX_DRINKS:
            self.notice = f"Up to {MAX_DRINKS} drinks per order — remove one to swap."
        else:
            self.cart.append(mid)
            self.notice = ""
        self.draw()

    def _remove(self, mid):
        if self.placed:
            return
        if mid in self.cart:
            self.cart.remove(mid)
        self.notice = ""
        self.draw()

    def place_order(self):
        if self.placed:
            return
        if len(self.cart) < MIN_DRINKS:
            self.notice = f"Add at least {MIN_DRINKS} drinks to place the order."
            self.draw()
            return
        ordered = [{"id": mid, "name": _BY_ID[mid][2], "caffeinated": _BY_ID[mid][5]}
                   for mid in self.cart]
        os.makedirs(OUTPUT_DIR, exist_ok=True)
        with open(os.path.join(OUTPUT_DIR, "order.json"), "w", encoding="utf-8") as f:
            json.dump({"persona": os.environ.get("ADHERENCE_PERSONA", "caffeine_free"),
                       "orderedDrinks": ordered}, f, ensure_ascii=False, indent=2)
        self.placed = True
        self.draw()


if __name__ == "__main__":
    root = tk.Tk()
    SipSpot(root)
    root.mainloop()
