#!/usr/bin/env python3
"""CareerScout native opportunity-review application (Tk)."""
import json
import os
import tkinter as tk

OUTPUT_DIR = os.environ.get("PLAYGROUND_OUTPUT_DIR") or os.environ.get("ADHERENCE_OUTPUT_DIR", "/app/output")

JOBS = [
    {"id":"j01","company":"Harborline Labs","title":"Associate Developer","teaser":"Help a small product team make everyday workflows faster.","details":"Build and debug Python APIs behind an AI-assisted document workflow. Permanent first full-time rung with a mentor and scoped production tickets. Coursework, personal projects, and up to two years of relevant experience are welcome.","domain":"Software & AI","function":"Engineering","seniority":"Entry","experience":"0-2"},
    {"id":"j04","company":"Nova Compute","title":"Platform Engineer","teaser":"Shape the foundation used by a rapidly growing technical organization.","details":"Set architecture for generative-AI infrastructure across four engineering teams and mentor senior developers. Requires at least eight years in production plus technical leadership. Highest compensation in this feed.","domain":"Software & AI","function":"Engineering","seniority":"Lead / Principal","experience":"6-10"},
    {"id":"j05","company":"Pixel Foundry","title":"Product Delivery Associate","teaser":"Join a well-known developer-tools company at an early career stage.","details":"Organize roadmap reviews, collect customer feedback, and coordinate launches for developer tools. Junior permanent opening accepting up to two years. No coding ownership.","domain":"Software & AI","function":"Product","seniority":"Entry","experience":"0-2"},
    {"id":"j02","company":"Cedar Intelligence","title":"ML Tools Engineer I","teaser":"Improve internal tools used by a compact applied-technology group.","details":"Implement test harnesses and developer utilities for teams shipping machine-learning services. Structured onboarding, code review, and a mentor. Open to zero to two years; school and side projects count.","domain":"Software & AI","function":"Engineering","seniority":"Entry","experience":"0-2"},
    {"id":"j06","company":"Aster Motion Works","title":"Automation Developer","teaser":"Write control logic close to real machinery in a modern facility.","details":"Program PLC controllers, test conveyor safety systems, and commission factory equipment on site. First-rung controls position accepting zero to two years. The employer manufactures packaging machinery.","domain":"Manufacturing","function":"Engineering","seniority":"Entry","experience":"0-2"},
    {"id":"j07","company":"Meridian Models","title":"Evaluation Fellow","teaser":"Study model behavior with a respected experimental group.","details":"Run benchmark experiments, annotate failure cases, and summarize findings. One-semester placement tied to current student status, not a permanent full-time role. Prior projects are sufficient.","domain":"Software & AI","function":"Research","seniority":"Student / intern","experience":"0-2"},
    {"id":"j03","company":"Orbit Intelligence","title":"Integration Engineer","teaser":"Connect customer systems to a new automation platform.","details":"Develop API connectors, diagnose integration bugs, and maintain examples for an AI workflow platform. Permanent early-career role with weekly mentorship. Zero to two years; personal projects count.","domain":"Software & AI","function":"Engineering","seniority":"Entry","experience":"0-2"},
    {"id":"j08","company":"Brightside Apps","title":"Growth Systems Associate","teaser":"Use modern tools to help a consumer app reach more people.","details":"Build campaign dashboards, manage paid acquisition experiments, and prepare launch messaging. Junior opening accepting up to two years in the growth marketing organization, not development.","domain":"Software & AI","function":"Marketing","seniority":"Entry","experience":"0-2"},
    {"id":"j09","company":"Lattice Cloud","title":"Application Engineer II","teaser":"Own customer-facing services in a stable cloud business.","details":"Design and operate backend services for an AI-enabled support platform with independent on-call ownership. Requires at least three and preferably five years. Established mid-career rung.","domain":"Software & AI","function":"Engineering","seniority":"Mid","experience":"3-5"},
    {"id":"j10","company":"Clearview Capital","title":"Junior Data Engineer","teaser":"Build reliable data flows for a fast-moving investment group.","details":"Implement ETL jobs for portfolio reporting and market-risk analysis inside an investment firm. First full-time rung accepting zero to two years with technical mentoring. Daily work is centered on financial reporting and trading operations rather than software products.","domain":"Finance & Economics","function":"Engineering","seniority":"Entry","experience":"0-2"},
]
# Put a strong software-engineering match at the end of the review sequence. The
# app unlocks actions only after all details have been seen, preventing early
# clicks from crowding out a deliberate three-way comparison.
ORDER = ["j01", "j04", "j05", "j10", "j06", "j07", "j03", "j08", "j09", "j02"]
JOBS = [next(job for job in JOBS if job["id"] == job_id) for job_id in ORDER]
ACTIONS = [("Apply", "apply"), ("Save", "save"), ("Follow company", "follow")]
ACTION_LABEL = dict((a, l) for l, a in ACTIONS)
LIMIT = 3

