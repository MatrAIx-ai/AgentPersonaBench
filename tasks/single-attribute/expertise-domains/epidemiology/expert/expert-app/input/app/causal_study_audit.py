#!/usr/bin/env python3
"""Native proposal-review queue for the Causal Study Audit task."""
from __future__ import annotations

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

PROPOSALS = (
    {
        "id": "pr-r8",
        "queue": "Randomized outreach",
        "title": "Pragmatic outreach trial",
        "summary": (
            "2,400 eligible adults were randomized 1:1 with concealed allocation. "
            "Outcome ascertainment was blinded; attrition was 1.8% and balanced."
        ),
        "facts": (
            ("Assignment", "Randomized; intention-to-treat analysis prespecified"),
            ("Timing", "Baseline strata → assignment → adherence → 90-day outcome"),
            ("Confounding", "Randomization balanced baseline causes in expectation"),
            ("Support", "Both arms represented in every enrollment stratum"),
            ("Interference", "No plausible spillover between participants"),
        ),
        "question": "Primary target: total effect of assignment in the enrolled population at 90 days.",
        "dispositions": (
            ("r8-a1", "Use association wording because pragmatic adherence varied and the interval includes no effect; reserve causal wording for an adherence-adjusted analysis."),
            ("r8-c6", "Approve a qualified intention-to-treat causal claim bounded to the randomized population and 90-day follow-up."),
            ("r8-p9", "Restrict the target to participants with complete follow-up within enrollment strata before reporting the assignment contrast."),
            ("r8-d4", "Require a new explanatory trial with monitored adherence before allowing causal language for the outreach program."),
        ),
        "rationales": (
            ("r8-v2", "Concealed randomization and intention-to-treat identify a bounded effect of assignment in enrolled participants."),
            ("r8-n7", "Instrumenting received outreach with assignment recovers a receipt effect that can be reported as the randomized total assignment effect."),
            ("r8-j5", "Pragmatic eligibility and multisite delivery support standardizing the trial effect to routine-care adults without assessing effect modifiers."),
            ("r8-s8", "A per-protocol model with prognostic adherence adjustment preserves the assignment estimand while improving clinical relevance."),
        ),
    },
    {
        "id": "pr-c2",
        "queue": "Treatment registry",
        "title": "Clinician-selected treatment registry",
        "summary": (
            "Clinicians chose treatment after baseline assessment. The adjusted model "
            "includes age and sex and reports RR 0.74, but severity and prior utilization were not extracted."
        ),
        "facts": (
            ("Assignment", "Nonrandom; clinician choice after assessment"),
            ("Timing", "Severity and prior use precede treatment; outcome follows"),
            ("Confounding", "Severity and prior utilization unavailable in current model"),
            ("Support", "Not yet assessed within severity strata"),
            ("Interference", "No treatment sharing expected"),
        ),
        "question": "Primary target: effect of initiating treatment on 30-day admission.",
        "dispositions": (
            ("c2-a8", "Report the age- and sex-adjusted registry association, explicitly withholding a treatment-effect interpretation."),
            ("c2-d5", "Extract severity and prior utilization or redesign assignment before advancing from association to a causal claim."),
            ("c2-c3", "Approve the risk ratio as a causal effect after fitting outcome and propensity models based on the available age, sex, and clinic data."),
            ("c2-p7", "Restrict to age-sex strata with treatment overlap and retain the causal wording without adding the omitted baseline causes."),
        ),
        "rationales": (
            ("c2-h9", "Agreement between outcome regression and propensity weighting based on the available covariates is sufficient for conditional exchangeability."),
            ("c2-u4", "Omitted pre-treatment severity and prior utilization leave conditional exchangeability unsupported in the current analysis."),
            ("c2-k1", "A precise estimate that remains below one under a moderate E-value sensitivity scenario supports the causal interpretation."),
            ("c2-z6", "Without randomized assignment or a validated natural experiment, retain association wording even after the missing causes are measured."),
        ),
    },
    {
        "id": "pr-o5",
        "queue": "District policy",
        "title": "Policy adoption without common support",
        "summary": (
            "Every highest-severity district adopted the policy and every lowest-severity district did not. "
            "Both policy states occur only in the middle severity range."
        ),
        "facts": (
            ("Assignment", "Adoption determined strongly by baseline severity"),
            ("Timing", "Severity measured before policy and outcome"),
            ("Confounding", "Baseline severity is measured"),
            ("Support", "No treated/untreated comparison in extreme severity strata"),
            ("Interference", "District outcomes are geographically separated"),
        ),
        "question": "Primary target: policy effect for a population supported by observed comparisons.",
        "dispositions": (
            ("o5-p2", "Restrict the causal target to the prespecified middle-severity population represented under both policy states."),
            ("o5-d8", "Defer the full-district target until comparison data are added for the high- and low-severity boundary strata."),
            ("o5-a4", "Report severity-adjusted associations in the middle range while leaving the supported target population unspecified."),
            ("o5-c7", "Target the full district population using a hierarchical severity-response model calibrated to external outcome totals."),
        ),
        "rationales": (
            ("o5-q5", "The full-population contrast is unsupported in severity strata where one policy state has no observed counterpart."),
            ("o5-r1", "Smoothness of a flexible outcome surface supplies the counterfactual contrasts needed in deterministic treatment strata."),
            ("o5-g9", "Overlap weighting with moderate truncation stabilizes the analysis while retaining the original full-population estimand."),
            ("o5-b6", "Regularized propensity scores without extreme fitted weights establish practical positivity despite deterministic boundary strata."),
        ),
    },
    {
        "id": "pr-l7",
        "queue": "Occupational cohort",
        "title": "Hospitalization in the adjustment set",
        "summary": (
            "Baseline frailty affects hospitalization and the outcome. Exposure affects both hospitalization "
            "and the outcome. The full worker cohort is available, but the plan adjusts for hospitalization."
        ),
        "facts": (
            ("Assignment", "Exposure measured at baseline"),
            ("Timing", "Frailty/exposure → hospitalization → final outcome"),
            ("Confounding", "Baseline frailty is measured"),
            ("Support", "Exposed and unexposed workers occur across frailty"),
            ("Graph", "Exposure → hospitalization ← frailty → outcome; exposure → outcome"),
        ),
        "question": "Primary target: total effect of baseline exposure in the worker cohort.",
        "dispositions": (
            ("l7-c9", "Approve a qualified total-effect claim after removing hospitalization from the adjustment set and retaining baseline frailty."),
            ("l7-a2", "Use association wording after correcting the baseline adjustment set, pending a separate analysis of hospitalization pathways."),
            ("l7-d6", "Reanalyze the full cohort with a temporally valid adjustment set before approving the currently proposed coefficient."),
            ("l7-p4", "Restrict to hospitalized workers, adjust for baseline frailty, and interpret that selected-cohort coefficient as the population total effect."),
        ),
        "rationales": (
            ("l7-e1", "Use outcome-adaptive variable selection that retains hospitalization for prediction along with baseline frailty."),
            ("l7-f3", "Adjust for baseline frailty while excluding the post-exposure common effect from the total-effect model."),
            ("l7-h8", "Include hospitalization in sequential regression to isolate the non-hospitalization pathway, then use that coefficient for the total-effect question."),
            ("l7-t5", "Within the hospitalized cohort, adjustment for measured frailty makes selection ignorable for the population total effect."),
        ),
    },
    {
        "id": "pr-m4",
        "queue": "Nutrition program",
        "title": "Mediator in a total-effect model",
        "summary": (
            "Program assignment is randomized. A biomarker measured two weeks later is changed by treatment "
            "and affects the six-month outcome. The plan adjusts for the biomarker."
        ),
        "facts": (
            ("Assignment", "Randomized program assignment"),
            ("Timing", "Baseline covariates → assignment → biomarker → outcome"),
            ("Confounding", "Baseline causes measured; assignment randomized"),
            ("Support", "Both arms represented across baseline strata"),
            ("Interference", "No plausible between-person spillover"),
        ),
        "question": "Primary target: total effect of program assignment at six months.",
        "dispositions": (
            ("m4-c1", "Approve a qualified randomized total-effect claim after removing the post-treatment biomarker from the primary model."),
            ("m4-a7", "Use association wording for the assignment comparison until the biomarker pathway is modeled jointly with the outcome."),
            ("m4-d3", "Require a new trial that intervenes on both program assignment and biomarker level before estimating the total assignment effect."),
            ("m4-p8", "Define biomarker responders using the observed two-week value and estimate the randomized total effect within that response subgroup."),
        ),
        "rationales": (
            ("m4-k6", "Leave the post-treatment biomarker out of the adjustment set for the prespecified total assignment effect."),
            ("m4-b2", "Include the biomarker in a prognostic score because randomization protects the assignment coefficient from post-treatment adjustment."),
            ("m4-j9", "The biomarker-adjusted coefficient estimates the randomized total effect when baseline causes of the biomarker and outcome are included."),
            ("m4-w5", "Use the unadjusted randomized comparison; prespecified baseline prognostic adjustment is optional for precision."),
        ),
    },
    {
        "id": "pr-i9",
        "queue": "Vaccination campaign",
        "title": "Village spillovers",
        "summary": (
            "Villages are randomized to a vaccination campaign. One resident's uptake changes neighbors' "
            "infection risk, but the proposal assumes each outcome depends only on that resident's assignment."
        ),
        "facts": (
            ("Assignment", "Village-level randomization"),
            ("Timing", "Campaign → individual uptake and neighbor exposure → infection"),
            ("Confounding", "Cluster randomization protects the assigned comparison"),
            ("Support", "Campaign and control villages represented"),
            ("Interference", "Within-village spillovers are expected by mechanism"),
        ),
        "question": "Primary target: distinguish direct, spillover, and cluster-level campaign effects.",
        "dispositions": (
            ("i9-d7", "Redesign the analysis around a prespecified exposure mapping and direct, spillover, or cluster-level estimand."),
            ("i9-a3", "Report the observed cluster-level association while deferring causal decomposition until an exposure mapping is specified."),
            ("i9-p5", "Restrict to vaccinated residents and estimate an individual direct effect after adjustment for measured village coverage."),
            ("i9-c8", "Approve an individual causal effect using village assignment, cluster-robust uncertainty, and campaign coverage as a nuisance covariate."),
        ),
        "rationales": (
            ("i9-s2", "Specify how own and neighbors’ assignments define exposure, then align the design with direct, spillover, or cluster-level estimands."),
            ("i9-v6", "Cluster randomization identifies the individual direct effect after conditioning on village treatment, even when neighbor uptake changes outcomes."),
            ("i9-n1", "Village fixed effects, clustered uncertainty, and a saturation covariate recover the proposed individual interpretation without exposure mapping."),
            ("i9-g4", "Treat neighbor exposure as nondifferential treatment contamination and retain the standard individual assignment estimand."),
        ),
    },
)


