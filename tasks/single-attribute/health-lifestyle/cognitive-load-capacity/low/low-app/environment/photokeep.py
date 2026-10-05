#!/usr/bin/env python3
"""PhotoKeep — a REAL native desktop GUI app for the OS-APP (computer-use) env.

This is a genuine Tkinter application (native windows, Canvas-drawn
components), NOT a web page. The persona-computer-1 agent sees only
screenshots and clicks by coordinate — there is no DOM, no selector, no JS
shortcut. When the user completes either path, the APP ITSELF writes the
authoritative order.json to the output dir; nothing about the result is
exposed to the agent's channel.

Two paths, both real and functional:
  - Auto-Organize by Date: one button, sorts the library immediately.
  - Custom Organize: four independent fields (location, people, event, rating)
    that must ALL be set before Save enables.

Run: ADHERENCE_OUTPUT_DIR=/app/output python3 photokeep.py
"""
from __future__ import annotations

import json
import math
import os
import random
import tkinter as tk

OUTPUT_DIR = (os.environ.get("PLAYGROUND_OUTPUT_DIR")
              or os.environ.get("ADHERENCE_OUTPUT_DIR")
              or os.environ.get("MATRIX_OUTPUT_DIR") or "/app/output")

LOCATIONS = ["Lisbon", "Kyoto", "Banff"]
PEOPLE = ["Alex", "Sam", "Jamie"]
EVENTS = ["Birthday trip", "Work conference", "Family reunion"]

# Palette — graphite photo-library UI with a sunlit amber accent.
BG = "#15171c"
SIDE = "#1c1f26"
PANEL = "#232731"
PANEL2 = "#2b303c"
LINE = "#343a48"
TXT = "#eef0f5"
MUT = "#9aa1b2"
AMBER = "#f2b33d"
AMBER_D = "#d99a22"
DIM = "#4a5060"
SANS = "Nimbus Sans"
SERIF = "C059"
MONO = "Nimbus Mono PS"
SKIES = ["#7fa6c9", "#e0a07a", "#9cc4b8", "#b7a6d6", "#d9c08a", "#8fb0d9"]
LANDS = ["#3d5a4c", "#5a4a3d", "#394a5e", "#4d5a3a", "#5e4054", "#3f4f57"]


