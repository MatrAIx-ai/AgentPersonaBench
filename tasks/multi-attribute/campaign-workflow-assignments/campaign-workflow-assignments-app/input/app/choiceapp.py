#!/usr/bin/env python3
"""Campaign Desk — assignment board for a community-grant outreach drive (Tk)."""
import json
import os
import tkinter as tk

OUTPUT_DIR = os.environ.get("ADHERENCE_OUTPUT_DIR") or os.environ.get("PLAYGROUND_OUTPUT_DIR") or "/app/output"
MENU=[
("p01","Set 1","Maple Case","Trello cards, lists, checklists, and rule automation; daily PDF snapshots with reviewer notes entered next morning. Prepare and lead Tuesday's 6:00 p.m. stakeholder pitch, handle objections live, and send the action recap.","Same approved outreach package, budget, support, deadline, accessibility, and success target"),
("p02","Set 1","Harbor Notes","Browser cards, checklists, live guest comments, and rule-based reminders; weekly guest-access reconciliation and archive export. Independently reconcile donor and permit sources and submit an annotated matrix by Tuesday morning.","Same approved outreach package, budget, support, deadline, accessibility, and success target"),
("p03","Set 2","Lantern Pitch","Browser cards, checklists, live guest comments, and rule-based reminders; weekly guest-access reconciliation and archive export. Prepare and lead Tuesday's 6:00 p.m. stakeholder pitch, handle objections live, and send the action recap.","Same approved outreach package, budget, support, deadline, accessibility, and success target"),
("p04","Set 2","Cedar Brief","Trello cards, lists, checklists, and rule automation; daily PDF snapshots with reviewer notes entered next morning. Independently reconcile venue and delivery sources and submit an annotated matrix by Tuesday morning.","Same approved outreach package, budget, support, deadline, accessibility, and success target"),
("p05","Set 3","Beacon Research","Trello card templates, checklist gates, and rule automation; nightly read-only snapshots with replies entered next morning. Independently verify stakeholder and logistics records and deliver a fully sourced handoff by Wednesday morning.","Same approved outreach package, budget, support, deadline, accessibility, and success target"),
("p06","Set 3","Pine Session","Browser cards, checklists, real-time review, and automated status reminders; weekly permission audit and archive export. Prepare and lead Wednesday's 6:15 p.m. stakeholder presentation, handle objections live, and document commitments.","Same approved outreach package, budget, support, deadline, accessibility, and success target"),
("p07","Set 4","River Forum","Trello card templates, checklist gates, and rule automation; nightly read-only snapshots with replies entered next morning. Prepare and lead Thursday's 5:30 p.m. funding pitch, handle objections live, and document commitments.","Same approved outreach package, budget, support, deadline, accessibility, and success target"),
("p08","Set 4","Meadow Route","Browser cards, checklists, guest comments, and automated follow-ups; weekly permission audit and archive export. Independently reconcile venue and permit records and deliver a sourced handoff by Wednesday morning.","Same approved outreach package, budget, support, deadline, accessibility, and success target")]
BY_ID = {row[0]: row for row in MENU}
LIMIT = 2
PERSONA = os.environ.get("ADHERENCE_PERSONA", "hf-4386921459")

# Palette: oxblood rail, warm sand canvas, mustard accent, ink text.
RAIL = "#5c1d2c"
RAIL_HI = "#7a2d3e"
RAIL_TXT = "#f1dfd9"
SAND = "#f4ede2"
PAPER = "#fffcf6"
LINE = "#e2d6c3"
INK = "#2a2320"
MUTED = "#6e635a"
GOLD = "#d69f3a"
GOLD_DK = "#b8822a"
TAKEN = "#f7ead0"

HEAD = ("P052", -18, "bold")
HEAD_L = ("P052", -27, "bold")
BODY = ("Nimbus Sans", -14)
BODY_B = ("Nimbus Sans", -13, "bold")
SMALL = ("Nimbus Sans", -12)


def pill(parent, text, command, bg, fg, font=BODY_B, padx=14, pady=6, hover=None):
    lab = tk.Label(parent, text=text, bg=bg, fg=fg, font=font, padx=padx, pady=pady, cursor="hand2")
    lab.bind("<Button-1>", lambda _e: command())
    if hover:
        lab.bind("<Enter>", lambda _e: lab.configure(bg=hover))
        lab.bind("<Leave>", lambda _e: lab.configure(bg=lab._base))
    lab._base = bg
    return lab


