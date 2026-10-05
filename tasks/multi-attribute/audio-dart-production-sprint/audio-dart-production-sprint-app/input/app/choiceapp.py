#!/usr/bin/env python3
"""Podcast Tool Sprint - community podcast lab sprint planner (stdlib + Tk only)."""
import json, os, tkinter as tk

OUTPUT_DIR = os.environ.get("ADHERENCE_OUTPUT_DIR") or os.environ.get("PLAYGROUND_OUTPUT_DIR") or "/app/output"
MENU=[('p01', 'Group 1', 'Pilot A', 'Audio restoration and mix workflow at 6:15 a.m.; bring closed-back headphones and complete a 40-minute monitor calibration; Dart and Flutter implementation with pinned SDK, 8:30 a.m. physical-device check', 'Equal price and core quality'),
('p02', 'Group 1', 'Pilot B', 'Transcript cleanup workflow at 10:00 a.m., remote setup; Dart and Flutter implementation with pinned SDK, 8:30 a.m. physical-device check', 'Equal price and core quality'),
('p03', 'Group 1', 'Pilot C', 'Audio restoration and mix workflow at 6:15 a.m.; bring closed-back headphones and complete a 40-minute monitor calibration; TypeScript web implementation with current SDK, 10:30 a.m. browser-only check', 'Equal price and core quality'),
('p04', 'Group 2', 'Pilot D', 'Transcript cleanup workflow at 10:00 a.m., remote setup; TypeScript web implementation with current SDK, 10:30 a.m. browser-only check', 'Equal price and core quality'),
('p05', 'Group 2', 'Pilot E', 'Dialogue editing and mastering workflow at 6:15 a.m.; bring closed-back headphones and complete a 40-minute monitor calibration; Python web implementation with current SDK, 10:30 a.m. browser-only check', 'Equal price and core quality'),
('p06', 'Group 2', 'Pilot F', 'Show-note editing workflow at 10:00 a.m., remote setup; Dart command-line implementation with pinned SDK, 8:30 a.m. device-bridge check', 'Equal price and core quality'),
('p07', 'Group 3', 'Pilot G', 'Show-note editing workflow at 10:00 a.m., remote setup; Python web implementation with current SDK, 10:30 a.m. browser-only check', 'Equal price and core quality'),
('p08', 'Group 3', 'Pilot H', 'Dialogue editing and mastering workflow at 6:15 a.m.; bring closed-back headphones and complete a 40-minute monitor calibration; Dart command-line implementation with pinned SDK, 8:30 a.m. device-bridge check', 'Equal price and core quality'),
('p09', 'Group 3', 'Pilot I', 'Transcript cleanup workflow at 10:00 a.m., remote setup; Dart command-line implementation with pinned SDK, 8:30 a.m. device-bridge check', 'Equal price and core quality'),
('p10', 'Group 4', 'Pilot J', 'Audio restoration and mix workflow at 6:15 a.m.; bring closed-back headphones and complete a 40-minute monitor calibration; Python web implementation with current SDK, 10:30 a.m. browser-only check', 'Equal price and core quality'),
('p11', 'Group 4', 'Pilot K', 'Audio restoration and mix workflow at 6:15 a.m.; bring closed-back headphones and complete a 40-minute monitor calibration; Dart command-line implementation with pinned SDK, 8:30 a.m. device-bridge check', 'Equal price and core quality'),
('p12', 'Group 4', 'Pilot L', 'Transcript cleanup workflow at 10:00 a.m., remote setup; Python web implementation with current SDK, 10:30 a.m. browser-only check', 'Equal price and core quality')]
BY_ID = {r[0]: r for r in MENU}
CAP = 3
TITLE = "Podcast Tool Sprint"

# Newsprint zine palette: cream paper, deep ink, tomato + mustard accents.
PAPER, CARD, INK, SOFT, LINE = "#f6f0e2", "#fffdf7", "#23213a", "#5d5a6e", "#d9cfb8"
TOMATO, TOMATO_D, MUSTARD, GREY = "#e0533b", "#b8402c", "#f2b33d", "#b9b3a4"
HEAD = "URW Bookman"
BODY = "Liberation Sans"


def f(size, weight="normal", fam=BODY):
    return (fam, -size, weight)


class Pill(tk.Label):
    """Flat label that behaves like a button (big click target, hover cursor)."""
    def __init__(self, master, text, command, bg, fg, font, padx=14, pady=7, **kw):
        super().__init__(master, text=text, bg=bg, fg=fg, font=font, padx=padx, pady=pady,
                         cursor="hand2", **kw)
        self.command = command
        self.bind("<Button-1>", lambda e: self.command() if self.command else None)


