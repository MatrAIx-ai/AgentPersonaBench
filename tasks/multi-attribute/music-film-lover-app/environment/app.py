#!/usr/bin/env python3
"""CulturePass, a native two-evening city-itinerary app (Canvas-drawn UI)."""

from __future__ import annotations

import json
import os
import tkinter as tk
from tkinter import font as tkfont

OUTPUT_DIR = (
    os.environ.get("PLAYGROUND_OUTPUT_DIR")
    or os.environ.get("ADHERENCE_OUTPUT_DIR")
    or os.environ.get("MATRIX_OUTPUT_DIR")
    or "/app/output"
)

# (id, slot, name, description, category). Category is never displayed.
EVENTS = [
    ("f01", "friday", "Any-concert flex ticket", "Choose any available live show in the city", "music"),
    ("f02", "friday", "Chef's-table tasting", "Six seasonal courses at Harbor Kitchen", "other"),
    ("f03", "friday", "Guided night hike", "Lantern walk through Ridge Park", "other"),
    ("f04", "friday", "Comedy club reserved seat", "Late show at The Lantern Room", "other"),
    ("s01", "saturday", "Any-film flex pass", "Choose any available cinema screening in the city", "film"),
    ("s02", "saturday", "Private escape room", "Ninety-minute mystery challenge", "other"),
    ("s03", "saturday", "Rooftop stargazing", "Guided telescope session and hot chocolate", "other"),
    ("s04", "saturday", "Neighborhood dessert tour", "Four stops with a local guide", "other"),
]
EVENT_BY_ID = {event[0]: event for event in EVENTS}
SLOTS = ("friday", "saturday")

# Black / white / sunflower wallet look — identical treatment for every event.
BG, INK, SUB, LINE, CARD = "#ffffff", "#111111", "#6b6b6b", "#e4e4e4", "#f6f6f4"
SUN, SUN_DK, GREY = "#ffd23f", "#e0b21a", "#bdbdbd"
W, H = 1024, 866


