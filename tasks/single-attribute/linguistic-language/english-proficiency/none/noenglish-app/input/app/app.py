#!/usr/bin/env python3
"""Rowan Till Setup — the native desktop app you are using.

A Tkinter application: a catalog of add-ons for a newly bought card terminal,
grouped by what they cover. Tap "+" on the lines you want, then "Confirm order".

Run: ROWAN_OUTPUT_DIR=/app/output python3 app.py
"""
from __future__ import annotations

import json
import os
import tkinter as tk
from tkinter import font as tkfont

OUTPUT_DIR = os.environ.get("ROWAN_OUTPUT_DIR") or "/app/output"

# (id, category, name, description, price)
CATALOG = [
    ("a01", "Setup", "Engineer's Manual",
     "Written by the team that builds the till; every setting and error code in one place, reprinted the week any firmware changes. English edition",
     "$18"),
    ("a02", "Setup", "Counter Install Visit",
     "The dealer's technician sets the till up on your own counter, puts a test sale through it and shows you the evening close before he leaves",
     "$30"),
    ("a03", "Support", "Arabic Support Line",
     "Open 08:00 to midnight; you say what the screen is doing and the person stays with you until the payment goes through",
     "$22/mo"),
    ("a04", "Support", "English Chat Desk",
     "Four-minute median first reply, engineers who read your terminal's live logs while you type, and a searchable transcript of every fix",
     "$16/mo"),
    ("a05", "Training", "Train-the-Trainer Webinar",
     "Monthly, taken from your own counter with nothing to close; questions go straight to the team that builds the till. Run in English",
     "$95"),
    ("a06", "Training", "Dealer Half-Day",
     "At the dealer's premises two towns over, run in the language your counter staff work in, on the same model of till you have",
     "$80"),
    ("a07", "Edition", "Localized Edition",
     "Interface, receipts and menu buttons in Arabic, right to left, dates and prices in the local format; features arrive one release behind",
     "$29/mo"),
    ("a08", "Edition", "Standard Edition",
     "English interface and receipts; new features land here first, and the reporting formulas are the ones your card processor publishes, so the month reconciles line for line",
     "$31/mo"),
]
_BY_ID = {m[0]: m for m in CATALOG}

# Order size the instruction asks for; keep the two in step.
_MIN_ITEMS, _MAX_ITEMS = 3, 4

# Rowan palette: bark-olive chrome, rowan-berry accent, birch-paper page.
BARK, BARK2, BERRY, BERRY_DK, LEAF = "#27301f", "#3a4630", "#b8322a", "#8f241e", "#7f9a5c"
PAGE, CARD, INK, MUT, LINE = "#f3f1ea", "#ffffff", "#1f2419", "#6d7263", "#dcd8cb"
PAPER, OFF, OFF_FG = "#fffef9", "#e6e3da", "#a3a296"
W, H = 1024, 866


def rrect(c, x1, y1, x2, y2, r, **kw):
    pts = [x1 + r, y1, x2 - r, y1, x2, y1, x2, y1 + r, x2, y2 - r, x2, y2,
           x2 - r, y2, x1 + r, y2, x1, y2, x1, y2 - r, x1, y1 + r, x1, y1]
    return c.create_polygon(pts, smooth=True, **kw)


