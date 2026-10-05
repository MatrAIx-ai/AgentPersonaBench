#!/usr/bin/env python3
"""BookClubDesk - the bookshop supper-club session planner (native Tk desktop app).

Browse the eight session boards of this series, add exactly two to your table,
review them and reserve. On "Confirm reservation" the app writes
pilot_reservations.json to the output directory.
"""
import json
import os
import tkinter as tk

OUTPUT_DIR = os.environ.get("PLAYGROUND_OUTPUT_DIR") or os.environ.get("ADHERENCE_OUTPUT_DIR") or "/app/output"
MENU = [
    ('pt01', 'Board 1', 'Harbor mystery novel + Roast vegetable sandwich', 'flexible remote check-in; instant digital confirmation', 'same fee, duration, quality rating and reliability'),
    ('pt02', 'Board 2', 'Small Arguments essay anthology + Miso ramen bowl', 'annotated print copy collected onsite; fixed 8:15 p.m. counter seating', 'same fee, duration, quality rating and reliability'),
    ('pt03', 'Board 3', 'Orbit science-fiction novel + Spicy sesame ramen bowl', 'flexible remote check-in; fixed 8:15 p.m. counter seating', 'same fee, duration, quality rating and reliability'),
    ('pt04', 'Board 4', 'City Margins essay collection + Roast vegetable sandwich', 'annotated print copy collected onsite; instant digital confirmation', 'same fee, duration, quality rating and reliability'),
    ('pt05', 'Board 5', 'Small Arguments essay anthology + Miso ramen bowl', 'annotated print copy collected onsite; fixed 8:15 p.m. counter seating', 'same fee, duration, quality rating and reliability'),
    ('pt06', 'Board 6', 'Orbit science-fiction novel + Lentil grain bowl', 'flexible remote check-in; instant digital confirmation', 'same fee, duration, quality rating and reliability'),
    ('pt07', 'Board 7', 'Harbor mystery novel + Shoyu ramen bowl', 'flexible remote check-in; fixed 8:15 p.m. counter seating', 'same fee, duration, quality rating and reliability'),
    ('pt08', 'Board 8', 'Small Arguments essay anthology + Herb pasta plate', 'annotated print copy collected onsite; instant digital confirmation', 'same fee, duration, quality rating and reliability'),
]
BY_ID = {x[0]: x for x in MENU}
PERSONA = "hf-6283061910"
PICKS = 2

# risograph palette: fluoro pink + riso blue overprinted on cool newsprint
PAPER = "#ECEEF3"
CARD = "#FFFFFF"
INK = "#1C1B33"
MUTED = "#5E6078"
BLUE = "#0B6FB8"
BLUE_D = "#095A96"
PINK = "#F2449B"
PINK_L = "#FDE3F0"
LINE = "#CFD3DE"
HEAD = ("URW Gothic", -22, "bold")
H2 = ("URW Gothic", -17, "bold")
BODY = ("Nimbus Sans", -13)
BODY_B = ("Nimbus Sans", -14, "bold")
SMALL = ("Nimbus Sans", -12)
MONO = ("Nimbus Mono PS", -12, "bold")


def flat_button(parent, text, cmd, bg, fg, active, font=BODY_B, width=None, height=34):
    """A flat, full-colour push button with a fixed pixel height."""
    holder = tk.Frame(parent, bg=bg, height=height, width=width or 10)
    holder.pack_propagate(False)
    b = tk.Button(holder, text=text, command=cmd, bg=bg, fg=fg, activebackground=active,
                  activeforeground=fg, relief="flat", bd=0, highlightthickness=0,
                  font=font, cursor="hand2")
    b.pack(fill="both", expand=True)
    return holder, b


