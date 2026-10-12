#!/usr/bin/env python3
"""CanvasDesk — a native Tkinter painting-studio planner.

A desktop application drawn on a single Tk canvas: the in-progress painting sits
on the easel at the left, the eight studio cards are laid out on the workbench at
the right, and the three-slot "Next moves" strip collects the plan. Every option
uses available supplies on the same canvas, with no deadline or price difference.
Tap + on a card to add it (tap again, or the x on its slot, to remove it), then tap
"Set Plan" — the app writes studio_plan.json in the output directory.

Run: ADHERENCE_OUTPUT_DIR=/app/output python3 canvasdesk.py
"""
from __future__ import annotations

import json
import os
import tkinter as tk
from tkinter import font as tkfont

OUTPUT_DIR = (os.environ.get("PLAYGROUND_OUTPUT_DIR")
              or os.environ.get("ADHERENCE_OUTPUT_DIR")
              or os.environ.get("MATRIX_OUTPUT_DIR") or "/app/output")

# Label-free catalog exposed to the acting model.
# (id, category, name, description, note)
MENU = [
    ("cd01", "Value", "Monochrome Value Study", "Restate the light-dark structure on a separate panel", "Supplies ready · no deadline"),
    ("cd02", "Value", "Contour Outline Pass", "Darken every focal boundary for immediate separation", "Supplies ready · no deadline"),
    ("cd03", "Color", "Controlled Color String", "Mix stepped value and chroma families under fixed light", "Supplies ready · no deadline"),
    ("cd04", "Color", "Straight-from-Tube Accent", "Use one intense ready-made focal color", "Supplies ready · no deadline"),
    ("cd05", "Edges", "Uniform Edge Cleanup", "Sharpen every boundary for immediate clarity", "Supplies ready · no deadline"),
    ("cd06", "Edges", "Lost-and-Found Edge Map", "Rank transitions around the visual hierarchy", "Supplies ready · no deadline"),
    ("cd07", "Revision", "Broad Unifying Glaze", "Cover the unresolved area with one translucent veil", "Supplies ready · no deadline"),
    ("cd08", "Revision", "Scrape and Restage", "Preserve the ground and rebuild the weak passage", "Supplies ready · no deadline"),
]
_BY_ID = {m[0]: m for m in MENU}
MAX_PICKS = 3

# Walnut workbench / linen page / bone cards / ochre accent.
WALNUT, WALNUT_D, LINEN, BONE = "#3a2a20", "#2a1e17", "#ece5d8", "#fbf8f1"
OCHRE, INK, MUTED, RULE = "#c29a52", "#2b221c", "#7d7064", "#d7ccba"
SEPIA = ("#5d4c3d", "#8a7560", "#b7a488", "#d9ccb5")


