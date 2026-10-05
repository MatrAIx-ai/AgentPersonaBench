#!/usr/bin/env python3
"""ArchiveWorkbench — the neighborhood archive's release desk (native Tkinter app).

A reading-room style desktop app: every work package is filed as an accession
sheet under its collection. Every package has the same source access,
fact-checking support, publication credit, and Friday deadline.
Tap + on a sheet to put it on your release slip (tap again to take it off), then
tap "Reserve packages" — the app writes archive_plan.json to the output directory.

Run: ADHERENCE_OUTPUT_DIR=/app/output python3 archiveworkbench.py
"""
from __future__ import annotations

import json
import os
import tkinter as tk
from tkinter import font as tkfont

OUTPUT_DIR = (os.environ.get("PLAYGROUND_OUTPUT_DIR")
              or os.environ.get("ADHERENCE_OUTPUT_DIR")
              or os.environ.get("MATRIX_OUTPUT_DIR") or "/app/output")

# (id, category, name, description, note)
MENU = [
    ("aw01", "Oral histories", "SQL ledger + caption kit", "two fixed 6:30 a.m. onsite secure-terminal blocks, handwritten joins and manual row/export reconciliation with no saved recipe; remotely assemble a 1,200-word source-linked release from professionally authored approved modules in 30 minutes; choose sequence and tone while the editor handles final polish", "same verified release and Friday deadline"),
    ("aw02", "Oral histories", "Ledger joins + neighborhood narrative", "two fixed 6:30 a.m. onsite secure-terminal blocks, handwritten SQL joins and manual row/export reconciliation with no saved recipe; complete three fixed two-hour onsite drafting sessions for a 1,200-word source-linked narrative, four revision passes and a fixed two-hour editorial review", "same verified release and Friday deadline"),
    ("aw03", "Housing records", "Builder interviews + voices essay", "remote visual filters, instant preview and a reusable recipe; complete three fixed two-hour onsite drafting sessions for a 1,200-word source-linked voices essay, four revision passes and a fixed two-hour editorial review", "same verified release and Friday deadline"),
    ("aw04", "Housing records", "Builder interviews + form copy", "remote visual filters, instant preview and a reusable recipe; remotely assemble a 1,200-word source-linked release from professionally authored approved modules in 30 minutes; choose sequence and tone while the editor handles final polish", "same verified release and Friday deadline"),
    ("aw05", "Market ledgers", "Builder ledger + caption kit", "remote browser builder with validated joins, instant preview and a reusable recipe; remotely assemble a 1,200-word source-linked release from professionally authored approved modules in 30 minutes; choose sequence and tone while the editor handles final polish", "same verified release and Friday deadline"),
    ("aw06", "Market ledgers", "Builder ledger + neighborhood narrative", "remote browser builder with validated joins, instant preview and a reusable recipe; complete three fixed two-hour onsite drafting sessions for a 1,200-word source-linked narrative, four revision passes and a fixed two-hour editorial review", "same verified release and Friday deadline"),
    ("aw07", "Transit files", "Interview query + voices essay", "two fixed 6:30 a.m. onsite secure-terminal blocks, direct SQL filters and manual row/export reconciliation with no saved recipe; complete three fixed two-hour onsite drafting sessions for a 1,200-word source-linked voices essay, four revision passes and a fixed two-hour editorial review", "same verified release and Friday deadline"),
    ("aw08", "Transit files", "SQL interviews + form copy", "two fixed 6:30 a.m. onsite secure-terminal blocks, direct SQL filters and manual row/export reconciliation with no saved recipe; remotely assemble a 1,200-word source-linked release from professionally authored approved modules in 30 minutes; choose sequence and tone while the editor handles final polish", "same verified release and Friday deadline"),
]
_BY_ID = {m[0]: m for m in MENU}

MAX_PICKS = 2

# Palette: plum-charcoal chrome, stone reading-room canvas, acid-free sheets,
# one ochre accent (used identically for every sheet).
PLUM, PLUM2 = "#2a2231", "#3b3144"
STONE, SHEET, RULE = "#e7e4dc", "#fffdf8", "#d4cfc3"
INK, MUTED, FAINT = "#231f26", "#5d5763", "#8b8590"
OCHRE, OCHRE_D = "#c57d1f", "#9c6014"
BONE = "#f3eee4"


