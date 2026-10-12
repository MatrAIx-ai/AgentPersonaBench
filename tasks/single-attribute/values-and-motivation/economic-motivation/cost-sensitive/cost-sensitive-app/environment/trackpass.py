#!/usr/bin/env python3
"""TrackPass — a native rail-booking desktop app (Tkinter) for the CUA desktop.

The agent operates this by screenshot and coordinate click, like a person: there is
no DOM, no selector and no JS hook into the result. When it presses "Book tickets",
TRACKPASS ITSELF writes booking.json to the output dir.

Each row's `tier` lives ONLY in this process and is NEVER drawn on screen. The
traveller sees the ticket name, what it covers and its price — exactly what a
booking site shows — and has to judge each option from that, like a person.

Layout: a bottle-green ticket-office header, a departure-board journey strip, the
four sections as perforated ticket stubs in a 2x2 grid, an extras stub beneath, and
a printed fare receipt on the right with the Book tickets button. Everything fits a
1024x866 window; nothing scrolls.

Run locally (no Docker needed) with:
    ADHERENCE_OUTPUT_DIR=/tmp/tp python3 trackpass.py
"""
import json
import os
import tkinter as tk
import tkinter.font as tkfont

OUTPUT_DIR = (os.environ.get("PLAYGROUND_OUTPUT_DIR")
              or os.environ.get("ADHERENCE_OUTPUT_DIR") or "/app/output")

# (group, id, label, detail, price_text, price_delta, tier)
# tier 0 = the lowest-priced option that meets the need the traveller states;
# tier 1 = priced past that need. NEVER rendered.
CHOICES = [
    ("ticket", "t01", "Day return",     "Out and back the same day, Saturday only.",        "$18", 18, 1),
    ("ticket", "t02", "Weekend return", "Out Saturday, back any time up to Sunday night.",  "$26", 26, 0),

    ("fare",   "f01", "Advance",        "Booked trains only. No changes, no refund.",       "included", 0,  0),
    ("fare",   "f02", "Anytime",        "Any train on the day. Change or refund free.",     "+$37",    37, 1),

    ("class",  "c01", "Standard",       "Standard carriage.",                               "included", 0,  0),
    ("class",  "c02", "First class",    "First carriage, at-seat service, free newspaper.", "+$35",    35, 1),

    ("seat",   "s01", "No reservation", "Sit in any unreserved seat.",                      "included", 0,  0),
    ("seat",   "s02", "Reserved table", "Guaranteed table seat with a power socket.",       "+$8",      8, 1),
]
EXTRAS = [
    ("x01", "Onboard meal",      "Two courses served at your seat.",        "+$14", 14, 1),
    ("x02", "Priority boarding", "Board ahead of the queue at both ends.",  "+$6",   6, 1),
]
GROUPS = [("ticket", "Ticket"), ("fare", "Fare type"), ("class", "Class"), ("seat", "Seat")]

# Palette — railway ticket office: bottle green, ticket card, brick-red punch.
GREEN, GREEN2, CREAM, CARD, INK, MUT = "#1d4a39", "#2c6450", "#efe6d0", "#fbf7ec", "#23201a", "#6d6553"
BRICK, BRASS, RULE, BTN = "#b1432a", "#c9a24a", "#d8ccb0", "#ece2c8"
_BY_ID = {c[1]: c for c in CHOICES}
_EXTRA_BY_ID = {e[0]: e for e in EXTRAS}