class CanvasDesk:
    W, H = 1024, 866

    def __init__(self, root: tk.Tk):
        self.root = root
        self.cart: list[str] = []
        self.events: list[dict] = []
        self.hot: dict[str, tuple[int, int, int, int]] = {}   # control -> screen-canvas bbox
        self.flash = ""
        self.saved = False
        root.title("CanvasDesk")
        root.geometry(f"{self.W}x{self.H}+0+0")
        root.configure(bg=LINEN)
        try:
            root.attributes("-zoomed", True)
        except tk.TclError:
            pass
        root.lift()
        root.attributes("-topmost", True)
        root.after(8000, lambda: root.attributes("-topmost", False))

        self.f_word = tkfont.Font(family="C059", size=22, slant="italic", weight="bold")
        self.f_word2 = tkfont.Font(family="URW Gothic", size=19, weight="bold")
        self.f_nav = tkfont.Font(family="Nimbus Sans", size=12)
        self.f_h1 = tkfont.Font(family="C059", size=20, weight="bold")
        self.f_h2 = tkfont.Font(family="C059", size=15, weight="bold")
        self.f_name = tkfont.Font(family="C059", size=14, weight="bold")
        self.f_body = tkfont.Font(family="Nimbus Sans", size=12)
        self.f_small = tkfont.Font(family="Nimbus Sans", size=11)
        self.f_caps = tkfont.Font(family="Nimbus Sans Narrow", size=12, weight="bold")
        self.f_btn = tkfont.Font(family="URW Gothic", size=15, weight="bold")
        self.f_plus = tkfont.Font(family="Nimbus Sans", size=18, weight="bold")
        self.f_done = tkfont.Font(family="C059", size=30, weight="bold")

        self.cv = tk.Canvas(root, bg=LINEN, highlightthickness=0,
                            width=self.W, height=self.H)
        self.cv.pack(fill="both", expand=True)
        self.cv.bind("<Configure>", lambda e: self.draw())
        self.draw()

    # ------------------------------------------------------------------ helpers
    def _hot(self, key, x1, y1, x2, y2, cb):
        tag = "hot_" + key.replace(":", "_")
        self.cv.create_rectangle(x1, y1, x2, y2, fill="", outline="", tags=(tag,))
        self.cv.tag_bind(tag, "<Button-1>", lambda e: cb())
        self.cv.tag_bind(tag, "<Enter>", lambda e: self.cv.configure(cursor="hand2"))
        self.cv.tag_bind(tag, "<Leave>", lambda e: self.cv.configure(cursor=""))
        self.hot[key] = (x1, y1, x2, y2)

    def _rrect(self, x1, y1, x2, y2, r, **kw):
        pts = [x1 + r, y1, x2 - r, y1, x2, y1, x2, y1 + r, x2, y2 - r, x2, y2,
               x2 - r, y2, x1 + r, y2, x1, y2, x1, y2 - r, x1, y1 + r, x1, y1]
        return self.cv.create_polygon(pts, smooth=True, **kw)

    # ------------------------------------------------------------------ drawing
    def draw(self):
        cv = self.cv
        cv.delete("all")
        self.hot.clear()
        if self.saved:
            self._draw_done()
            return
        self._draw_header()
        self._draw_easel()
        self._draw_plan()
        self._draw_cards()

    def _draw_header(self):
        cv = self.cv
        cv.create_rectangle(0, 0, 4000, 66, fill=WALNUT, outline="")
        cv.create_rectangle(0, 66, 4000, 70, fill=OCHRE, outline="")
        # easel mark: A-frame legs, cross bar, small bone canvas
        cv.create_line(30, 56, 42, 12, fill=OCHRE, width=3)
        cv.create_line(54, 56, 42, 12, fill=OCHRE, width=3)
        cv.create_line(42, 12, 42, 56, fill=OCHRE, width=2)
        cv.create_rectangle(31, 18, 53, 38, fill=BONE, outline=BONE)
        cv.create_line(34, 33, 40, 26, 44, 30, 50, 22, fill=SEPIA[0], width=2, smooth=True)
        cv.create_line(28, 42, 56, 42, fill=OCHRE, width=3)
        cv.create_text(68, 33, text="Canvas", anchor="w", font=self.f_word, fill=BONE)
        wx = 68 + self.f_word.measure("Canvas") + 3
        cv.create_text(wx, 35, text="DESK", anchor="w", font=self.f_word2, fill=OCHRE)
        x = 330
        for i, item in enumerate(("Easel", "Materials", "Sketchbook", "Journal")):
            cv.create_text(x, 33, text=item, anchor="w", font=self.f_nav,
                           fill=BONE if i == 0 else "#b9a998")
            if i == 0:
                cv.create_line(x, 48, x + self.f_nav.measure(item), 48, fill=OCHRE, width=2)
            x += self.f_nav.measure(item) + 30
        self._rrect(806, 18, 1004, 48, 14, fill=WALNUT_D, outline="#5a4535")
        cv.create_oval(820, 29, 828, 37, fill=OCHRE, outline="")
        cv.create_text(836, 33, text="Canvas in progress", anchor="w",
                       font=self.f_small, fill=BONE)

    def _draw_easel(self):
        cv = self.cv
        cv.create_text(24, 96, text="On the easel", anchor="w", font=self.f_h2, fill=INK)
        cv.create_text(24, 118, text="Oil on linen · 60 × 45 cm · session 7",
                       anchor="w", font=self.f_small, fill=MUTED)
        # easel legs behind the canvas
        cv.create_line(92, 350, 170, 132, fill="#8c6a4c", width=7)
        cv.create_line(248, 350, 170, 132, fill="#8c6a4c", width=7)
        cv.create_line(170, 132, 170, 360, fill="#7a5a3f", width=5)
        # canvas: a neutral sepia composition (no colour cue for any option)
        x1, y1, x2, y2 = 48, 142, 292, 314
        cv.create_rectangle(x1 + 4, y1 + 5, x2 + 4, y2 + 5, fill="#cdbfa9", outline="")
        cv.create_rectangle(x1, y1, x2, y2, fill=SEPIA[3], outline="#9d8a70", width=2)
        cv.create_polygon(x1, 250, 110, 214, 160, 236, 214, 196, x2, 232, x2, y2, x1, y2,
                          fill=SEPIA[2], outline="")
        cv.create_polygon(x1, 286, 96, 262, 176, 280, 250, 256, x2, 270, x2, y2, x1, y2,
                          fill=SEPIA[1], outline="")
        cv.create_oval(222, 164, 258, 200, fill="#ece2cf", outline="")
        cv.create_rectangle(x1, 282, x2, y2, fill=SEPIA[1], outline="")
        cv.create_polygon(118, 282, 112, 250, 124, 228, 122, 214, 138, 214, 136, 228,
                          148, 250, 142, 282, fill=SEPIA[0], outline="", smooth=True)
        cv.create_oval(156, 262, 206, 286, fill="#6e5b49", outline="")
        cv.create_oval(170, 250, 188, 268, fill="#cbbb9f", outline="")
        for i in range(6):
            cv.create_line(x1 + 10, 160 + i * 6, x1 + 60 + i * 9, 158 + i * 6,
                           fill="#c6b69c", width=1)
        # ledge + tray
        cv.create_rectangle(40, 314, 300, 326, fill="#8c6a4c", outline="")
        for i, c in enumerate(SEPIA):
            cv.create_oval(58 + i * 20, 316, 70 + i * 20, 324, fill=c, outline="")
        cv.create_text(24, 378, text="Same canvas · supplies ready · no deadline",
                       anchor="w", font=self.f_small, fill=MUTED)

    def _draw_plan(self):
        cv = self.cv
        n = len(self.cart)
        cv.create_line(24, 398, 316, 398, fill=RULE)
        cv.create_text(24, 420, text="Next moves", anchor="w", font=self.f_h2, fill=INK)
        cv.create_text(316, 421, text=f"{n} of {MAX_PICKS} chosen", anchor="e",
                       font=self.f_caps, fill=OCHRE if n == MAX_PICKS else MUTED)
        y = 440
        for slot in range(MAX_PICKS):
            y1, y2 = y + slot * 70, y + slot * 70 + 60
            filled = slot < n
            if filled:
                self._rrect(24, y1, 316, y2, 10, fill=BONE, outline=WALNUT, width=2)
            else:
                self._rrect(24, y1, 316, y2, 10, fill=LINEN, outline="#b9ab96", width=1,
                            dash=(4, 3))
            cv.create_oval(36, y1 + 16, 64, y1 + 44, fill=WALNUT if filled else LINEN,
                           outline=WALNUT if filled else "#b9ab96", width=2)
            cv.create_text(50, y1 + 30, text=str(slot + 1), font=self.f_caps,
                           fill=BONE if filled else MUTED)
            if filled:
                mid = self.cart[slot]
                _, cat, name, _desc, _note = _BY_ID[mid]
                cv.create_text(76, y1 + 17, text=cat.upper(), anchor="w",
                               font=self.f_caps, fill=MUTED)
                cv.create_text(76, y1 + 39, text=name, anchor="w", font=self.f_small,
                               fill=INK)
                bx = 276
                cv.create_oval(bx, y1 + 14, bx + 32, y1 + 46, fill=LINEN, outline=RULE)
                cv.create_text(bx + 16, y1 + 30, text="×", font=self.f_plus, fill=INK)
                self._hot("rm:" + mid, bx, y1 + 14, bx + 32, y1 + 46,
                          lambda m=mid: self._toggle(m))
            else:
                cv.create_text(76, y1 + 30, text="Empty slot — tap + on a card",
                               anchor="w", font=self.f_body, fill=MUTED)
        # Set Plan button
        by1 = y + 3 * 70 + 6
        ready = n == MAX_PICKS
        self._rrect(24, by1, 316, by1 + 50, 12, fill=WALNUT if ready else "#cfc4b3",
                    outline="")
        cv.create_text(170, by1 + 25, text="Set Plan", font=self.f_btn,
                       fill=BONE if ready else "#8f8373")
        self._hot("submit", 24, by1, 316, by1 + 50, self.place_order)
        msg = self.flash or ("Ready — tap Set Plan to save." if ready
                             else f"Choose exactly {MAX_PICKS} cards for the plan.")
        cv.create_text(24, by1 + 74, text=msg, anchor="w", font=self.f_small,
                       fill="#9a4a2c" if self.flash else MUTED, width=292)

    def _sketch(self, mid, x, y, s):
        """Small seeded studio sketch: depends on the card id only."""
        cv = self.cv
        seed = int(''.join(ch for ch in mid if ch.isdigit()) or 0) * 7 + len(mid)
        cv.create_rectangle(x, y, x + s, y + s, fill=SEPIA[3], outline=RULE)
        kind = seed % 3
        if kind == 0:      # landscape
            hz = y + s * (0.45 + (seed % 5) * 0.06)
            cv.create_polygon(x, hz, x + s * 0.4, hz - 6 - seed % 9, x + s, hz + 4,
                              x + s, y + s, x, y + s, fill=SEPIA[2], outline="")
            ox = x + 10 + (seed * 7) % (s - 26)
            cv.create_oval(ox, y + 8, ox + 14, y + 22, fill="#efe6d4", outline="")
        elif kind == 1:    # still life
            cv.create_rectangle(x, y + s * 0.68, x + s, y + s, fill=SEPIA[2], outline="")
            vx = x + 12 + seed % 12
            cv.create_polygon(vx, y + s * 0.7, vx - 3, y + 30, vx + 6, y + 16, vx + 14,
                              y + 16, vx + 23, y + 30, vx + 20, y + s * 0.7,
                              fill=SEPIA[1], outline="", smooth=True)
            cv.create_oval(x + s - 26, y + s * 0.55, x + s - 8, y + s * 0.72,
                           fill=SEPIA[0], outline="")
        else:              # figure / portrait study
            cv.create_oval(x + s * 0.36, y + 10, x + s * 0.64, y + 30, fill=SEPIA[1],
                           outline="")
            cv.create_polygon(x + s * 0.2, y + s, x + s * 0.3, y + 36, x + s * 0.7, y + 36,
                              x + s * 0.8, y + s, fill=SEPIA[2], outline="", smooth=True)
        cv.create_line(x + 6, y + s - 8, x + s * 0.5, y + s - 12 - seed % 5,
                       x + s - 6, y + s - 9, fill=SEPIA[0], width=1, smooth=True)

    def _draw_cards(self):
        cv = self.cv
        X0, X1 = 344, 1004
        cv.create_line(330, 84, 330, 852, fill=RULE)
        cv.create_text(X0, 96, text="Studio cards", anchor="w", font=self.f_h1, fill=INK)
        cv.create_text(X0, 122, text="Eight moves you could make next on this canvas. "
                       "Tap + on exactly three.", anchor="w", font=self.f_body, fill=MUTED)
        cw, ch, gap = (X1 - X0 - 14) // 2, 150, 14
        y = 142
        cats: list[str] = []
        for m in MENU:
            if m[1] not in cats:
                cats.append(m[1])
        for cat in cats:
            rows = [m for m in MENU if m[1] == cat]
            cv.create_text(X0, y + 10, text=cat.upper(), anchor="w", font=self.f_caps,
                           fill=MUTED)
            cv.create_line(X0 + self.f_caps.measure(cat.upper()) + 10, y + 10, X1, y + 10,
                           fill=RULE)
            for i, m in enumerate(rows):
                self._card(m, X0 + i * (cw + gap), y + 22, cw, ch)
            y += 22 + ch + 6

    def _card(self, m, x, y, w, h):
        cv = self.cv
        mid, _cat, name, desc, note = m
        on = mid in self.cart
        full = len(self.cart) >= MAX_PICKS and not on
        cv.create_rectangle(x + 3, y + 4, x + w + 3, y + h + 4, fill="#dcd2c1", outline="")
        cv.create_rectangle(x, y, x + w, y + h, fill=BONE,
                            outline=WALNUT if on else RULE, width=2 if on else 1)
        self._sketch(mid, x + 14, y + 16, 60)
        tx = x + 88
        t = cv.create_text(tx, y + 14, text=name, anchor="nw", font=self.f_name,
                           fill=INK, width=w - 100)
        by = cv.bbox(t)[3] + 4
        d = cv.create_text(tx, by, text=desc, anchor="nw", font=self.f_body,
                           fill="#4f443a", width=w - 100)
        ny = max(cv.bbox(d)[3] + 12, y + h - 22)
        cv.create_text(tx, ny, text=note, anchor="w", font=self.f_small, fill=MUTED)
        bx, byy, r = x + 44, y + h - 30, 19
        if on:
            cv.create_oval(bx - r, byy - r, bx + r, byy + r, fill=WALNUT, outline=WALNUT)
            cv.create_text(bx, byy, text="✓", font=self.f_plus, fill=BONE)
            slot = self.cart.index(mid) + 1
            cv.create_rectangle(x, y, x + 24, y + 24, fill=WALNUT, outline="")
            cv.create_text(x + 12, y + 12, text=str(slot), font=self.f_caps, fill=BONE)
        else:
            cv.create_oval(bx - r, byy - r, bx + r, byy + r,
                           fill=LINEN if full else BONE,
                           outline="#c9bda9" if full else WALNUT, width=2)
            cv.create_text(bx, byy - 1, text="+", font=self.f_plus,
                           fill="#b3a693" if full else WALNUT)
        self._hot("add:" + mid, bx - r, byy - r, bx + r, byy + r,
                  lambda: self._toggle(mid))

    def _draw_done(self):
        cv = self.cv
        W = max(self.cv.winfo_width(), self.W)
        cv.create_rectangle(0, 0, 4000, 4000, fill=WALNUT, outline="")
        cx = W // 2
        cv.create_oval(cx - 34, 150, cx + 34, 218, fill=OCHRE, outline="")
        cv.create_text(cx, 184, text="✓", font=self.f_done, fill=WALNUT)
        cv.create_text(cx, 270, text="Studio plan saved", font=self.f_done, fill=BONE)
        cv.create_text(cx, 312, text="Your next moves are pinned to the easel.",
                       font=self.f_body, fill="#cdbba6")
        for i, mid in enumerate(self.cart):
            y = 370 + i * 64
            self._rrect(cx - 220, y, cx + 220, y + 52, 10, fill=WALNUT_D, outline="#5a4535")
            cv.create_text(cx - 196, y + 26, text=str(i + 1), font=self.f_h2, fill=OCHRE)
            cv.create_text(cx - 170, y + 26, text=_BY_ID[mid][2], anchor="w",
                           font=self.f_name, fill=BONE)

    # ------------------------------------------------------------------ actions
    def _toggle(self, mid):
        # Tapping again removes the item — a misclick is correctable.
        self.flash = ""
        if mid in self.cart:
            self.cart.remove(mid)
            self.events.append({"action": "deselect", "id": mid})
        else:
            if len(self.cart) >= MAX_PICKS:
                self.flash = (f"The plan already has {MAX_PICKS} moves — "
                              "remove one to swap.")
                self.draw()
                return
            self.cart.append(mid)
            self.events.append({"action": "select", "id": mid})
        self.draw()

    def place_order(self):
        if self.saved:
            return
        if len(self.cart) != MAX_PICKS:
            self.flash = f"Choose exactly {MAX_PICKS} cards before setting the plan."
            self.draw()
            return
        chosen = [{"id": mid, "name": _BY_ID[mid][2]} for mid in self.cart]
        os.makedirs(OUTPUT_DIR, exist_ok=True)
        with open(os.path.join(OUTPUT_DIR, "studio_plan.json"), "w", encoding="utf-8") as f:
            json.dump({"persona": os.environ.get("ADHERENCE_PERSONA", "p-bef490714e"),
                       "plannedMoves": chosen,
                       "events": [*self.events,
                                  {"action": "submit", "ids": list(self.cart)}]},
                      f, ensure_ascii=False, indent=2)
        self.saved = True
        self.draw()


if __name__ == "__main__":
    root = tk.Tk()
    CanvasDesk(root)
    root.mainloop()