def rrect(cv, x0, y0, x1, y1, r, **kw):
    pts = [x0 + r, y0, x1 - r, y0, x1, y0, x1, y0 + r, x1, y1 - r, x1, y1,
           x1 - r, y1, x0 + r, y1, x0, y1, x0, y1 - r, x0, y0 + r, x0, y0]
    return cv.create_polygon(pts, smooth=True, **kw)


class ArchiveWorkbench:
    def __init__(self, root: tk.Tk):
        self.root = root
        self.cart: list[str] = []
        self.done = False
        self.notice = ""
        root.title("ArchiveWorkbench")
        root.geometry(f"{root.winfo_screenwidth()}x{root.winfo_screenheight()}+0+0")
        root.configure(bg=STONE)
        try:
            root.attributes("-zoomed", True)
        except tk.TclError:
            pass
        root.lift()
        root.attributes("-topmost", True)
        root.after(8000, lambda: root.attributes("-topmost", False))

        fam = set(tkfont.families())
        def pick(*names):
            for n in names:
                if n in fam:
                    return n
            return "TkDefaultFont"
        sans = pick("Nimbus Sans", "Liberation Sans", "DejaVu Sans")
        mono = pick("Nimbus Mono PS", "Liberation Mono", "DejaVu Sans Mono")
        serif = pick("Liberation Serif", "Nimbus Roman", "DejaVu Serif")
        body = pick("Liberation Sans", "DejaVu Sans")
        self.f_word = tkfont.Font(family=sans, size=-24, weight="bold")
        self.f_word2 = tkfont.Font(family=mono, size=-22)
        self.f_tag = tkfont.Font(family=mono, size=-12)
        self.f_nav = tkfont.Font(family=sans, size=-14)
        self.f_coll = tkfont.Font(family=serif, size=-17, weight="bold")
        self.f_mono = tkfont.Font(family=mono, size=-12)
        self.f_monob = tkfont.Font(family=mono, size=-12, weight="bold")
        self.f_name = tkfont.Font(family=serif, size=-17, weight="bold")
        self.f_desc = tkfont.Font(family=body, size=-13)
        self.f_btn = tkfont.Font(family=sans, size=-20, weight="bold")
        self.f_cta = tkfont.Font(family=sans, size=-16, weight="bold")
        self.f_slot = tkfont.Font(family=sans, size=-13)
        self.f_done = tkfont.Font(family=serif, size=-34, weight="bold")

        self.cv = tk.Canvas(root, bg=STONE, highlightthickness=0)
        self.cv.pack(fill="both", expand=True)
        self.cv.bind("<Configure>", lambda e: self.draw())

    # ------------------------------------------------------------------ draw
    def draw(self):
        cv = self.cv
        cv.delete("all")
        W = max(cv.winfo_width(), 900)
        H = max(cv.winfo_height(), 760)
        if self.done:
            self._draw_done(W, H)
            return
        # header
        hh = 66
        cv.create_rectangle(0, 0, W, hh, fill=PLUM, outline="")
        self._mark(18, 12)
        cv.create_text(70, 22, text="Archive", anchor="w", font=self.f_word, fill=BONE)
        wx = 70 + self.f_word.measure("Archive") + 2
        cv.create_text(wx, 23, text="Workbench", anchor="w", font=self.f_word2, fill="#e6b872")
        cv.create_text(71, 48, text="NEIGHBORHOOD ARCHIVE  ·  FRIDAY RELEASE  ·  8 PACKAGES ON FILE", anchor="w",
                       font=self.f_tag, fill="#b7aebf")
        x = W - 20
        for lab in ("Reading room hours", "Finding aids", "Release desk"):
            tw = self.f_nav.measure(lab)
            cv.create_text(x, 33, text=lab, anchor="e", font=self.f_nav,
                           fill=BONE if lab == "Release desk" else "#b7aebf")
            if lab == "Release desk":
                cv.create_line(x - tw, 50, x, 50, fill="#e6b872", width=2)
            x -= tw + 26
        cv.create_rectangle(0, hh, W, hh + 4, fill=OCHRE, outline="")

        # grid of collections
        top = hh + 4 + 4
        foot = 72
        gut = 112
        rows = []
        for m in MENU:
            if not rows or rows[-1][0] != m[1]:
                rows.append((m[1], []))
            rows[-1][1].append(m)
        avail = H - top - foot - 2
        rh = avail / len(rows)
        cw = (W - gut - 20 - 12 - 16) / 2
        for ri, (coll, items) in enumerate(rows):
            y0 = top + ri * rh
            # collection gutter: box label
            bx0, by0, bx1, by1 = 16, y0 + 6, gut - 4, y0 + rh - 6
            cv.create_rectangle(bx0, by0, bx1, by1, fill="#d9d4c8", outline="#c3bdaf")
            cv.create_rectangle(bx0 + 10, by0 + 10, bx1 - 10, by0 + 30, fill=SHEET,
                                outline="#b9b2a3")
            cv.create_text((bx0 + bx1) / 2, by0 + 20, text=f"BOX {ri + 1:02d}",
                           font=self.f_monob, fill=INK)
            cv.create_text(bx0 + 10, by0 + 42, text="COLLECTION", anchor="nw",
                           font=self.f_mono, fill=MUTED)
            cv.create_text(bx0 + 10, by0 + 58, text=coll, anchor="nw", font=self.f_coll,
                           fill=INK, width=bx1 - bx0 - 16)
            # pull hole
            cv.create_oval((bx0 + bx1) / 2 - 14, by1 - 20, (bx0 + bx1) / 2 + 14, by1 - 8,
                           fill="#b9b2a3", outline="")
            for ci, m in enumerate(items):
                x0 = gut + 8 + ci * (cw + 12)
                self._sheet(m, x0, y0 + 6, x0 + cw, y0 + rh - 6)

        # release slip footer
        fy = H - foot
        cv.create_rectangle(0, fy, W, H, fill=PLUM, outline="")
        cv.create_text(20, fy + 22, text="RELEASE SLIP", anchor="w", font=self.f_monob,
                       fill="#e6b872")
        n = len(self.cart)
        cv.create_text(20, fy + 48, anchor="w", font=self.f_slot, fill=BONE,
                       text=self.notice or f"{n} of {MAX_PICKS} packages reserved")
        sx = 300
        sw = (W - 240 - sx - 24) / 2
        for i in range(MAX_PICKS):
            x0 = sx + i * (sw + 10)
            if i < n:
                m = _BY_ID[self.cart[i]]
                rrect(cv, x0, fy + 14, x0 + sw, fy + foot - 14, 8, fill=PLUM2,
                      outline="#e6b872")
                cv.create_text(x0 + 12, fy + foot / 2, anchor="w", font=self.f_slot,
                               fill=BONE, text=f"{i + 1}.  {m[2]}", width=sw - 20)
            else:
                cv.create_rectangle(x0, fy + 14, x0 + sw, fy + foot - 14, outline="#7d7087",
                                    dash=(4, 3))
                cv.create_text(x0 + 12, fy + foot / 2, anchor="w", font=self.f_slot,
                               fill="#9d93a6", text=f"{i + 1}.  empty slot")
        bx0, bx1 = W - 220, W - 18
        tag = "reserve"
        rrect(cv, bx0, fy + 14, bx1, fy + foot - 14, 10, fill=OCHRE, outline="", tags=tag)
        cv.create_text((bx0 + bx1) / 2, fy + foot / 2, text="Reserve packages",
                       font=self.f_cta, fill="white", tags=tag)
        cv.tag_bind(tag, "<Button-1>", lambda e: self.place_order())
        cv.tag_bind(tag, "<Enter>", lambda e: cv.configure(cursor="hand2"))
        cv.tag_bind(tag, "<Leave>", lambda e: cv.configure(cursor=""))

    def _mark(self, x, y):
        cv = self.cv
        # archival box with lid, label and a reading lens
        cv.create_polygon(x, y + 12, x + 8, y + 4, x + 40, y + 4, x + 32, y + 12,
                          fill="#e6b872", outline="")
        cv.create_rectangle(x, y + 12, x + 32, y + 40, fill="#c57d1f", outline="")
        cv.create_polygon(x + 32, y + 12, x + 40, y + 4, x + 40, y + 32, x + 32, y + 40,
                          fill="#9c6014", outline="")
        cv.create_rectangle(x + 6, y + 18, x + 26, y + 26, fill=BONE, outline="")
        cv.create_oval(x + 20, y + 24, x + 38, y + 42, outline=BONE, width=3)
        cv.create_line(x + 35, y + 39, x + 44, y + 48, fill=BONE, width=4)

    def _sheet(self, m, x0, y0, x1, y1):
        cv = self.cv
        mid, _coll, name, desc, note = m
        on = mid in self.cart
        # shadow + sheet
        cv.create_rectangle(x0 + 3, y0 + 3, x1 + 3, y1 + 3, fill="#cfc9bb", outline="")
        cv.create_rectangle(x0, y0, x1, y1, fill=SHEET,
                            outline=OCHRE if on else RULE, width=3 if on else 1)
        # binder punch holes
        for hy in (y0 + 20, y1 - 20):
            cv.create_oval(x0 + 9, hy - 5, x0 + 19, hy + 5, fill=STONE, outline=RULE)
        cv.create_line(x0 + 28, y0 + 8, x0 + 28, y1 - 8, fill="#efd9d5")
        tx = x0 + 38
        cv.create_text(x1 - 12, y1 - 9, anchor="se", font=self.f_mono, fill=FAINT,
                       text=f"ACC. {mid.upper()}")
        cv.create_text(tx, y0 + 10, anchor="nw", font=self.f_name, fill=INK, text=name,
                       width=x1 - tx - 60)
        nh = self.f_name.metrics("linespace")
        cv.create_text(tx, y0 + 13 + nh, anchor="nw", font=self.f_desc, fill=MUTED,
                       text=desc, width=x1 - tx - 58)
        cv.create_text(tx, y1 - 9, anchor="sw", font=self.f_mono, fill=INK,
                       text=f"— {note}")
        # + / check button
        tag = f"btn_{mid}"
        bx0, by0 = x1 - 48, y0 + 10
        cv.create_rectangle(bx0, by0, bx0 + 38, by0 + 38, tags=tag,
                            fill=OCHRE if on else SHEET, outline=OCHRE_D if on else PLUM,
                            width=2)
        cv.create_text(bx0 + 19, by0 + 19, text="✓" if on else "+", tags=tag,
                       font=self.f_btn, fill="white" if on else PLUM)
        cv.tag_bind(tag, "<Button-1>", lambda e, i=mid: self._toggle(i))
        cv.tag_bind(tag, "<Enter>", lambda e: cv.configure(cursor="hand2"))
        cv.tag_bind(tag, "<Leave>", lambda e: cv.configure(cursor=""))

    def _draw_done(self, W, H):
        cv = self.cv
        cv.create_rectangle(0, 0, W, H, fill=PLUM, outline="")
        self._mark(W / 2 - 22, H / 2 - 150)
        cv.create_text(W / 2, H / 2 - 60, text="✓  Packages reserved", font=self.f_done,
                       fill=BONE)
        y = H / 2
        for i, mid in enumerate(self.cart):
            cv.create_text(W / 2, y + i * 30, text=f"{i + 1}.  {_BY_ID[mid][2]}",
                           font=self.f_nav, fill="#e6b872")
        cv.create_text(W / 2, y + 90, text="Your release slip is filed with the archive desk.",
                       font=self.f_slot, fill="#b7aebf")

    # --------------------------------------------------------------- actions
    def _toggle(self, mid):
        if self.done:
            return
        self.notice = ""
        if mid in self.cart:
            self.cart.remove(mid)
        elif len(self.cart) >= MAX_PICKS:
            self.notice = "Slip full — tap ✓ on a sheet to free a slot"
        else:
            self.cart.append(mid)
        self.draw()

    def place_order(self):
        if self.done:
            return
        if len(self.cart) != MAX_PICKS:
            self.notice = f"{len(self.cart)} of 2 — pick exactly two"
            self.draw()
            return
        chosen = [{"id": mid, "name": _BY_ID[mid][2]} for mid in self.cart]
        os.makedirs(OUTPUT_DIR, exist_ok=True)
        with open(os.path.join(OUTPUT_DIR, "archive_plan.json"), "w", encoding="utf-8") as f:
            json.dump({"persona": os.environ.get("ADHERENCE_PERSONA", "hf-4386921459"),
                       "reservedPackages": chosen}, f, ensure_ascii=False, indent=2)
        self.done = True
        self.draw()


if __name__ == "__main__":
    root = tk.Tk()
    ArchiveWorkbench(root)
    root.mainloop()