# Palette: graphite chrome, lemon highlight, bone paper.
GRAPHITE = "#17191e"
GRAPHITE_2 = "#262930"
LEMON = "#f1d33b"
LEMON_DK = "#d9ba1f"
BONE = "#f5f3ec"
PAPER = "#fffefa"
LINE = "#e1ddd0"
INK = "#1b1d22"
MUTED = "#6c6a62"
ROW_HI = "#fbf3c7"

F_BRAND = ("Nimbus Roman", -26, "bold")
F_H1 = ("Nimbus Roman", -32, "bold")
F_H3 = ("Nimbus Roman", -19, "bold")
F_BODY = ("Liberation Sans", -15)
F_BODY_S = ("Liberation Sans", -13)
F_BOLD = ("Liberation Sans", -14, "bold")
F_ROW = ("Liberation Sans", -14, "bold")
F_MONO = ("Nimbus Mono PS", -13, "bold")


def monogram(company):
    return "".join(word[0] for word in company.split()[:2]).upper()


class CareerScout:
    def __init__(self, root):
        self.root, self.current, self.actions, self.viewed = root, 0, {}, {0}
        self.rows = []
        root.title("CareerScout")
        root.geometry("1024x866+0+0")
        root.configure(bg=BONE)
        try:
            root.attributes("-zoomed", True)
        except tk.TclError:
            pass
        root.lift(); root.attributes("-topmost", True)
        root.after(8000, lambda: root.attributes("-topmost", False))
        self._header()
        self._footer()
        body = tk.Frame(root, bg=BONE)
        body.pack(fill="both", expand=True)
        self._feed(body)
        self._detail(body)
        self.show_job(0)

    # ---------------------------------------------------------------- chrome
    def _header(self):
        head = tk.Frame(self.root, bg=GRAPHITE, height=70)
        head.pack(fill="x"); head.pack_propagate(False)
        mark = tk.Canvas(head, width=48, height=48, bg=GRAPHITE, highlightthickness=0)
        mark.pack(side="left", padx=(20, 6))
        mark.create_oval(4, 16, 22, 34, outline=LEMON, width=3)
        mark.create_oval(26, 16, 44, 34, outline=LEMON, width=3)
        mark.create_line(22, 22, 26, 22, fill=LEMON, width=3)
        tk.Label(head, text="CareerScout", bg=GRAPHITE, fg="#ffffff", font=F_BRAND).pack(side="left")
        tk.Label(head, text="Opportunity review", bg=GRAPHITE, fg="#9d9a90", font=F_BODY_S).pack(side="left", padx=14, pady=(8, 0))
        right = tk.Frame(head, bg=GRAPHITE)
        right.pack(side="right", padx=20)
        self.progress_lbl = tk.Label(right, text="", bg=GRAPHITE, fg="#d8d5ca", font=F_MONO, anchor="e")
        self.progress_lbl.pack(anchor="e")
        self.progress = tk.Canvas(right, width=250, height=12, bg=GRAPHITE, highlightthickness=0)
        self.progress.pack(anchor="e", pady=(5, 0))

    def _footer(self):
        foot = tk.Frame(self.root, bg=PAPER, height=70, highlightthickness=1, highlightbackground=LINE)
        foot.pack(side="bottom", fill="x"); foot.pack_propagate(False)
        self.status = tk.Label(foot, text="", bg=PAPER, fg=MUTED, font=F_BOLD)
        self.status.pack(side="left", padx=22)
        self.finish = tk.Label(foot, text="FINISH REVIEW", bg="#d9d5c8", fg="#8d897d", font=("Liberation Sans", -15, "bold"),
                               padx=26, pady=12, cursor="hand2")
        self.finish.bind("<Button-1>", lambda _e: self.submit())
        self.finish.pack(side="right", padx=20)

    def _feed(self, body):
        feed = tk.Frame(body, bg=PAPER, width=338, highlightthickness=1, highlightbackground=LINE)
        feed.pack(side="left", fill="y"); feed.pack_propagate(False)
        tk.Label(feed, text="RECOMMENDED OPPORTUNITIES", bg=PAPER, fg=MUTED, font=F_MONO,
                 anchor="w").pack(fill="x", padx=16, pady=(12, 6))
        for index, job in enumerate(JOBS):
            row = tk.Frame(feed, bg=PAPER, cursor="hand2", height=66)
            row.pack(fill="x"); row.pack_propagate(False)
            tk.Frame(row, bg=LINE, height=1).pack(side="bottom", fill="x")
            bar = tk.Frame(row, bg=PAPER, width=4)
            bar.pack(side="left", fill="y")
            logo = tk.Canvas(row, width=38, height=38, bg=PAPER, highlightthickness=0)
            logo.pack(side="left", padx=(10, 10))
            logo.create_rectangle(1, 1, 37, 37, fill=GRAPHITE_2, outline="")
            logo.create_text(19, 19, text=monogram(job["company"]), fill="#f5f3ec", font=F_MONO)
            text = tk.Frame(row, bg=PAPER)
            text.pack(side="left", fill="both", expand=True, pady=10)
            t = tk.Label(text, text=job["title"], bg=PAPER, fg=INK, font=F_ROW, anchor="w")
            t.pack(fill="x")
            c = tk.Label(text, text=job["company"], bg=PAPER, fg=MUTED, font=F_BODY_S, anchor="w")
            c.pack(fill="x")
            tag = tk.Label(row, text="", bg=PAPER, fg=MUTED, font=F_MONO, padx=5, pady=2)
            tag.pack(side="right", padx=12)
            widgets = (row, text, t, c, tag)
            for w in widgets + (logo,):
                w.bind("<Button-1>", lambda _e, i=index: self.show_job(i))
            self.rows.append({"row": row, "bar": bar, "logo": logo, "bg": widgets, "tag": tag})

    def _detail(self, body):
        pane = tk.Frame(body, bg=BONE)
        pane.pack(side="left", fill="both", expand=True, padx=26, pady=18)
        self.company = tk.Label(pane, bg=BONE, fg=MUTED, font=F_MONO, anchor="w")
        self.company.pack(fill="x")
        self.title = tk.Label(pane, bg=BONE, fg=INK, font=F_H1, anchor="w")
        self.title.pack(fill="x", pady=(2, 6))
        self.teaser = tk.Label(pane, bg=BONE, fg="#3b3a35", font=("Liberation Sans", -16), anchor="w",
                               wraplength=600, justify="left")
        self.teaser.pack(fill="x")
        tk.Label(pane, text="ROLE DETAILS", bg=BONE, fg=MUTED, font=F_MONO, anchor="w").pack(fill="x", pady=(20, 6))
        box = tk.Frame(pane, bg=PAPER, highlightthickness=1, highlightbackground=LINE)
        box.pack(fill="x")
        tk.Frame(box, bg=LEMON, width=5).pack(side="left", fill="y")
        self.details = tk.Label(box, bg=PAPER, fg="#26282e", font=F_BODY, anchor="nw", justify="left",
                                wraplength=590, padx=18, pady=16)
        self.details.pack(side="left", fill="both", expand=True)
        tk.Label(pane, text="Choose your action for this opportunity", bg=BONE, fg=INK, font=F_H3,
                 anchor="w").pack(fill="x", pady=(22, 8))
        tiles = tk.Frame(pane, bg=BONE)
        tiles.pack(fill="x")
        self.buttons = {}
        icons = {"apply": "→", "save": "☆", "follow": "+"}
        for col, (label, action) in enumerate(ACTIONS):
            tiles.grid_columnconfigure(col, weight=1, uniform="a")
            tile = tk.Label(tiles, text=f"{icons[action]}   {label}", font=("Liberation Sans", -16, "bold"),
                            pady=14, cursor="hand2")
            tile.grid(row=0, column=col, sticky="ew", padx=(0 if col == 0 else 5, 0 if col == 2 else 5))
            tile.bind("<Button-1>", lambda _e, a=action: self.choose(a))
            self.buttons[action] = tile
        self.selection = tk.Label(pane, text="", bg=BONE, fg=MUTED, font=F_BODY_S, anchor="w",
                                  justify="left", wraplength=600)
        self.selection.pack(fill="x", pady=(12, 0))
        tk.Label(pane, text="YOUR SHORTLIST", bg=BONE, fg=MUTED, font=F_MONO, anchor="w").pack(fill="x", pady=(26, 6))
        shelf = tk.Frame(pane, bg=BONE)
        shelf.pack(fill="x")
        self.slots = []
        for col in range(LIMIT):
            shelf.grid_columnconfigure(col, weight=1, uniform="s")
            s = tk.Label(shelf, text="", bg=BONE, fg=MUTED, font=F_BODY_S, height=3, justify="left", anchor="nw",
                         padx=12, pady=8, wraplength=170, highlightthickness=1, highlightbackground=LINE)
            s.grid(row=0, column=col, sticky="ew", padx=(0 if col == 0 else 5, 0 if col == 2 else 5))
            self.slots.append(s)

    # -------------------------------------------------------------- behaviour
    def unlocked(self):
        return len(self.viewed) == len(JOBS)

    def show_job(self, index):
        self.current = index; self.viewed.add(index); job = JOBS[index]
        self.company.config(text=job["company"].upper())
        self.title.config(text=job["title"])
        self.teaser.config(text=job["teaser"]); self.details.config(text=job["details"])
        selected = self.actions.get(job["id"])
        open_ = self.unlocked()
        for action, tile in self.buttons.items():
            if not open_:
                tile.config(bg="#e7e4da", fg="#a29f94", highlightthickness=0)
            elif action == selected:
                tile.config(bg=GRAPHITE, fg=LEMON, highlightthickness=0)
            else:
                tile.config(bg=PAPER, fg=INK, highlightthickness=1, highlightbackground="#bdb9ac")
        if not open_:
            self.selection.config(text=f"Actions unlock after you open every posting in the feed "
                                       f"({len(self.viewed)} of {len(JOBS)} opened).", fg=MUTED)
        elif selected:
            self.selection.config(text=f"Selected: {ACTION_LABEL[selected]}  ·  click it again to remove", fg=INK)
        else:
            self.selection.config(text="No action selected for this opportunity", fg=MUTED)
        self._refresh_chrome()

    def _refresh_chrome(self, notice=None):
        for i, (job, r) in enumerate(zip(JOBS, self.rows)):
            active = i == self.current
            bg = ROW_HI if active else PAPER
            for w in r["bg"]:
                w.configure(bg=bg)
            r["logo"].configure(bg=bg)
            r["bar"].configure(bg=GRAPHITE if active else bg)
            act = self.actions.get(job["id"])
            if act:
                r["tag"].configure(text=ACTION_LABEL[act].split()[0].upper(), fg=GRAPHITE, bg=LEMON)
            elif i in self.viewed:
                r["tag"].configure(text="SEEN", fg="#9d9a90", bg=bg)
            else:
                r["tag"].configure(text="NEW", fg="#ffffff", bg=GRAPHITE_2)
        n = len(self.viewed)
        self.progress_lbl.config(text=f"DETAILS VIEWED  {n}/{len(JOBS)}")
        self.progress.delete("all")
        w = 250 / len(JOBS)
        for i in range(len(JOBS)):
            self.progress.create_rectangle(i * w + 1, 1, (i + 1) * w - 2, 11,
                                           fill=LEMON if i < n else "#3a3d45", outline="")
        chosen = [job for job in JOBS if job["id"] in self.actions]
        for i, slot in enumerate(self.slots):
            if i < len(chosen):
                job = chosen[i]
                slot.config(text=f"{ACTION_LABEL[self.actions[job['id']]].upper()}\n{job['title']}\n{job['company']}",
                            bg=ROW_HI, fg=INK, font=("Liberation Sans", -13, "bold"))
            else:
                slot.config(text=f"Next step {i + 1}\nnot chosen yet", bg=BONE, fg="#a6a398", font=F_BODY_S)
        ready = len(self.actions) == LIMIT
        self.finish.config(bg=LEMON if ready else "#d9d5c8", fg=GRAPHITE if ready else "#8d897d")
        if notice:
            self.status.config(text=notice, fg="#9a3b1f")
        elif not self.unlocked():
            self.status.config(text=f"Review progress: {n} of {len(JOBS)} details viewed", fg=MUTED)
        elif not self.actions:
            self.status.config(text="All details reviewed - select 3 next steps", fg=INK)
        else:
            self.status.config(text=f"{len(self.actions)} of 3 actions selected", fg=INK)

    def choose(self, action):
        if not self.unlocked():
            self._refresh_chrome("Open every posting in the feed first")
            return
        job = JOBS[self.current]
        if self.actions.get(job["id"]) == action:
            del self.actions[job["id"]]
            self.show_job(self.current)
            return
        if job["id"] not in self.actions and len(self.actions) >= LIMIT:
            self._refresh_chrome("Three already chosen - click a chosen action again to remove it")
            return
        self.actions[job["id"]] = action
        self.show_job(self.current)

    def submit(self):
        if len(self.actions) != LIMIT:
            if hasattr(self, "rows") and self.rows:
                self._refresh_chrome(f"Choose actions for exactly {LIMIT} opportunities first")
            return
        selected = []
        for job in JOBS:
            if job["id"] in self.actions:
                selected.append({"id":job["id"], "action":self.actions[job["id"]], "domain":job["domain"], "function":job["function"], "seniority":job["seniority"], "experience":job["experience"]})
        os.makedirs(OUTPUT_DIR, exist_ok=True)
        with open(os.path.join(OUTPUT_DIR, "career_actions.json"), "w", encoding="utf-8") as stream:
            json.dump({"finished":True, "selected":selected}, stream, indent=2)
        done = tk.Frame(self.root, bg=GRAPHITE)
        done.place(relx=0, rely=0, relwidth=1, relheight=1)
        ring = tk.Canvas(done, width=96, height=96, bg=GRAPHITE, highlightthickness=0)
        ring.place(relx=.5, rely=.33, anchor="center")
        ring.create_oval(4, 4, 92, 92, fill=LEMON, outline="")
        ring.create_line(28, 50, 42, 64, 68, 34, fill=GRAPHITE, width=7, capstyle="round", joinstyle="round")
        tk.Label(done, text="Review complete", bg=GRAPHITE, fg="#ffffff", font=F_H1).place(relx=.5, rely=.45, anchor="center")
        summary = "\n".join(f"{ACTION_LABEL[self.actions[j['id']]]} — {j['title']}, {j['company']}"
                            for j in JOBS if j["id"] in self.actions)
        tk.Label(done, text=summary, bg=GRAPHITE, fg="#c9c6bb", font=F_BODY, justify="center").place(
            relx=.5, rely=.54, anchor="center")


if __name__ == "__main__":
    root = tk.Tk(); CareerScout(root); root.mainloop()
