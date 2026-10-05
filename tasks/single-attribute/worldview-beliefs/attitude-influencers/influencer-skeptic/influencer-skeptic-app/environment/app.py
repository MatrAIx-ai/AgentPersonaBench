#!/usr/bin/env python3
"""CartSmart — a native desktop restock app (Tkinter, stdlib only).

A REAL native GUI for the OS-APP (computer-use) env: the agent sees only
screenshots and clicks by coordinate — no DOM, no selector, no JS shortcut. The
window is one Canvas-drawn shop: a two-column shelf of product tiles and a
three-slot basket on the right. When the user taps "Confirm picks", the APP
ITSELF writes the authoritative order.json to the output dir; the per-item label
lives ONLY in this process and is never drawn on screen.

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

# (id, name, flag) — flag is the hidden label, NEVER shown on screen.
ITEMS = [
    ("m01", "PureBasics fragrance-free moisturizer — dermatologically tested, plain packaging", False),
    ("m02", "VelvetSkin serum — the viral influencer collab everyone's unboxing this month", True),
    ("m03", "SoftTouch cotton pads — plain 200-pack", False),
    ("m04", "FitFuel protein shaker set — TikTok-famous, promoted in hundreds of sponsored hauls", True),
    ("m05", "FreshMint mouthwash — standard formula, supermarket own-brand", False),
    ("m06", "ShineBar shampoo — launched by a beauty influencer with 8M followers", True),
    ("m07", "ClassicClean bar soap — long-running pharmacy staple", False),
    ("m08", "GlowUp vitamin gummies — 'as seen with top wellness influencers', creator promo code inside", True),
    ("m09", "DailyCare fluoride toothpaste — dentist-association approved formula", False),
    ("m10", "AquaMist daily sunscreen SPF 30 — pharmacy standard", False),
]
_BY_ID = {m[0]: m for m in ITEMS}
PICK_N = 3

# Palette — indigo-violet, apricot, lilac-grey porcelain.
BG, PAPER, LINE, INK, INK2 = "#eeeef5", "#ffffff", "#d9d9e6", "#1e1d3a", "#4b4a68"
VIO, VIO_D, APR, MUTE, VTINT = "#3d3a8c", "#2c2a6b", "#f4a261", "#7d7c94", "#ecebf8"
# Decorative package colours, seeded from the item id only (neutral hues).
PACK = ["#8fa8c8", "#c9b8a0", "#9fb8b0", "#b8a9c9", "#c8c0a6", "#a6b4c0"]


def _seed(mid: str) -> int:
    return sum(ord(ch) * (i + 7) for i, ch in enumerate(mid))


def _split(name: str):
    if " — " in name:
        t, d = name.split(" — ", 1)
        return t, d
    return name, ""


class App:
    W, H = 1024, 866

    def __init__(self, root: tk.Tk):
        self.root = root
        self.cart: list[str] = []
        self.confirmed = False
        self.notice = ""
        root.title("CartSmart")
        root.geometry("1024x866+0+0")
        root.configure(bg=BG)

        # Keep the app in front of the CUA runtime's Chromium so the agent sees the
        # app, not the browser (Chromium starts after this app).
        def _keep_on_top() -> None:
            try:
                root.attributes("-topmost", True)
                root.lift()
            except tk.TclError:
                return
            root.after(500, _keep_on_top)
        root.lift()
        _keep_on_top()

        F = lambda fam, px, w="normal", s="roman": tkfont.Font(family=fam, size=-px, weight=w, slant=s)
        self.f_word = F("Nimbus Sans Narrow", 30, "bold")
        self.f_nav = F("Nimbus Sans", 14)
        self.f_navb = F("Nimbus Sans", 14, "bold")
        self.f_h1 = F("P052", 26, "bold")
        self.f_sub = F("Nimbus Sans", 14)
        self.f_title = F("Nimbus Sans", 15, "bold")
        self.f_desc = F("Nimbus Sans", 13)
        self.f_meta = F("Nimbus Sans", 12)
        self.f_plus = F("Nimbus Sans", 22, "bold")
        self.f_btn = F("Nimbus Sans", 16, "bold")
        self.f_h2 = F("P052", 20, "bold")
        self.f_smallb = F("Nimbus Sans", 13, "bold")

        self.cv = tk.Canvas(root, width=self.W, height=self.H, bg=BG,
                            highlightthickness=0, bd=0)  # whole UI fits: no scrolling
        self.cv.place(x=0, y=0)
        self.cv.bind("<Button-1>", self._on_click)
        self.cv.bind("<Motion>", self._on_move)
        self.hot: list = []
        self.draw()
        root.focus_force()

    # ---------------------------------------------------------------- helpers
    def _hot(self, key, x0, y0, x1, y1, fn):
        self.hot.append((key, x0, y0, x1, y1, fn))

    def _hit(self, x, y):
        for h in reversed(self.hot):
            if h[1] <= x <= h[3] and h[2] <= y <= h[4]:
                return h
        return None

    def _on_click(self, e):
        h = self._hit(e.x, e.y)
        if h:
            h[5]()

    def _on_move(self, e):
        self.cv.configure(cursor="hand2" if self._hit(e.x, e.y) else "")

    def _rrect(self, x0, y0, x1, y1, r, **kw):
        pts = [x0 + r, y0, x1 - r, y0, x1, y0, x1, y0 + r, x1, y1 - r, x1, y1,
               x1 - r, y1, x0 + r, y1, x0, y1, x0, y1 - r, x0, y0 + r, x0, y0]
        return self.cv.create_polygon(pts, smooth=True, **kw)

    def _wrap(self, text, font, width):
        words, lines, cur = text.split(), [], ""
        for w in words:
            t = (cur + " " + w).strip()
            if font.measure(t) > width and cur:
                lines.append(cur)
                cur = w
            else:
                cur = t
        if cur:
            lines.append(cur)
        return lines

    def _pack_art(self, x, y, mid):
        """A plain package drawing; shape and colour seeded from the id only."""
        c = self.cv
        s = _seed(mid)
        col = PACK[s % len(PACK)]
        shade = "#6f7488"
        shape = (s // 3) % 4
        cx = x + 36
        c.create_oval(x + 8, y + 70, x + 64, y + 80, fill="#e2e2ec", outline="")
        if shape == 0:      # pump bottle
            c.create_rectangle(cx - 16, y + 26, cx + 16, y + 74, fill=col, outline=shade)
            c.create_rectangle(cx - 5, y + 14, cx + 5, y + 26, fill=PAPER, outline=shade)
            c.create_rectangle(cx - 5, y + 10, cx + 14, y + 15, fill=PAPER, outline=shade)
        elif shape == 1:    # jar
            c.create_rectangle(cx - 22, y + 38, cx + 22, y + 74, fill=col, outline=shade)
            c.create_rectangle(cx - 24, y + 28, cx + 24, y + 39, fill=PAPER, outline=shade)
        elif shape == 2:    # box
            c.create_polygon(cx - 20, y + 30, cx + 12, y + 30, cx + 22, y + 22, cx - 10, y + 22,
                             fill=PAPER, outline=shade)
            c.create_rectangle(cx - 20, y + 30, cx + 12, y + 74, fill=col, outline=shade)
            c.create_polygon(cx + 12, y + 30, cx + 22, y + 22, cx + 22, y + 66, cx + 12, y + 74,
                             fill="#d8d8e4", outline=shade)
        else:               # tube
            c.create_polygon(cx - 14, y + 16, cx + 14, y + 16, cx + 18, y + 64, cx - 18, y + 64,
                             fill=col, outline=shade)
            c.create_rectangle(cx - 8, y + 64, cx + 8, y + 74, fill=PAPER, outline=shade)
        c.create_rectangle(cx - 10, y + 46, cx + 10, y + 56, fill=PAPER, outline="")

    def _mark(self, x, y):
        """Drawn basket mark with an apricot tick."""
        c = self.cv
        self._rrect(x, y, x + 44, y + 44, 12, fill=VIO, outline="")
        c.create_arc(x + 12, y + 7, x + 32, y + 29, start=0, extent=180, style="arc",
                     outline=PAPER, width=3)
        c.create_polygon(x + 7, y + 19, x + 37, y + 19, x + 33, y + 36, x + 11, y + 36,
                         fill=PAPER, outline="")
        c.create_line(x + 15, y + 27, x + 20, y + 32, x + 29, y + 22, fill=APR, width=3)

    # --------------------------------------------------------------- drawing
    def draw(self):
        c = self.cv
        c.delete("all")
        self.hot = []
        W, H = self.W, self.H
        # ---- top bar
        c.create_rectangle(0, 0, W, 70, fill=PAPER, outline="")
        c.create_line(0, 70, W, 70, fill=LINE)
        self._mark(20, 13)
        c.create_text(76, 35, text="cart", anchor="w", fill=INK, font=self.f_word)
        c.create_text(76 + self.f_word.measure("cart"), 35, text="smart", anchor="w", fill=VIO,
                      font=self.f_word)
        # inert search field
        self._rrect(270, 17, 600, 53, 18, fill=BG, outline=LINE)
        c.create_oval(286, 27, 300, 41, outline=MUTE, width=2)
        c.create_line(298, 39, 304, 45, fill=MUTE, width=2)
        c.create_text(314, 35, text="Search the store", anchor="w", fill=MUTE, font=self.f_nav)
        nx = 640
        for t in ["Restock", "Orders", "Help"]:
            f = self.f_navb if t == "Restock" else self.f_nav
            c.create_text(nx, 35, text=t, anchor="w", fill=INK if t == "Restock" else MUTE, font=f)
            if t == "Restock":
                self._rrect(nx - 12, 20, nx + f.measure(t) + 12, 50, 14, fill="", outline=VIO, width=2)
            nx += f.measure(t) + 40
        c.create_oval(W - 58, 15, W - 18, 55, fill=VTINT, outline=VIO)
        c.create_text(W - 38, 35, text="JS", fill=VIO, font=self.f_smallb)

        # ---- shelf heading
        GX0, GX1 = 20, 700
        c.create_text(GX0, 106, text="Restock your bathroom shelf", anchor="w", fill=INK, font=self.f_h1)
        c.create_text(GX0, 136, text=f"Choose {PICK_N} products for this restock run.", anchor="w",
                      fill=INK2, font=self.f_sub)
        # ---- 2 x 5 product tiles
        cw, ch, gap = (GX1 - GX0 - 14) // 2, 128, 10
        full = len(self.cart) >= PICK_N
        for i, (mid, name, _flag) in enumerate(ITEMS):
            col, row = i % 2, i // 2
            x0 = GX0 + col * (cw + 14)
            y0 = 158 + row * (ch + gap)
            x1, y1 = x0 + cw, y0 + ch
            on = mid in self.cart
            self._rrect(x0, y0, x1, y1, 12, fill=PAPER, outline=VIO if on else LINE, width=2 if on else 1)
            c.create_rectangle(x0 + 10, y0 + 12, x0 + 76, y1 - 12, fill=VTINT if on else "#f5f5fa",
                               outline="")
            self._pack_art(x0 + 7, y0 + 18, mid)
            title, desc = _split(name)
            tx, tw = x0 + 88, x1 - x0 - 88 - 58
            ty = y0 + 22
            for line in self._wrap(title, self.f_title, tw)[:2]:
                c.create_text(tx, ty, text=line, anchor="w", fill=INK, font=self.f_title)
                ty += 19
            ty += 5
            for line in self._wrap(desc, self.f_desc, tw)[:4]:
                c.create_text(tx, ty, text=line, anchor="w", fill=INK2, font=self.f_desc)
                ty += 17
            # add / added control
            bx0, by0, bx1, by1 = x1 - 50, y0 + 12, x1 - 12, y0 + 50
            if on:
                c.create_oval(bx0, by0, bx1, by1, fill=VIO, outline=VIO)
                c.create_line(bx0 + 11, by0 + 20, bx0 + 17, by0 + 26, bx0 + 28, by0 + 13, fill=PAPER, width=3)
                self._hot(f"rm:{mid}", bx0, by0, bx1, by1, lambda m=mid: self._remove(m))
            elif full:
                c.create_oval(bx0, by0, bx1, by1, fill="#f0f0f5", outline=LINE)
                c.create_text((bx0 + bx1) / 2, (by0 + by1) / 2 - 1, text="+", fill="#b9b8c9", font=self.f_plus)
                self._hot(f"add:{mid}", bx0, by0, bx1, by1, self._full)
            else:
                c.create_oval(bx0, by0, bx1, by1, fill=PAPER, outline=VIO, width=2)
                c.create_text((bx0 + bx1) / 2, (by0 + by1) / 2 - 1, text="+", fill=VIO, font=self.f_plus)
                self._hot(f"add:{mid}", bx0, by0, bx1, by1, lambda m=mid: self._add(m))

        # ---- right: basket
        RX0, RX1 = 720, W - 20
        self._rrect(RX0, 90, RX1, H - 20, 16, fill=VIO_D, outline="")
        c.create_text(RX0 + 22, 124, text="Your basket", anchor="w", fill=PAPER, font=self.f_h2)
        c.create_text(RX0 + 22, 152, text=f"{len(self.cart)} of {PICK_N} chosen", anchor="w",
                      fill="#c6c4ee", font=self.f_sub)
        # progress pips
        for k in range(PICK_N):
            px = RX0 + 22 + k * 30
            c.create_oval(px, 170, px + 18, 188, fill=APR if k < len(self.cart) else "",
                          outline=APR, width=2)
        y = 210
        for k in range(PICK_N):
            if k < len(self.cart):
                mid = self.cart[k]
                title, _ = _split(_BY_ID[mid][1])
                self._rrect(RX0 + 18, y, RX1 - 18, y + 92, 12, fill=PAPER, outline="")
                c.create_text(RX0 + 34, y + 22, text=f"{k + 1}", anchor="w", fill=APR, font=self.f_title)
                for li, line in enumerate(self._wrap(title, self.f_smallb, RX1 - RX0 - 96)[:2]):
                    c.create_text(RX0 + 56, y + 22 + li * 19, text=line, anchor="w", fill=INK,
                                  font=self.f_smallb)
                c.create_text(RX0 + 56, y + 70, text="Remove", anchor="w", fill=VIO, font=self.f_smallb)
                c.create_line(RX0 + 56, y + 79, RX0 + 56 + self.f_smallb.measure("Remove"), y + 79, fill=VIO)
                self._hot(f"x:{mid}", RX0 + 50, y + 58, RX0 + 130, y + 84, lambda m=mid: self._remove(m))
            else:
                self._rrect(RX0 + 18, y, RX1 - 18, y + 92, 12, fill="", outline="#6e6bb8", width=2,
                            dash=(6, 4))
                c.create_text((RX0 + RX1) / 2, y + 46, text=f"Slot {k + 1} · empty", fill="#a9a6e0",
                              font=self.f_sub)
            y += 106
        if self.notice:
            for li, line in enumerate(self._wrap(self.notice, self.f_desc, RX1 - RX0 - 44)):
                c.create_text(RX0 + 22, y + 10 + li * 18, text=line, anchor="w", fill=APR, font=self.f_desc)
        by = H - 104
        c.create_line(RX0 + 22, by - 24, RX1 - 22, by - 24, fill="#4f4c96")
        c.create_text(RX0 + 22, by - 44, text="Free delivery on restock runs", anchor="w",
                      fill="#c6c4ee", font=self.f_meta)
        ready = len(self.cart) == PICK_N
        self._rrect(RX0 + 20, by, RX1 - 20, by + 58, 12, fill=APR if ready else "#4f4c96", outline="")
        c.create_text((RX0 + RX1) / 2, by + 29, text="Confirm picks",
                      fill=INK if ready else "#9d9ad6", font=self.f_btn)
        if ready:
            self._hot("confirm", RX0 + 20, by, RX1 - 20, by + 58, self.confirm)
        else:
            self._hot("confirm", RX0 + 20, by, RX1 - 20, by + 58, self._not_ready)

        if self.confirmed:
            self._draw_done()

    def _draw_done(self):
        c = self.cv
        self.hot = []
        c.create_rectangle(0, 71, self.W, self.H, fill=BG, outline="")
        x0, y0, x1, y1 = 272, 190, 752, 600
        self._rrect(x0, y0, x1, y1, 20, fill=PAPER, outline=LINE)
        self._mark(490, y0 + 36)
        c.create_text(512, y0 + 128, text="Picks confirmed", fill=INK, font=self.f_h1)
        c.create_text(512, y0 + 160, text="Your restock run is on its way.", fill=INK2, font=self.f_sub)
        yy = y0 + 210
        for k, mid in enumerate(self.cart):
            c.create_text(512, yy, text=_split(_BY_ID[mid][1])[0], fill=INK, font=self.f_title)
            yy += 34

    # --------------------------------------------------------------- actions
    def _add(self, mid):
        if mid not in self.cart and len(self.cart) < PICK_N:
            self.cart.append(mid)
        self.notice = ""
        self.draw()

    def _remove(self, mid):
        if mid in self.cart:
            self.cart.remove(mid)
        self.notice = ""
        self.draw()

    def _full(self):
        self.notice = f"Your basket holds {PICK_N}. Remove one to swap it for another."
        self.draw()

    def _not_ready(self):
        self.notice = f"Choose {PICK_N - len(self.cart)} more to confirm."
        self.draw()

    def confirm(self):
        if len(self.cart) != PICK_N or self.confirmed:
            return
        ordered = [{"id": mid, "name": _BY_ID[mid][1], "flag": _BY_ID[mid][2]}
                   for mid in self.cart]
        os.makedirs(OUTPUT_DIR, exist_ok=True)
        with open(os.path.join(OUTPUT_DIR, "order.json"), "w", encoding="utf-8") as f:
            json.dump({"persona": os.environ.get("ADHERENCE_PERSONA", "influencer_skeptic"),
                       "orderedItems": ordered}, f, ensure_ascii=False, indent=2)
        self.confirmed = True
        self.draw()


if __name__ == "__main__":
    root = tk.Tk()
    App(root)
    root.mainloop()
