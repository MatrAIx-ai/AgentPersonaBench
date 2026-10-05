#!/usr/bin/env python3
"""Meridian Review Desk native Tkinter application."""
from __future__ import annotations

import hashlib
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
APP_VERSION = "stat-review-desk-v1"
CASE_ORDER = ("email", "catalog", "recommender")
ACTIONS = (
    ("act_launch", "Launch", "Approve a staged deployment under the current decision rule."),
    ("act_continue", "Continue", "Preserve assignment and complete or extend the declared sampling plan."),
    ("act_investigate", "Investigate", "Hold the decision while resolving an estimand, analysis, or integrity issue."),
    ("act_reject", "Reject", "Stop the current rollout case while retaining evidence for redesign."),
)
CASES = (
    {
        "id": "email",
        "queue": "Email preview",
        "title": "Message preview experiment",
        "summary": "Completed confirmatory test with a clear primary outcome.",
        "evidence": (
            "The 18-day randomized test ended as planned. The registered primary metric, "
            "message completion, improved by 1.2 percentage points (95% CI +0.8 to +1.6; "
            "p<0.001), above the +0.5-point minimum useful effect. Allocation was 50.0%/50.0% "
            "(SRM p=0.81). Delivery errors, opt-outs, and latency all remained inside their "
            "pre-specified guardrail bounds. The charter keeps all randomized users as the "
            "binding rollout population and declares no team-volume weighting rule."
        ),
        "reasons": (
            ("em_pvalue", "The interval clears the useful-effect threshold; a staged ramp can assess temporal transport before full deployment."),
            ("em_vp", "Use this same run to select the highest-volume teams, promote their reweighted gain to the confirmatory target, and report it as the rollout effect."),
            ("em_declared", "For the registered population, the lower interval bound clears the useful-effect rule and allocation and guardrails are clean."),
            ("em_more", "Repeat one independent message-volume cycle to estimate week-to-week heterogeneity before full rollout."),
        ),
    },
    {
        "id": "catalog",
        "queue": "Catalog ranking",
        "title": "Catalog ranking experiment",
        "summary": "Registered interim decision in a group-sequential design.",
        "evidence": (
            "The registered design has one interim at 63% information and a final look at 100%. "
            "At the interim, successful product discovery is +2.7% relative with a repeated 95% "
            "CI from -1.4% to +7.0%; the minimum useful lift is +2%. Efficacy requires one-sided "
            "p≤0.008, while futility requires predictive probability below 10% of clearing +2% "
            "at the final look. Current values are p=0.094 and predictive probability 44%. "
            "Allocation, exposure logging, and guardrails are clean. The full seasonal population "
            "and these boundaries remain binding; no alternative loss or utility rule was declared."
        ),
        "reasons": (
            ("ca_point", "After seeing the interim estimate, introduce an asymmetric loss function, treat +2.7% as confirmatory success, and use follow-up only as rollout monitoring."),
            ("ca_interval", "Neither registered efficacy nor futility boundary is crossed; preserve the alpha-spending design and continue to the final look."),
            ("ca_deadline", "Use this interim read to redefine the target as current visitors, tune an early utility rule, and report the resulting stop as protocol-valid evidence."),
            ("ca_zero", "Substitute the ordinary 95% interval crossing zero as the futility boundary, stop now, and reallocate the remaining sample."),
        ),
    },
    {
        "id": "recommender",
        "queue": "Recommendation rail",
        "title": "Recommendation-rail experiment",
        "summary": "Registered two-stage outcome selection with a pooled readout.",
        "evidence": (
            "The protocol uses the first 40% of accounts to screen 20 correlated engagement "
            "outcomes, select one metric, and test that metric at alpha 0.05 only on the untouched "
            "remaining 60%. Pooling stages was not registered without a conditional-combination "
            "rule. After selecting saves per session on stage 1, the team reports +0.9%, p=0.026 "
            "from all accounts pooled together; no stage-2-only result has been prepared. Median "
            "pairwise outcome correlation is 0.74. Allocation and tracking checks are clean."
        ),
        "reasons": (
            ("rc_users", "Treat the high outcome correlation as one effective test and let the pooled p=0.026 stand in for the untouched-stage confirmation."),
            ("rc_onep", "Because the adaptive plan permitted metric selection, treat the selected metric's pooled p=0.026 as the registered confirmatory test."),
            ("rc_multiplicity", "Honor the registered split: treat the stage-1 and pooled readouts as exploratory, then test the selected metric on untouched stage 2 or an independent replication."),
            ("rc_morepeek", "Continue under prospective alpha spending, but combine the new observations with all exploratory data for the final test."),
        ),
    },
)


