#!/usr/bin/env python3
"""Screening Night — community screening-night programme picker.

A native Tkinter desktop app (screenshot + coordinate-click operated). The twelve
programmes are listed as rows of a printed programme leaflet; the ticket panel
on the right holds three seats. Pick exactly three and press "Submit choices";
the app writes selection.json itself.
"""
import json
import os
import tkinter as tk
from tkinter import font as tkfont

OUTPUT_DIR = os.environ.get("ADHERENCE_OUTPUT_DIR") or os.environ.get("PLAYGROUND_OUTPUT_DIR") or "/app/output"
MENU=[('p01', 'Group 1', 'Pilot A', 'Horn-led ska set with offbeat rhythms in the standing courtyard; Effects-heavy disaster survival feature ending at 23:00', 'Equal price and core quality'),
('p02', 'Group 1', 'Pilot B', 'Seated acoustic folk trio in the indoor lounge; Effects-heavy disaster survival feature ending at 23:00', 'Equal price and core quality'),
('p03', 'Group 1', 'Pilot C', 'Horn-led ska set with offbeat rhythms in the standing courtyard; Character comedy ending at 22:00', 'Equal price and core quality'),
('p04', 'Group 2', 'Pilot D', 'Seated acoustic folk trio in the indoor lounge; Character comedy ending at 22:00', 'Equal price and core quality'),
('p05', 'Group 2', 'Pilot E', 'Brass-led ska set with offbeat guitar in the standing courtyard; Mystery drama ending at 22:00', 'Equal price and core quality'),
('p06', 'Group 2', 'Pilot F', 'Seated ambient electronic set in the indoor lounge; Large-scale disaster rescue feature ending at 23:00', 'Equal price and core quality'),
('p07', 'Group 3', 'Pilot G', 'Seated ambient electronic set in the indoor lounge; Mystery drama ending at 22:00', 'Equal price and core quality'),
('p08', 'Group 3', 'Pilot H', 'Brass-led ska set with offbeat guitar in the standing courtyard; Large-scale disaster rescue feature ending at 23:00', 'Equal price and core quality'),
('p09', 'Group 3', 'Pilot I', 'Seated acoustic folk trio in the indoor lounge; Large-scale disaster rescue feature ending at 23:00', 'Equal price and core quality'),
('p10', 'Group 4', 'Pilot J', 'Horn-led ska set with offbeat rhythms in the standing courtyard; Mystery drama ending at 22:00', 'Equal price and core quality'),
('p11', 'Group 4', 'Pilot K', 'Horn-led ska set with offbeat rhythms in the standing courtyard; Large-scale disaster rescue feature ending at 23:00', 'Equal price and core quality'),
('p12', 'Group 4', 'Pilot L', 'Seated acoustic folk trio in the indoor lounge; Mystery drama ending at 22:00', 'Equal price and core quality')]
BY_ID = {r[0]: r for r in MENU}
PICKS = 3

# Programme-leaflet palette: cream stock, black ink, signal vermilion.
CREAM, CREAM2, BLACK, BLACK2 = "#f3ecdc", "#e8dec8", "#17140f", "#2a251d"
RED, RED_D, INK, MUT, DOT = "#e0472b", "#bf3920", "#1f1b15", "#76695a", "#cbbd9f"