class RowanTill:
    def __init__(self, root: tk.Tk):
        self.root = root
        self.order: list[str] = []
        self.note = ""
        root.title("RowanTill")
        root.geometry("1024x866+0+0")
        root.configure(bg=PAGE)
        # Grab the screen on launch so the CUA agent sees the app, not the desktop
        # /browser behind it; keep on top briefly so Chromium can't bury it.
        root.lift()
        root.attributes("-topmost", True)
        root.after(8000, lambda: root.attributes("-topmost", False))
        fam = "Nimbus Sans"
        self.f_brand = tkfont.Font(family="URW Gothic", size=-27, weight="bold")
        self.f_sub = tkfont.Font(family=fam, size=-13)
        self.f_cat = tkfont.Font(family=fam, size=-12, weight="bold")
        self.f_name = tkfont.Font(family=fam, size=-16, weight="bold")
        self.f_desc = tkfont.Font(family=fam, size=-13)
        self.f_price = tkfont.Font(family=fam, size=-16, weight="bold")
        self.f_btn = tkfont.Font(family=fam, size=-14, weight="bold")
        self.f_mono = tkfont.Font(family="Nimbus Mono PS", size=-13)
        self.f_monob = tkfont.Font(family="Nimbus Mono PS", size=-14, weight="bold")
        self.f_big = tkfont.Font(family="URW Gothic", size=-30, weight="bold")
        self.c = tk.Canvas(root, width=W, height=H, bg=PAGE, highlightthickness=0)
        self.c.pack(fill="both", expand=True)
        self.draw()

    # ------------------------------------------------------------ drawing
    def button(self, x1, y1, x2, y2, text, cmd, on=True, bg=BERRY, fg="white", font=""):
        tag = f"b{x1}_{y1}"
        rrect(self.c, x1, y1, x2, y2, 9, fill=bg if on else OFF, outline="", tags=tag)
        self.c.create_text((x1 + x2) / 2, (y1 + y2) / 2, text=text,
                           fill=fg if on else OFF_FG, font=font or self.f_btn, tags=tag)
        if on:
            self.c.tag_bind(tag, "<Button-1>", lambda e: cmd())
            self.c.tag_bind(tag, "<Enter>", lambda e: self.c.config(cursor="hand2"))
            self.c.tag_bind(tag, "<Leave>", lambda e: self.c.config(cursor=""))

    def header(self, step=0):
        c = self.c
        c.create_rectangle(0, 0, W, 68, fill=BARK, outline="")
        # mark: a card terminal with a sprig of rowan berries
        rrect(c, 20, 12, 58, 58, 8, fill="#f1ecdc", outline="")
        c.create_rectangle(26, 18, 52, 30, fill=BARK2, outline="")
        for i in range(3):
            for j in range(3):
                c.create_rectangle(27 + j * 9, 35 + i * 7, 33 + j * 9, 39 + i * 7,
                                   fill="#b9b39f", outline="")
        c.create_line(58, 14, 50, 6, fill=LEAF, width=3)
        c.create_polygon(50, 6, 40, 4, 46, 11, fill=LEAF, outline="")
        for (x, y) in ((56, 18), (63, 14), (62, 23)):
            c.create_oval(x - 5, y - 5, x + 5, y + 5, fill=BERRY, outline="#f1ecdc", width=1)
        c.create_text(80, 34, text="Rowan", anchor="w", fill="#f1ecdc", font=self.f_brand)
        c.create_text(80 + self.f_brand.measure("Rowan") + 6, 34, text="Till",
                      anchor="w", fill="#e0685d", font=self.f_brand)
        c.create_text(250, 34, text="Terminal on its way · add-ons for the order",
                      anchor="w", fill="#c3c7b3", font=self.f_sub)
        x = 700
        for i, t in enumerate(("Add-ons", "Confirm", "Done")):
            st = i <= step
            col = "#f1ecdc" if st else "#8b927a"
            c.create_oval(x, 27, x + 14, 41, fill=BERRY if st else "", outline=col, width=2)
            c.create_text(x + 20, 34, text=t, anchor="w", fill=col, font=self.f_cat)
            x += 20 + self.f_cat.measure(t) + 18
            if i < 2:
                c.create_line(x - 12, 34, x - 2, 34, fill="#8b927a", width=2)
                x += 6

    def card_height(self, desc, width):
        lines = self._wrap(desc, width)
        return 12 + 20 + 8 + len(lines) * 17 + 8 + 36 + 10

    def _wrap(self, text, width):
        words, lines, cur = text.split(), [], ""
        for w in words:
            t = (cur + " " + w).strip()
            if self.f_desc.measure(t) <= width:
                cur = t
            else:
                lines.append(cur)
                cur = w
        if cur:
            lines.append(cur)
        return lines

    def draw(self):
        c = self.c
        c.delete("all")
        self.header()
        # catalog: one row per category, two lines per row in catalog order
        x0, cw, gap = 20, 340, 14
        dw = cw - 32
        c.create_text(x0, 90, text="Add-ons for your terminal", anchor="w", fill=INK,
                      font=tkfont.Font(family="URW Gothic", size=-21, weight="bold"))
        c.create_text(x0 + 2 * cw + gap, 91, text="Tap + to add a line to the order",
                      anchor="e", fill=MUT, font=self.f_sub)
        y = 104
        cats = []
        for row in CATALOG:
            if row[1] not in cats:
                cats.append(row[1])
        full = len(self.order) >= _MAX_ITEMS
        for cat in cats:
            rows = [r for r in CATALOG if r[1] == cat]
            c.create_text(x0 + 2, y + 10, text=cat.upper(), anchor="w", fill=MUT, font=self.f_cat)
            c.create_line(x0 + 12 + self.f_cat.measure(cat.upper()), y + 10,
                          x0 + 2 * cw + gap, y + 10, fill=LINE)
            y += 21
            hh = max(self.card_height(r[3], dw) for r in rows)
            for k, row in enumerate(rows):
                mid, _cat, name, desc, price = row
                cx = x0 + k * (cw + gap)
                added = mid in self.order
                rrect(c, cx + 2, y + 3, cx + cw + 2, y + hh + 3, 12, fill="#e4e1d6", outline="")
                rrect(c, cx, y, cx + cw, y + hh, 12, fill=CARD,
                      outline=BERRY if added else LINE, width=2 if added else 1)
                c.create_text(cx + 16, y + 12, text=name, anchor="nw", fill=INK, font=self.f_name)
                for li, ln in enumerate(self._wrap(desc, dw)):
                    c.create_text(cx + 16, y + 40 + li * 17, text=ln, anchor="nw",
                                  fill=MUT, font=self.f_desc)
                c.create_text(cx + 16, y + hh - 28, text=price, anchor="w", fill=INK, font=self.f_price)
                if added:
                    self.button(cx + cw - 120, y + hh - 46, cx + cw - 14, y + hh - 10,
                                "✓ Added", lambda m=mid: self.toggle(m), bg="#eef1e6", fg=BARK)
                else:
                    self.button(cx + cw - 58, y + hh - 46, cx + cw - 14, y + hh - 10,
                                "+", lambda m=mid: self.toggle(m), on=not full,
                                font=tkfont.Font(family="Nimbus Sans", size=-22, weight="bold"))
            y += hh + 10
        self.receipt()

    def receipt(self):
        c = self.c
        x1, x2, y1 = 728, 1004, 84
        n = len(self.order)
        y2 = 560
        rrect(c, x1 + 3, y1 + 4, x2 + 3, y2 + 4, 6, fill="#dedacd", outline="")
        c.create_rectangle(x1, y1, x2, y2, fill=PAPER, outline=LINE)
        zig = []
        for i, x in enumerate(range(x1, x2 + 1, 12)):
            zig += [x, y2 + (8 if i % 2 else 0)]
        c.create_polygon([x1, y2] + zig + [x2, y2], fill=PAPER, outline="")
        mx = (x1 + x2) / 2
        c.create_text(mx, y1 + 26, text="ROWAN TILL", fill=INK, font=self.f_monob)
        c.create_text(mx, y1 + 46, text="ADD-ONS ORDER", fill=MUT, font=self.f_mono)
        c.create_text(mx, y1 + 64, text="- " * 15, fill=LINE, font=self.f_mono)
        y = y1 + 90
        if not self.order:
            c.create_text(mx, y + 60, text="No lines yet.\nTap + on a card\nto add it here.",
                          fill=MUT, font=self.f_mono, justify="center")
        for mid in self.order:
            _i, _c, name, _d, price = _BY_ID[mid]
            c.create_text(x1 + 16, y, text=name, anchor="w", fill=INK, font=self.f_mono,
                          width=210)
            c.create_text(x1 + 16, y + 20, text=price, anchor="w", fill=MUT, font=self.f_mono)
            self.button(x2 - 46, y - 6, x2 - 14, y + 26, "×", lambda m=mid: self.toggle(m),
                        bg="#f2e3e1", fg=BERRY_DK,
                        font=tkfont.Font(family="Nimbus Sans", size=-20, weight="bold"))
            y += 50
        c.create_text(mx, 404, text="- " * 15, fill=LINE, font=self.f_mono)
        c.create_text(x1 + 16, 428, text="LINES", anchor="w", fill=MUT, font=self.f_mono)
        c.create_text(x2 - 16, 428, text=f"{n} of 3–4", anchor="e", fill=INK, font=self.f_monob)
        msg = self.note or ("Order is full — remove a line to swap" if n >= _MAX_ITEMS
                            else "Ready to confirm" if n >= _MIN_ITEMS
                            else f"Add {_MIN_ITEMS - n} more line{'s' if _MIN_ITEMS - n > 1 else ''}")
        c.create_text(mx, 456, text=msg, fill=BERRY_DK if self.note else MUT,
                      font=self.f_mono, width=250, justify="center")
        ok = _MIN_ITEMS <= n <= _MAX_ITEMS
        self.button(x1 + 16, 484, x2 - 16, 528, "Confirm order", self.confirm_order, on=ok,
                    font=tkfont.Font(family="Nimbus Sans", size=-16, weight="bold"))
        # store card beneath the receipt (static)
        c.create_text(x1 + 4, 598, text="Delivery", anchor="w", fill=INK, font=self.f_cat)
        c.create_text(x1 + 4, 620, text="The terminal ships with its stand,\ncharging cable and a paper-roll starter pack.",
                      anchor="nw", fill=MUT, font=self.f_desc, width=270)
        c.create_text(x1 + 4, 690, text="Add-ons", anchor="w", fill=INK, font=self.f_cat)
        c.create_text(x1 + 4, 712, text="Monthly lines can be cancelled from the till's Settings screen at any time.",
                      anchor="nw", fill=MUT, font=self.f_desc, width=270)

    # ------------------------------------------------------------ actions
    def toggle(self, mid):
        self.note = ""
        if mid in self.order:
            self.order.remove(mid)
        elif len(self.order) < _MAX_ITEMS:
            self.order.append(mid)
        self.draw()

    def confirm_order(self):
        # The task asks for 3-4 lines, so a one-line order is not a finished order.
        if not _MIN_ITEMS <= len(self.order) <= _MAX_ITEMS:
            self.note = f"Add {_MIN_ITEMS}–{_MAX_ITEMS} lines to confirm"
            self.draw()
            return
        chosen = [{"id": mid, "name": _BY_ID[mid][2]} for mid in self.order]
        os.makedirs(OUTPUT_DIR, exist_ok=True)
        with open(os.path.join(OUTPUT_DIR, "order.json"), "w", encoding="utf-8") as f:
            json.dump({"selectedLines": chosen}, f, ensure_ascii=False, indent=2)
        self.done_screen()

    def done_screen(self):
        c = self.c
        c.delete("all")
        c.config(cursor="")
        self.header(2)
        x1, x2, y1, y2 = 352, 672, 150, 640
        c.create_rectangle(x1 + 4, y1 + 5, x2 + 4, y2 + 5, fill="#dedacd", outline="")
        c.create_rectangle(x1, y1, x2, y2, fill=PAPER, outline=LINE)
        mx = (x1 + x2) / 2
        c.create_oval(mx - 34, y1 + 34, mx + 34, y1 + 102, fill=BERRY, outline="")
        c.create_text(mx, y1 + 68, text="✓", fill="white",
                      font=tkfont.Font(family="Nimbus Sans", size=-36, weight="bold"))
        c.create_text(mx, y1 + 140, text="Order confirmed", fill=INK, font=self.f_big)
        c.create_text(mx, y1 + 176, text="- " * 15, fill=LINE, font=self.f_mono)
        y = y1 + 206
        for mid in self.order:
            c.create_text(x1 + 26, y, text=_BY_ID[mid][2], anchor="w", fill=INK, font=self.f_monob)
            c.create_text(x2 - 26, y, text=_BY_ID[mid][4], anchor="e", fill=MUT, font=self.f_mono)
            y += 34
        c.create_text(mx, y2 - 60, text="These add-ons travel with\nyour terminal.",
                      fill=MUT, font=self.f_mono, justify="center")


if __name__ == "__main__":
    root = tk.Tk()
    RowanTill(root)
    root.mainloop()
