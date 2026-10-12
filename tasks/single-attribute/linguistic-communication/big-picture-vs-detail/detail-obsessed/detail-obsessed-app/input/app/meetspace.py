#!/usr/bin/env python3
"""MeetSpace — native Tk room-booking app for the OS-APP (computer-use) env.

Scenario: booking a room for a board game club's monthly tournament (20 people).
The room list shows name, a coarse price tier, capacity, rating and badge; each
room's "View details" opens its full listing (exact price and a few neutral
facts) in the side panel, with its own "Book this room" button. The app records
which distinct rooms' details were opened before booking (real navigation) and
writes it with the booked room to order.json. Nothing in the UI marks any room
as correct.

Run: ADHERENCE_OUTPUT_DIR=/app/output python3 meetspace.py
"""
from __future__ import annotations

import json
import os
import tkinter as tk
from tkinter import font as tkfont

OUTPUT_DIR = (os.environ.get("PLAYGROUND_OUTPUT_DIR")
              or os.environ.get("ADHERENCE_OUTPUT_DIR")
              or os.environ.get("MATRIX_OUTPUT_DIR") or "/app/output")

# Room data, in list order (top to bottom). "facts" show only in the details panel.
ROOMS = [
    {
        "id": "skyline_room",
        "name": "Skyline Room",
        "price_tier": "$$$",
        "capacity": 20,
        "rating": 4.9,
        "badge": "Top Rated",
        "facts": [
            ("Price", "$310"),
            ("Setting", "Floor-to-ceiling windows overlooking downtown"),
            ("Access", "Elevator access, no stairs"),
            ("Notes", "Popular with local tech meetups"),
        ],
    },
    {
        "id": "harbor_room",
        "name": "Harbor Room",
        "price_tier": "$$",
        "capacity": 20,
        "rating": 4.6,
        "badge": None,
        "facts": [
            ("Price", "$285"),
            ("Setting", "Faces the marina, good natural light in the afternoon"),
            ("Access", "Short walk from the parking garage"),
            ("Notes", "Whiteboard wall runs the length of the room"),
        ],
    },
    {
        "id": "meadow_room",
        "name": "Meadow Room",
        "price_tier": "$",
        "capacity": 18,
        "rating": 4.3,
        "badge": "Best Value",
        "facts": [
            ("Price", "$210"),
            ("Setting", "Ground floor, easy load-in for equipment"),
            ("Access", "Skylight over the main table"),
            ("Notes", "Quietest of the available rooms"),
        ],
    },
    {
        "id": "union_hall",
        "name": "Union Hall",
        "price_tier": "$$",
        "capacity": 20,
        "rating": 4.5,
        "badge": None,
        "facts": [
            ("Price", "$260"),
            ("Setting", "High ceilings, good acoustics for group discussion"),
            ("Access", "Shared building with a small cafe downstairs"),
            ("Notes", "Lighting is adjustable by dimmer"),
        ],
    },
    {
        "id": "garden_terrace",
        "name": "Garden Terrace",
        "price_tier": "$$",
        "capacity": 20,
        "rating": 4.2,
        "badge": "Popular",
        "facts": [
            ("Price", "$270"),
            ("Setting", "Outdoor-adjacent patio access"),
            ("Access", "A few steps from the building entrance"),
            ("Notes", "Rustic wood tables, seats mix easily for board games"),
        ],
    },
    {
        "id": "tech_hub_room",
        "name": "Tech Hub Room",
        "price_tier": "$$$",
        "capacity": 20,
        "rating": 4.6,
        "badge": None,
        "facts": [
            ("Price", "$300"),
            ("Setting", "Built-in projector screen and sound system"),
            ("Access", "Standing desks available on request"),
            ("Notes", "Popular for hackathons and game nights alike"),
        ],
    },
]
_BY_ID = {r["id"]: r for r in ROOMS}

# palette: crimson accent, charcoal ink, cool-grey canvas
CRIMSON = "#b3261e"
CRIMSON_DK = "#8c1d17"
INK = "#1f1f24"
MUT = "#6b6b74"
BG = "#f3f3f1"
CARD = "#ffffff"
LINE = "#e2e1dc"
SOFT = "#fbeeec"
SANS = "Nimbus Sans"
SERIF = "URW Bookman"
# neutral tile colours for the decorative room art (picked from the room id only)
ART = [("#e9e4da", "#c9c0ae"), ("#dfe6e8", "#b3c2c7"), ("#e6e2ea", "#c0b7cc"),
       ("#e3e8df", "#b8c4ae"), ("#ece3dc", "#cdb9a9"), ("#e0e3ec", "#b6bdd2")]


