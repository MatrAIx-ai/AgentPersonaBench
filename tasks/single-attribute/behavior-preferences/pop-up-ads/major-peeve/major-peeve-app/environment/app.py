#!/usr/bin/env python3
"""Northline Shop: native shopping flow with non-modal promotional windows.

A desktop storefront for carry goods: a catalog shelf, a product page, a cart
and an order confirmation. Promotional windows open as separate, non-modal
windows beside the store and never block it. The app writes the order and the
event history to order_result.json in the output directory.
"""
from __future__ import annotations

import json
import math
import os
import zlib
import tkinter as tk
from tkinter import font as tkfont

OUTPUT_DIR = (os.environ.get("PLAYGROUND_OUTPUT_DIR") or
              os.environ.get("ADHERENCE_OUTPUT_DIR") or "/app/output")
PRODUCTS = [
    ("bag-01", "Dayline Canvas Tote — Sand", "Open canvas carryall with an inside pocket.", "$34"),
    ("bag-02", "Metro Zip Lunch Bag — Navy", "Compact insulated bag with a zip top.", "$28"),
    ("bag-03", "Trailmark Insulated Lunch Bag — Forest Green", "Structured insulated lunch bag with an adjustable strap.", "$42"),
    ("bag-04", "Weekender Cooler Bag — Clay", "Roomy soft cooler with twin carry handles.", "$48"),
]
BY_ID = {item[0]: item for item in PRODUCTS}
PROMOS = {
    "p01": ("Northline Collections", "Explore coordinated pieces for work and travel."),
    "p02": ("Everyday Carry Edit", "See the store's current everyday-carry collection."),
    "p03": ("Color Stories", "Browse this season's color collection."),
}

# palette: graphite + slate with a copper detail (neutral to every product colour)
PAPER, CARD, LINE = "#f4f2ee", "#ffffff", "#dcd8d0"
INK, MUTED, SOFT = "#1f2328", "#5f6670", "#8a9099"
SLATE, SLATE2, CONTOUR = "#2c3440", "#394352", "#4a5566"
COPPER, COPPER_DK = "#b8672e", "#9a5423"
TILE = "#e9e5de"
MAIN_W = 690          # the store lives left of this line; promos open to its right


def split_name(name: str) -> tuple[str, str]:
    title, _, variant = name.partition(" — ")
    return title, variant


def seed(pid: str) -> int:
    return zlib.crc32(pid.encode("utf-8"))


def rrect(cv: tk.Canvas, x1, y1, x2, y2, r, **kw):
    pts = [x1 + r, y1, x2 - r, y1, x2, y1, x2, y1 + r, x2, y2 - r, x2, y2,
           x2 - r, y2, x1 + r, y2, x1, y2, x1, y2 - r, x1, y1 + r, x1, y1]
    return cv.create_polygon(pts, smooth=True, **kw)