# ---------------------------------------------------------------------------
# Visual system: "methods docket" -- bone paper, graphite chrome, copper accent.
# ---------------------------------------------------------------------------
PAPER = "#f4f1ea"
SHEET = "#fffdf8"
GRAPHITE = "#1f2429"
GRAPHITE_2 = "#2c333a"
INK = "#20262c"
MUTED = "#6b6f73"
RULE = "#ddd6c8"
COPPER = "#b5652b"
COPPER_SOFT = "#f3e3d4"
SLATE = "#3d5a6c"
SLATE_SOFT = "#e3eaee"
DONE = "#4f7a5a"
LETTERS = "ABCD"


def _font(family: str, size: int, weight: str = "normal", slant: str = "roman") -> tkfont.Font:
    return tkfont.Font(family=family, size=-size, weight=weight, slant=slant)


class CausalAuditApp:
    def __init__(self, root: tk.Tk):
        self.root = root
        self.current = 0
        self.submitted = False
        self.choice = {proposal["id"]: {"disposition": "", "rationale": ""} for proposal in PROPOSALS}
        self.events: list[dict] = []
        self.option_rows: dict[tuple[str, str], list] = {}

        root.title("Causal Study Audit")
        root.geometry("1024x866+0+0")
        root.minsize(900, 760)
        root.configure(bg=PAPER)
        root.lift()
        root.attributes("-topmost", True)
        root.after(8000, lambda: root.attributes("-topmost", False))

        serif = "P052"
        sans = "Nimbus Sans"
        self.f_brand = _font(serif, 22, "bold")
        self.f_title = _font(serif, 21, "bold")
        self.f_head = _font(sans, 14, "bold")
        self.f_body = _font(sans, 13)
        self.f_body_b = _font(sans, 13, "bold")
        self.f_small = _font(sans, 12)
        self.f_small_b = _font(sans, 12, "bold")
        self.f_letter = _font(serif, 15, "bold")
        self.f_italic = _font(serif, 14, "normal", "italic")

        self._build_header()
        self._build_docket()
        self._build_footer()
        self.body = tk.Frame(root, bg=PAPER)
        self.body.pack(fill="both", expand=True)
        self._render()

    # ----------------------------------------------------------------- chrome
    def _build_header(self) -> None:
        bar = tk.Frame(self.root, bg=GRAPHITE, height=58)
        bar.pack(fill="x", side="top")
        bar.pack_propagate(False)
        mark = tk.Canvas(bar, width=42, height=42, bg=GRAPHITE, highlightthickness=0)
        mark.pack(side="left", padx=(18, 10), pady=8)
        mark.create_rectangle(1, 1, 41, 41, fill=COPPER, outline="")
        nodes = ((10, 30), (21, 11), (32, 30))
        mark.create_line(13, 26, 19, 15, fill=SHEET, width=2, arrow="last", arrowshape=(6, 7, 3))
        mark.create_line(23, 15, 29, 26, fill=SHEET, width=2, arrow="last", arrowshape=(6, 7, 3))
        mark.create_line(15, 30, 26, 30, fill=SHEET, width=2, arrow="last", arrowshape=(6, 7, 3))
        for x, y in nodes:
            mark.create_oval(x - 4, y - 4, x + 4, y + 4, fill=GRAPHITE, outline=SHEET, width=2)
        tk.Label(bar, text="Causal Study Audit", bg=GRAPHITE, fg=SHEET, font=self.f_brand).pack(side="left")
        tk.Label(bar, text="  methods review desk", bg=GRAPHITE, fg="#b7b0a3", font=self.f_italic).pack(side="left", pady=(6, 0))
        tk.Label(bar, text="Reviewer workspace", bg=GRAPHITE_2, fg="#d9d2c4", font=self.f_small, padx=12, pady=6).pack(side="right", padx=18)
        tk.Label(bar, text="Proposal queue", bg=GRAPHITE, fg=SHEET, font=self.f_small_b).pack(side="right", padx=8)

    def _build_docket(self) -> None:
        strip = tk.Frame(self.root, bg=SHEET, height=52, highlightthickness=0)
        strip.pack(fill="x", side="top")
        strip.pack_propagate(False)
        tk.Frame(self.root, bg=RULE, height=1).pack(fill="x", side="top")
        self.tabs: list[tuple[tk.Frame, tk.Label, tk.Label, tk.Frame]] = []
        for index, proposal in enumerate(PROPOSALS):
            tab = tk.Frame(strip, bg=SHEET, cursor="hand2", name=f"tab{index + 1}")
            tab.pack(side="left", fill="both", expand=True)
            num = tk.Label(tab, text=f"{index + 1:02d}", bg=SHEET, fg=MUTED, font=self.f_small_b)
            num.pack(side="left", padx=(12, 6))
            name = tk.Label(tab, text=proposal["queue"], bg=SHEET, fg=INK, font=self.f_small, anchor="w", wraplength=118, justify="left")
            name.pack(side="left", fill="x")
            underline = tk.Frame(tab, bg=SHEET, height=4)
            underline.place(relx=0, rely=1.0, anchor="sw", relwidth=1.0)
            for widget in (tab, num, name):
                widget.bind("<Button-1>", lambda _e, idx=index: self.show(idx))
            self.tabs.append((tab, num, name, underline))

    def _build_footer(self) -> None:
        foot = tk.Frame(self.root, bg=GRAPHITE, height=62)
        foot.pack(fill="x", side="bottom")
        foot.pack_propagate(False)
        self.progress = tk.Canvas(foot, width=150, height=14, bg=GRAPHITE, highlightthickness=0)
        self.progress.pack(side="left", padx=(20, 10))
        self.status = tk.Label(foot, text="", bg=GRAPHITE, fg=SHEET, font=self.f_body)
        self.status.pack(side="left")
        self.submit_button = tk.Button(
            foot, name="submit", text="Submit completed audit", bg=COPPER, fg="white", activebackground="#9b5323",
            activeforeground="white", relief="flat", bd=0, highlightthickness=0, font=self.f_head, padx=18, pady=8, cursor="hand2",
            command=self.submit,
        )
        self.submit_button.pack(side="right", padx=(8, 18), pady=10)
        self.next_button = tk.Button(
            foot, name="next", text="Next proposal  ›", bg=GRAPHITE_2, fg=SHEET, activebackground="#3a434c",
            activeforeground=SHEET, relief="flat", bd=0, highlightthickness=0, font=self.f_body_b, padx=14, pady=8, cursor="hand2",
            command=lambda: self.show(self.current + 1),
        )
        self.next_button.pack(side="right", padx=4, pady=10)
        self.prev_button = tk.Button(
            foot, name="prev", text="‹  Previous", bg=GRAPHITE_2, fg=SHEET, activebackground="#3a434c",
            activeforeground=SHEET, relief="flat", bd=0, highlightthickness=0, font=self.f_body_b, padx=14, pady=8, cursor="hand2",
            command=lambda: self.show(self.current - 1),
        )
        self.prev_button.pack(side="right", padx=4, pady=10)

    # ------------------------------------------------------------------ state
    def is_done(self, proposal_id: str) -> bool:
        return all(self.choice[proposal_id].values())

    def completed_count(self) -> int:
        return sum(self.is_done(proposal["id"]) for proposal in PROPOSALS)

    def show(self, index: int) -> None:
        if self.submitted or not 0 <= index < len(PROPOSALS):
            return
        self.current = index
        self._render()

    def _refresh_chrome(self, message: str | None = None, warn: bool = False) -> None:
        for index, (tab, num, name, underline) in enumerate(self.tabs):
            active = index == self.current
            done = self.is_done(PROPOSALS[index]["id"])
            bg = COPPER_SOFT if active else SHEET
            for widget in (tab, num, name):
                widget.configure(bg=bg)
            num.configure(text=("✓ " if done else "") + f"{index + 1:02d}", fg=DONE if done else (COPPER if active else MUTED))
            underline.configure(bg=COPPER if active else SHEET)
        self.progress.delete("all")
        for index, proposal in enumerate(PROPOSALS):
            x = index * 25
            self.progress.create_rectangle(x, 3, x + 20, 11, fill=COPPER if self.is_done(proposal["id"]) else "#4a525a", outline="")
        done = self.completed_count()
        if message is None:
            message = f"{done} of {len(PROPOSALS)} proposals reviewed"
        self.status.configure(text=message, fg="#ffc98f" if warn else SHEET)
        self.prev_button.configure(state="normal" if self.current > 0 and not self.submitted else "disabled")
        self.next_button.configure(state="normal" if self.current < len(PROPOSALS) - 1 and not self.submitted else "disabled")

    # ----------------------------------------------------------------- render
    def _render(self) -> None:
        for child in self.body.winfo_children():
            child.destroy()
        self.option_rows = {}
        proposal = PROPOSALS[self.current]

        left = tk.Frame(self.body, bg=SHEET, width=372, highlightthickness=1, highlightbackground=RULE)
        left.pack(side="left", fill="y", padx=(16, 10), pady=12)
        left.pack_propagate(False)
        tk.Frame(left, bg=COPPER, height=4).pack(fill="x")
        tk.Label(left, text=f"DOSSIER {self.current + 1} / {len(PROPOSALS)}  ·  {proposal['queue'].upper()}", bg=SHEET, fg=COPPER, font=self.f_small_b, anchor="w").pack(fill="x", padx=16, pady=(12, 2))
        tk.Label(left, text=proposal["title"], bg=SHEET, fg=INK, font=self.f_title, anchor="w", justify="left", wraplength=336).pack(fill="x", padx=16)
        tk.Label(left, text=proposal["summary"], bg=SHEET, fg="#3b4046", font=self.f_body, anchor="w", justify="left", wraplength=336).pack(fill="x", padx=16, pady=(6, 10))

        table = tk.Frame(left, bg=SHEET)
        table.pack(fill="x", padx=16)
        tk.Label(table, text="DESIGN FACTS", bg=SHEET, fg=MUTED, font=self.f_small_b, anchor="w").pack(fill="x", pady=(0, 3))
        for label, value in proposal["facts"]:
            tk.Frame(table, bg=RULE, height=1).pack(fill="x")
            row = tk.Frame(table, bg=SHEET)
            row.pack(fill="x", pady=3)
            tk.Label(row, text=label, width=11, bg=SHEET, fg=SLATE, font=self.f_small_b, anchor="nw", justify="left").pack(side="left", anchor="n")
            tk.Label(row, text=value, bg=SHEET, fg=INK, font=self.f_small, anchor="w", justify="left", wraplength=236).pack(side="left", fill="x")
        tk.Frame(table, bg=RULE, height=1).pack(fill="x")

        target = tk.Frame(left, bg=SLATE_SOFT)
        target.pack(fill="x", padx=16, pady=(12, 14))
        tk.Frame(target, bg=SLATE, width=4).pack(side="left", fill="y")
        tk.Label(target, text=proposal["question"], bg=SLATE_SOFT, fg="#23384a", font=self.f_small_b, anchor="w", justify="left", wraplength=316, padx=10, pady=8).pack(side="left", fill="x")

        right = tk.Frame(self.body, bg=PAPER)
        right.pack(side="left", fill="both", expand=True, padx=(0, 16), pady=12)
        self._choice_panel(right, proposal, "disposition", "Disposition", "What should the board record for this proposal?", proposal["dispositions"])
        self._choice_panel(right, proposal, "rationale", "Primary reason", "Which reason carries the decision?", proposal["rationales"])
        self._refresh_chrome()

    def _choice_panel(self, parent: tk.Widget, proposal: dict, field_id: str, title: str, prompt: str, options: tuple) -> None:
        panel = tk.Frame(parent, bg=PAPER)
        panel.pack(fill="x", pady=(0, 8))
        head = tk.Frame(panel, bg=PAPER)
        head.pack(fill="x", pady=(0, 4))
        tk.Label(head, text=title, bg=PAPER, fg=INK, font=self.f_head).pack(side="left")
        tk.Label(head, text="  " + prompt, bg=PAPER, fg=MUTED, font=self.f_small).pack(side="left", pady=(2, 0))
        rows = []
        for position, (option_id, text) in enumerate(options):
            card = tk.Frame(panel, bg=SHEET, highlightthickness=1, highlightbackground=RULE, cursor="hand2",
                            name=f"{field_id}_{self.current + 1}_{position + 1}")
            card.pack(fill="x", pady=2)
            letter = tk.Label(card, text=LETTERS[position], width=2, bg=SLATE_SOFT, fg=SLATE, font=self.f_letter)
            letter.pack(side="left", fill="y")
            label = tk.Label(card, text=text, bg=SHEET, fg=INK, font=self.f_body, anchor="w", justify="left", wraplength=560, padx=10, pady=6)
            label.pack(side="left", fill="both", expand=True)
            for widget in (card, letter, label):
                widget.bind("<Button-1>", lambda _e, pid=proposal["id"], fid=field_id, oid=option_id: self.select(pid, fid, oid))
            rows.append((option_id, card, letter, label))
        self.option_rows[(proposal["id"], field_id)] = rows
        self._paint(proposal["id"], field_id)

    def _paint(self, proposal_id: str, field_id: str) -> None:
        chosen = self.choice[proposal_id][field_id]
        for option_id, card, letter, label in self.option_rows.get((proposal_id, field_id), []):
            on = option_id == chosen
            card.configure(highlightbackground=COPPER if on else RULE, highlightthickness=2 if on else 1)
            letter.configure(bg=COPPER if on else SLATE_SOFT, fg="white" if on else SLATE)
            label.configure(bg=COPPER_SOFT if on else SHEET)

    # ---------------------------------------------------------------- actions
    def select(self, proposal_id: str, field_id: str, option_id: str) -> None:
        if self.submitted:
            return
        self.choice[proposal_id][field_id] = option_id
        self.events.append({"event": "select", "proposalId": proposal_id, "fieldId": field_id, "optionId": option_id})
        self._paint(proposal_id, field_id)
        self._refresh_chrome()

    def submit(self) -> None:
        if self.submitted:
            return
        if self.completed_count() != len(PROPOSALS):
            missing = next(i for i, p in enumerate(PROPOSALS) if not self.is_done(p["id"]))
            self.current = missing
            self._render()
            self._refresh_chrome("Choose a disposition and a primary reason for every proposal first.", warn=True)
            return
        reviews = [
            {"proposalId": p["id"], "dispositionId": self.choice[p["id"]]["disposition"], "rationaleId": self.choice[p["id"]]["rationale"]}
            for p in PROPOSALS
        ]
        self.events.append({"event": "submit"})
        payload = {
            "submitted": True,
            "reviews": reviews,
            "events": self.events,
            "confirmation": {
                "status": "submitted",
                "reviewCount": len(reviews),
                "selectionCount": sum(event.get("event") == "select" for event in self.events),
            },
        }
        os.makedirs(OUTPUT_DIR, exist_ok=True)
        temporary = os.path.join(OUTPUT_DIR, "causal_review.json.tmp")
        destination = os.path.join(OUTPUT_DIR, "causal_review.json")
        with open(temporary, "w", encoding="utf-8") as handle:
            json.dump(payload, handle, ensure_ascii=False, indent=2)
        os.replace(temporary, destination)
        self.submitted = True
        self.submit_button.configure(state="disabled", text="Audit submitted")
        self._refresh_chrome("Audit confirmed and submitted to the methods board.")
        for child in self.body.winfo_children():
            child.destroy()
        card = tk.Frame(self.body, bg=SHEET, highlightthickness=1, highlightbackground=RULE)
        card.place(relx=0.5, rely=0.42, anchor="center", width=520, height=220)
        tk.Frame(card, bg=COPPER, height=5).pack(fill="x")
        tk.Label(card, text="✓", bg=SHEET, fg=DONE, font=_font("P052", 40, "bold")).pack(pady=(18, 0))
        tk.Label(card, text="Audit submitted", bg=SHEET, fg=INK, font=self.f_title).pack()
        tk.Label(card, text=f"{len(reviews)} proposals reviewed · record filed with the methods board", bg=SHEET, fg=MUTED, font=self.f_body).pack(pady=(6, 0))


if __name__ == "__main__":
    root = tk.Tk()
    CausalAuditApp(root)
    root.mainloop()