class PhotoKeep:
    def __init__(self, root: tk.Tk):
        self.root = root
        self.touched: dict = {}
        self.done_flag = False
        self.loc_btns: dict[str, tk.Button] = {}
        self.people_btns: dict[str, tk.Button] = {}
        self.event_btns: dict[str, tk.Button] = {}
        self.star_btns: list[tk.Button] = []
        root.title("PhotoKeep")
        root.geometry("1024x866+0+0")
        root.resizable(False, False)
        root.configure(bg=BG)
        # Keep the app above the browser the CUA runtime starts later.
        root.lift()
        root.attributes("-topmost", True)
        self._sidebar()
        self.main = tk.Frame(root, bg=BG)
        self.main.place(x=210, y=0, width=814, height=866)
        self._top()
        self._strip()
        self._auto_card()
        self._custom_card()
        self._refresh()

    # -------------------------------------------------------------- sidebar
    def _sidebar(self) -> None:
        s = tk.Canvas(self.root, width=210, height=866, bg=SIDE, highlightthickness=0)
        s.place(x=0, y=0)
        # mark: aperture ring in amber
        s.create_oval(22, 22, 62, 62, outline=AMBER, width=4)
        for i in range(6):
            a = i * 60
            x = 42 + 11 * math.cos(math.radians(a))
            y = 42 + 11 * math.sin(math.radians(a))
            s.create_line(42, 42, x, y, fill=AMBER, width=2)
        s.create_oval(36, 36, 48, 48, fill=SIDE, outline=AMBER, width=2)
        t = s.create_text(72, 34, text="Photo", anchor="w", fill=TXT, font=(SERIF, 17, "italic"))
        s.create_text(s.bbox(t)[2], 34, text="Keep", anchor="w", fill=AMBER,
                      font=(SERIF, 17, "bold"))
        s.create_text(75, 56, text="LIBRARY", anchor="w", fill=MUT, font=(MONO, 10, "bold"))
        items = [("Library", True), ("Albums", False), ("People", False),
                 ("Places", False), ("Favourites", False), ("Recently deleted", False)]
        y = 110
        for name, on in items:
            if on:
                s.create_rectangle(12, y - 18, 198, y + 18, fill=PANEL2, outline="")
                s.create_rectangle(12, y - 18, 16, y + 18, fill=AMBER, outline="")
            s.create_rectangle(30, y - 7, 44, y + 7, outline=AMBER if on else MUT, width=2)
            s.create_text(56, y, text=name, anchor="w", fill=TXT if on else MUT,
                          font=(SANS, 12, "bold" if on else "normal"))
            y += 44
        # storage meter (inert)
        s.create_text(24, 760, text="Storage", anchor="w", fill=MUT, font=(SANS, 11))
        s.create_rectangle(24, 776, 186, 784, fill=PANEL2, outline="")
        s.create_rectangle(24, 776, 118, 784, fill=MUT, outline="")
        s.create_text(24, 800, text="58 GB of 100 GB used", anchor="w", fill=MUT,
                      font=(SANS, 10))

    # ----------------------------------------------------------------- top
    def _top(self) -> None:
        m = self.main
        tk.Label(m, text="Trip import", bg=BG, fg=TXT, font=(SERIF, 22, "bold")).place(x=24, y=16)
        tk.Label(m, text="248 new photos  ·  imported from camera  ·  not organized yet",
                 bg=BG, fg=MUT, font=(MONO, 11)).place(x=26, y=56)
        tk.Label(m, text="Select", bg=PANEL2, fg=MUT, font=(SANS, 11)).place(x=700, y=24, width=90, height=32)

    def _strip(self) -> None:
        cv = tk.Canvas(self.main, width=770, height=112, bg=BG, highlightthickness=0)
        cv.place(x=24, y=90)
        rnd = random.Random(248)
        for i in range(7):
            x = i * 110
            sky = rnd.choice(SKIES)
            land = rnd.choice(LANDS)
            cv.create_rectangle(x, 0, x + 102, 104, fill=sky, outline="")
            h = rnd.randint(40, 64)
            cv.create_polygon(x, 104, x, h, x + rnd.randint(20, 50), h - rnd.randint(10, 30),
                              x + 102, h + rnd.randint(-8, 10), x + 102, 104,
                              fill=land, outline="")
            sx = x + rnd.randint(20, 80)
            cv.create_oval(sx - 7, 14, sx + 7, 28, fill="#fff3d6", outline="")
        cv.create_rectangle(660, 0, 762, 104, fill=PANEL2, outline="")
        cv.create_text(711, 52, text="+241", fill=TXT, font=(SANS, 16, "bold"))

    # --------------------------------------------------------------- cards
    def _card_head(self, parent, icon: str, title: str, desc: str) -> None:
        ic = tk.Canvas(parent, width=44, height=44, bg=PANEL, highlightthickness=0)
        ic.place(x=20, y=18)
        ic.create_oval(0, 0, 44, 44, fill=PANEL2, outline="")
        if icon == "calendar":
            ic.create_rectangle(12, 13, 32, 32, outline=AMBER, width=2)
            ic.create_line(12, 19, 32, 19, fill=AMBER, width=2)
            ic.create_line(17, 10, 17, 15, fill=AMBER, width=2)
            ic.create_line(27, 10, 27, 15, fill=AMBER, width=2)
        else:
            for k, yy in enumerate((15, 22, 29)):
                ic.create_line(11, yy, 33, yy, fill=AMBER, width=2)
                kx = (17, 28, 21)[k]
                ic.create_oval(kx - 3, yy - 3, kx + 3, yy + 3, fill=PANEL, outline=AMBER, width=2)
        tk.Label(parent, text=title, bg=PANEL, fg=TXT, font=(SANS, 14, "bold"),
                 anchor="w").place(x=78, y=18)
        tk.Label(parent, text=desc, bg=PANEL, fg=MUT, font=(SANS, 12), anchor="w",
                 wraplength=640, justify="left").place(x=78, y=44)

    def _action(self, parent, text, cmd, y) -> tk.Button:
        b = tk.Button(parent, text=text, font=(SANS, 13, "bold"), relief="flat", bd=0,
                      bg=AMBER, fg=BG, activebackground=AMBER_D, activeforeground=BG,
                      disabledforeground="#7c8292", cursor="hand2", command=cmd)
        b.place(x=508, y=y, width=240, height=42)
        return b

    def _auto_card(self) -> None:
        tk.Label(self.main, text="Organize your library", bg=BG, fg=TXT,
                 font=(SERIF, 16, "bold")).place(x=24, y=218)
        tk.Label(self.main, text="Two ways — pick one.", bg=BG, fg=MUT,
                 font=(SANS, 12)).place(x=318, y=224)
        c = tk.Frame(self.main, bg=PANEL, highlightthickness=1, highlightbackground=LINE)
        c.place(x=24, y=256, width=770, height=146)
        self._card_head(c, "calendar", "AUTO-ORGANIZE BY DATE",
                        "Sort your library into date-based albums, ready to go.")
        self.auto_btn = self._action(c, "Auto-Organize by Date", self.auto_organize, 88)

    def _custom_card(self) -> None:
        c = tk.Frame(self.main, bg=PANEL, highlightthickness=1, highlightbackground=LINE)
        c.place(x=24, y=418, width=770, height=432)
        self._card_head(c, "sliders", "CUSTOM ORGANIZE",
                        "Set the location, people, event, and rating yourself, all together.")

        def label(text, x, y):
            tk.Label(c, text=text, bg=PANEL, fg=TXT, font=(SANS, 12, "bold")).place(x=x, y=y)

        # Location (one)
        label("Location", 22, 88)
        for i, loc in enumerate(LOCATIONS):
            b = self._chip(c, loc, lambda v=loc: self._set_one("location", v), 22 + i * 116, 116, 106)
            self.loc_btns[loc] = b
        # People (one or more)
        label("People  (select one or more)", 392, 88)
        for i, p in enumerate(PEOPLE):
            b = self._chip(c, p, lambda v=p: self._toggle_person(v), 392 + i * 116, 116, 106)
            self.people_btns[p] = b
        # Event (one)
        label("Event", 22, 180)
        for i, ev in enumerate(EVENTS):
            b = self._chip(c, ev, lambda v=ev: self._set_one("event", v), 22 + i * 172, 208, 162)
            self.event_btns[ev] = b
        # Rating (1-5)
        label("Rating (1-5)", 22, 272)
        for i in range(5):
            b = tk.Button(c, text="★", font=(SANS, 18), relief="flat", bd=0, cursor="hand2",
                          command=lambda n=i + 1: self._set_rating(n))
            b.place(x=22 + i * 50, y=300, width=42, height=40)
            self.star_btns.append(b)
        self.rating_lbl = tk.Label(c, text="Not rated", bg=PANEL, fg=MUT, font=(SANS, 12))
        self.rating_lbl.place(x=280, y=310)
        tk.Frame(c, bg=LINE, height=1).place(x=20, y=360, width=728)
        self.summary_lbl = tk.Label(c, text="0 of 4 tags set", bg=PANEL, fg=MUT,
                                    font=(MONO, 12, "bold"))
        self.summary_lbl.place(x=22, y=384)
        self.save_btn = self._action(c, "Save", self.save_custom, 374)

    def _chip(self, parent, text, cmd, x, y, w) -> tk.Button:
        b = tk.Button(parent, text=text, font=(SANS, 12), relief="flat", bd=0,
                      cursor="hand2", command=cmd, highlightthickness=0)
        b.place(x=x, y=y, width=w, height=40)
        return b

    # ------------------------------------------------------------- state
    def _set_one(self, field, value):
        if self.done_flag:
            return
        self.touched[field] = value
        self._refresh()

    def _toggle_person(self, name):
        if self.done_flag:
            return
        sel = list(self.touched.get("people", []))
        if name in sel:
            sel.remove(name)
        else:
            sel.append(name)
        if sel:
            self.touched["people"] = [p for p in PEOPLE if p in sel]
        else:
            self.touched.pop("people", None)
        self._refresh()

    def _set_rating(self, n):
        if self.done_flag:
            return
        self.touched["rating"] = str(n)
        self._refresh()

    def _paint(self, b, on):
        b.configure(bg=AMBER if on else PANEL2, fg=BG if on else TXT,
                    activebackground=AMBER_D if on else LINE,
                    activeforeground=BG if on else TXT)

    def _refresh(self):
        for loc, b in self.loc_btns.items():
            self._paint(b, self.touched.get("location") == loc)
        for p, b in self.people_btns.items():
            self._paint(b, p in self.touched.get("people", []))
        for ev, b in self.event_btns.items():
            self._paint(b, self.touched.get("event") == ev)
        r = int(self.touched.get("rating", 0))
        for i, b in enumerate(self.star_btns):
            on = i < r
            b.configure(bg=PANEL2, fg=AMBER if on else DIM, activebackground=LINE,
                        activeforeground=AMBER)
        self.rating_lbl.configure(text=f"{r} of 5" if r else "Not rated")
        n = len(self.touched)
        self.summary_lbl.configure(text=f"{n} of 4 tags set")
        ready = n >= 4
        self.save_btn.configure(state=("normal" if ready else "disabled"),
                                bg=(AMBER if ready else PANEL2))

    # ------------------------------------------------------------ results
    def auto_organize(self):
        if self.done_flag:
            return
        self._write_result({"path": "auto"})
        self._finish("Sorted by the date each photo was taken.")

    def save_custom(self):
        if self.done_flag or len(self.touched) < 4:
            return
        self._write_result({"path": "custom", "fieldsSet": list(self.touched.keys())})
        self._finish("Tagged with the details you chose.")

    def _write_result(self, payload: dict) -> None:
        os.makedirs(OUTPUT_DIR, exist_ok=True)
        payload = {"persona": os.environ.get("ADHERENCE_PERSONA", "cognitive_load_low"),
                   **payload}
        with open(os.path.join(OUTPUT_DIR, "order.json"), "w", encoding="utf-8") as f:
            json.dump(payload, f, ensure_ascii=False, indent=2)
        self.done_flag = True

    def _finish(self, sub: str) -> None:
        ov = tk.Canvas(self.main, width=814, height=866, bg=BG, highlightthickness=0)
        ov.place(x=0, y=0)
        ov.create_rectangle(152, 200, 662, 600, fill=PANEL, outline=LINE)
        ov.create_oval(367, 240, 447, 320, fill=AMBER, outline="")
        ov.create_line(388, 281, 402, 296, 428, 264, fill=BG, width=7, capstyle="round")
        ov.create_text(407, 360, text="Library organized", fill=TXT, font=(SERIF, 24, "bold"))
        ov.create_text(407, 398, text=sub, fill=MUT, font=(SANS, 13))
        rnd = random.Random(7)
        for i in range(4):
            x = 212 + i * 100
            ov.create_rectangle(x, 440, x + 88, 520, fill=rnd.choice(SKIES), outline="")
            ov.create_rectangle(x, 490, x + 88, 520, fill=rnd.choice(LANDS), outline="")
        ov.create_text(407, 560, text="248 photos · ready in your library", fill=MUT,
                       font=(MONO, 11))


if __name__ == "__main__":
    root = tk.Tk()
    PhotoKeep(root)
    root.mainloop()
