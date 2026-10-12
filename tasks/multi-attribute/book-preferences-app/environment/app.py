#!/usr/bin/env python3
"""Northbridge Library, a native catalog and two-book checkout application.

Two temporary displays are drawn as face-out shelves of book covers. Select a
cover to read its details in the reading panel, add one book from each display
to the loan slip, and click "Borrow selected books"; the app writes loan.json.
"""

from __future__ import annotations

import json
import os
import random
import tkinter as tk
import zlib
from tkinter import font as tkfont

OUTPUT_DIR = os.environ.get("ADHERENCE_OUTPUT_DIR", "/app/output")

# Visible catalog facts only, keyed by opaque IDs.
BOOKS = [
    ("b01", "Clockwork Vale", "Engineers aboard a distant colony ship discover that its navigation intelligence has invented a hidden destination."),
    ("b03", "Night Water", "Four friends spend a weekend in a lakeside house whose rooms begin changing after dark."),
    ("b07", "Small Fires at Noon", "Poems about city streets, family rituals, ordinary loss, and changing seasons."),
    ("b08", "A Seat by the Window", "A retired surgeon recounts the choices, mistakes, and relationships that shaped four decades of work."),
    ("b09", "Borrowed Aprons", "The author recalls migration, family expectations, a changing relationship with a parent, and starting over in middle age."),
    ("b11", "Under Painted Moons", "Rival heirs cross an enchanted archipelago to recover a city erased by an ancient spell."),
    ("b13", "The Locked Platform", "A detective reconstructs a disappearance from conflicting station-camera records and testimony."),
    ("b14", "The Quiet Ledger", "Case studies show how small organizations price, hire, negotiate, and survive difficult growth decisions."),
    ("b18", "The Useful Meeting", "Field examples explain how organizations make decisions, resolve stalled projects, and assign responsibility."),
    ("b20", "Inside the Tidal Pool", "An accessible explanation of coastal ecosystems, adaptation, and current marine field research."),
]
BOOK_BY_ID = {book[0]: book for book in BOOKS}
DISPLAY_BY_ID = {book_id: ("A" if int(book_id[1:]) <= 10 else "B") for book_id in BOOK_BY_ID}

# Parchment reading room, walnut shelves, oxblood + brass accents.
PARCH, PAPER, INK, MUT = "#efe6d6", "#fbf7ef", "#2a2320", "#6e625a"
WOOD, WOOD_D, OXBLOOD, BRASS = "#7a5436", "#553823", "#7a1f2b", "#c49a45"
# Cover cloth colours, dealt from each book's id only (never from its content).
CLOTH = ("#3f5e6b", "#6c4f6e", "#46624a", "#8a5a3c", "#35486e", "#7b6a3a", "#5b3a3a", "#476b6b")


def _rng(key: str) -> random.Random:
    return random.Random(zlib.crc32(key.encode("utf-8")))


def rrect(cv, x1, y1, x2, y2, r, **kw):
    pts = [x1 + r, y1, x2 - r, y1, x2, y1, x2, y1 + r, x2, y2 - r, x2, y2,
           x2 - r, y2, x1 + r, y2, x1, y2, x1, y2 - r, x1, y1 + r, x1, y1]
    return cv.create_polygon(pts, smooth=True, **kw)