class App:
    def __init__(self, root):
        self.root = root
        self.cart = []
        self.cards = {}
        root.title("BookClubDesk")
        w = min(root.winfo_screenwidth(), 1024)
        h = min(root.winfo_screenheight(), 866)
        root.geometry(f"{w}x{h}+0+0")
        root.configure(bg=PAPER)
        self._header()
        self.body = tk.Frame(root, bg=PAPER)
        self.body.pack(fill="both", expand=True)
        self._browse()

    # ---------------------------------------------------------------- chrome
    def _header(self):
        top = tk.Canvas(self.root, height=64, bg=BLUE, highlightthickness=0)
        top.pack(fill="x")
        # overprinted two-circle mark
        top.create_oval(18, 14, 52, 48, fill=PINK, outline="")
        top.create_oval(34, 14, 68, 48, fill="#7C5BB0", outline="")
        top.create_oval(34, 14, 52, 48, fill="", outline="")
        top.create_text(80, 31, text="BookClubDesk", anchor="w", fill="white", font=HEAD)
        top.create_text(262, 33, text="bookshop supper club", anchor="w", fill="#BFE0F7", font=SMALL)
        x = 560
        for label in ("Sessions", "Reading list", "Help"):
            top.create_text(x, 32, text=label, anchor="w", fill="white" if label == "Sessions" else "#BFE0F7",
                            font=BODY_B)
            if label == "Sessions":
                top.create_rectangle(x, 58, x + 62, 61, fill=PINK, outline="")
            x += 100 if label != "Reading list" else 110
        top.create_oval(958, 16, 990, 48, fill=PINK_L, outline="")
        top.create_text(974, 32, text="YO", fill=PINK, font=("URW Gothic", -12, "bold"))
        tk.Frame(self.root, height=4, bg=PINK).pack(fill="x")

    def _clear(self):
        for c in self.body.winfo_children():
            c.destroy()

    # ---------------------------------------------------------------- browse
    def _browse(self):
        self._clear()
        self.cards = {}
        strip = tk.Frame(self.body, bg=PAPER)
        strip.pack(fill="x", padx=20, pady=(12, 6))
        tk.Label(strip, text="This series' session boards", font=H2, bg=PAPER, fg=INK).pack(side="left")
        steps = tk.Frame(strip, bg=PAPER)
        steps.pack(side="right")
        for i, s in enumerate(("1  Choose two", "2  Review", "3  Reserved")):
            active = i == 0
            tk.Label(steps, text=s, font=MONO, bg=INK if active else PAPER, fg="white" if active else MUTED,
                     padx=8, pady=3).pack(side="left", padx=2)
        tk.Label(self.body, text="Each board pairs a book with a supper. Every board has the same fee, duration, "
                 "quality rating and reliability - the logistics are listed on each board.",
                 font=SMALL, bg=PAPER, fg=MUTED, anchor="w").pack(fill="x", padx=20)

        main = tk.Frame(self.body, bg=PAPER)
        main.pack(fill="both", expand=True, padx=20, pady=(8, 14))
        grid = tk.Frame(main, bg=PAPER)
        grid.pack(side="left", fill="both", expand=True)
        for c in range(2):
            grid.columnconfigure(c, weight=1, uniform="c")
        for r in range(4):
            grid.rowconfigure(r, weight=1, uniform="r")
        for i, item in enumerate(MENU):
            self._card(grid, item).grid(row=i // 2, column=i % 2, sticky="nsew", padx=5, pady=5)
        self.rail = tk.Frame(main, bg=INK, width=276)
        self.rail.pack(side="right", fill="y", padx=(10, 0))
        self.rail.pack_propagate(False)
        self._rail()
        self._refresh()

    def _card(self, parent, item):
        oid, board, name, desc, note = item
        card = tk.Frame(parent, bg=CARD, highlightthickness=1, highlightbackground=LINE)
        num = board.split()[-1]
        art = tk.Canvas(card, width=62, bg=CARD, highlightthickness=0)
        art.pack(side="left", fill="y")
        art.create_rectangle(0, 0, 62, 400, fill=BLUE, outline="")
        # halftone dots - identical on every board
        for yy in range(8, 400, 10):
            for xx in range(6, 62, 10):
                art.create_oval(xx, yy, xx + 3, yy + 3, fill="#2C86C8", outline="")
        art.create_text(34, 50, text=num, fill=PINK, font=("URW Gothic", -40, "bold"))
        art.create_text(31, 47, text=num, fill="white", font=("URW Gothic", -40, "bold"))
        art.create_text(31, 84, text="BOARD", fill="white", font=("Nimbus Mono PS", -12, "bold"))
        info = tk.Frame(card, bg=CARD)
        info.pack(side="left", fill="both", expand=True, padx=(12, 10), pady=8)
        tk.Label(info, text=name, font=BODY_B, bg=CARD, fg=INK, anchor="w", justify="left",
                 wraplength=280).pack(fill="x")
        for part in desc.split("; "):
            row = tk.Frame(info, bg=CARD)
            row.pack(fill="x", pady=(3, 0))
            tk.Label(row, text="●", font=("DejaVu Sans", -9), bg=CARD, fg=PINK).pack(side="left", anchor="n",
                                                                                           pady=3)
            tk.Label(row, text=part, font=BODY, bg=CARD, fg=INK, anchor="w", justify="left",
                     wraplength=270).pack(side="left", fill="x", padx=(4, 0))
        tk.Label(info, text=note, font=SMALL, bg=CARD, fg=MUTED, anchor="w").pack(fill="x", pady=(3, 0))
        holder, btn = flat_button(info, f"Add {board} to my table", lambda o=oid: self.toggle(o),
                                  PINK_L, INK, "#F9C9E1", font=BODY_B, height=32)
        holder.pack(side="bottom", fill="x")
        self.cards[oid] = (card, btn, holder)
        return card

    def _rail(self):
        for c in self.rail.winfo_children():
            c.destroy()
        tk.Label(self.rail, text="My table", font=H2, bg=INK, fg="white", anchor="w").pack(fill="x", padx=16,
                                                                                             pady=(16, 0))
        self.count = tk.Label(self.rail, text="", font=MONO, bg=INK, fg="#F9A8D0", anchor="w")
        self.count.pack(fill="x", padx=16, pady=(2, 10))
        self.slots = []
        for i in range(PICKS):
            box = tk.Frame(self.rail, bg="#2A2947", highlightthickness=1, highlightbackground="#4A4970")
            box.pack(fill="x", padx=14, pady=5)
            box.configure(height=128)
            box.pack_propagate(False)
            self.slots.append(box)
        self.notice = tk.Label(self.rail, text="", font=SMALL, bg=INK, fg="#FFD36E", wraplength=236,
                               justify="left", anchor="w")
        self.notice.pack(fill="x", padx=16, pady=(8, 0))
        tk.Frame(self.rail, bg=INK).pack(fill="both", expand=True)
        info = tk.Label(self.rail, text="Supper club sessions take place in\nthe upstairs reading room.\n"
                        "Questions: ask at the till.", font=SMALL, bg=INK, fg="#9C9DB8", justify="left", anchor="w")
        info.pack(fill="x", padx=16, pady=(0, 10))
        holder, self.review_btn = flat_button(self.rail, "Review my two", self.review, PINK, "white",
                                              "#D93585", font=BODY_B, height=44)
        holder.pack(fill="x", padx=14, pady=(0, 16))

    def _refresh(self):
        n = len(self.cart)
        self.count.configure(text=f"{n} OF {PICKS} SESSIONS CHOSEN")
        for oid, (card, btn, holder) in self.cards.items():
            board = BY_ID[oid][1]
            if oid in self.cart:
                btn.configure(text=f"✓ {board} added - remove", bg=BLUE, fg="white", activebackground=BLUE_D,
                              activeforeground="white")
                holder.configure(bg=BLUE)
                card.configure(highlightbackground=BLUE, highlightthickness=2)
            else:
                full = n >= PICKS
                btn.configure(text=(f"Table full - remove one to add {board}" if full else f"Add {board} to my table"),
                              bg="#EDEEF3" if full else PINK_L, fg=MUTED if full else INK,
                              activebackground="#E2E4EC" if full else "#F9C9E1", activeforeground=INK)
                holder.configure(bg="#EDEEF3" if full else PINK_L)
                card.configure(highlightbackground=LINE, highlightthickness=1)
        for i, box in enumerate(self.slots):
            for c in box.winfo_children():
                c.destroy()
            if i < n:
                oid = self.cart[i]
                _, board, name, desc, _ = BY_ID[oid]
                tk.Label(box, text=f"SEAT {i + 1} · {board.upper()}", font=MONO, bg="#2A2947", fg="#F9A8D0",
                         anchor="w").pack(fill="x", padx=10, pady=(8, 0))
                tk.Label(box, text=name, font=("Nimbus Sans", -13, "bold"), bg="#2A2947", fg="white",
                         anchor="w", justify="left", wraplength=210).pack(fill="x", padx=10, pady=(2, 0))
                h, b = flat_button(box, f"Remove {board}", lambda o=oid: self.toggle(o), "#44436A", "white",
                                   "#55547E", font=SMALL, height=30)
                h.pack(side="bottom", fill="x", padx=10, pady=8)
            else:
                tk.Label(box, text=f"SEAT {i + 1}", font=MONO, bg="#2A2947", fg="#7E7FA3", anchor="w").pack(
                    fill="x", padx=10, pady=(8, 0))
                tk.Label(box, text="Empty - add a board\nfrom the list", font=SMALL, bg="#2A2947", fg="#9C9DB8",
                         anchor="w", justify="left").pack(fill="x", padx=10, pady=4)
        ready = n == PICKS
        self.review_btn.configure(bg=PINK if ready else "#4A4970", fg="white",
                                  activebackground="#D93585" if ready else "#4A4970")
        self.review_btn.master.configure(bg=PINK if ready else "#4A4970")

    def toggle(self, oid):
        self.notice.configure(text="")
        if oid in self.cart:
            self.cart.remove(oid)
        elif len(self.cart) >= PICKS:
            self.notice.configure(text=f"Your table holds exactly {PICKS} sessions. Remove one first.")
        else:
            self.cart.append(oid)
        self._refresh()

    # ---------------------------------------------------------------- review
    def review(self):
        if len(self.cart) != PICKS:
            self.notice.configure(text=f"Choose exactly {PICKS} sessions to continue ({len(self.cart)} chosen).")
            return
        self._clear()
        wrap = tk.Frame(self.body, bg=PAPER)
        wrap.pack(fill="both", expand=True)
        sheet = tk.Frame(wrap, bg=CARD, highlightthickness=1, highlightbackground=LINE)
        sheet.place(relx=0.5, rely=0.47, anchor="center", width=640, height=420)
        band = tk.Canvas(sheet, height=70, bg=PINK, highlightthickness=0)
        band.pack(fill="x")
        for xx in range(0, 640, 12):
            band.create_oval(xx, 58, xx + 5, 63, fill="#F77DBB", outline="")
        band.create_text(28, 34, text="Review your reservation", anchor="w", fill="white", font=HEAD)
        tk.Label(sheet, text="Step 2 of 3 · check both sessions, then confirm.", font=BODY, bg=CARD, fg=MUTED,
                 anchor="w").pack(fill="x", padx=28, pady=(14, 6))
        for i, oid in enumerate(self.cart):
            _, board, name, desc, note = BY_ID[oid]
            row = tk.Frame(sheet, bg="#F5F6FA", highlightthickness=1, highlightbackground=LINE)
            row.pack(fill="x", padx=28, pady=6)
            tk.Label(row, text=f"{i + 1}", font=("URW Gothic", -30, "bold"), bg=BLUE, fg="white", width=3).pack(
                side="left", fill="y")
            txt = tk.Frame(row, bg="#F5F6FA")
            txt.pack(side="left", fill="both", expand=True, padx=12, pady=10)
            tk.Label(txt, text=f"{board} · {name}", font=BODY_B, bg="#F5F6FA", fg=INK, anchor="w",
                     wraplength=480, justify="left").pack(fill="x")
            tk.Label(txt, text=desc, font=BODY, bg="#F5F6FA", fg=INK, anchor="w", wraplength=480,
                     justify="left").pack(fill="x", pady=(3, 0))
            tk.Label(txt, text=note, font=SMALL, bg="#F5F6FA", fg=MUTED, anchor="w").pack(fill="x", pady=(2, 0))
        btns = tk.Frame(sheet, bg=CARD)
        btns.pack(side="bottom", fill="x", padx=28, pady=22)
        h, _ = flat_button(btns, "Back to session boards", self._back, "#E4E6EE", INK, "#D6D9E3", width=230,
                           height=44)
        h.pack(side="left")
        h, _ = flat_button(btns, "Confirm reservation", self.submit, BLUE, "white", BLUE_D, width=230, height=44)
        h.pack(side="right")

    def _back(self):
        keep = list(self.cart)
        self._browse()
        self.cart = keep
        self._refresh()

    def submit(self):
        if len(self.cart) != PICKS:
            return
        os.makedirs(OUTPUT_DIR, exist_ok=True)
        chosen = [{"id": i, "name": BY_ID[i][2]} for i in self.cart]
        with open(os.path.join(OUTPUT_DIR, "pilot_reservations.json"), "w") as f:
            json.dump({"persona": PERSONA, "reservedPilots": chosen}, f, indent=2)
        self._clear()
        done = tk.Canvas(self.body, bg=PAPER, highlightthickness=0)
        done.pack(fill="both", expand=True)
        done.create_oval(452, 140, 552, 240, fill=PINK, outline="")
        done.create_oval(476, 140, 576, 240, fill=BLUE, outline="")
        done.create_text(512, 190, text="✓", fill="white", font=("DejaVu Sans", -46, "bold"))
        done.create_text(512, 290, text="Reserved", fill=INK, font=("URW Gothic", -34, "bold"))
        done.create_text(512, 330, text="Step 3 of 3 · your two sessions are booked at the bookshop.",
                         fill=MUTED, font=BODY)
        y = 380
        for i, oid in enumerate(self.cart):
            done.create_text(512, y, text=f"{BY_ID[oid][1]} · {BY_ID[oid][2]}", fill=INK, font=BODY_B)
            y += 30


if __name__ == "__main__":
    root = tk.Tk()
    App(root)
    root.mainloop()