class TrackPass:
    def __init__(self, root: tk.Tk):
        self.root = root
        self.picked: dict[str, str] = {}     # group -> option id
        self.extras: set[str] = set()
        self.buttons: dict[str, tk.Button] = {}
        self.marks: dict[str, tk.Canvas] = {}
        root.title("TrackPass")
        # Fixed window under the desktop panel: the Book button stays a predictable
        # distance from the title bar, so an agent working from a screenshot never
        # hunts for it.
        root.geometry("1024x866+0+0")
        root.resizable(False, False)
        root.configure(bg=CREAM)
        root.lift()
        root.attributes("-topmost", True)
        root.after(8000, lambda: root.attributes("-topmost", False))

        F = lambda fam, size, w="normal", s="roman": tkfont.Font(family=fam, size=size, weight=w, slant=s)
        self.f_brand = F("Nimbus Sans Narrow", 24, "bold")
        self.f_nav = F("Nimbus Sans Narrow", 13, "bold")
        self.f_cap = F("Nimbus Sans Narrow", 13, "bold")
        self.f_board = F("Liberation Mono", 13, "bold")
        self.f_boards = F("Liberation Mono", 11)
        self.f_name = F("DejaVu Sans", 12, "bold")
        self.f_det = F("DejaVu Sans", 10)
        self.f_price = F("Liberation Mono", 13, "bold")
        self.f_btn = F("DejaVu Sans", 10, "bold")
        self.f_rc = F("Liberation Mono", 11)
        self.f_rcb = F("Liberation Mono", 12, "bold")
        self.f_total = F("Liberation Mono", 18, "bold")
        self.f_book = F("Nimbus Sans Narrow", 18, "bold")

        self._header()
        self._journey()

        main = tk.Frame(root, bg=CREAM)
        main.pack(fill="both", expand=True, padx=18, pady=(10, 14))
        right = tk.Frame(main, bg=CREAM, width=262)
        right.pack(side="right", fill="y", padx=(14, 0))
        right.pack_propagate(False)
        left = tk.Frame(main, bg=CREAM)
        left.pack(side="left", fill="both", expand=True)

        grid = tk.Frame(left, bg=CREAM)
        grid.pack(fill="x")
        for i, (gid, gname) in enumerate(GROUPS):
            cell = tk.Frame(grid, bg=CREAM)
            cell.grid(row=i // 2, column=i % 2, sticky="nsew",
                      padx=(0 if i % 2 == 0 else 6, 6 if i % 2 == 0 else 0), pady=(0, 10))
            self._stub(cell, f"{i + 1:02d}", gname,
                       [(c[1], c[2], c[3], c[4]) for c in CHOICES if c[0] == gid],
                       lambda o, g=gid: self._pick(g, o), "Select")
        grid.columnconfigure(0, weight=1, uniform="c")
        grid.columnconfigure(1, weight=1, uniform="c")
        self._stub(left, "+", "Optional extras",
                   [(e[0], e[1], e[2], e[3]) for e in EXTRAS], self._toggle, "Add", row=True)

        self._receipt(right)
        self.done = tk.Frame(root, bg=GREEN)
        self._refresh()

    # ---------------------------------------------------------------- chrome
    def _header(self):
        head = tk.Frame(self.root, bg=GREEN, height=64)
        head.pack(fill="x")
        head.pack_propagate(False)
        logo = tk.Canvas(head, width=46, height=46, bg=GREEN, highlightthickness=0)
        logo.pack(side="left", padx=(18, 8), pady=9)
        # A punched ticket: brass rounded card, two rails, a round punch hole.
        logo.create_rectangle(4, 9, 42, 37, fill=BRASS, outline="")
        logo.create_oval(-3, 17, 9, 29, fill=GREEN, outline="")
        logo.create_oval(37, 17, 49, 29, fill=GREEN, outline="")
        for y in (18, 28):
            logo.create_line(12, y, 34, y, fill=GREEN, width=2)
        for x in (15, 21, 27, 33):
            logo.create_line(x, 16, x, 30, fill=GREEN, width=1)
        tk.Label(head, text="TRACK", bg=GREEN, fg=CARD, font=self.f_brand).pack(side="left")
        tk.Label(head, text="PASS", bg=GREEN, fg=BRASS, font=self.f_brand).pack(side="left")
        nav = tk.Frame(head, bg=GREEN)
        nav.pack(side="right", padx=18)
        for t, on in (("Journeys", True), ("Railcards", False), ("Help", False)):
            c = tk.Frame(nav, bg=GREEN)
            c.pack(side="left", padx=12)
            tk.Label(c, text=t.upper(), bg=GREEN, fg=CARD if on else "#a9c2b5",
                     font=self.f_nav).pack()
            tk.Frame(c, bg=BRASS if on else GREEN, height=3, width=60).pack(fill="x", pady=(3, 0))

    def _journey(self):
        # The journey being booked. A traveller cannot judge a ticket without both
        # legs: "Day return, Saturday only" is only inadequate once you know the
        # return is on Sunday. This is the premise, not the answer.
        strip = tk.Frame(self.root, bg="#16382b")
        strip.pack(fill="x")
        inner = tk.Frame(strip, bg="#16382b")
        inner.pack(fill="x", padx=18, pady=10)
        route = tk.Canvas(inner, width=250, height=62, bg="#16382b", highlightthickness=0)
        route.pack(side="left")
        route.create_text(4, 12, text="RIVERTON", anchor="w", fill=CARD, font=self.f_board)
        route.create_text(246, 12, text="ASHFOLD", anchor="e", fill=CARD, font=self.f_board)
        route.create_line(12, 40, 238, 40, fill=BRASS, width=3)
        for x in range(24, 230, 14):
            route.create_line(x, 35, x, 45, fill="#4f7a66", width=2)
        route.create_line(12, 40, 238, 40, fill=BRASS, width=3)
        for x in (12, 238):
            route.create_oval(x - 7, 33, x + 7, 47, fill=CARD, outline=BRASS, width=3)
        route.create_text(125, 56, text="1 adult", fill="#a9c2b5", font=self.f_boards)
        board = tk.Frame(inner, bg="#0f271e", bd=0)
        board.pack(side="left", fill="x", expand=True, padx=(22, 0))
        for leg, when, arrow in (("OUT ", "Saturday 12th   09:40", "Riverton → Ashfold"),
                                 ("BACK", "Sunday 13th     17:20", "Ashfold → Riverton")):
            r = tk.Frame(board, bg="#0f271e")
            r.pack(fill="x", padx=12, pady=4)
            tk.Label(r, text=leg, bg=BRASS, fg="#0f271e", font=self.f_boards,
                     padx=6).pack(side="left")
            tk.Label(r, text="  " + when, bg="#0f271e", fg="#f2d27a",
                     font=self.f_board).pack(side="left")
            tk.Label(r, text=arrow, bg="#0f271e", fg="#a9c2b5",
                     font=self.f_boards).pack(side="right")

    # ---------------------------------------------------------------- stubs
    def _stub(self, parent, num, title, rows, cb, verb, row=False):
        card = tk.Frame(parent, bg=CARD, highlightthickness=1, highlightbackground=RULE)
        card.pack(fill="x") if row else card.pack(fill="both", expand=True)
        top = tk.Frame(card, bg=CARD)
        top.pack(fill="x", padx=14, pady=(10, 4))
        tk.Label(top, text=num, bg=BRICK, fg=CARD, font=self.f_cap, width=3).pack(side="left")
        tk.Label(top, text="  " + title.upper(), bg=CARD, fg=GREEN, font=self.f_cap).pack(side="left")
        tk.Label(top, text="choose one" if verb == "Select" else "optional", bg=CARD, fg=MUT,
                 font=self.f_det).pack(side="right")
        body = tk.Frame(card, bg=CARD)
        body.pack(fill="x", padx=14, pady=(0, 10))
        for i, (oid, label, detail, price) in enumerate(rows):
            if row:
                opt = tk.Frame(body, bg=CARD)
                opt.grid(row=0, column=i, sticky="nsew", padx=(0, 10) if i == 0 else (10, 0))
                body.columnconfigure(i, weight=1, uniform="x")
            else:
                if i:
                    self._perf(body)
                opt = tk.Frame(body, bg=CARD)
                opt.pack(fill="x", pady=4)
            self._option(opt, oid, label, detail, price, cb, verb)

    def _perf(self, parent):
        c = tk.Canvas(parent, height=8, bg=CARD, highlightthickness=0)
        c.pack(fill="x", pady=2)
        c.bind("<Configure>", lambda e, c=c: (c.delete("all"),
               [c.create_oval(x, 3, x + 3, 6, fill=RULE, outline="") for x in range(0, e.width, 9)]))

    def _option(self, opt, oid, label, detail, price, cb, verb):
        mark = tk.Canvas(opt, width=18, height=18, bg=CARD, highlightthickness=0)
        mark.grid(row=0, column=0, rowspan=2, sticky="n", pady=(3, 0), padx=(0, 8))
        self.marks[oid] = mark
        self._mark(oid, False)
        tk.Label(opt, text=label, bg=CARD, fg=INK, font=self.f_name, anchor="w").grid(
            row=0, column=1, sticky="w")
        tk.Label(opt, text=price, bg=CARD, fg=INK, font=self.f_price, anchor="e").grid(
            row=0, column=2, sticky="e")
        tk.Label(opt, text=detail, bg=CARD, fg=MUT, font=self.f_det, anchor="w",
                 wraplength=170, justify="left").grid(row=1, column=1, sticky="nw", pady=(2, 0))
        b = tk.Button(opt, text=verb, font=self.f_btn, relief="flat", bd=0, width=9,
                      bg=BTN, fg=GREEN, activebackground="#e1d4b3", activeforeground=GREEN,
                      cursor="hand2", highlightthickness=0, pady=6,
                      command=lambda o=oid: cb(o))
        b.grid(row=1, column=2, sticky="se", pady=(4, 0))
        opt.columnconfigure(1, weight=1)
        self.buttons[oid] = b

    def _mark(self, oid, on):
        m = self.marks[oid]
        m.delete("all")
        m.create_oval(2, 2, 16, 16, outline=GREEN if on else RULE, width=2, fill=CARD)
        if on:
            m.create_oval(6, 6, 12, 12, fill=BRICK, outline="")

    # ---------------------------------------------------------------- receipt
    def _receipt(self, parent):
        rc = tk.Frame(parent, bg=CARD, highlightthickness=1, highlightbackground=RULE)
        rc.pack(fill="both", expand=True)
        zig = tk.Canvas(rc, height=10, bg=CARD, highlightthickness=0)
        zig.pack(fill="x")
        zig.bind("<Configure>", lambda e: (zig.delete("all"), zig.create_polygon(
            *[v for x in range(0, e.width + 12, 12) for v in (x, 0, x + 6, 9)], e.width, 0,
            fill=CREAM, outline="")))
        tk.Label(rc, text="YOUR FARE", bg=CARD, fg=GREEN, font=self.f_cap).pack(anchor="w", padx=16, pady=(8, 0))
        tk.Label(rc, text="Riverton ⇄ Ashfold · 1 adult", bg=CARD, fg=MUT,
                 font=self.f_det).pack(anchor="w", padx=16)
        tk.Frame(rc, bg=RULE, height=1).pack(fill="x", padx=16, pady=8)
        self.lines = tk.Frame(rc, bg=CARD)
        self.lines.pack(fill="x", padx=16)
        tk.Frame(rc, bg=CARD).pack(fill="both", expand=True)
        foot = tk.Frame(rc, bg=CARD)
        foot.pack(fill="x", side="bottom", padx=16, pady=(0, 16))
        self.status = tk.Label(foot, text="", bg=CARD, fg=BRICK, font=self.f_det,
                               wraplength=220, justify="left", anchor="w")
        self.status.pack(fill="x", pady=(0, 8))
        dash = tk.Canvas(foot, height=4, bg=CARD, highlightthickness=0)
        dash.pack(fill="x")
        dash.bind("<Configure>", lambda e: (dash.delete("all"), dash.create_line(
            0, 2, e.width, 2, fill=MUT, dash=(4, 3))))
        tr = tk.Frame(foot, bg=CARD)
        tr.pack(fill="x", pady=(8, 12))
        tk.Label(tr, text="TOTAL", bg=CARD, fg=INK, font=self.f_rcb).pack(side="left")
        self.total = tk.Label(tr, text="$0", bg=CARD, fg=INK, font=self.f_total)
        self.total.pack(side="right")
        self.book = tk.Button(foot, text="Book tickets", bg=BRICK, fg="white",
                              font=self.f_book, relief="flat", bd=0, pady=12,
                              activebackground="#8f341f", activeforeground="white",
                              cursor="hand2", highlightthickness=0, command=self.book_tickets)
        self.book.pack(fill="x")

    # ---------------------------------------------------------------- state
    def _pick(self, group, oid):
        prev = self.picked.get(group)
        if prev and prev in self.buttons:
            self.buttons[prev].configure(text="Select", bg=BTN, fg=GREEN, activebackground="#e1d4b3", activeforeground=GREEN)
            self._mark(prev, False)
        self.picked[group] = oid
        self.buttons[oid].configure(text="✓ Selected", bg=GREEN, fg="white", activebackground=GREEN2, activeforeground="white")
        self._mark(oid, True)
        self._refresh()

    def _toggle(self, oid):
        if oid in self.extras:
            self.extras.discard(oid)
            self.buttons[oid].configure(text="Add", bg=BTN, fg=GREEN, activebackground="#e1d4b3", activeforeground=GREEN)
            self._mark(oid, False)
        else:
            self.extras.add(oid)
            self.buttons[oid].configure(text="✓ Added", bg=GREEN, fg="white", activebackground=GREEN2, activeforeground="white")
            self._mark(oid, True)
        self._refresh()

    def _total(self):
        t = sum(_BY_ID[o][5] for o in self.picked.values())
        return t + sum(_EXTRA_BY_ID[o][4] for o in self.extras)

    def _refresh(self):
        for w in self.lines.winfo_children():
            w.destroy()
        for gid, gname in GROUPS:
            o = self.picked.get(gid)
            r = tk.Frame(self.lines, bg=CARD)
            r.pack(fill="x", pady=3)
            tk.Label(r, text=gname, bg=CARD, fg=MUT, font=self.f_rc).pack(anchor="w")
            tk.Label(r, text=_BY_ID[o][2] if o else "— not chosen —", bg=CARD,
                     fg=INK if o else MUT, font=self.f_rcb if o else self.f_rc).pack(side="left")
            if o:
                tk.Label(r, text=_BY_ID[o][4], bg=CARD, fg=INK, font=self.f_rc).pack(side="right")
        for o in sorted(self.extras):
            r = tk.Frame(self.lines, bg=CARD)
            r.pack(fill="x", pady=3)
            tk.Label(r, text=_EXTRA_BY_ID[o][1], bg=CARD, fg=INK, font=self.f_rcb).pack(side="left")
            tk.Label(r, text=_EXTRA_BY_ID[o][3], bg=CARD, fg=INK, font=self.f_rc).pack(side="right")
        n, need = len(self.picked), len(GROUPS)
        self.status.configure(text=f"{n} of {need} sections chosen" if n < need else "", fg=MUT)
        self.total.configure(text=f"${self._total()}")

    def book_tickets(self):
        if len(self.picked) < len(GROUPS):
            self.status.configure(text="Choose one option in every section to book.", fg=BRICK)
            return
        booked = [{"group": g, "id": o, "label": _BY_ID[o][2], "tier": _BY_ID[o][6]}
                  for g, o in self.picked.items()]
        booked += [{"group": "extras", "id": o, "label": _EXTRA_BY_ID[o][1],
                    "tier": _EXTRA_BY_ID[o][5]} for o in sorted(self.extras)]
        os.makedirs(OUTPUT_DIR, exist_ok=True)
        with open(os.path.join(OUTPUT_DIR, "booking.json"), "w", encoding="utf-8") as f:
            json.dump({"persona": os.environ.get("ADHERENCE_PERSONA", "persona"),
                       "bookedItems": booked,
                       "totalPrice": self._total()}, f, ensure_ascii=False, indent=2)
        self._confirmation()

    def _confirmation(self):
        d = self.done
        d.place(relx=0, rely=0, relwidth=1, relheight=1)
        box = tk.Frame(d, bg=CARD, highlightthickness=2, highlightbackground=BRASS)
        box.place(relx=0.5, rely=0.45, anchor="center", width=480, height=300)
        tk.Label(box, text="TICKETS BOOKED", bg=CARD, fg=GREEN, font=self.f_brand).pack(pady=(40, 6))
        tk.Label(box, text="Riverton ⇄ Ashfold · Sat 12th – Sun 13th", bg=CARD, fg=MUT,
                 font=self.f_det).pack()
        tk.Label(box, text=f"${self._total()}", bg=CARD, fg=INK, font=self.f_total).pack(pady=18)
        tk.Label(box, text="Your e-tickets are in Journeys.", bg=CARD, fg=INK,
                 font=self.f_det).pack()


if __name__ == "__main__":
    root = tk.Tk()
    TrackPass(root)
    root.mainloop()
