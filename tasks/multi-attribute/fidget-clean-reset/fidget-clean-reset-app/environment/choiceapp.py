#!/usr/bin/env python3
"""FocusReset - book focus-session plans at the studio (native desktop app).

Browse the four plan groups, add three plans to your booking tray, review
them and click "Submit choices"; the app writes selection.json to the
output directory.
"""
import json
import os
import tkinter as tk

OUTPUT_DIR = os.environ.get("ADHERENCE_OUTPUT_DIR") or os.environ.get("PLAYGROUND_OUTPUT_DIR") or "/app/output"
MENU=[('p01', 'Group 1', 'Pilot A', 'Compact 45 cm desk with no external monitor or desk power and a silent resistance ring; Thirty-minute self-cleaning and sorting reset inside every session', 'Equal price and core quality'),
('p02', 'Group 1', 'Pilot B', 'Full 120 cm desk with an external monitor and no tactile hand aid; Thirty-minute self-cleaning and sorting reset inside every session', 'Equal price and core quality'),
('p03', 'Group 1', 'Pilot C', 'Compact 45 cm desk with no external monitor or desk power and a silent resistance ring; Uninterrupted full focus block with a weekly facilities clean', 'Equal price and core quality'),
('p04', 'Group 2', 'Pilot D', 'Full 120 cm desk with an external monitor and no tactile hand aid; Uninterrupted full focus block with a weekly facilities clean', 'Equal price and core quality'),
('p05', 'Group 2', 'Pilot E', 'Compact 45 cm standing desk with no external monitor or desk power and a silent textured ring; Uninterrupted focus block with weekly surface organization by staff', 'Equal price and core quality'),
('p06', 'Group 2', 'Pilot F', 'Full 120 cm standing desk with an external monitor and no tactile hand aid; Thirty-minute self-cleaning and desk reset inside every session', 'Equal price and core quality'),
('p07', 'Group 3', 'Pilot G', 'Full 120 cm standing desk with an external monitor and no tactile hand aid; Uninterrupted focus block with weekly surface organization by staff', 'Equal price and core quality'),
('p08', 'Group 3', 'Pilot H', 'Compact 45 cm standing desk with no external monitor or desk power and a silent textured ring; Thirty-minute self-cleaning and desk reset inside every session', 'Equal price and core quality'),
('p09', 'Group 3', 'Pilot I', 'Full 120 cm desk with an external monitor and no tactile hand aid; Thirty-minute self-cleaning and desk reset inside every session', 'Equal price and core quality'),
('p10', 'Group 4', 'Pilot J', 'Compact 45 cm desk with no external monitor or desk power and a silent resistance ring; Uninterrupted focus block with weekly surface organization by staff', 'Equal price and core quality'),
('p11', 'Group 4', 'Pilot K', 'Compact 45 cm desk with no external monitor or desk power and a silent resistance ring; Thirty-minute self-cleaning and desk reset inside every session', 'Equal price and core quality'),
('p12', 'Group 4', 'Pilot L', 'Full 120 cm desk with an external monitor and no tactile hand aid; Uninterrupted focus block with weekly surface organization by staff', 'Equal price and core quality')]
BY_ID = {r[0]: r for r in MENU}
GROUPS = []
for _r in MENU:
    if _r[1] not in GROUPS:
        GROUPS.append(_r[1])
LIMIT = 3
SHARED = ("Every plan has the same fee, three-hour reservation, lighting, chair, "
          "laptop, privacy, and deliverable target.")

W, H = 1024, 866
# palette: slate-indigo chrome, oat paper, citron accent
SLATE, SLATE2, INK, MUTED = "#2b2d42", "#3a3d58", "#23252f", "#6b6f7e"
PAPER, CARD, LINE = "#f5f2ec", "#ffffff", "#e3ded4"
CITRON, CITRON_D, CORAL = "#d8e357", "#a9b52c", "#e4574c"
HEAD, BODY = "URW Gothic", "Nimbus Sans"