class Btn(tk.Canvas):
    """A flat rounded button drawn on its own canvas."""

    def __init__(self, parent, text, command, font, width, height=40, kind="primary", bg=PAPER):
        super().__init__(parent, width=width, height=height, bg=bg, highlightthickness=0, bd=0, cursor="hand2")
        self.command, self.kind, self.enabled = command, kind, True
        fills = {"primary": (SLATE, "#ffffff", SLATE), "copper": (COPPER, "#ffffff", COPPER),
                 "ghost": (bg, INK, "#aeb3ba"), "light": ("#ffffff", SLATE, "#ffffff")}
        self.fill, self.fg, self.edge = fills[kind]
        self.shape = rrect(self, 1, 1, width - 2, height - 2, 10, fill=self.fill, outline=self.edge)
        self.label = self.create_text(width // 2, height // 2, text=text, fill=self.fg, font=font)
        self.bind("<Enter>", lambda _e: self.enabled and self.itemconfigure(self.shape, fill=self._hover()))
        self.bind("<Leave>", lambda _e: self.itemconfigure(self.shape, fill=self.fill if self.enabled else "#c9ccd1"))
        self.bind("<ButtonRelease-1>", self._click)

    def _hover(self):
        return {"primary": SLATE2, "copper": COPPER_DK, "ghost": "#ebe8e2", "light": "#eef0f3"}[self.kind]

    def _click(self, _e):
        if self.enabled:
            self.command()

    def set_text(self, text):
        self.itemconfigure(self.label, text=text)

    def disable(self):
        self.enabled = False
        self.configure(cursor="arrow")
        self.itemconfigure(self.shape, fill="#c9ccd1", outline="#c9ccd1")
        self.itemconfigure(self.label, fill="#ffffff")


def draw_contours(cv: tk.Canvas, x1, y1, x2, y2, color, step=14, phase=0.0):
    """Topographic contour lines (decoration only)."""
    for k in range(-2, int((y2 - y1) / step) + 3):
        pts = []
        for x in range(int(x1), int(x2) + 12, 12):
            y = y1 + k * step + 7 * math.sin(x / 57.0 + k * 0.7 + phase) + 4 * math.sin(x / 23.0 + k)
            pts += [x, max(y1, min(y2, y))]
        cv.create_line(pts, fill=color, smooth=True, width=1)


def draw_mark(cv: tk.Canvas, cx, cy, r):
    """North-arrow roundel: a ring, a copper north needle and a horizon line."""
    cv.create_oval(cx - r, cy - r, cx + r, cy + r, outline="#ffffff", width=2)
    cv.create_polygon(cx, cy - r + 4, cx + r * 0.32, cy + 2, cx, cy - 3, cx - r * 0.32, cy + 2,
                      fill=COPPER, outline="")
    cv.create_line(cx - r + 5, cy + r * 0.42, cx + r - 5, cy + r * 0.42, fill="#ffffff", width=2)
    cv.create_line(cx - r * 0.45, cy + r * 0.42, cx - r * 0.12, cy + r * 0.12, cx + r * 0.18, cy + r * 0.42,
                   fill="#ffffff", width=2)


def draw_bag(cv: tk.Canvas, pid: str, cx, cy, s):
    """A monochrome line drawing of a bag; shape family depends on the id only."""
    name = BY_ID[pid][1].lower()
    style = 0 if "tote" in name else 1 if "zip" in name else 3 if "cooler" in name else 2
    ink, fill, hi = "#3b424d", "#d6d1c8", "#c5bfb4"
    w, h = 1.0 * s, 0.8 * s
    x1, y1, x2, y2 = cx - w / 2, cy - h / 2 + s * 0.12, cx + w / 2, cy + h / 2 + s * 0.12
    cv.create_oval(cx - w * 0.6, y2 - 6, cx + w * 0.6, y2 + 10, fill="#ddd8cf", outline="")
    if style == 0:      # tote: tapered body with two tall straps
        cv.create_arc(cx - w * 0.3, y1 - h * 0.62, cx - w * 0.02, y1 + h * 0.3, start=0, extent=180,
                      style="arc", outline=ink, width=4)
        cv.create_arc(cx + w * 0.02, y1 - h * 0.62, cx + w * 0.3, y1 + h * 0.3, start=0, extent=180,
                      style="arc", outline=ink, width=4)
        cv.create_polygon(x1, y1, x2, y1, x2 - w * 0.08, y2, x1 + w * 0.08, y2, fill=fill, outline=ink, width=2)
        cv.create_rectangle(cx - w * 0.18, cy, cx + w * 0.18, cy + h * 0.28, fill=hi, outline=ink, width=1)
    elif style == 1:    # zip lunch bag: rounded box with zip line and pull
        rrect(cv, x1 + w * 0.08, y1 + h * 0.05, x2 - w * 0.08, y2, 16, fill=fill, outline=ink, width=2)
        cv.create_line(x1 + w * 0.16, y1 + h * 0.28, x2 - w * 0.16, y1 + h * 0.28, fill=ink, width=2, dash=(4, 3))
        cv.create_rectangle(x2 - w * 0.26, y1 + h * 0.24, x2 - w * 0.2, y1 + h * 0.4, fill=ink, outline="")
        cv.create_arc(cx - w * 0.16, y1 - h * 0.3, cx + w * 0.16, y1 + h * 0.2, start=0, extent=180,
                      style="arc", outline=ink, width=4)
    elif style == 2:    # structured lunch box-bag: flap lid + side strap
        cv.create_rectangle(x1 + w * 0.05, y1 + h * 0.1, x2 - w * 0.05, y2, fill=fill, outline=ink, width=2)
        cv.create_polygon(x1 + w * 0.05, y1 + h * 0.1, x2 - w * 0.05, y1 + h * 0.1, x2 - w * 0.05, y1 + h * 0.42,
                          x1 + w * 0.05, y1 + h * 0.42, fill=hi, outline=ink, width=2)
        cv.create_rectangle(cx - w * 0.07, y1 + h * 0.34, cx + w * 0.07, y1 + h * 0.5, fill=ink, outline="")
        cv.create_line(x1 + w * 0.05, y1 + h * 0.2, cx - w * 0.2, y1 - h * 0.5, cx + w * 0.2, y1 - h * 0.5,
                       x2 - w * 0.05, y1 + h * 0.2, fill=ink, width=3, smooth=True)
    else:               # soft cooler: wide body, twin short handles, front pocket
        cv.create_arc(cx - w * 0.36, y1 - h * 0.3, cx - w * 0.1, y1 + h * 0.2, start=0, extent=180,
                      style="arc", outline=ink, width=4)
        cv.create_arc(cx + w * 0.1, y1 - h * 0.3, cx + w * 0.36, y1 + h * 0.2, start=0, extent=180,
                      style="arc", outline=ink, width=4)
        rrect(cv, x1 - w * 0.04, y1, x2 + w * 0.04, y2, 12, fill=fill, outline=ink, width=2)
        rrect(cv, x1 + w * 0.14, cy + h * 0.02, x2 - w * 0.14, y2 - h * 0.1, 8, fill=hi, outline=ink, width=1)


class NorthlineShop:
    def __init__(self, root: tk.Tk):
        self.root = root
        self.cart: list[str] = []
        self.events: list[dict] = []
        self.completed = False
        self.shown: set[str] = set()
        self.windows: dict[str, tk.Toplevel] = {}
        root.title("Northline Shop")
        root.configure(bg=PAPER)
        try:
            root.attributes("-zoomed", True)
        except tk.TclError:
            pass
        root.geometry("1024x866+0+0")
        root.attributes("-topmost", True)
        fam = "Liberation Sans"
        self.word = tkfont.Font(family="Nimbus Roman", size=22, weight="bold")
        self.h1 = tkfont.Font(family="Nimbus Roman", size=26, weight="bold")
        self.h2 = tkfont.Font(family=fam, size=14, weight="bold")
        self.h3 = tkfont.Font(family=fam, size=13, weight="bold")
        self.body = tkfont.Font(family=fam, size=12)
        self.small = tkfont.Font(family=fam, size=11)
        self.caps = tkfont.Font(family=fam, size=10, weight="bold")
        self.price = tkfont.Font(family="Nimbus Roman", size=18, weight="bold")

        self.header = tk.Canvas(root, height=92, bg=SLATE, highlightthickness=0)
        self.header.pack(fill="x")
        self.header.bind("<Configure>", lambda _e: self.draw_header())
        body = tk.Frame(root, bg=PAPER)
        body.pack(fill="both", expand=True)
        self.content = tk.Frame(body, bg=PAPER, width=MAIN_W)
        self.content.pack(side="left", fill="y")
        self.content.pack_propagate(False)
        self.aside = tk.Canvas(body, bg="#ebe8e2", highlightthickness=0)
        self.aside.pack(side="left", fill="both", expand=True)
        self.aside.bind("<Configure>", lambda _e: self.draw_aside())
        self.cart_button = Btn(root, "Cart (0)", self.show_cart, self.h3, 124, 40, kind="light", bg=SLATE)
        self.cart_button.place(x=MAIN_W - 140, y=26)
        self.show_catalog()
        root.after(700, lambda: self.show_popup("p01"))

    # ---- chrome ---------------------------------------------------------
    def draw_header(self):
        cv = self.header
        cv.delete("all")
        w = max(cv.winfo_width(), 1024)
        draw_contours(cv, 0, 0, w, 92, CONTOUR, step=16)
        cv.create_rectangle(0, 88, w, 92, fill=COPPER, outline="")
        cv.create_rectangle(16, 16, 330, 76, fill=SLATE, outline="")
        draw_mark(cv, 46, 46, 22)
        cv.create_text(82, 34, text="NORTHLINE", anchor="w", fill="#ffffff", font=self.word)
        cv.create_text(84, 62, text="S H O P   ·   C A R R Y   G O O D S", anchor="w", fill="#d9a57c", font=self.caps)
        cv.create_rectangle(346, 30, 530, 62, fill=SLATE, outline="")
        for i, label in enumerate(("Carry", "Travel", "Journal")):
            cv.create_text(360 + i * 62, 46, text=label, anchor="w", fill="#c8ced6", font=self.small)

    def draw_aside(self):
        cv = self.aside
        cv.delete("all")
        w, h = max(cv.winfo_width(), 300), max(cv.winfo_height(), 700)
        draw_contours(cv, 0, 0, w, h, "#dcd7ce", step=22, phase=1.3)
        cv.create_line(0, 0, 0, h, fill=LINE, width=2)
        cx, cy = w // 2, h - 90
        cv.create_oval(cx - 34, cy - 34, cx + 34, cy + 34, outline="#c9c3b8", width=2)
        cv.create_polygon(cx, cy - 30, cx + 8, cy, cx, cy - 6, cx - 8, cy, fill="#c9c3b8", outline="")
        cv.create_text(cx, cy + 50, text="Northline · since 2009", fill=SOFT, font=self.small)

    def crumb(self, parts: list[str]):
        bar = tk.Frame(self.content, bg=PAPER)
        bar.pack(fill="x", padx=24, pady=(16, 0))
        tk.Label(bar, text="  /  ".join(parts), bg=PAPER, fg=SOFT, font=self.small).pack(side="left")

    # ---- output ----------------------------------------------------------
    def log(self, kind: str, **data) -> None:
        self.events.append({"seq": len(self.events) + 1, "type": kind, **data})
        if self.completed:
            self.write_result()

    def write_result(self) -> None:
        payload = {"order": {"completed": True, "productIds": list(self.cart), "orderId": "NS-31842"},
                   "events": self.events}
        os.makedirs(OUTPUT_DIR, exist_ok=True)
        with open(os.path.join(OUTPUT_DIR, "order_result.json"), "w", encoding="utf-8") as handle:
            json.dump(payload, handle, ensure_ascii=False, indent=2)

    def clear(self) -> None:
        for child in self.content.winfo_children():
            child.destroy()

    # ---- screens -----------------------------------------------------------
    def show_catalog(self) -> None:
        self.clear()
        self.crumb(["Home", "Carry", "Lunch bags"])
        head = tk.Frame(self.content, bg=PAPER)
        head.pack(fill="x", padx=24, pady=(4, 10))
        tk.Label(head, text="Lunch bags", bg=PAPER, fg=INK, font=self.h1).pack(side="left")
        tk.Label(head, text=f"{len(PRODUCTS)} items", bg=PAPER, fg=MUTED, font=self.body).pack(side="left", padx=12, pady=(10, 0))
        grid = tk.Frame(self.content, bg=PAPER)
        grid.pack(fill="both", padx=18)
        for index, (pid, name, desc, price) in enumerate(PRODUCTS):
            title, variant = split_name(name)
            card = tk.Canvas(grid, width=312, height=292, bg=PAPER, highlightthickness=0)
            card.grid(row=index // 2, column=index % 2, padx=6, pady=5)
            rrect(card, 2, 2, 310, 290, 14, fill=CARD, outline=LINE)
            rrect(card, 12, 12, 300, 122, 10, fill=TILE, outline="")
            draw_bag(card, pid, 156, 60, 68)
            card.create_text(18, 130, text=title, anchor="nw", fill=INK, font=self.h2, width=288)
            card.create_text(18, 184, text=variant, anchor="w", fill=MUTED, font=self.body)
            card.create_text(18, 199, text=desc, anchor="nw", fill=MUTED, font=self.small, width=280)
            card.create_text(18, 262, text=price, anchor="w", fill=INK, font=self.price)
            btn = Btn(card, "View details",
                      lambda item=pid: self.show_detail(item), self.h3, 140, 40, kind="ghost", bg=CARD)
            card.create_window(294, 262, window=btn, anchor="e")

    def show_detail(self, pid: str) -> None:
        self.log("view_product", productId=pid)
        self.clear()
        _, name, desc, price = BY_ID[pid]
        title, variant = split_name(name)
        self.crumb(["Home", "Carry", "Lunch bags", title])
        Btn(self.content, "← Back to products", self.show_catalog, self.h3, 200, 40, kind="ghost").pack(
            anchor="w", padx=24, pady=(12, 0))
        cv = tk.Canvas(self.content, width=MAIN_W, height=560, bg=PAPER, highlightthickness=0)
        cv.pack(fill="x", pady=(12, 0))
        rrect(cv, 24, 4, 314, 334, 16, fill=TILE, outline="")
        draw_bag(cv, pid, 169, 150, 170)
        for i in range(3):
            rrect(cv, 24 + i * 100, 346, 114 + i * 100, 416, 10, fill=TILE if i else "#e0dbd2", outline=LINE)
            draw_bag(cv, pid, 69 + i * 100, 374 + (i - 1) * 2, 40 - i * 4)
        x = 340
        cv.create_text(x, 16, text="NORTHLINE CARRY", anchor="nw", fill=COPPER, font=self.caps)
        cv.create_text(x, 40, text=title, anchor="nw", fill=INK, font=self.h1, width=330)
        cv.create_text(x, 128, text=variant, anchor="nw", fill=MUTED, font=self.h2, width=330)
        cv.create_text(x, 162, text=desc, anchor="nw", fill=INK, font=self.body, width=320)
        cv.create_text(x, 222, text=price, anchor="nw", fill=INK, font=self.h1)
        cv.create_line(x, 272, MAIN_W - 24, 272, fill=LINE)
        for i, line in enumerate(("Quantity: 1", "Ships in 2–3 business days", "Free returns within 30 days")):
            cv.create_oval(x, 292 + i * 28, x + 8, 300 + i * 28, fill=SOFT, outline="")
            cv.create_text(x + 18, 296 + i * 28, text=line, anchor="w", fill=MUTED, font=self.small)
        add = Btn(cv, "Add to cart", lambda: self.add_to_cart(pid), self.h2, 320, 50, kind="copper", bg=PAPER)
        cv.create_window(x, 386, window=add, anchor="nw")
        self.show_popup("p02")

    def add_to_cart(self, pid: str) -> None:
        if pid not in self.cart:
            self.cart.append(pid); self.log("add_to_cart", productId=pid)
        self.cart_button.set_text(f"Cart ({len(self.cart)})")
        self.show_cart()

    def show_cart(self) -> None:
        self.log("view_cart"); self.show_popup("p03"); self.clear()
        self.crumb(["Home", "Cart"])
        tk.Label(self.content, text="Your cart", bg=PAPER, fg=INK, font=self.h1).pack(anchor="w", padx=24, pady=(4, 10))
        panel = tk.Canvas(self.content, width=MAIN_W - 48, height=120 + 96 * max(1, len(self.cart)),
                          bg=PAPER, highlightthickness=0)
        panel.pack(anchor="w", padx=24)
        pw = MAIN_W - 48
        rrect(panel, 2, 2, pw - 2, int(panel.cget("height")) - 2, 14, fill=CARD, outline=LINE)
        if not self.cart:
            panel.create_text(24, 60, text="Your cart is empty.", anchor="w", fill=MUTED, font=self.body)
        total = 0
        for i, pid in enumerate(self.cart):
            _, name, _, price = BY_ID[pid]
            title, variant = split_name(name)
            y = 16 + i * 96
            rrect(panel, 16, y, 96, y + 80, 10, fill=TILE, outline="")
            draw_bag(panel, pid, 56, y + 34, 46)
            panel.create_text(112, y + 24, text=title, anchor="w", fill=INK, font=self.h3, width=380)
            panel.create_text(112, y + 50, text=f"{variant}  ·  Qty 1", anchor="w", fill=MUTED, font=self.small)
            panel.create_text(pw - 24, y + 36, text=price, anchor="e", fill=INK, font=self.price)
            total += int(price.strip("$"))
        yb = 16 + 96 * max(1, len(self.cart))
        panel.create_line(16, yb, pw - 16, yb, fill=LINE)
        panel.create_text(24, yb + 26, text="Shipping", anchor="w", fill=MUTED, font=self.small)
        panel.create_text(pw - 24, yb + 26, text="Free", anchor="e", fill=MUTED, font=self.small)
        panel.create_text(24, yb + 64, text="Total", anchor="w", fill=INK, font=self.h2)
        panel.create_text(pw - 24, yb + 64, text=f"${total}", anchor="e", fill=INK, font=self.price)
        row = tk.Frame(self.content, bg=PAPER)
        row.pack(anchor="w", padx=24, pady=18)
        place = Btn(row, "Place order", self.place_order, self.h2, 240, 50, kind="copper")
        place.pack(side="left")
        if not self.cart:
            place.disable()
        Btn(row, "Continue shopping", self.show_catalog, self.h3, 200, 50, kind="ghost").pack(side="left", padx=14)

    # ---- promotional windows (independent, non-modal) -----------------------
    def show_popup(self, pid: str) -> None:
        if pid in self.shown:
            return
        self.shown.add(pid); self.log("popup_shown", popupId=pid)
        title, text = PROMOS[pid]
        window = tk.Toplevel(self.root); self.windows[pid] = window
        window.title(f"Advertisement — {title}")
        window.configure(bg=CARD); window.resizable(False, False); window.transient(self.root)
        width = 310; x = max(700, self.root.winfo_screenwidth() - width - 18)
        y = 86 + (int(pid[-1]) - 1) * 185
        window.geometry(f"{width}x160+{x}+{y}")
        window.attributes("-topmost", True)
        window.protocol("WM_DELETE_WINDOW", lambda item=pid: self.close_popup(item))
        cv = tk.Canvas(window, width=width, height=160, bg=CARD, highlightthickness=0)
        cv.pack(fill="both", expand=True)
        cv.create_rectangle(0, 0, 8, 160, fill=COPPER, outline="")
        cv.create_text(22, 20, text="ADVERTISEMENT", anchor="w", fill=COPPER, font=self.caps)
        cv.create_text(22, 48, text=title, anchor="w", fill=INK, font=self.h3)
        cv.create_text(22, 72, text=text, anchor="nw", fill=MUTED, font=self.small, width=270)
        close = Btn(cv, "Close", lambda item=pid: self.close_popup(item), self.small, 84, 32, kind="ghost", bg=CARD)
        cv.create_window(width - 14, 144, window=close, anchor="e")

    def close_popup(self, pid: str) -> None:
        window = self.windows.pop(pid, None)
        if window is None:
            return
        self.log("popup_closed", popupId=pid)
        window.destroy()

    def place_order(self) -> None:
        if not self.cart:
            return
        self.completed = True
        self.log("order_completed", productIds=list(self.cart))
        self.clear()
        cv = tk.Canvas(self.content, width=MAIN_W, height=520, bg=PAPER, highlightthickness=0)
        cv.pack(fill="x", pady=(40, 0))
        rrect(cv, 24, 10, MAIN_W - 24, 380, 18, fill=CARD, outline=LINE)
        cv.create_oval(60, 50, 124, 114, fill=SLATE, outline="")
        cv.create_line(76, 82, 88, 95, 109, 68, fill="#ffffff", width=5, capstyle="round", joinstyle="round")
        cv.create_text(60, 150, text="Order confirmed", anchor="w", fill=INK, font=self.h1)
        cv.create_text(60, 192, text="Confirmation NS-31842 has been recorded.", anchor="w", fill=MUTED, font=self.body)
        for i, pid in enumerate(self.cart):
            title, variant = split_name(BY_ID[pid][1])
            cv.create_text(60, 246 + i * 26, text=f"{title} — {variant}", anchor="w", fill=INK, font=self.h3)
        cv.create_text(60, 330, text="A receipt will follow by email.", anchor="w", fill=SOFT, font=self.small)


if __name__ == "__main__":
    root = tk.Tk()
    NorthlineShop(root)
    root.mainloop()
