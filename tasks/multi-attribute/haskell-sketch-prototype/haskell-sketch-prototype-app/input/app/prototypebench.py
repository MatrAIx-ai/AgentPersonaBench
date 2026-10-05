#!/usr/bin/env python3
"""PrototypeBench — a native Tkinter interactive-exhibit app.

A genuine desktop application drawn on a Tk canvas (blueprint work sheet, package
rows, a reservation sheet). Every package uses the same kiosk hardware, accessibility
review, test crew and launch date.
Browse the options, add items with the + buttons, and tap "Reserve prototypes" — the app
then writes the result to prototype_plan.json in the output directory.

Run: ADHERENCE_OUTPUT_DIR=/app/output python3 prototypebench.py
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
    ("pb01", "River kiosk", "Managed river studio kiosk", "visual builder with hosted builds; professionally commissioned neighborhood illustrations arranged remotely in 45 minutes, with reusable components and instant resizing", "same art direction, hardware, testing and launch date"),
    ("pb02", "River kiosk", "Typed river studio kiosk", "Haskell interaction layer and manual build handoff; professionally commissioned neighborhood illustrations arranged remotely, with reusable components", "same art direction, hardware, testing and launch date"),
    ("pb03", "Market kiosk", "Typed river drawing kiosk", "Haskell interaction layer with handwritten device adapter; three fixed two-hour on-site drawing sessions, manual scan and color correction, and four revision passes", "same art direction, hardware, testing and launch date"),
    ("pb04", "Market kiosk", "Managed river drawing kiosk", "visual interaction builder with instant preview; three fixed two-hour on-site drawing sessions, manual scan and color correction, and four revision passes", "same art direction, hardware, testing and launch date"),
    ("pb05", "Rail kiosk", "Functional market studio kiosk", "local Haskell toolchain; professionally commissioned market illustrations with reusable layers and one-click resizing", "same art direction, hardware, testing and launch date"),
    ("pb06", "Rail kiosk", "Managed market studio kiosk", "instant device preview; professionally commissioned market illustrations with reusable layers and one-click resizing", "same art direction, hardware, testing and launch date"),
    ("pb07", "Park kiosk", "Functional market drawing kiosk", "local Haskell build and manual handoff; three fixed two-hour on-site blank-page drawing sessions plus manual scan, color correction, and four revision passes", "same art direction, hardware, testing and launch date"),
    ("pb08", "Park kiosk", "Managed market drawing kiosk", "hosted visual build; three fixed two-hour on-site blank-page drawing sessions plus manual scan, color correction, and four revision passes", "same art direction, hardware, testing and launch date"),
]
_BY_ID = {m[0]: m for m in MENU}
LIMIT = 2

# Blueprint work-sheet palette: navy ink on pale drafting paper, one vermilion accent.
NAVY, NAVY2, PAPER, GRID = "#16325c", "#23467a", "#eaf0f8", "#dbe5f2"
CARD, LINE, INK, MUT = "#ffffff", "#b7c6dc", "#14233d", "#56657d"
ACC, ACC_SOFT, OK = "#e4572e", "#fdebe5", "#1d7a4f"
W, H = 1024, 866
LIST_X0, LIST_X1 = 18, 690
SIDE_X0, SIDE_X1 = 708, 1006


def rrect(cv, x0, y0, x1, y1, r=8, **kw):
    pts = [x0 + r, y0, x1 - r, y0, x1, y0, x1, y0 + r, x1, y1 - r, x1, y1,
           x1 - r, y1, x0 + r, y1, x0, y1, x0, y1 - r, x0, y0 + r, x0, y0]
    return cv.create_polygon(pts, smooth=True, **kw)


class PrototypeBench:
    def __init__(self, root: tk.Tk):
        self.root = root
        self.cart: list[str] = []
        self.msg = ""
        self.submitted = False
        root.title("PrototypeBench")
        # The CUA desktop is 1024x900 with a panel; 1024x866 fits under it.
        root.geometry("1024x866+0+0")
        root.minsize(1024, 866)
        root.configure(bg=PAPER)
        root.lift()
        root.attributes("-topmost", True)
        root.after(8000, lambda: root.attributes("-topmost", False))
        fam = "URW Gothic"
        self.f_brand = tkfont.Font(family=fam, size=-26, weight="bold")
        self.f_sub = tkfont.Font(family="Nimbus Sans", size=-13)
        self.f_crumb = tkfont.Font(family="Nimbus Sans", size=-13, weight="bold")
        self.f_group = tkfont.Font(family="Nimbus Mono PS", size=-13, weight="bold")
        self.f_id = tkfont.Font(family="Nimbus Mono PS", size=-13, weight="bold")
        self.f_name = tkfont.Font(family="Nimbus Sans", size=-16, weight="bold")
        self.f_desc = tkfont.Font(family="Nimbus Sans", size=-13)
        self.f_note = tkfont.Font(family="Nimbus Sans", size=-12, slant="italic")
        self.f_plus = tkfont.Font(family="DejaVu Sans", size=-20, weight="bold")
        self.f_h2 = tkfont.Font(family=fam, size=-18, weight="bold")
        self.f_btn = tkfont.Font(family="Nimbus Sans", size=-16, weight="bold")
        self.f_small = tkfont.Font(family="Nimbus Sans", size=-12)
        self.f_big = tkfont.Font(family=fam, size=-34, weight="bold")

        self.cv = tk.Canvas(root, width=W, height=H, bg=PAPER, highlightthickness=0)
        self.cv.pack(fill="both", expand=True)
        self.render()

    # ------------------------------------------------------------------ drawing
    def status_text(self):
        return f"{len(self.cart)} of {LIMIT} selected {self.msg}"

    def render(self):
        cv = self.cv
        cv.delete("all")
        for x in range(0, W, 24):
            cv.create_line(x, 0, x, H, fill=GRID)
        for y in range(0, H, 24):
            cv.create_line(0, y, W, y, fill=GRID)
        self._header()
        if self.submitted:
            self._confirmation()
            return
        self._list()
        self._sidebar()

    def _header(self):
        cv = self.cv
        cv.create_rectangle(0, 0, W, 70, fill=NAVY, outline="")
        # mark: a set square over a drafting circle
        cv.create_oval(20, 14, 62, 56, outline="#9fb9de", width=2)
        cv.create_polygon(28, 50, 56, 50, 28, 20, fill="", outline="white", width=3)
        cv.create_line(28, 42, 36, 42, 36, 50, fill=ACC, width=3)
        cv.create_text(76, 16, anchor="nw", text="PrototypeBench", fill="white", font=self.f_brand)
        cv.create_text(78, 48, anchor="nw", text="Community exhibit · two prototype packages",
                       fill="#b9cbe6", font=self.f_sub)
        cv.create_text(W - 20, 26, anchor="ne", text="Exhibit  ›  Kiosk prototypes  ›  Reserve",
                       fill="white", font=self.f_crumb)
        cv.create_text(W - 20, 48, anchor="ne", text="Work sheet WS-2 · package catalogue",
                       fill="#9fb9de", font=self.f_small)
        cv.create_rectangle(0, 70, W, 74, fill=ACC, outline="")

    def _list(self):
        cv = self.cv
        y = 86
        last = None
        tw = LIST_X1 - LIST_X0 - 150
        for mid, group, name, desc, note in MENU:
            if group != last:
                cv.create_text(LIST_X0 + 2, y + 2, anchor="nw", text=group.upper(), fill=NAVY2,
                               font=self.f_group)
                cv.create_line(LIST_X0 + 16 + self.f_group.measure(group.upper()), y + 10,
                               LIST_X1, y + 10, fill=LINE, dash=(3, 3))
                y += 19
                last = group
            y = self._row(mid, name, desc, note, y, tw) + 5

    def _row(self, mid, name, desc, note, y, tw):
        cv = self.cv
        sel = mid in self.cart
        tag = f"row:{mid}"
        tx = LIST_X0 + 78
        t1 = cv.create_text(tx, y + 7, anchor="nw", text=name, fill=INK, font=self.f_name, tags=tag)
        t2 = cv.create_text(tx, y + 27, anchor="nw", text=desc, fill=INK, font=self.f_desc,
                            width=tw, tags=tag)
        b = cv.bbox(t2)
        t3 = cv.create_text(tx, b[3] + 2, anchor="nw", text=note, fill=MUT, font=self.f_note, tags=tag)
        y1 = cv.bbox(t3)[3] + 7
        card = rrect(cv, LIST_X0, y, LIST_X1, y1, r=6, fill=ACC_SOFT if sel else CARD,
                     outline=ACC if sel else LINE, width=2 if sel else 1, tags=tag)
        cv.tag_lower(card, t1)
        # id plate
        cv.create_rectangle(LIST_X0 + 12, y + 10, LIST_X0 + 64, y + 32, fill=NAVY if not sel else ACC,
                            outline="", tags=tag)
        cv.create_text(LIST_X0 + 38, y + 21, text=mid.upper().replace("PB", "PB-"), fill="white",
                       font=self.f_id, tags=tag)
        cv.create_line(LIST_X0 + 38, y + 38, LIST_X0 + 38, y1 - 10, fill=LINE, dash=(2, 3), tags=tag)
        # + / check toggle
        bx0, bx1 = LIST_X1 - 58, LIST_X1 - 14
        cy = (y + y1) // 2
        atag = f"add:{mid}"
        rrect(cv, bx0, cy - 22, bx1, cy + 22, r=8, fill=ACC if sel else "white",
              outline=ACC if sel else NAVY, width=2, tags=atag)
        cv.create_text((bx0 + bx1) // 2, cy, text="✓" if sel else "+", fill="white" if sel else NAVY,
                       font=self.f_plus, tags=atag)
        cv.tag_bind(atag, "<Button-1>", lambda e, m=mid: self.toggle(m))
        cv.tag_bind(atag, "<Enter>", lambda e: cv.configure(cursor="hand2"))
        cv.tag_bind(atag, "<Leave>", lambda e: cv.configure(cursor=""))
        return y1

    def _sidebar(self):
        cv = self.cv
        x0, x1 = SIDE_X0, SIDE_X1
        rrect(cv, x0, 88, x1, H - 18, r=10, fill=CARD, outline=LINE)
        cv.create_rectangle(x0 + 1, 88, x1 - 1, 132, fill=NAVY2, outline="")
        cv.create_text(x0 + 18, 110, anchor="w", text="Reservation sheet", fill="white", font=self.f_h2)
        n = len(self.cart)
        cv.create_text(x1 - 16, 110, anchor="e", text=f"{n} of {LIMIT}", fill="white", font=self.f_btn)
        y = 150
        cv.create_text(x0 + 18, y, anchor="nw", text="Choose exactly two packages to build — tap + on a package to add it.",
                       width=x1 - x0 - 36,
                       fill=MUT, font=self.f_small)
        y += 40
        for i in range(LIMIT):
            sy0, sy1 = y, y + 92
            if i < n:
                mid = self.cart[i]
                rrect(cv, x0 + 16, sy0, x1 - 16, sy1, r=8, fill=ACC_SOFT, outline=ACC)
                cv.create_text(x0 + 30, sy0 + 12, anchor="nw", text=f"SLOT {i + 1} · {mid.upper()}",
                               fill=ACC, font=self.f_group)
                cv.create_text(x0 + 30, sy0 + 34, anchor="nw", text=_BY_ID[mid][2], fill=INK,
                               font=self.f_btn, width=x1 - x0 - 60)
                rtag = f"rm:{mid}"
                rrect(cv, x1 - 110, sy1 - 34, x1 - 26, sy1 - 8, r=6, fill="white", outline=LINE, tags=rtag)
                cv.create_text(x1 - 68, sy1 - 21, text="Remove", fill=INK, font=self.f_small, tags=rtag)
                cv.tag_bind(rtag, "<Button-1>", lambda e, m=mid: self.toggle(m))
            else:
                cv.create_rectangle(x0 + 16, sy0, x1 - 16, sy1, outline=LINE, dash=(5, 4), width=2)
                cv.create_text((x0 + x1) // 2, (sy0 + sy1) // 2, text=f"Slot {i + 1} — empty",
                               fill=MUT, font=self.f_desc)
            y = sy1 + 14
        y += 8
        cv.create_line(x0 + 16, y, x1 - 16, y, fill=LINE)
        y += 14
        cv.create_text(x0 + 18, y, anchor="nw", text="Shared by every package", fill=INK, font=self.f_crumb)
        y += 24
        for k, v in (("Kiosk hardware", "same unit"), ("Accessibility review", "same"),
                     ("Test crew", "same"), ("Launch date", "same")):
            cv.create_text(x0 + 18, y, anchor="nw", text=k, fill=MUT, font=self.f_small)
            cv.create_text(x1 - 18, y, anchor="ne", text=v, fill=INK, font=self.f_small)
            cv.create_line(x0 + 18, y + 20, x1 - 18, y + 20, fill=GRID)
            y += 26
        # status + submit
        ready = n == LIMIT
        if self.msg:
            cv.create_text((x0 + x1) // 2, H - 118, text=self.msg, fill=ACC, font=self.f_small,
                           width=x1 - x0 - 36, justify="center")
        stag = "submit"
        rrect(cv, x0 + 16, H - 92, x1 - 16, H - 40, r=10, fill=ACC if ready else NAVY, outline="", tags=stag)
        cv.create_text((x0 + x1) // 2, H - 66, text="Reserve prototypes", fill="white",
                       font=self.f_btn, tags=stag)
        cv.tag_bind(stag, "<Button-1>", lambda e: self.place_order())
        cv.tag_bind(stag, "<Enter>", lambda e: cv.configure(cursor="hand2"))
        cv.tag_bind(stag, "<Leave>", lambda e: cv.configure(cursor=""))

    def _confirmation(self):
        cv = self.cv
        x0, x1, y0, y1 = 212, 812, 170, 640
        rrect(cv, x0, y0, x1, y1, r=14, fill=CARD, outline=LINE, width=2)
        cv.create_oval(W // 2 - 34, y0 + 36, W // 2 + 34, y0 + 104, fill=OK, outline="")
        cv.create_line(W // 2 - 16, y0 + 70, W // 2 - 4, y0 + 84, W // 2 + 18, y0 + 56,
                       fill="white", width=6, capstyle="round", joinstyle="round")
        cv.create_text(W // 2, y0 + 140, text="Prototypes reserved", fill=INK, font=self.f_big)
        cv.create_text(W // 2, y0 + 180, text="Your two packages are on the build schedule.",
                       fill=MUT, font=self.f_desc)
        y = y0 + 220
        for i, mid in enumerate(self.cart):
            rrect(cv, x0 + 40, y, x1 - 40, y + 60, r=8, fill=PAPER, outline=LINE)
            cv.create_text(x0 + 60, y + 30, anchor="w", text=f"{i + 1}.  {_BY_ID[mid][2]}", fill=INK,
                           font=self.f_btn)
            cv.create_text(x1 - 60, y + 30, anchor="e", text=mid.upper(), fill=NAVY2, font=self.f_id)
            y += 74
        ref = sum(ord(c) for c in "".join(self.cart)) * 37 % 9000 + 1000
        cv.create_text(W // 2, y1 - 40, text=f"Reservation WS-2-{ref} · same hardware, testing and launch date",
                       fill=MUT, font=self.f_small)

    # ------------------------------------------------------------------ actions
    def toggle(self, mid):
        # Tapping again removes the item — a misclick is correctable.
        self.msg = ""
        if mid in self.cart:
            self.cart.remove(mid)
        elif len(self.cart) >= LIMIT:
            self.msg = "Both slots are full — remove one before adding another."
        else:
            self.cart.append(mid)
        self.render()

    def place_order(self):
        if len(self.cart) != LIMIT:
            self.msg = f"Choose exactly two packages ({len(self.cart)} of 2 selected)."
            self.render()
            return
        chosen = [{"id": mid, "name": _BY_ID[mid][2]} for mid in self.cart]
        os.makedirs(OUTPUT_DIR, exist_ok=True)
        with open(os.path.join(OUTPUT_DIR, "prototype_plan.json"), "w", encoding="utf-8") as f:
            json.dump({"persona": os.environ.get("ADHERENCE_PERSONA", "hf-5170043725"),
                       "reservedPrototypes": chosen}, f, ensure_ascii=False, indent=2)
        self.submitted = True
        self.render()


if __name__ == "__main__":
    root = tk.Tk()
    PrototypeBench(root)
    root.mainloop()