def _seed(room_id: str) -> int:
    return sum(ord(ch) * (i + 1) for i, ch in enumerate(room_id))


class MeetSpace:
    def __init__(self, root: tk.Tk):
        self.root = root
        root.title("MeetSpace")
        root.geometry("1024x866+0+0")
        root.resizable(False, False)
        root.configure(bg=BG)
        root.lift()
        root.attributes("-topmost", True)
        root.after(8000, lambda: root.attributes("-topmost", False))

        self.f_brand = tkfont.Font(family=SERIF, size=20, weight="bold")
        self.f_h1 = tkfont.Font(family=SERIF, size=22, weight="bold")
        self.f_name = tkfont.Font(family=SANS, size=14, weight="bold")
        self.f_body = tkfont.Font(family=SANS, size=12)
        self.f_small = tkfont.Font(family=SANS, size=11)
        self.f_bold = tkfont.Font(family=SANS, size=12, weight="bold")
        self.f_fact = tkfont.Font(family=SANS, size=13, weight="bold")

        # distinct rooms whose details were opened before booking (never rendered)
        self.opened: list[str] = []
        self.current: str | None = None
        self.booked = False
        self.list_cards: dict[str, tuple[tk.Frame, list[tk.Widget]]] = {}

        self._topbar()
        body = tk.Frame(root, bg=BG)
        body.pack(fill="both", expand=True, padx=22, pady=(12, 18))
        self.left = tk.Frame(body, bg=BG, width=484)
        self.left.pack(side="left", fill="y")
        self.left.pack_propagate(False)
        self.right = tk.Frame(body, bg=CARD, highlightthickness=1, highlightbackground=LINE)
        self.right.pack(side="left", fill="both", expand=True, padx=(18, 0))
        self.show_list()
        self._placeholder()

    # -- chrome --------------------------------------------------------------
    def _topbar(self):
        bar = tk.Frame(self.root, bg=CARD, height=68, highlightthickness=1, highlightbackground=LINE)
        bar.pack(fill="x")
        bar.pack_propagate(False)
        mark = tk.Canvas(bar, width=42, height=42, bg=CARD, highlightthickness=0)
        mark.pack(side="left", padx=(22, 8))
        # mark: crimson arched doorway with a small white key-hole
        mark.create_rectangle(6, 18, 36, 40, fill=CRIMSON, outline="")
        mark.create_oval(6, 3, 36, 33, fill=CRIMSON, outline="")
        mark.create_oval(18, 17, 24, 23, fill="white", outline="")
        mark.create_polygon(19, 22, 23, 22, 24, 31, 18, 31, fill="white", outline="")
        tk.Label(bar, text="MeetSpace", bg=CARD, fg=INK, font=self.f_brand).pack(side="left")
        pill = tk.Frame(bar, bg=BG, padx=16, pady=7)
        pill.pack(side="left", padx=28)
        tk.Label(pill, text="Board Game Club", bg=BG, fg=INK, font=self.f_bold).pack(side="left")
        tk.Label(pill, text="  ·  Monthly tournament  ·  20 guests", bg=BG, fg=MUT,
                 font=self.f_small).pack(side="left")
        av = tk.Canvas(bar, width=36, height=36, bg=CARD, highlightthickness=0)
        av.pack(side="right", padx=(6, 22))
        av.create_oval(2, 2, 34, 34, fill=INK, outline="")
        av.create_text(18, 18, text="BG", fill="white", font=self.f_small)
        tk.Label(bar, text="Saved rooms", bg=CARD, fg=MUT, font=self.f_small).pack(side="right", padx=10)

    def _art(self, canvas: tk.Canvas, room_id: str, w: int, h: int):
        """Decorative top-down room sketch, laid out from the room id only."""
        seed = _seed(room_id)
        base, deep = ART[seed % len(ART)]
        canvas.create_rectangle(0, 0, w, h, fill=base, outline="")
        canvas.create_rectangle(5, 5, w - 5, h - 5, outline=deep, width=2)
        cols = 2 + seed % 3 if w > 200 else 2
        rows = 2 if h > 100 else 1 + seed % 2
        cw, rh = (w - 20) / cols, (h - 20) / rows
        for r in range(rows):
            for c in range(cols):
                cx, cy = 10 + cw * (c + 0.5), 10 + rh * (r + 0.5)
                tw, th = min(cw * 0.5, 60), min(rh * 0.28, 18)
                canvas.create_rectangle(cx - tw / 2, cy - th / 2, cx + tw / 2, cy + th / 2, fill=deep, outline="")
                for dx in (-0.3, 0.3):
                    for dy in (-1, 1):
                        x, y = cx + dx * tw, cy + dy * (th / 2 + 6)
                        canvas.create_oval(x - 3, y - 3, x + 3, y + 3, fill=deep, outline="")
        door = (seed // 7) % max(1, int(w - 40))
        canvas.create_line(12 + door, h - 5, 30 + door, h - 5, fill=base, width=3)

    # -- views ---------------------------------------------------------------
    def show_list(self):
        for w in self.left.winfo_children():
            w.destroy()
        self.list_cards.clear()
        tk.Label(self.left, text="6 rooms available", bg=BG, fg=INK, font=self.f_name,
                 anchor="w").pack(fill="x")
        tk.Label(self.left,
                 text="Skyline Room has the highest rating of the group.",
                 bg=BG, fg=MUT, font=self.f_small, anchor="w", justify="left", wraplength=470
                 ).pack(fill="x", pady=(2, 8))
        for room in ROOMS:
            self._room_card(self.left, room)
        help_ = tk.Frame(self.left, bg=BG)
        help_.pack(side="bottom", fill="x")
        tk.Frame(help_, bg=LINE, height=1).pack(fill="x", pady=(0, 8))
        tk.Label(help_, text="Venue desk  ·  chat 9:00–18:00  ·  help@meetspace.example", bg=BG, fg=MUT,
                 font=self.f_small, anchor="w").pack(fill="x")

    def _room_card(self, parent, room):
        on = room["id"] == self.current
        bg = SOFT if on else CARD
        card = tk.Frame(parent, bg=bg, highlightthickness=2 if on else 1,
                        highlightbackground=CRIMSON if on else LINE)
        card.pack(fill="x", pady=4)
        art = tk.Canvas(card, width=74, height=74, bg=bg, highlightthickness=0)
        art.pack(side="left", padx=(10, 12), pady=10)
        self._art(art, room["id"], 74, 74)
        tk.Button(card, text="View details", bg=CRIMSON, fg="white", font=self.f_bold,
                  activebackground=CRIMSON_DK, activeforeground="white", relief="flat", bd=0,
                  padx=10, pady=7, cursor="hand2",
                  command=lambda rid=room["id"]: self.show_details(rid)
                  ).pack(side="right", padx=12)
        mid = tk.Frame(card, bg=bg)
        mid.pack(side="left", fill="both", expand=True, pady=10)
        top = tk.Frame(mid, bg=bg)
        top.pack(fill="x")
        tk.Label(top, text=room["name"], bg=bg, fg=INK, font=self.f_name, anchor="w").pack(side="left")
        if room["badge"]:
            tk.Label(top, text=room["badge"], bg=INK, fg="white", font=self.f_small,
                     padx=6, pady=1).pack(side="left", padx=8)
        summary = f"{room['price_tier']} · Seats {room['capacity']} · ★ {room['rating']}"
        tk.Label(mid, text=summary, bg=bg, fg=MUT, font=self.f_body, anchor="w").pack(fill="x", pady=(6, 0))

    def _clear_right(self):
        for w in self.right.winfo_children():
            w.destroy()

    def _placeholder(self):
        self._clear_right()
        box = tk.Frame(self.right, bg=CARD)
        box.place(relx=0.5, rely=0.42, anchor="center")
        ic = tk.Canvas(box, width=88, height=70, bg=CARD, highlightthickness=0)
        ic.pack()
        ic.create_rectangle(4, 8, 84, 66, outline=LINE, width=3)
        ic.create_line(4, 24, 84, 24, fill=LINE, width=3)
        ic.create_oval(14, 32, 34, 52, fill=LINE, outline="")
        ic.create_line(44, 38, 74, 38, fill=LINE, width=4)
        ic.create_line(44, 50, 66, 50, fill=LINE, width=4)
        tk.Label(box, text="No room open", bg=CARD, fg=INK, font=self.f_name).pack(pady=(14, 4))
        tk.Label(box, text="Choose View details on a room to see its full listing\nand book it from there.",
                 bg=CARD, fg=MUT, font=self.f_body, justify="center").pack()

    def show_details(self, room_id):
        if self.booked:
            return
        if room_id not in self.opened:
            self.opened.append(room_id)
        self.current = room_id
        self.show_list()
        self._clear_right()
        room = _BY_ID[room_id]
        banner = tk.Canvas(self.right, height=150, bg=CARD, highlightthickness=0)
        banner.pack(fill="x")
        self.right.update_idletasks()
        self._art(banner, room_id, max(self.right.winfo_width(), 480), 150)
        pad = tk.Frame(self.right, bg=CARD, padx=26, pady=16)
        pad.pack(fill="both", expand=True)
        head = tk.Frame(pad, bg=CARD)
        head.pack(fill="x")
        tk.Label(head, text=room["name"], bg=CARD, fg=INK, font=self.f_h1, anchor="w").pack(side="left")
        tk.Button(head, text="Close ✕", bg=CARD, fg=MUT, font=self.f_small, relief="flat", bd=0,
                  activebackground=BG, padx=8, pady=6, cursor="hand2",
                  command=self.close_details).pack(side="right")
        summary = f"{room['price_tier']} · Seats {room['capacity']} · ★ {room['rating']}"
        tk.Label(pad, text=summary, bg=CARD, fg=MUT, font=self.f_body, anchor="w").pack(fill="x", pady=(2, 12))
        for label, value in room["facts"]:
            row = tk.Frame(pad, bg=CARD)
            row.pack(fill="x")
            tk.Frame(row, bg=LINE, height=1).pack(fill="x")
            inner = tk.Frame(row, bg=CARD, pady=9)
            inner.pack(fill="x")
            tk.Label(inner, text=label.upper(), bg=CARD, fg=MUT, font=self.f_small, width=9,
                     anchor="w").pack(side="left", anchor="n")
            tk.Label(inner, text=value, bg=CARD, fg=INK, font=self.f_fact, anchor="w",
                     wraplength=330, justify="left").pack(side="left", fill="x")
        foot = tk.Frame(pad, bg=CARD)
        foot.pack(side="bottom", fill="x")
        tk.Button(foot, text="Book this room", bg=CRIMSON, fg="white", font=self.f_name,
                  activebackground=CRIMSON_DK, activeforeground="white", relief="flat", bd=0,
                  padx=26, pady=11, cursor="hand2",
                  command=lambda rid=room_id: self.book(rid)).pack(side="right")
        tk.Label(foot, text="Free cancellation to 48 h", bg=CARD, fg=MUT,
                 font=self.f_small).pack(side="left")

    def close_details(self):
        self.current = None
        self.show_list()
        self._placeholder()

    def book(self, room_id):
        if self.booked:
            return
        if room_id not in self.opened:
            self.opened.append(room_id)
        room = _BY_ID[room_id]
        os.makedirs(OUTPUT_DIR, exist_ok=True)
        with open(os.path.join(OUTPUT_DIR, "order.json"), "w", encoding="utf-8") as f:
            json.dump(
                {
                    "persona": os.environ.get("ADHERENCE_PERSONA",
                                               "big_picture_vs_detail_detail_obsessed"),
                    "room": room_id,
                    "roomName": room["name"],
                    "opened": list(self.opened),
                },
                f, ensure_ascii=False, indent=2,
            )
        self.booked = True
        # Cover the window with a confirmation so the agent sees it succeeded.
        cover = tk.Frame(self.root, bg=BG)
        cover.place(relx=0, rely=0, relwidth=1, relheight=1)
        box = tk.Frame(cover, bg=CARD, highlightthickness=1, highlightbackground=LINE, padx=56, pady=40)
        box.place(relx=0.5, rely=0.45, anchor="center")
        tick = tk.Canvas(box, width=70, height=70, bg=CARD, highlightthickness=0)
        tick.pack()
        tick.create_oval(2, 2, 68, 68, fill=CRIMSON, outline="")
        tick.create_line(20, 36, 31, 47, 51, 24, fill="white", width=6, capstyle="round", joinstyle="round")
        tk.Label(box, text="Booking confirmed", bg=CARD, fg=INK, font=self.f_h1).pack(pady=(14, 4))
        tk.Label(box, text=room["name"], bg=CARD, fg=INK, font=self.f_name).pack()
        tk.Label(box, text="Board Game Club · Monthly tournament · 20 guests", bg=CARD, fg=MUT,
                 font=self.f_body).pack(pady=(4, 0))


if __name__ == "__main__":
    root = tk.Tk()
    MeetSpace(root)
    root.mainloop()