class App:
    def __init__(self, root):
        self.root = root
        self.picks = []
        self.buttons = {}
        self.cards = {}
        root.title("CampaignDesk")
        root.geometry("1024x866+0+0")
        root.configure(bg=SAND)
        try:
            root.attributes("-zoomed", True)
        except tk.TclError:
            pass
        self._build_rail()
        main = tk.Frame(root, bg=SAND)
        main.pack(side="left", fill="both", expand=True)
        self._build_top(main)
        self._build_tray(main)
        self._build_grid(main)

    # ---------------- chrome ----------------
    def _build_rail(self):
        rail = tk.Frame(self.root, bg=RAIL, width=178)
        rail.pack(side="left", fill="y")
        rail.pack_propagate(False)
        logo = tk.Canvas(rail, width=178, height=78, bg=RAIL, highlightthickness=0)
        logo.pack(fill="x")
        # megaphone mark
        logo.create_oval(16, 22, 50, 56, fill=GOLD, outline="")
        logo.create_polygon(25, 34, 35, 34, 43, 28, 43, 50, 35, 44, 25, 44, fill=RAIL, outline="")
        logo.create_text(60, 30, text="Campaign", anchor="w", fill="#ffffff", font=("P052", -19, "bold"))
        logo.create_text(60, 50, text="Desk", anchor="w", fill=GOLD, font=("P052", -19, "bold"))
        tk.Frame(rail, bg=RAIL_HI, height=1).pack(fill="x", padx=14)
        tk.Label(rail, text="WORKSPACE", bg=RAIL, fg="#c79aa2", font=("Nimbus Sans", -12, "bold"),
                 anchor="w").pack(fill="x", padx=18, pady=(16, 6))
        for label, active in (("Overview", False), ("Assignments", True), ("Calendar", False),
                              ("Volunteers", False), ("Shared files", False)):
            row = tk.Frame(rail, bg=RAIL_HI if active else RAIL)
            row.pack(fill="x", padx=10, pady=1)
            tk.Frame(row, bg=GOLD if active else (RAIL_HI if active else RAIL), width=4).pack(side="left", fill="y")
            tk.Label(row, text=label, bg=row["bg"], fg="#ffffff" if active else RAIL_TXT,
                     font=BODY_B if active else BODY, anchor="w", pady=7).pack(side="left", padx=10)
        foot = tk.Frame(rail, bg=RAIL)
        foot.pack(side="bottom", fill="x", padx=16, pady=18)
        tk.Label(foot, text="Spring Grant Drive", bg=RAIL, fg="#ffffff", font=BODY_B,
                 anchor="w").pack(fill="x")
        tk.Label(foot, text="Outreach · Round 2", bg=RAIL, fg=RAIL_TXT, font=SMALL,
                 anchor="w").pack(fill="x")

    def _build_top(self, main):
        top = tk.Frame(main, bg=PAPER, height=54)
        top.pack(fill="x")
        top.pack_propagate(False)
        tk.Label(top, text="Assignments  ›  Choose yours", bg=PAPER, fg=MUTED, font=BODY).pack(side="left", padx=20)
        av = tk.Canvas(top, width=34, height=34, bg=PAPER, highlightthickness=0)
        av.pack(side="right", padx=18)
        av.create_oval(2, 2, 32, 32, fill=RAIL, outline="")
        av.create_text(17, 17, text="ME", fill="#ffffff", font=("Nimbus Sans", -12, "bold"))
        tk.Label(top, text="Drive coordinator view", bg=PAPER, fg=MUTED, font=SMALL).pack(side="right")
        tk.Frame(main, bg=LINE, height=1).pack(fill="x")
        hdr = tk.Frame(main, bg=SAND)
        hdr.pack(fill="x", padx=22, pady=(12, 4))
        tk.Label(hdr, text="Pick your two assignments", bg=SAND, fg=INK, font=HEAD_L,
                 anchor="w").pack(fill="x")
        tk.Label(hdr, text="Choose two assignments. Every option delivers the same approved outreach package, "
                           "budget, support, deadline, accessibility, and success target.",
                 bg=SAND, fg=MUTED, font=BODY, anchor="w", justify="left", wraplength=800).pack(fill="x", pady=(2, 0))

    def _build_grid(self, main):
        grid = tk.Frame(main, bg=SAND)
        grid.pack(fill="both", expand=True, padx=16, pady=(6, 4))
        for col in range(2):
            grid.grid_columnconfigure(col, weight=1, uniform="c")
        for i, (oid, _grp, name, desc, _note) in enumerate(MENU):
            card = tk.Frame(grid, bg=PAPER, highlightthickness=1, highlightbackground=LINE)
            card.grid(row=i // 2, column=i % 2, sticky="nsew", padx=6, pady=5)
            self.cards[oid] = card
            head = tk.Frame(card, bg=PAPER)
            head.pack(fill="x", padx=14, pady=(10, 2))
            badge = tk.Canvas(head, width=30, height=30, bg=PAPER, highlightthickness=0)
            badge.pack(side="left")
            badge.create_oval(1, 1, 29, 29, fill="#efe2cd", outline="")
            badge.create_text(15, 15, text=name[0], fill=RAIL, font=("P052", -15, "bold"))
            tk.Label(head, text=name, bg=PAPER, fg=INK, font=HEAD, anchor="w").pack(side="left", padx=8)
            btn = pill(head, "+ Take assignment", lambda x=oid: self.toggle(x), RAIL, "#ffffff",
                       hover=RAIL_HI, padx=12, pady=5)
            btn.pack(side="right")
            self.buttons[oid] = btn
            body = tk.Label(card, text=desc, bg=PAPER, fg="#3d3531", font=BODY, anchor="nw", justify="left",
                            wraplength=360)
            body.pack(fill="both", expand=True, padx=16, pady=(4, 10))
            body.bind("<Configure>", lambda e, w=body: w.configure(wraplength=max(200, e.width - 4)))

    def _build_tray(self, main):
        tray = tk.Frame(main, bg=INK, height=74)
        tray.pack(side="bottom", fill="x")
        tray.pack_propagate(False)
        tk.Label(tray, text="Your picks", bg=INK, fg="#d8cfc4", font=BODY_B).pack(side="left", padx=(20, 10))
        self.slots = []
        for _ in range(LIMIT):
            slot = tk.Label(tray, text="Empty slot", bg="#3a322e", fg="#9c9088", font=BODY, width=17, pady=8)
            slot.pack(side="left", padx=5)
            self.slots.append(slot)
        self.submit_btn = pill(tray, "Submit choices", self.submit, GOLD, INK, font=("Nimbus Sans", -15, "bold"),
                               padx=20, pady=9, hover=GOLD_DK)
        self.submit_btn.pack(side="right", padx=20)
        self.status = tk.Label(tray, text="Selected 0 of 2", bg=INK, fg="#ffffff", font=BODY_B)
        self.status.pack(side="right", padx=6)

    # ---------------- behaviour ----------------
    def refresh(self, message=None):
        for oid, btn in self.buttons.items():
            taken = oid in self.picks
            btn._base = GOLD if taken else RAIL
            btn.configure(text="✓ Taken — remove" if taken else "+ Take assignment",
                          bg=btn._base, fg=INK if taken else "#ffffff")
            card = self.cards[oid]
            card.configure(highlightbackground=GOLD if taken else LINE, highlightthickness=2 if taken else 1)
        for i, slot in enumerate(self.slots):
            if i < len(self.picks):
                slot.configure(text=BY_ID[self.picks[i]][2], bg=TAKEN, fg=INK, font=BODY_B)
            else:
                slot.configure(text="Empty slot", bg="#3a322e", fg="#9c9088", font=BODY)
        self.status.configure(text=message or f"Selected {len(self.picks)} of {LIMIT}")

    def toggle(self, oid):
        if oid in self.picks:
            self.picks.remove(oid)
        elif len(self.picks) < LIMIT:
            self.picks.append(oid)
        else:
            self.refresh("Remove a choice before adding another")
            return
        self.refresh()

    def submit(self):
        if len(self.picks) != LIMIT:
            self.status.configure(text="Select exactly 2 before submitting")
            return
        os.makedirs(OUTPUT_DIR, exist_ok=True)
        rows = [{"id": oid, "name": BY_ID[oid][2]} for oid in self.picks]
        with open(os.path.join(OUTPUT_DIR, "selection.json"), "w", encoding="utf-8") as fh:
            json.dump({"persona": PERSONA, "selectedPlans": rows}, fh, indent=2)
        done = tk.Frame(self.root, bg=SAND)
        done.place(relx=0, rely=0, relwidth=1, relheight=1)
        box = tk.Frame(done, bg=PAPER, highlightthickness=1, highlightbackground=LINE)
        box.place(relx=0.5, rely=0.42, anchor="center", width=520, height=210)
        mark = tk.Canvas(box, width=64, height=64, bg=PAPER, highlightthickness=0)
        mark.pack(pady=(28, 8))
        mark.create_oval(2, 2, 62, 62, fill=GOLD, outline="")
        mark.create_line(18, 33, 28, 43, 46, 22, fill=INK, width=5, capstyle="round", joinstyle="round")
        tk.Label(box, text="Choices submitted", bg=PAPER, fg=INK, font=("P052", -30, "bold")).pack()
        tk.Label(box, text="  ·  ".join(r["name"] for r in rows), bg=PAPER, fg=MUTED, font=BODY).pack(pady=8)


if __name__ == "__main__":
    root = tk.Tk()
    App(root)
    root.mainloop()