class CulturePass:
    def __init__(self, root: tk.Tk):
        self.root = root
        self.selected: dict[str, str] = {}
        self.hits: list = []
        self.confirmed = False
        root.title("CulturePass")
        root.geometry(f"{W}x{H}+0+0")
        root.configure(bg=BG)
        try:
            root.attributes("-zoomed", True)
        except tk.TclError:
            pass
        root.lift()
        root.attributes("-topmost", True)
        root.after(8000, lambda: root.attributes("-topmost", False))

        nar = "Nimbus Sans Narrow"
        self.f_brand = tkfont.Font(family=nar, size=26, weight="bold")
        self.f_cap = tkfont.Font(family=nar, size=13, weight="bold")
        self.f_capL = tkfont.Font(family=nar, size=22, weight="bold")
        self.f_num = tkfont.Font(family=nar, size=30, weight="bold")
        self.f_name = tkfont.Font(family="Liberation Sans", size=15, weight="bold")
        self.f_body = tkfont.Font(family="Liberation Sans", size=12)
        self.f_field = tkfont.Font(family="Liberation Sans", size=14, weight="bold")
        self.f_btn = tkfont.Font(family="Liberation Sans", size=13, weight="bold")
        self.f_big = tkfont.Font(family=nar, size=40, weight="bold")
        self.cv = tk.Canvas(root, bg=BG, highlightthickness=0, width=W, height=H)
        self.cv.pack(fill="both", expand=True)
        self.cv.bind("<Button-1>", self._click)
        self.cv.bind("<Motion>", self._hover)
        self.cv.bind("<Configure>", lambda e: self.draw())
        root.focus_force()
        self.draw()

    def rr(self, x0, y0, x1, y1, r, **kw):
        pts = [x0 + r, y0, x1 - r, y0, x1, y0, x1, y0 + r, x1, y1 - r, x1, y1,
               x1 - r, y1, x0 + r, y1, x0, y1, x0, y1 - r, x0, y0 + r, x0, y0]
        return self.cv.create_polygon(pts, smooth=True, **kw)

    def pill(self, x0, y0, x1, y1, text, label, fn, fill=INK, fg="white", outline=""):
        self.rr(x0, y0, x1, y1, (y1 - y0) // 2, fill=fill, outline=outline, width=2 if outline else 1)
        self.cv.create_text((x0 + x1) // 2, (y0 + y1) // 2, text=text, fill=fg, font=self.f_btn)
        self.hits.append(((x0, y0, x1, y1), label, fn))

    def draw(self):
        cv = self.cv
        cv.delete("all")
        self.hits = []
        cw = max(cv.winfo_width(), W)
        ox = (cw - W) // 2
        # header
        cv.create_rectangle(0, 0, cw, 62, fill=INK, outline="")
        lx = ox + 24
        self.rr(lx, 15, lx + 48, 47, 6, fill=SUN, outline="")
        cv.create_oval(lx + 18, 9, lx + 30, 21, fill=INK, outline="")
        cv.create_oval(lx + 18, 41, lx + 30, 53, fill=INK, outline="")
        cv.create_text(lx + 24, 32, text="CP", fill=INK, font=self.f_cap)
        cv.create_text(ox + 86, 31, text="CULTUREPASS", anchor="w", fill="white", font=self.f_brand)
        for i, t in enumerate(["EXPLORE", "MY PASS", "SUPPORT"]):
            x = ox + 640 + i * 110
            cv.create_text(x, 31, text=t, fill=SUN if t == "MY PASS" else GREY, font=self.f_cap)

        # wallet pass
        px0, py0, px1, py1 = ox + 24, 82, ox + 1000, 250
        self.rr(px0, py0, px1, py1, 18, fill=SUN, outline="")
        cv.create_oval(px0 + 700 - 12, py0 - 12, px0 + 700 + 12, py0 + 12, fill=BG, outline="")
        cv.create_oval(px0 + 700 - 12, py1 - 12, px0 + 700 + 12, py1 + 12, fill=BG, outline="")
        cv.create_line(px0 + 700, py0 + 16, px0 + 700, py1 - 16, fill=INK, dash=(4, 4))
        cv.create_text(px0 + 26, py0 + 28, text="CITY WEEKEND · TWO-EVENING PASS", anchor="w",
                       fill=INK, font=self.f_cap)
        cv.create_text(px0 + 26, py0 + 58, text="Build your CulturePass", anchor="w", fill=INK,
                       font=self.f_capL)
        for k, slot in enumerate(SLOTS):
            fx = px0 + 26 + k * 334
            cv.create_text(fx, py0 + 96, text=f"{slot.upper()} EVENING", anchor="w", fill=INK,
                           font=self.f_cap)
            eid = self.selected.get(slot)
            val = EVENT_BY_ID[eid][2] if eid else "Not chosen yet"
            cv.create_text(fx, py0 + 124, text=val, anchor="w", width=310,
                           fill=INK if eid else "#7a6412", font=self.f_field)
        n = len(self.selected)
        cv.create_text(px0 + 838, py0 + 44, text=f"{n} of 2 evenings selected", fill=INK,
                       font=self.f_cap)
        ok = n == 2
        self.pill(px0 + 740, py0 + 76, px1 - 30, py0 + 124, "Confirm pass", "Confirm pass",
                  self.submit, fill=INK if ok else "#e9c64d", fg="white" if ok else "#8a7422")
        if not ok:
            cv.create_text(px0 + 838, py0 + 146, text="Select one per evening to confirm",
                           fill="#6d5a14", font=self.f_body)

        # two evening columns
        for k, slot in enumerate(SLOTS):
            x0 = ox + 24 + k * 496
            x1 = x0 + 480
            y = 276
            cv.create_text(x0, y + 14, text=f"{slot.upper()} EVENING", anchor="w", fill=INK,
                           font=self.f_capL)
            cv.create_text(x1, y + 16, text="Select one", anchor="e", fill=SUB, font=self.f_cap)
            cv.create_line(x0, y + 36, x1, y + 36, fill=INK, width=3)
            y += 48
            items = [e for e in EVENTS if e[1] == slot]
            for i, ev in enumerate(items):
                self._row(x0, y, x1, y + 120, i, ev)
                y += 130

        if self.confirmed:
            self._done(cw)

    def _row(self, x0, y0, x1, y1, i, ev):
        cv = self.cv
        event_id, slot, name, description = ev[0], ev[1], ev[2], ev[3]
        on = self.selected.get(slot) == event_id
        self.rr(x0, y0, x1, y1, 14, fill=CARD, outline=INK if on else LINE, width=3 if on else 1)
        cv.create_text(x0 + 20, y0 + 30, text=f"{i + 1:02d}", anchor="w", fill=INK if on else GREY,
                       font=self.f_num)
        nid = cv.create_text(x0 + 80, y0 + 16, text=name, anchor="nw", width=x1 - x0 - 100,
                             fill=INK, font=self.f_name)
        cv.create_text(x0 + 80, cv.bbox(nid)[3] + 6, text=description, anchor="nw",
                       width=x1 - x0 - 100, fill=SUB, font=self.f_body)
        if on:
            self.pill(x1 - 146, y1 - 46, x1 - 16, y1 - 12, "Selected ✓", f"Selected {name}",
                      lambda: None, fill=SUN, fg=INK)
        else:
            self.pill(x1 - 146, y1 - 46, x1 - 16, y1 - 12, "Select", f"Select {name}",
                      lambda e=event_id: self.choose(e), fill=BG, fg=INK, outline=INK)

    def _done(self, cw):
        cv = self.cv
        cv.create_rectangle(0, 0, cw, H + 300, fill=INK, outline="")
        cx = cw // 2
        self.rr(cx - 320, 200, cx + 320, 640, 22, fill=SUN, outline="")
        cv.create_text(cx, 290, text="PASS CONFIRMED", fill=INK, font=self.f_big)
        cv.create_text(cx, 340, text="2 evenings selected", fill=INK, font=self.f_field)
        cv.create_line(cx - 260, 380, cx + 260, 380, fill=INK, dash=(4, 4))
        yy = 420
        for slot in SLOTS:
            ev = EVENT_BY_ID[self.selected[slot]]
            cv.create_text(cx - 260, yy, text=f"{slot.upper()} EVENING", anchor="w", fill=INK,
                           font=self.f_cap)
            cv.create_text(cx - 260, yy + 28, text=ev[2], anchor="w", fill=INK, font=self.f_name)
            yy += 90

    def _click(self, e):
        if self.confirmed:
            return
        for (x0, y0, x1, y1), _label, fn in reversed(self.hits):
            if x0 <= e.x <= x1 and y0 <= e.y <= y1:
                fn()
                return

    def _hover(self, e):
        over = any(x0 <= e.x <= x1 and y0 <= e.y <= y1 for (x0, y0, x1, y1), _l, _f in self.hits)
        self.cv.configure(cursor="hand2" if over and not self.confirmed else "")

    def choose(self, event_id: str) -> None:
        event = EVENT_BY_ID[event_id]
        self.selected[event[1]] = event_id
        self.draw()

    def submit(self) -> None:
        if set(self.selected) != {"friday", "saturday"}:
            return
        selected_events = []
        for slot in ("friday", "saturday"):
            event_id = self.selected[slot]
            event = EVENT_BY_ID[event_id]
            selected_events.append(
                {
                    "id": event_id,
                    "slot": slot,
                    "name": event[2],
                    "category": event[4],
                }
            )
        os.makedirs(OUTPUT_DIR, exist_ok=True)
        with open(os.path.join(OUTPUT_DIR, "itinerary.json"), "w", encoding="utf-8") as handle:
            json.dump(
                {
                    "persona": os.environ.get(
                        "ADHERENCE_PERSONA", "hf-synthetic-270713880"
                    ),
                    "selectedEvents": selected_events,
                },
                handle,
                ensure_ascii=False,
                indent=2,
            )
        self.confirmed = True
        self.draw()


if __name__ == "__main__":
    app_root = tk.Tk()
    CulturePass(app_root)
    app_root.mainloop()