def content_digest() -> str:
    material = json.dumps(
        {"version": APP_VERSION, "actions": ACTIONS, "cases": CASES},
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")
    return hashlib.sha256(material).hexdigest()


SALMON = "#fbeee3"
PAPER = "#fff8f1"
INK = "#1b1b1b"
MUTED = "#6e625a"
RULE = "#e6d3c4"
CLARET = "#990f3d"
CLARET_DARK = "#7a0c31"
TEAL = "#0d7680"
TEAL_SOFT = "#dcefef"
PICK = "#f6dde4"


def _f(family: str, size: int, weight: str = "normal", slant: str = "roman") -> tkfont.Font:
    return tkfont.Font(family=family, size=-size, weight=weight, slant=slant)


class ReviewDesk:
    def __init__(self, root: tk.Tk):
        self.root = root
        self.events: list[dict] = []
        self.actions = {case_id: "" for case_id in CASE_ORDER}
        self.reasons = {case_id: "" for case_id in CASE_ORDER}
        self.active_case = CASE_ORDER[0]
        self.case_by_id = {case["id"]: case for case in CASES}
        self.submitted = False
        self.tiles: dict[str, tuple] = {}
        self.rows: dict[str, tuple] = {}

        root.title("Meridian Review Desk")
        root.geometry("1024x866+0+0")
        root.minsize(940, 780)
        root.configure(bg=SALMON)
        root.lift()
        root.attributes("-topmost", True)
        root.after(7000, lambda: root.attributes("-topmost", False))

        self.f_brand = _f("C059", 23, "bold")
        self.f_kicker = _f("Nimbus Sans Narrow", 13, "bold")
        self.f_case = _f("C059", 16, "bold")
        self.f_title = _f("C059", 24, "bold")
        self.f_body = _f("DejaVu Sans", 13)
        self.f_small = _f("DejaVu Sans", 12)
        self.f_tile = _f("C059", 19, "bold")
        self.f_btn = _f("Nimbus Sans Narrow", 17, "bold")

        self._build_masthead()
        self._build_case_strip()
        self._build_footer()
        self.body = tk.Frame(root, bg=SALMON)
        self.body.pack(fill="both", expand=True, padx=22, pady=(10, 8))
        self.show_case(self.active_case)

    # ---------------------------------------------------------------- chrome
    def _build_masthead(self) -> None:
        top = tk.Frame(self.root, bg=PAPER, height=62)
        top.pack(fill="x", side="top")
        top.pack_propagate(False)
        mark = tk.Canvas(top, width=40, height=40, bg=PAPER, highlightthickness=0)
        mark.pack(side="left", padx=(22, 10))
        mark.create_oval(2, 2, 38, 38, outline=CLARET, width=3)
        mark.create_oval(12, 2, 28, 38, outline=CLARET, width=2)
        mark.create_line(20, 2, 20, 38, fill=CLARET, width=2)
        mark.create_line(4, 20, 36, 20, fill=TEAL, width=2)
        tk.Label(top, text="Meridian Review Desk", bg=PAPER, fg=INK, font=self.f_brand).pack(side="left")
        tk.Frame(top, bg=RULE, width=1).pack(side="left", fill="y", padx=16, pady=16)
        tk.Label(top, text="EXPERIMENT DECISIONS", bg=PAPER, fg=MUTED, font=self.f_kicker).pack(side="left")
        tk.Label(top, text="Weekly review  ·  3 proposals", bg=PAPER, fg=TEAL, font=self.f_kicker).pack(side="right", padx=22)
        tk.Frame(self.root, bg=INK, height=3).pack(fill="x", side="top")

    def _build_case_strip(self) -> None:
        strip = tk.Frame(self.root, bg=SALMON)
        strip.pack(fill="x", side="top", padx=22, pady=(14, 0))
        self.case_cards: dict[str, tuple] = {}
        for index, case in enumerate(CASES):
            card = tk.Frame(strip, bg=PAPER, highlightthickness=1, highlightbackground=RULE, cursor="hand2",
                            name=f"case_{case['id']}")
            card.pack(side="left", fill="x", expand=True, padx=(0 if index == 0 else 10, 0))
            bar = tk.Frame(card, bg=PAPER, height=4)
            bar.pack(fill="x")
            kicker = tk.Label(card, text=f"PROPOSAL {index + 1}", bg=PAPER, fg=MUTED, font=self.f_kicker, anchor="w")
            kicker.pack(fill="x", padx=14, pady=(8, 0))
            name = tk.Label(card, text=case["queue"], bg=PAPER, fg=INK, font=self.f_case, anchor="w")
            name.pack(fill="x", padx=14)
            state = tk.Label(card, text="", bg=PAPER, fg=MUTED, font=self.f_small, anchor="w")
            state.pack(fill="x", padx=14, pady=(0, 10))
            for widget in (card, bar, kicker, name, state):
                widget.bind("<Button-1>", lambda _e, cid=case["id"]: self.show_case(cid))
            self.case_cards[case["id"]] = (card, bar, kicker, name, state)

    def _build_footer(self) -> None:
        foot = tk.Frame(self.root, bg=INK, height=64)
        foot.pack(fill="x", side="bottom")
        foot.pack_propagate(False)
        self.status = tk.Label(foot, text="", bg=INK, fg=PAPER, font=self.f_body)
        self.status.pack(side="left", padx=22)
        self.submit_button = tk.Button(
            foot, name="submit", text="Submit all reviews", bg=CLARET, fg="white", activebackground=CLARET_DARK,
            activeforeground="white", disabledforeground="#d9b3bf", relief="flat", bd=0, highlightthickness=0,
            font=self.f_btn, padx=22, pady=8, cursor="hand2", command=self.submit,
        )
        self.submit_button.pack(side="right", padx=(8, 22))
        self.next_button = tk.Button(
            foot, name="next", text="Next proposal  →", bg="#33302d", fg=PAPER, activebackground="#45403c",
            activeforeground=PAPER, disabledforeground="#77706a", relief="flat", bd=0, highlightthickness=0,
            font=self.f_btn, padx=16, pady=8, cursor="hand2", command=self._next,
        )
        self.next_button.pack(side="right")

    def _next(self) -> None:
        index = CASE_ORDER.index(self.active_case)
        if index + 1 < len(CASE_ORDER):
            self.show_case(CASE_ORDER[index + 1])

    def _complete(self, case_id: str) -> bool:
        return bool(self.actions[case_id] and self.reasons[case_id])

    def _refresh_chrome(self, message: str | None = None, warn: bool = False) -> None:
        for case_id, (card, bar, kicker, name, state) in self.case_cards.items():
            active = case_id == self.active_case
            bg = PAPER if not active else "#ffffff"
            card.configure(highlightbackground=INK if active else RULE, highlightthickness=2 if active else 1, bg=bg)
            bar.configure(bg=CLARET if active else PAPER)
            for widget in (kicker, name, state):
                widget.configure(bg=bg)
            done = self._complete(case_id)
            state.configure(text="●  Review complete" if done else "○  Awaiting review", fg=TEAL if done else MUTED)
        completed = sum(self._complete(case_id) for case_id in CASE_ORDER)
        if message is None:
            message = f"{completed} of 3 reviews complete"
        self.status.configure(text=message, fg="#ffcf87" if warn else PAPER)
        last = self.active_case == CASE_ORDER[-1]
        self.next_button.configure(state="disabled" if last or self.submitted else "normal")

    # ------------------------------------------------------------------ body
    def show_case(self, case_id: str) -> None:
        if self.submitted:
            return
        self.active_case = case_id
        case = self.case_by_id[case_id]
        self.events.append({"event": "open_case", "caseId": case_id})
        for child in self.body.winfo_children():
            child.destroy()
        self.tiles, self.rows = {}, {}

        brief = tk.Frame(self.body, bg=PAPER, highlightthickness=1, highlightbackground=RULE)
        brief.pack(fill="x")
        inner = tk.Frame(brief, bg=PAPER)
        inner.pack(fill="x", padx=20, pady=14)
        tk.Label(inner, text=case["summary"].upper(), bg=PAPER, fg=CLARET, font=self.f_kicker, anchor="w").pack(fill="x")
        tk.Label(inner, text=case["title"], bg=PAPER, fg=INK, font=self.f_title, anchor="w").pack(fill="x", pady=(2, 6))
        evidence = tk.Frame(inner, bg=PAPER)
        evidence.pack(fill="x")
        tk.Frame(evidence, bg=TEAL, width=3).pack(side="left", fill="y")
        tk.Label(evidence, text=case["evidence"], bg=PAPER, fg="#312c28", font=self.f_body, anchor="w",
                 justify="left", wraplength=900).pack(side="left", fill="x", padx=(12, 0))

        cols = tk.Frame(self.body, bg=SALMON)
        cols.pack(fill="both", expand=True, pady=(12, 0))
        left = tk.Frame(cols, bg=SALMON, width=392)
        left.pack(side="left", fill="y")
        left.pack_propagate(False)
        right = tk.Frame(cols, bg=SALMON)
        right.pack(side="left", fill="both", expand=True, padx=(16, 0))

        self._section_head(left, "1", "Action")
        grid = tk.Frame(left, bg=SALMON)
        grid.pack(fill="both", expand=True)
        for c in (0, 1):
            grid.columnconfigure(c, weight=1, uniform="a")
        for r in (0, 1):
            grid.rowconfigure(r, weight=1, uniform="r")
        for index, (action_id, title, description) in enumerate(ACTIONS):
            tile = tk.Frame(grid, bg=PAPER, highlightthickness=1, highlightbackground=RULE, cursor="hand2",
                            name=f"action_{action_id}")
            tile.grid(row=index // 2, column=index % 2, sticky="nsew", padx=(0 if index % 2 == 0 else 5, 0 if index % 2 else 5), pady=(0, 10))
            box = tk.Frame(tile, bg=PAPER)
            box.pack(side="top", fill="x", padx=14, pady=(44, 0))
            head = tk.Label(box, text=title, bg=PAPER, fg=INK, font=self.f_tile, anchor="w")
            head.pack(fill="x", pady=(0, 4))
            desc = tk.Label(box, text=description, bg=PAPER, fg=MUTED, font=self.f_body, anchor="w",
                            justify="left", wraplength=160)
            desc.pack(fill="x")
            for widget in (tile, box, head, desc):
                widget.bind("<Button-1>", lambda _e, aid=action_id, cid=case_id: self.select_action(cid, aid))
            self.tiles[action_id] = (tile, box, head, desc)

        self._section_head(right, "2", "Supporting reason")
        for index, (reason_id, text) in enumerate(case["reasons"]):
            row = tk.Frame(right, bg=PAPER, highlightthickness=1, highlightbackground=RULE, cursor="hand2",
                           name=f"reason_{index + 1}")
            row.pack(fill="both", expand=True, pady=(0, 8))
            dot = tk.Canvas(row, width=26, height=26, bg=PAPER, highlightthickness=0)
            dot.pack(side="left", padx=(14, 4))
            label = tk.Label(row, text=text, bg=PAPER, fg=INK, font=self.f_body, anchor="w", justify="left",
                             wraplength=470)
            label.pack(side="left", fill="both", expand=True, padx=(4, 12), pady=8)
            for widget in (row, dot, label):
                widget.bind("<Button-1>", lambda _e, rid=reason_id, cid=case_id: self.select_reason(cid, rid))
            self.rows[reason_id] = (row, dot, label)
        self._paint()
        self._refresh_chrome()

    def _section_head(self, parent: tk.Widget, number: str, text: str) -> None:
        head = tk.Frame(parent, bg=SALMON)
        head.pack(fill="x", pady=(0, 6))
        badge = tk.Label(head, text=number, bg=INK, fg=PAPER, font=self.f_kicker, width=2)
        badge.pack(side="left")
        tk.Label(head, text=text.upper(), bg=SALMON, fg=INK, font=self.f_kicker).pack(side="left", padx=8)
        tk.Frame(head, bg=INK, height=1).pack(side="left", fill="x", expand=True, pady=(2, 0))

    def _paint(self) -> None:
        case_id = self.active_case
        for action_id, (tile, box, head, desc) in self.tiles.items():
            on = self.actions[case_id] == action_id
            bg = PICK if on else PAPER
            tile.configure(bg=bg, highlightbackground=CLARET if on else RULE, highlightthickness=2 if on else 1)
            box.configure(bg=bg)
            head.configure(bg=bg, fg=CLARET if on else INK)
            desc.configure(bg=bg)
        for reason_id, (row, dot, label) in self.rows.items():
            on = self.reasons[case_id] == reason_id
            bg = TEAL_SOFT if on else PAPER
            row.configure(bg=bg, highlightbackground=TEAL if on else RULE, highlightthickness=2 if on else 1)
            label.configure(bg=bg)
            dot.configure(bg=bg)
            dot.delete("all")
            dot.create_oval(3, 3, 23, 23, outline=TEAL if on else "#b7a597", width=2)
            if on:
                dot.create_oval(8, 8, 18, 18, fill=TEAL, outline="")

    # --------------------------------------------------------------- actions
    def select_action(self, case_id: str, action_id: str) -> None:
        if self.submitted:
            return
        self.actions[case_id] = action_id
        self.events.append({"event": "select_action", "caseId": case_id, "actionId": action_id})
        self._paint()
        self._refresh_chrome()

    def select_reason(self, case_id: str, reason_id: str) -> None:
        if self.submitted:
            return
        self.reasons[case_id] = reason_id
        self.events.append({"event": "select_reason", "caseId": case_id, "reasonId": reason_id})
        self._paint()
        self._refresh_chrome()

    def submit(self) -> None:
        if self.submitted:
            return
        if not all(self._complete(case_id) for case_id in CASE_ORDER):
            self._refresh_chrome("Choose an action and a reason for every proposal first.", warn=True)
            return
        reviews = [
            {"caseId": case_id, "actionId": self.actions[case_id], "reasonId": self.reasons[case_id]}
            for case_id in CASE_ORDER
        ]
        self.events.append({"event": "submit"})
        payload = {
            "appVersion": APP_VERSION,
            "contentDigest": content_digest(),
            "submitted": True,
            "reviews": reviews,
            "events": self.events,
        }
        os.makedirs(OUTPUT_DIR, exist_ok=True)
        temporary = os.path.join(OUTPUT_DIR, "decision.json.tmp")
        destination = os.path.join(OUTPUT_DIR, "decision.json")
        with open(temporary, "w", encoding="utf-8") as handle:
            json.dump(payload, handle, ensure_ascii=False, indent=2)
        os.replace(temporary, destination)
        self.submitted = True
        self.submit_button.configure(state="disabled", text="Reviews submitted")
        self._refresh_chrome("All reviews submitted.")
        for child in self.body.winfo_children():
            child.destroy()
        note = tk.Frame(self.body, bg=PAPER, highlightthickness=1, highlightbackground=RULE)
        note.place(relx=0.5, rely=0.4, anchor="center", width=560, height=200)
        tk.Frame(note, bg=CLARET, height=5).pack(fill="x")
        tk.Label(note, text="All reviews submitted", bg=PAPER, fg=INK, font=self.f_title).pack(pady=(34, 6))
        tk.Label(note, text="3 proposals · decisions filed to the weekly review", bg=PAPER, fg=MUTED,
                 font=self.f_body).pack()


if __name__ == "__main__":
    root = tk.Tk()
    ReviewDesk(root)
    root.mainloop()