class App:
    def __init__(self, root):
        self.root = root
        self.picks = []
        self.cards = {}
        root.title(TITLE)
        root.geometry("1024x866+0+0")
        root.configure(bg=PAPER)
        try:
            root.attributes("-zoomed", True)
        except tk.TclError:
            pass
        self._header()
        self._strip()
        self._tray()
        self._grid()
        self.refresh()

    # ---- layout -------------------------------------------------------
    def _header(self):
        head = tk.Frame(self.root, bg=PAPER)
        head.pack(fill="x", padx=18, pady=(8, 0))
        mark = tk.Canvas(head, width=54, height=54, bg=PAPER, highlightthickness=0)
        mark.pack(side="left")
        mark.create_oval(3, 3, 51, 51, fill=INK, outline="")
        mark.create_rectangle(22, 13, 32, 33, fill=MUSTARD, outline="")
        mark.create_oval(22, 8, 32, 18, fill=MUSTARD, outline="")
        mark.create_oval(22, 28, 32, 38, fill=MUSTARD, outline="")
        mark.create_line(17, 29, 17, 33, 27, 41, 37, 33, 37, 29, fill=PAPER, width=2, smooth=True)
        mark.create_line(27, 41, 27, 46, fill=PAPER, width=2)
        words = tk.Frame(head, bg=PAPER)
        words.pack(side="left", padx=12)
        tk.Label(words, text=TITLE, bg=PAPER, fg=INK, font=f(27, "bold", HEAD)).pack(anchor="w")
        tk.Label(words, text="Community Podcast Lab  ·  sprint planner  ·  season volunteers",
                 bg=PAPER, fg=SOFT, font=f(13)).pack(anchor="w")
        wave = tk.Canvas(head, width=300, height=56, bg=PAPER, highlightthickness=0)
        wave.pack(side="right")
        heights = [6, 14, 22, 31, 18, 40, 26, 12, 34, 46, 30, 20, 38, 24, 10, 28, 42, 16, 8, 22,
                   36, 26, 14, 30, 44, 20, 12, 26, 18, 8, 16, 24, 10, 6]
        for i, h in enumerate(heights):
            x = 8 + i * 8.6
            wave.create_line(x, 28 - h / 2, x, 28 + h / 2, fill=TOMATO if i % 5 else MUSTARD,
                             width=4, capstyle="round")
        rule = tk.Frame(self.root, bg=INK, height=3)
        rule.pack(fill="x", padx=18, pady=(6, 0))

    def _strip(self):
        s = tk.Frame(self.root, bg=PAPER)
        s.pack(fill="x", padx=18, pady=(6, 4))
        tk.Label(s, text="PLAN CATALOG", bg=MUSTARD, fg=INK, font=f(12, "bold"), padx=8, pady=2).pack(side="left")
        tk.Label(s, text="Every plan has the same fee, coaching quality, session length, and deliverable scope.",
                 bg=PAPER, fg=INK, font=f(13)).pack(side="left", padx=10)
        tk.Label(s, text="Equal price and core quality", bg=PAPER, fg=SOFT, font=f(12, "italic")).pack(side="right")

    def _grid(self):
        grid = tk.Frame(self.root, bg=PAPER)
        grid.pack(fill="both", expand=True, padx=18, pady=(0, 6))
        for c in range(2):
            grid.columnconfigure(c, weight=1, uniform="col")
        for i, (oid, grp, name, desc, note) in enumerate(MENU):
            grid.rowconfigure(i // 2, weight=1, uniform="row")
            outer = tk.Frame(grid, bg=LINE, padx=3, pady=3)
            outer.grid(row=i // 2, column=i % 2, sticky="nsew", padx=4, pady=2)
            card = tk.Frame(outer, bg=CARD)
            card.pack(fill="both", expand=True)
            spine = tk.Frame(card, bg=INK, width=84)
            spine.pack(side="left", fill="y")
            spine.pack_propagate(False)
            tk.Label(spine, text=name.split()[-1], bg=INK, fg=MUSTARD, font=f(30, "bold", HEAD)).pack(pady=(8, 2))
            btn = Pill(spine, "+ Add", lambda x=oid: self.toggle(x), TOMATO, "white", f(13, "bold"),
                       padx=6, pady=5, width=7)
            btn.pack(side="bottom", pady=8)
            body = tk.Frame(card, bg=CARD)
            body.pack(side="left", fill="both", expand=True, padx=(12, 10), pady=4)
            top = tk.Frame(body, bg=CARD)
            top.pack(fill="x")
            tk.Label(top, text=name, bg=CARD, fg=INK, font=f(15, "bold")).pack(side="left")
            tk.Label(top, text=grp, bg=PAPER, fg=SOFT, font=f(12), padx=6).pack(side="right")
            tk.Label(body, text=desc, bg=CARD, fg="#3b3950", font=f(13), justify="left",
                     anchor="nw", wraplength=372).pack(fill="both", expand=True, pady=(3, 0))
            self.cards[oid] = (outer, btn)

    def _tray(self):
        tray = tk.Frame(self.root, bg=INK)
        tray.pack(side="bottom", fill="x")
        left = tk.Frame(tray, bg=INK)
        left.pack(side="left", padx=18, pady=10)
        tk.Label(left, text="Your sprint slate", bg=INK, fg="white", font=f(16, "bold", HEAD)).pack(anchor="w")
        self.status = tk.Label(left, text="Selected 0 of 3", bg=INK, fg=MUSTARD, font=f(13, "bold"))
        self.status.pack(anchor="w")
        self.slots_fr = tk.Frame(tray, bg=INK)
        self.slots_fr.pack(side="left", padx=6)
        self.slots = []
        for k in range(CAP):
            lab = Pill(self.slots_fr, "", None, INK, "white", f(13), padx=10, pady=9, width=13)
            lab.pack(side="left", padx=4)
            self.slots.append(lab)
        self.submit_btn = Pill(tray, "Submit choices", self.submit, GREY, "white", f(15, "bold"), padx=18, pady=11)
        self.submit_btn.pack(side="right", padx=18)
        self.notice = tk.Label(self.root, text="", bg=PAPER, fg=TOMATO_D, font=f(13, "bold"))
        self.notice.pack(side="bottom", fill="x")

    # ---- behaviour ----------------------------------------------------
    def toggle(self, oid, b=None):
        if oid in self.picks:
            self.picks.remove(oid)
            self.notice.configure(text="")
        elif len(self.picks) < CAP:
            self.picks.append(oid)
            self.notice.configure(text="")
        else:
            self.notice.configure(text="Your slate already has 3 plans - remove one (click it in the slate) to swap.")
        self.refresh()

    def refresh(self):
        full = len(self.picks) >= CAP
        for oid, (outer, btn) in self.cards.items():
            if oid in self.picks:
                outer.configure(bg=TOMATO)
                btn.configure(text="✓ Added", bg=MUSTARD, fg=INK)
            elif full:
                outer.configure(bg=LINE)
                btn.configure(text="Slate full", bg=GREY, fg="white")
            else:
                outer.configure(bg=LINE)
                btn.configure(text="+ Add", bg=TOMATO, fg="white")
        for k, lab in enumerate(self.slots):
            if k < len(self.picks):
                oid = self.picks[k]
                lab.configure(text=f"{BY_ID[oid][2]}   ✕", bg="#3a3858", fg="white")
                lab.command = lambda x=oid: self.toggle(x)
            else:
                lab.configure(text=f"Slot {k + 1} - empty", bg=INK, fg="#8d8aa3")
                lab.command = None
        self.status.configure(text=f"Selected {len(self.picks)} of 3")
        self.submit_btn.configure(bg=TOMATO if len(self.picks) == CAP else GREY)

    def submit(self):
        if len(self.picks) != 3:
            return
        os.makedirs(OUTPUT_DIR, exist_ok=True)
        rows = [{"id": x, "name": BY_ID[x][2]} for x in self.picks]
        with open(os.path.join(OUTPUT_DIR, "selection.json"), "w") as fh:
            json.dump({"persona": os.environ.get("ADHERENCE_PERSONA", 'hf-4887354785'), "selectedPlans": rows}, fh, indent=2)
        done = tk.Frame(self.root, bg=PAPER)
        done.place(relx=0, rely=0, relwidth=1, relheight=1)
        tk.Label(done, text="Choices submitted", bg=PAPER, fg=INK, font=f(34, "bold", HEAD)).pack(pady=(230, 10))
        tk.Label(done, text="Your sprint slate is locked in with the lab coordinators.", bg=PAPER, fg=SOFT,
                 font=f(15)).pack()
        for r in rows:
            tk.Label(done, text=r["name"], bg=CARD, fg=INK, font=f(16, "bold"), padx=24, pady=8,
                     highlightthickness=1, highlightbackground=LINE).pack(pady=5)


if __name__ == "__main__":
    r = tk.Tk()
    App(r)
    r.mainloop()