def split_desc(desc):
    a, _, b = desc.partition("; ")
    return a, b


def rrect(c, x0, y0, x1, y1, r, **kw):
    pts = [x0 + r, y0, x1 - r, y0, x1, y0, x1, y0 + r, x1, y1 - r, x1, y1,
           x1 - r, y1, x0 + r, y1, x0, y1, x0, y1 - r, x0, y0 + r, x0, y0]
    return c.create_polygon(pts, smooth=True, splinesteps=12, **kw)


class App:
    def __init__(self, root):
        self.root = root
        self.picks = []
        self.group = GROUPS[0]
        self.screen = "browse"
        self.notice = ""
        self._hot = {}
        root.title("FocusReset")
        root.geometry("1024x866+0+0")
        root.configure(bg=PAPER)
        try:
            root.attributes("-zoomed", True)
        except tk.TclError:
            pass
        self.c = tk.Canvas(root, bg=PAPER, highlightthickness=0, width=W, height=H)
        self.c.pack(fill="both", expand=True)
        self.c.bind("<Button-1>", self._click)
        self.c.bind("<Motion>", self._motion)
        self.c.bind("<Configure>", lambda e: self.draw())
        self.draw()

    # ---- hit regions -------------------------------------------------
    def region(self, key, box, action):
        self._hot[key] = (box, action)

    def hot(self, key):
        (x0, y0, x1, y1), _ = self._hot[key]
        return self.c.winfo_rootx() + (x0 + x1) // 2, self.c.winfo_rooty() + (y0 + y1) // 2

    def _find(self, x, y):
        for key, ((x0, y0, x1, y1), action) in self._hot.items():
            if x0 <= x <= x1 and y0 <= y <= y1:
                return action
        return None

    def _click(self, e):
        action = self._find(e.x, e.y)
        if action:
            action()
            self.draw()

    def _motion(self, e):
        self.c.configure(cursor="hand2" if self._find(e.x, e.y) else "")

    # ---- actions -----------------------------------------------------
    def add(self, oid):
        if oid in self.picks:
            return
        if len(self.picks) >= LIMIT:
            self.notice = "Your tray already holds three plans - remove one to swap."
            return
        self.picks.append(oid)
        self.notice = f"{BY_ID[oid][2]} added to your tray."

    def remove(self, oid):
        if oid in self.picks:
            self.picks.remove(oid)
            self.notice = f"{BY_ID[oid][2]} removed."

    def set_group(self, g):
        self.group = g
        self.notice = ""

    def go(self, screen):
        if screen == "review" and len(self.picks) != LIMIT:
            self.notice = "Choose exactly three plans before reviewing."
            return
        self.screen = screen
        self.notice = ""

    def submit(self):
        if len(self.picks) != LIMIT:
            return
        os.makedirs(OUTPUT_DIR, exist_ok=True)
        rows = [{"id": x, "name": BY_ID[x][2]} for x in self.picks]
        with open(os.path.join(OUTPUT_DIR, "selection.json"), "w") as fh:
            json.dump({"persona": os.environ.get("ADHERENCE_PERSONA", '0094'), "selectedPlans": rows}, fh, indent=2)
        self.screen = "done"

    # ---- drawing -----------------------------------------------------
    def button(self, key, x0, y0, x1, y1, text, action, style="primary", size=12):
        c = self.c
        fill, fg, outline = {
            "primary": (SLATE, "#ffffff", SLATE),
            "accent": (CITRON, INK, CITRON_D),
            "ghost": (CARD, INK, "#c9c3b6"),
            "done": ("#eef1c9", INK, CITRON_D),
            "off": ("#e8e5de", "#9a9aa3", "#dcd8cf"),
        }[style]
        rrect(c, x0, y0, x1, y1, (y1 - y0) // 2, fill=fill, outline=outline, width=1)
        c.create_text((x0 + x1) // 2, (y0 + y1) // 2, text=text, fill=fg, font=(BODY, size, "bold"))
        if action is not None:
            self.region(key, (x0, y0, x1, y1), action)

    def logo(self, x, y):
        c = self.c
        c.create_oval(x - 17, y - 17, x + 17, y + 17, outline="#585c7a", width=4)
        c.create_arc(x - 17, y - 17, x + 17, y + 17, start=90, extent=-250, style="arc", outline=CITRON, width=4)
        c.create_line(x, y, x, y - 9, fill="#ffffff", width=3, capstyle="round")
        c.create_line(x, y, x + 7, y + 3, fill="#ffffff", width=3, capstyle="round")

    def draw(self):
        c = self.c
        c.delete("all")
        self._hot = {}
        self.sidebar()
        if self.screen == "browse":
            self.browse()
        elif self.screen == "review":
            self.review()
        else:
            self.done()

    def sidebar(self):
        c = self.c
        c.create_rectangle(0, 0, 250, H, fill=SLATE, outline="")
        self.logo(40, 44)
        c.create_text(70, 36, text="FocusReset", anchor="w", fill="#ffffff", font=(HEAD, 20, "bold"))
        c.create_text(71, 60, text="focus studio booking", anchor="w", fill="#b9bcd3", font=(BODY, 11))
        steps = [("1", "Choose three plans", "browse"), ("2", "Review your tray", "review"), ("3", "Booked", "done")]
        order = ["browse", "review", "done"]
        cur = order.index(self.screen)
        y = 120
        c.create_text(24, y, text="YOUR BOOKING", anchor="w", fill="#8f93b3", font=(BODY, 10, "bold"))
        y += 30
        for i, (num, label, key) in enumerate(steps):
            active = i == cur
            past = i < cur
            if active:
                rrect(c, 14, y - 20, 236, y + 20, 12, fill=SLATE2, outline="")
            col = CITRON if (active or past) else "#6d7194"
            c.create_oval(28, y - 13, 54, y + 13, fill=col if past else "", outline=col, width=2)
            c.create_text(41, y, text="✓" if past else num, fill=INK if past else col, font=(BODY, 11, "bold"))
            c.create_text(66, y, text=label, anchor="w", fill="#ffffff" if active else "#c3c6dc",
                          font=(BODY, 13, "bold" if active else "normal"))
            y += 50
        # included box
        y += 16
        rrect(c, 14, y, 236, y + 150, 14, fill=SLATE2, outline="")
        c.create_text(30, y + 22, text="Included with every plan", anchor="w", fill=CITRON, font=(BODY, 11, "bold"))
        c.create_text(30, y + 44, text=SHARED, anchor="nw", width=190, fill="#e6e7f1", font=(BODY, 12))
        # studio card
        y = H - 150
        c.create_line(24, y, 226, y, fill="#44476a")
        c.create_text(24, y + 22, text="Studio hours", anchor="w", fill="#8f93b3", font=(BODY, 10, "bold"))
        c.create_text(24, y + 44, text="Open 07:00 - 22:00", anchor="w", fill="#ffffff", font=(BODY, 12))
        c.create_text(24, y + 66, text="Front desk: ext. 204", anchor="w", fill="#c3c6dc", font=(BODY, 12))
        c.create_oval(24, y + 92, 58, y + 126, fill="#585c7a", outline="")
        c.create_text(41, y + 109, text="ME", fill="#ffffff", font=(BODY, 10, "bold"))
        c.create_text(68, y + 101, text="Member account", anchor="w", fill="#ffffff", font=(BODY, 12, "bold"))
        c.create_text(68, y + 119, text="Signed in", anchor="w", fill="#9fa3c2", font=(BODY, 10))

    def browse(self):
        c = self.c
        X0, X1 = 280, W - 30
        c.create_text(X0, 40, text="Focus-session plans", anchor="w", fill=INK, font=(HEAD, 22, "bold"))
        c.create_text(X0, 68, text="Each plan pairs a workstation setup with a reset-break pattern. Pick three.",
                      anchor="w", fill=MUTED, font=(BODY, 12))
        # segmented group control
        seg_y0, seg_y1 = 92, 132
        rrect(c, X0, seg_y0, X1, seg_y1, 20, fill="#ebe6dc", outline="")
        sw = (X1 - X0 - 8) / len(GROUPS)
        for i, g in enumerate(GROUPS):
            gx0 = int(X0 + 4 + i * sw)
            gx1 = int(X0 + 4 + (i + 1) * sw)
            n_in = sum(1 for p in self.picks if BY_ID[p][1] == g)
            if g == self.group:
                rrect(c, gx0, seg_y0 + 4, gx1, seg_y1 - 4, 16, fill=CARD, outline=LINE)
            txt = f"{g}" + (f"  ({n_in} in tray)" if n_in else "")
            c.create_text((gx0 + gx1) // 2, (seg_y0 + seg_y1) // 2, text=txt,
                          fill=INK if g == self.group else MUTED, font=(BODY, 12, "bold" if g == self.group else "normal"))
            self.region(f"tab:{g}", (gx0, seg_y0, gx1, seg_y1), lambda g=g: self.set_group(g))
        # cards
        rows = [r for r in MENU if r[1] == self.group]
        y = 148
        ch = 158
        for oid, grp, name, desc, note in rows:
            ws, rhythm = split_desc(desc)
            picked = oid in self.picks
            rrect(c, X0, y, X1, y + ch, 16, fill=CARD, outline=CITRON_D if picked else LINE, width=2 if picked else 1)
            # monogram tile (seeded by name only)
            letter = name.split()[-1][:1]
            rrect(c, X0 + 18, y + 18, X0 + 62, y + 62, 12, fill="#eeeaf6", outline="")
            c.create_text(X0 + 40, y + 40, text=letter, fill=SLATE, font=(HEAD, 18, "bold"))
            c.create_text(X0 + 78, y + 30, text=name, anchor="w", fill=INK, font=(HEAD, 16, "bold"))
            c.create_text(X0 + 78, y + 52, text=note, anchor="w", fill=MUTED, font=(BODY, 11))
            # two spec rows
            tx = X0 + 222
            c.create_text(X0 + 78, y + 84, text="WORKSTATION", anchor="w", fill="#8a8e9c", font=(BODY, 10, "bold"))
            c.create_text(tx, y + 76, text=ws, anchor="nw", width=X1 - tx - 20, fill=INK, font=(BODY, 12))
            c.create_text(X0 + 78, y + 124, text="SESSION RHYTHM", anchor="w", fill="#8a8e9c", font=(BODY, 10, "bold"))
            c.create_text(tx, y + 116, text=rhythm, anchor="nw", width=X1 - tx - 20, fill=INK, font=(BODY, 12))
            bx1, by0 = X1 - 18, y + 20
            if picked:
                self.button(f"remove:{oid}", bx1 - 170, by0, bx1, by0 + 36, f"✓ In tray - remove {name.split()[-1]}",
                            lambda o=oid: self.remove(o), "done", 11)
            else:
                self.button(f"add:{oid}", bx1 - 170, by0, bx1, by0 + 36, f"Add {name}",
                            lambda o=oid: self.add(o), "accent" if len(self.picks) < LIMIT else "off", 12)
            y += ch + 12
        self.tray(y + 4)

    def tray(self, y):
        c = self.c
        X0, X1 = 280, W - 30
        rrect(c, X0, y, X1, H - 18, 16, fill=SLATE, outline="")
        c.create_text(X0 + 20, y + 24, text=f"Booking tray  -  {len(self.picks)} of {LIMIT} plans chosen",
                      anchor="w", fill="#ffffff", font=(BODY, 13, "bold"))
        if self.notice:
            c.create_text(X0 + 20, y + 118, text=self.notice, anchor="w", fill=CITRON, font=(BODY, 12))
        sx = X0 + 20
        slot_w = 150
        for i in range(LIMIT):
            x0 = sx + i * (slot_w + 10)
            x1 = x0 + slot_w
            if i < len(self.picks):
                oid = self.picks[i]
                rrect(c, x0, y + 46, x1, y + 94, 12, fill=SLATE2, outline="")
                c.create_text(x0 + 14, y + 70, text=BY_ID[oid][2], anchor="w", fill="#ffffff", font=(BODY, 12, "bold"))
                c.create_text(x1 - 22, y + 70, text="✕", fill="#c3c6dc", font=(BODY, 13, "bold"))
                self.region(f"tray-remove:{oid}", (x1 - 42, y + 50, x1 - 2, y + 90), lambda o=oid: self.remove(o))
            else:
                rrect(c, x0, y + 46, x1, y + 94, 12, fill="", outline="#5d6185", dash=(4, 3))
                c.create_text((x0 + x1) // 2, y + 70, text=f"Slot {i + 1}", fill="#8f93b3", font=(BODY, 12))
        ready = len(self.picks) == LIMIT
        self.button("review", X1 - 190, y + 50, X1 - 20, y + 92, "Review plans  ›", lambda: self.go("review"),
                    "accent" if ready else "off", 13)

    def review(self):
        c = self.c
        X0, X1 = 280, W - 30
        c.create_text(X0, 40, text="Review your tray", anchor="w", fill=INK, font=(HEAD, 22, "bold"))
        c.create_text(X0, 68, text="Check your three focus-session plans, then submit.", anchor="w", fill=MUTED, font=(BODY, 12))
        y = 100
        for i, oid in enumerate(self.picks):
            _, grp, name, desc, note = BY_ID[oid]
            ws, rhythm = split_desc(desc)
            rrect(c, X0, y, X1, y + 150, 16, fill=CARD, outline=LINE)
            c.create_oval(X0 + 18, y + 18, X0 + 50, y + 50, fill=CITRON, outline="")
            c.create_text(X0 + 34, y + 34, text=str(i + 1), fill=INK, font=(BODY, 13, "bold"))
            c.create_text(X0 + 66, y + 34, text=f"{name}", anchor="w", fill=INK, font=(HEAD, 16, "bold"))
            c.create_text(X0 + 160, y + 35, text=grp, anchor="w", fill=MUTED, font=(BODY, 11))
            c.create_text(X0 + 66, y + 62, text=ws, anchor="nw", width=X1 - X0 - 250, fill=INK, font=(BODY, 12))
            c.create_text(X0 + 66, y + 104, text=rhythm, anchor="nw", width=X1 - X0 - 250, fill=INK, font=(BODY, 12))
            self.button(f"review-remove:{oid}", X1 - 150, y + 18, X1 - 18, y + 52, "Remove",
                        lambda o=oid: (self.remove(o), setattr(self, "screen", "browse")), "ghost", 12)
            y += 162
        c.create_text(X0, y + 20, text=SHARED, anchor="nw", width=X1 - X0, fill=MUTED, font=(BODY, 12))
        self.button("back", X0, H - 90, X0 + 200, H - 44, "‹  Back to plans", lambda: self.go("browse"), "ghost", 13)
        self.button("submit", X1 - 240, H - 90, X1, H - 44, "Submit choices", self.submit, "primary", 14)

    def done(self):
        c = self.c
        X0, X1 = 280, W - 30
        cx = (X0 + X1) // 2
        c.create_oval(cx - 46, 170, cx + 46, 262, fill=CITRON, outline="")
        c.create_text(cx, 216, text="✓", fill=INK, font=(BODY, 38, "bold"))
        c.create_text(cx, 310, text="Choices submitted", fill=INK, font=(HEAD, 26, "bold"))
        c.create_text(cx, 346, text="Your focus-session plans are booked.", fill=MUTED, font=(BODY, 13))
        y = 390
        for oid in self.picks:
            rrect(c, cx - 200, y, cx + 200, y + 44, 12, fill=CARD, outline=LINE)
            c.create_text(cx, y + 22, text=BY_ID[oid][2], fill=INK, font=(BODY, 13, "bold"))
            y += 54


if __name__ == "__main__":
    r = tk.Tk()
    App(r)
    r.mainloop()