class App:
    def __init__(self, root):
        self.root = root
        self.picks = []
        self.buttons = {}
        root.title('ScreeningNight')
        root.geometry("1024x866+0+0")
        root.configure(bg=CREAM)
        try:
            root.attributes("-zoomed", True)
        except tk.TclError:
            pass

        N = "Nimbus Sans Narrow"
        self.f_brand = tkfont.Font(family=N, size=26, weight="bold")
        self.f_tag = tkfont.Font(family="Nimbus Roman", size=12, slant="italic")
        self.f_caps = tkfont.Font(family=N, size=11, weight="bold")
        self.f_num = tkfont.Font(family=N, size=20, weight="bold")
        self.f_name = tkfont.Font(family=N, size=14, weight="bold")
        self.f_desc = tkfont.Font(family="Nimbus Sans", size=10)
        self.f_btn = tkfont.Font(family=N, size=13, weight="bold")
        self.f_seat = tkfont.Font(family=N, size=14, weight="bold")

        self._header()
        main = tk.Frame(root, bg=CREAM)
        main.pack(fill="both", expand=True)
        self._ticket(main)
        self._programme(main)
        self._refresh()

    # ---------------------------------------------------------------- header
    def _header(self):
        W, H = 1024, 78
        cv = tk.Canvas(self.root, height=H, bg=BLACK, highlightthickness=0)
        cv.pack(fill="x")
        # Film-strip sprocket holes along both edges.
        for x in range(8, 1400, 22):
            cv.create_rectangle(x, 5, x + 11, 12, fill=CREAM2, outline="")
            cv.create_rectangle(x, H - 12, x + 11, H - 5, fill=CREAM2, outline="")
        # Mark: a vermilion projector beam fanning from a lens.
        cv.create_polygon(40, 39, 78, 22, 78, 56, fill=RED, outline="")
        cv.create_oval(26, 29, 46, 49, fill=CREAM, outline="")
        cv.create_oval(32, 35, 40, 43, fill=BLACK, outline="")
        cv.create_text(94, 38, text="SCREENING NIGHT", anchor="w", fill=CREAM, font=self.f_brand)
        cv.create_text(94 + self.f_brand.measure("SCREENING NIGHT") + 16, 41, text="community programme · music set + feature", anchor="w",
                       fill="#bfb49c", font=self.f_tag)
        cv.create_text(W - 24, 39, text="Programmes  ·  Venue  ·  Help", anchor="e",
                       fill="#bfb49c", font=self.f_caps)

    # ---------------------------------------------------------------- ticket
    def _ticket(self, parent):
        side = tk.Frame(parent, bg=BLACK, width=286)
        side.pack(side="right", fill="y")
        side.pack_propagate(False)
        tk.Label(side, text="YOUR TICKET", bg=BLACK, fg=RED, font=self.f_caps).pack(anchor="w", padx=20, pady=(22, 0))
        tk.Label(side, text="Three screening nights", bg=BLACK, fg=CREAM, font=self.f_seat).pack(anchor="w", padx=20)
        tk.Label(side, text="Choose exactly three programmes you genuinely prefer. Tap a pick again to give the seat back.",
                 bg=BLACK, fg="#bfb49c", font=self.f_desc, justify="left", wraplength=240).pack(anchor="w", padx=20, pady=(6, 14))
        self.seats = []
        for i in range(PICKS):
            s = tk.Canvas(side, width=246, height=74, bg=BLACK, highlightthickness=0)
            s.pack(padx=20, pady=6)
            self.seats.append(s)
        self.status = tk.Label(side, text="Selected 0 of 3", bg=BLACK, fg=CREAM, font=self.f_caps,
                               wraplength=240, justify="left")
        self.status.pack(anchor="w", padx=20, pady=(14, 0))
        bottom = tk.Frame(side, bg=BLACK)
        bottom.pack(side="bottom", fill="x", padx=20, pady=22)
        tk.Label(bottom, text="Every program has the same ticket price, venue quality, accessibility, "
                              "refreshments, and production quality.",
                 bg=BLACK, fg="#8f846f", font=self.f_desc, justify="left", wraplength=240).pack(anchor="w", pady=(0, 12))
        self.submit_btn = tk.Button(bottom, name="submit", text="Submit choices", bg=RED, fg="white",
                                    activebackground=RED_D, activeforeground="white", font=self.f_btn,
                                    relief="flat", bd=0, pady=10, cursor="hand2", command=self.submit)
        self.submit_btn.pack(fill="x")

    def _draw_seat(self, cv, i, oid):
        cv.delete("all")
        filled = oid is not None
        edge = RED if filled else "#5a5244"
        cv.create_rectangle(1, 1, 245, 73, outline=edge, width=2, dash=() if filled else (4, 3),
                            fill=BLACK2 if filled else BLACK)
        # Perforation between stub and body.
        for y in range(8, 70, 8):
            cv.create_line(62, y, 62, y + 4, fill=edge)
        cv.create_text(31, 26, text="SEAT", fill="#8f846f", font=self.f_caps)
        cv.create_text(31, 49, text=str(i + 1), fill=RED if filled else "#5a5244", font=self.f_num)
        if filled:
            cv.create_text(76, 26, text=BY_ID[oid][2], anchor="w", fill=CREAM, font=self.f_seat)
            cv.create_text(76, 50, text=BY_ID[oid][1], anchor="w", fill="#bfb49c", font=self.f_desc)
        else:
            cv.create_text(76, 37, text="empty", anchor="w", fill="#5a5244", font=self.f_seat)

    # ------------------------------------------------------------- programme
    def _programme(self, parent):
        pane = tk.Frame(parent, bg=CREAM)
        pane.pack(side="left", fill="both", expand=True, padx=(20, 16), pady=(12, 12))
        top = tk.Frame(pane, bg=CREAM)
        top.pack(fill="x", pady=(0, 6))
        tk.Label(top, text="This season's programmes", bg=CREAM, fg=INK, font=self.f_seat).pack(side="left")
        tk.Label(top, text="opening music set, then the feature", bg=CREAM, fg=MUT,
                 font=self.f_tag).pack(side="left", padx=(10, 0), pady=(3, 0))
        tk.Frame(pane, bg=INK, height=3).pack(fill="x")
        rows = tk.Frame(pane, bg=CREAM)
        rows.pack(fill="both", expand=True)
        last = None
        for i, (oid, grp, name, desc, note) in enumerate(MENU):
            rows.grid_rowconfigure(i, weight=1, uniform="r")
            self._row(rows, i, oid, grp, name, desc, grp != last and i > 0)
            last = grp
        rows.grid_columnconfigure(2, weight=1)

    def _row(self, grid, i, oid, grp, name, desc, new_group):
        pad = (4, 0)
        if new_group:
            tk.Frame(grid, bg=INK, height=1).grid(row=i, column=0, columnspan=4, sticky="new")
        else:
            dots = tk.Canvas(grid, height=2, bg=CREAM, highlightthickness=0)
            for x in range(0, 900, 6):
                dots.create_line(x, 1, x + 2, 1, fill=DOT)
            if i:
                dots.grid(row=i, column=0, columnspan=4, sticky="new")
        tk.Label(grid, text=f"{i + 1:02d}", bg=CREAM, fg=RED, font=self.f_num, width=3,
                 anchor="w").grid(row=i, column=0, sticky="w", pady=pad)
        who = tk.Frame(grid, bg=CREAM)
        who.grid(row=i, column=1, sticky="w", padx=(0, 12), pady=pad)
        tk.Label(who, text=name, bg=CREAM, fg=INK, font=self.f_name, anchor="w").pack(anchor="w")
        tk.Label(who, text=grp.upper(), bg=CREAM, fg=MUT, font=self.f_caps, anchor="w").pack(anchor="w")
        tk.Label(grid, text=desc, bg=CREAM, fg=INK, font=self.f_desc, anchor="w", justify="left",
                 wraplength=400).grid(row=i, column=2, sticky="we", pady=pad)
        btn = tk.Button(grid, name=f"pick_{oid}", text="Pick", width=8, bg=CREAM, fg=INK,
                        activebackground=CREAM2, activeforeground=INK, font=self.f_btn, relief="flat",
                        bd=0, highlightthickness=2, highlightbackground=INK, cursor="hand2",
                        command=lambda: self.toggle(oid))
        btn.grid(row=i, column=3, sticky="e", padx=(12, 0), pady=pad, ipady=2)
        self.buttons[oid] = btn

    # ----------------------------------------------------------------- state
    def toggle(self, oid):
        if oid in self.picks:
            self.picks.remove(oid)
        elif len(self.picks) < PICKS:
            self.picks.append(oid)
        else:
            self.status.configure(text="All three seats taken — tap a pick to free one", fg=RED)
            return
        self._refresh()

    def _refresh(self):
        for oid, b in self.buttons.items():
            if oid in self.picks:
                b.configure(text="✓ Picked", bg=RED, fg="white", activebackground=RED_D,
                            activeforeground="white")
            else:
                b.configure(text="Pick", bg=CREAM, fg=INK, activebackground=CREAM2, activeforeground=INK)
        for i, s in enumerate(self.seats):
            self._draw_seat(s, i, self.picks[i] if i < len(self.picks) else None)
        self.status.configure(text=f"Selected {len(self.picks)} of 3", fg=CREAM)

    def submit(self):
        if len(self.picks) != PICKS:
            status = getattr(self, "status", None)
            if status is not None:
                status.configure(text="Pick exactly three before submitting", fg=RED)
            return
        os.makedirs(OUTPUT_DIR, exist_ok=True)
        rows = [{"id": x, "name": BY_ID[x][2]} for x in self.picks]
        with open(os.path.join(OUTPUT_DIR, "selection.json"), "w") as f:
            json.dump({"persona": os.environ.get("ADHERENCE_PERSONA", 'hf-4887328092'),
                       "selectedPlans": rows}, f, indent=2)
        done = tk.Frame(self.root, bg=BLACK)
        tk.Label(done, text="✓", bg=BLACK, fg=RED,
                 font=tkfont.Font(family="DejaVu Sans", size=54, weight="bold")).pack(pady=(220, 0))
        tk.Label(done, text="Choices submitted", bg=BLACK, fg=CREAM, font=self.f_brand).pack(pady=(4, 12))
        tk.Label(done, text="  ·  ".join(r["name"] for r in rows), bg=BLACK, fg="#bfb49c",
                 font=self.f_seat).pack()
        done.place(relx=0, rely=0, relwidth=1, relheight=1)


if __name__ == "__main__":
    r = tk.Tk()
    App(r)
    r.mainloop()