class LibraryApp:
    def __init__(self, root: tk.Tk):
        self.root = root
        self.selected: dict[str, str] = {}
        self.current: str | None = None
        self.done = False
        self.targets: dict[str, tuple] = {}
        root.title("Northbridge Library")
        sw, sh = root.winfo_screenwidth(), root.winfo_screenheight()
        root.geometry(f"{min(sw, 1024)}x{min(sh, 866)}+0+0")
        root.configure(bg=PARCH)
        try:
            root.attributes("-zoomed", True)
        except tk.TclError:
            pass
        root.lift(); root.attributes("-topmost", True)
        root.after(8000, lambda: root.attributes("-topmost", False))

        B = lambda size, w="normal", sl="roman": tkfont.Font(family="URW Bookman", size=size, weight=w, slant=sl)
        N = lambda size, w="normal": tkfont.Font(family="Nimbus Sans", size=size, weight=w)
        self.f_mark = B(21, "bold")
        self.f_kicker = N(12, "bold")
        self.f_ui = N(12)
        self.f_uib = N(13, "bold")
        self.f_shelf = B(15, "bold")
        self.f_cover = B(11, "bold")
        self.f_title = B(20, "bold")
        self.f_desc = B(13, "normal")
        self.f_slip = B(12, "normal", "italic")
        self.f_big = B(32, "bold")

        self.cv = tk.Canvas(root, bg=PARCH, highlightthickness=0)
        self.cv.pack(fill="both", expand=True)
        self._size = (0, 0)
        self.cv.bind("<Configure>", self._on_resize)

    def _on_resize(self, e):
        if (e.width, e.height) != self._size:
            self._size = (e.width, e.height)
            self.render()

    def _click(self, tag, box, fn):
        self.cv.tag_bind(tag, "<Button-1>", lambda e: fn())
        self.cv.tag_bind(tag, "<Enter>", lambda e: self.cv.configure(cursor="hand2"))
        self.cv.tag_bind(tag, "<Leave>", lambda e: self.cv.configure(cursor=""))
        self.targets[tag] = box

    # ------------------------------------------------------------------ #
    def render(self) -> None:
        cv = self.cv
        cv.delete("all")
        self.targets = {}
        W, H = max(self._size[0], 900), max(self._size[1], 760)
        if self.done:
            return self._render_done(W, H)
        right_w = 372
        LW = W - right_w

        # ---- header -------------------------------------------------------
        cv.create_rectangle(0, 0, W, 74, fill=OXBLOOD, outline="")
        cv.create_rectangle(0, 74, W, 78, fill=BRASS, outline="")
        # arched-window crest
        cv.create_arc(22, 16, 62, 56, start=0, extent=180, style="pieslice", fill=BRASS, outline="")
        cv.create_rectangle(22, 36, 62, 60, fill=BRASS, outline="")
        for k in range(3):
            cv.create_rectangle(28 + k * 11, 34, 34 + k * 11, 56, fill=OXBLOOD, outline="")
        cv.create_text(76, 28, anchor="w", text="NORTHBRIDGE LIBRARY", font=self.f_kicker, fill="#f1d9a8")
        cv.create_text(76, 52, anchor="w", text="Choose one book from each display", font=self.f_mark, fill="white")
        cv.create_text(W - 22, 38, anchor="e", width=330, justify="right", font=self.f_ui, fill="#f3e3cf",
                       text="All titles are available today · comparable reading time · hardcover · four-week loan")

        # ---- two face-out displays ----------------------------------------
        y = 92
        shelf_h = (H - y - 20) / 2
        for disp in ("A", "B"):
            self._shelf(disp, 18, y, LW - 14, y + shelf_h - 12)
            y += shelf_h

        # ---- right column: reading panel + loan slip ----------------------
        self._reading_panel(LW, 92, W - 18, H - 262)
        self._loan_slip(LW, H - 250, W - 18, H - 18)

    def _shelf(self, disp, x1, y1, x2, y2):
        cv = self.cv
        books = [b for b in BOOKS if DISPLAY_BY_ID[b[0]] == disp]
        rrect(cv, x1, y1, x2, y2, 14, fill=PAPER, outline="#dccfb8")
        cv.create_text(x1 + 18, y1 + 22, anchor="w", text=f"Display {disp}", font=self.f_shelf, fill=OXBLOOD)
        chosen = self.selected.get(disp)
        cv.create_text(x2 - 18, y1 + 22, anchor="e", font=self.f_ui, fill=MUT,
                       text=f"On your slip: {BOOK_BY_ID[chosen][1]}" if chosen else "Temporary display · 5 books")
        # ledge
        ledge_y = y2 - 30
        cv.create_rectangle(x1 + 10, ledge_y, x2 - 10, ledge_y + 12, fill=WOOD, outline="")
        cv.create_rectangle(x1 + 10, ledge_y + 12, x2 - 10, ledge_y + 18, fill=WOOD_D, outline="")
        n = len(books)
        gap = 14
        cw = (x2 - x1 - 36 - gap * (n - 1)) / n
        ctop = y1 + 44
        for i, (bid, title, _desc) in enumerate(books):
            cx1 = x1 + 18 + i * (cw + gap)
            self._cover(bid, title, cx1, ctop, cx1 + cw, ledge_y)

    def _cover(self, bid, title, x1, y1, x2, y2):
        cv = self.cv
        rng = _rng("cover|" + bid)
        cloth = CLOTH[rng.randrange(len(CLOTH))]
        top = y1 + rng.randint(0, 14)          # slight height variation
        tag = f"book_{bid}"
        is_cur = bid == self.current
        on_slip = bid in self.selected.values()
        if is_cur:
            cv.create_rectangle(x1 - 5, top - 5, x2 + 5, y2 + 1, fill=BRASS, outline="", tags=tag)
        cv.create_rectangle(x1 + 3, top + 3, x2 + 3, y2, fill="#cbbda3", outline="", tags=tag)
        cv.create_rectangle(x1, top, x2, y2, fill=cloth, outline="", tags=tag)
        cv.create_rectangle(x1, top, x1 + 7, y2, fill="#000000", stipple="gray25", outline="", tags=tag)
        # label plate with the title
        px1, px2 = x1 + 11, x2 - 5
        py1 = top + 18
        plate = cv.create_text((px1 + px2) / 2, py1 + 10, anchor="n", width=px2 - px1 - 6, justify="center",
                               text=title, font=self.f_cover, fill=INK, tags=tag)
        bb = cv.bbox(plate)
        pr = cv.create_rectangle(px1, py1, px2, bb[3] + 10, fill="#f4ecd8", outline=BRASS, width=2, tags=tag)
        cv.tag_raise(plate)
        # id-seeded ornament
        oy = bb[3] + 26
        kind = rng.choice(("rules", "diamond", "dots"))
        mx = (x1 + x2) / 2 + 3
        if kind == "rules":
            for k in range(3):
                cv.create_line(px1 + 6, oy + k * 7, px2 - 6, oy + k * 7, fill="#e6d3a6", width=1, tags=tag)
        elif kind == "diamond":
            cv.create_polygon(mx, oy - 8, mx + 10, oy + 4, mx, oy + 16, mx - 10, oy + 4, fill="#e6d3a6",
                              outline="", tags=tag)
        else:
            for k in range(-2, 3):
                cv.create_oval(mx + k * 12 - 3, oy, mx + k * 12 + 3, oy + 6, fill="#e6d3a6", outline="", tags=tag)
        if on_slip:
            rrect(cv, x1 + 6, y2 - 34, x2 - 6, y2 - 8, 10, fill=BRASS, outline="", tags=tag)
            cv.create_text((x1 + x2) / 2 + 3, y2 - 21, text="✓ On slip", font=self.f_uib, fill=INK, tags=tag)
        self._click(tag, (x1, top, x2, y2), lambda: self.select(bid))

    def _reading_panel(self, x1, y1, x2, y2):
        cv = self.cv
        rrect(cv, x1, y1, x2, y2, 14, fill=PAPER, outline="#dccfb8")
        cv.create_text(x1 + 20, y1 + 24, anchor="w", text="BOOK DETAILS", font=self.f_kicker, fill=MUT)
        cv.create_line(x1 + 20, y1 + 40, x2 - 20, y1 + 40, fill="#e2d6c1")
        tw = x2 - x1 - 40
        if self.current is None:
            cv.create_text((x1 + x2) / 2, (y1 + y2) / 2 - 10, width=tw, justify="center",
                           text="Select a title on a display to read its details.", font=self.f_desc, fill=MUT)
            return
        bid, title, desc = BOOK_BY_ID[self.current]
        disp = DISPLAY_BY_ID[bid]
        cv.create_text(x1 + 20, y1 + 60, anchor="w", text=f"Display {disp}", font=self.f_uib, fill=OXBLOOD)
        t = cv.create_text(x1 + 20, y1 + 76, anchor="nw", width=tw, text=title, font=self.f_title, fill=INK)
        yy = cv.bbox(t)[3] + 12
        t = cv.create_text(x1 + 20, yy, anchor="nw", width=tw, text=desc, font=self.f_desc, fill="#3d3430")
        yy = cv.bbox(t)[3] + 14
        for fact in ("Available today", "Hardcover", "Four-week loan"):
            cv.create_oval(x1 + 22, yy + 4, x1 + 30, yy + 12, fill=BRASS, outline="")
            cv.create_text(x1 + 38, yy + 8, anchor="w", text=fact, font=self.f_ui, fill=INK)
            yy += 22
        on = self.selected.get(disp) == bid
        other = self.selected.get(disp)
        bx1, by1, bx2, by2 = x1 + 20, y2 - 70, x2 - 20, y2 - 22
        rrect(cv, bx1, by1, bx2, by2, 12, fill=PAPER if on else OXBLOOD, outline=OXBLOOD, width=2, tags="add")
        label = "Remove from loan" if on else ("Swap onto loan slip" if other else "Add to loan")
        cv.create_text((bx1 + bx2) / 2, (by1 + by2) / 2, text=label, font=self.f_uib,
                       fill=OXBLOOD if on else "white", tags="add")
        self._click("add", (bx1, by1, bx2, by2), self.toggle_current)
        if other and not on:
            cv.create_text((x1 + x2) / 2, by1 - 24, width=tw, justify="center", font=self.f_ui, fill=MUT,
                           text=f"Replaces {BOOK_BY_ID[other][1]} (one book per display)")

    def _loan_slip(self, x1, y1, x2, y2):
        cv = self.cv
        rrect(cv, x1 + 3, y1 + 4, x2 + 3, y2 + 4, 6, fill="#d7c9ae", outline="")
        rrect(cv, x1, y1, x2, y2, 6, fill="#fffdf6", outline="#cdbd9d")
        cv.create_text(x1 + 18, y1 + 22, anchor="w", text="LOAN SLIP", font=self.f_kicker, fill=OXBLOOD)
        n = len(self.selected)
        cv.create_text(x2 - 18, y1 + 22, anchor="e", text=f"{n} of 2 displays selected", font=self.f_ui, fill=MUT)
        yy = y1 + 42
        for disp in ("A", "B"):
            cv.create_line(x1 + 18, yy + 34, x2 - 18, yy + 34, fill="#b9c7d8")
            cv.create_text(x1 + 18, yy + 20, anchor="w", text=disp, font=self.f_shelf, fill=OXBLOOD)
            bid = self.selected.get(disp)
            if bid:
                cv.create_text(x1 + 44, yy + 20, anchor="w", width=x2 - x1 - 110, text=BOOK_BY_ID[bid][1],
                               font=self.f_slip, fill=INK)
                tag = f"rm_{disp}"
                bx = x2 - 52
                rrect(cv, bx, yy + 6, bx + 34, yy + 32, 8, fill=PAPER, outline="#cdbd9d", tags=tag)
                cv.create_text(bx + 17, yy + 19, text="✕", font=self.f_uib, fill=OXBLOOD, tags=tag)
                self._click(tag, (bx, yy + 6, bx + 34, yy + 32), lambda d=disp: self._remove(d))
            else:
                cv.create_text(x1 + 44, yy + 20, anchor="w", text=f"one book from Display {disp}",
                               font=self.f_slip, fill="#a39584")
            yy += 46
        ready = set(self.selected) == {"A", "B"}
        bx1, by1, bx2, by2 = x1 + 18, y2 - 66, x2 - 18, y2 - 16
        rrect(cv, bx1, by1, bx2, by2, 12, fill=OXBLOOD if ready else "#cbbfae", outline="", tags="borrow")
        cv.create_text((bx1 + bx2) / 2, (by1 + by2) / 2, text="Borrow selected books", font=self.f_uib,
                       fill="white" if ready else "#8b7f70", tags="borrow")
        self._click("borrow", (bx1, by1, bx2, by2), self.checkout)

    def _render_done(self, W, H):
        cv = self.cv
        cv.create_rectangle(0, 0, W, H, fill=PARCH, outline="")
        cv.create_rectangle(0, 0, W, 10, fill=OXBLOOD, outline="")
        cv.create_arc(W / 2 - 40, 150, W / 2 + 40, 230, start=0, extent=180, style="pieslice", fill=BRASS, outline="")
        cv.create_rectangle(W / 2 - 40, 190, W / 2 + 40, 236, fill=BRASS, outline="")
        cv.create_text(W / 2, 212, text="✓", font=self.f_big, fill=OXBLOOD)
        cv.create_text(W / 2, 290, text="Loan confirmed", font=self.f_big, fill=OXBLOOD)
        cv.create_text(W / 2, 334, text="Two books are ready at the front desk.", font=self.f_desc, fill=INK)
        yy = 380
        for disp in ("A", "B"):
            bid = self.selected[disp]
            rrect(cv, W / 2 - 250, yy, W / 2 + 250, yy + 52, 8, fill="#fffdf6", outline="#cdbd9d")
            cv.create_text(W / 2 - 228, yy + 26, anchor="w", text=f"Display {disp}", font=self.f_uib, fill=OXBLOOD)
            cv.create_text(W / 2 - 110, yy + 26, anchor="w", text=BOOK_BY_ID[bid][1], font=self.f_uib, fill=INK)
            yy += 64

    # ------------------------------------------------------------------ #
    def select(self, bid: str) -> None:
        self.current = bid
        self.render()

    def _remove(self, disp: str) -> None:
        self.selected.pop(disp, None)
        self.render()

    def toggle_current(self) -> None:
        if self.current is None:
            return
        display = DISPLAY_BY_ID[self.current]
        if self.selected.get(display) == self.current:
            del self.selected[display]
        else:
            self.selected[display] = self.current
        self.render()

    def checkout(self) -> None:
        if set(self.selected) != {"A", "B"}:
            return
        selected_ids = [self.selected["A"], self.selected["B"]]
        os.makedirs(OUTPUT_DIR, exist_ok=True)
        with open(os.path.join(OUTPUT_DIR, "loan.json"), "w", encoding="utf-8") as handle:
            json.dump({"submitted": True, "selectedBookIds": selected_ids}, handle, indent=2)
        self.done = True
        self.render()


if __name__ == "__main__":
    app_root = tk.Tk()
    LibraryApp(app_root)
    app_root.mainloop()
