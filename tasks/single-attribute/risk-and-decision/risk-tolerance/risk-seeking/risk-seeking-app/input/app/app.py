"""BidDesk proposal-workflow desktop application.

A canvas-drawn studio "proposal desk": an olive pipeline rail lists all 16
client opportunities; the desk shows one brief at a time with its two proposal
decisions as option cards. Choose one card in each panel, Save & next, and once
all 16 proposals are saved, Submit portfolio — the app then writes
proposal_portfolio.json itself.
"""
from __future__ import annotations

import json
import os
from pathlib import Path
import tkinter as tk
from tkinter import font as tkfont

OUTPUT_DIR = Path(
    os.environ.get("PLAYGROUND_OUTPUT_DIR")
    or os.environ.get("ADHERENCE_OUTPUT_DIR")
    or os.environ.get("MATRIX_OUTPUT_DIR")
    or "/app/output"
)
DATA_PATH = Path(__file__).with_name("workflows.json")

# Olive rail / cream desk / chartreuse accent — identical for every option card.
RAIL, RAIL2, RAIL_TXT = "#2f3a2c", "#3d4a39", "#c9d1bd"
DESK, PAPER, GRID, INK = "#f4f1e6", "#fffdf6", "#e9e4d3", "#1f261d"
MUTED, RULE, LIME, LIME_D, AMBER = "#667060", "#d8d2bf", "#c8d94c", "#6f7d1f", "#e39b3a"
W, H = 1024, 866
RAIL_W = 250


def load_workflows() -> list[dict]:
    value = json.loads(DATA_PATH.read_text(encoding="utf-8"))
    if not isinstance(value, dict) or set(value) != {"workflows"}:
        raise RuntimeError("workflows.json must contain only workflows")
    workflows = value["workflows"]
    if not isinstance(workflows, list) or len(workflows) != 16:
        raise RuntimeError("BidDesk requires exactly 16 workflows")
    return workflows


class BidDeskApp:
    def __init__(self, root: tk.Tk):
        self.root = root
        self.workflows = load_workflows()
        self.index = 0
        self.saved: dict[str, dict[str, str]] = {}
        self.current: dict[str, str] = {}
        self.events: list[dict] = [
            {"event": "start", "workflowCount": len(self.workflows)}
        ]
        self.status = ""
        self.status_warn = False
        self.submitted = False
        self.boxes: dict[str, tuple[int, int, int, int]] = {}

        root.title("BidDesk Opportunity Workspace")
        sw, sh = root.winfo_screenwidth(), root.winfo_screenheight()
        root.geometry(f"{min(W, sw)}x{min(H, sh)}+0+0")
        root.configure(bg=DESK)
        try:
            root.attributes("-zoomed", True)
        except tk.TclError:
            pass
        root.lift()
        root.attributes("-topmost", True)
        root.after(8000, lambda: root.attributes("-topmost", False))

        fams = set(tkfont.families(root))
        narrow = "Nimbus Sans Narrow" if "Nimbus Sans Narrow" in fams else "DejaVu Sans Condensed"
        sans = "Liberation Sans" if "Liberation Sans" in fams else "DejaVu Sans"
        self.f_brand = tkfont.Font(family=narrow, size=24, weight="bold")
        rnarrow = "Liberation Sans Narrow" if "Liberation Sans Narrow" in fams else sans
        self.f_rail = tkfont.Font(family=rnarrow, size=13)
        self.f_rail_b = tkfont.Font(family=rnarrow, size=13, weight="bold")
        self.f_kicker = tkfont.Font(family=narrow, size=13, weight="bold")
        self.f_title = tkfont.Font(family=narrow, size=22, weight="bold")
        self.f_body = tkfont.Font(family=sans, size=12)
        self.f_label = tkfont.Font(family=narrow, size=16, weight="bold")
        self.f_opt = tkfont.Font(family=sans, size=12)
        self.f_btn = tkfont.Font(family=sans, size=13, weight="bold")

        self.cv = tk.Canvas(root, bg=DESK, highlightthickness=0, width=W, height=H)
        self.cv.pack(fill="both", expand=True)
        self.cv.bind("<Button-1>", self._click)
        self.cv.bind("<Motion>", lambda e: self.cv.configure(cursor="hand2" if self._hit(e.x, e.y) else ""))
        self._open(0)

    # ------------------------------------------------------------ navigation
    def _open(self, index: int) -> None:
        self.index = index
        workflow = self.workflows[index]
        self.current = dict(self.saved.get(workflow["id"], {}))
        self.events.append({"event": "open", "workflowId": workflow["id"]})
        self._default_status()
        self.draw()

    def _default_status(self) -> None:
        complete = len(self.current) == 2
        message = "Both proposal choices selected." if complete else "Choose one option in both panels."
        self.status = f"{message}  {len(self.saved)} of 16 proposals saved."
        self.status_warn = False

    # --------------------------------------------------------------- drawing
    def draw(self) -> None:
        self.cv.delete("all")
        self.boxes = {}
        self._rail()
        self._desk()
        self._footer()

    def _rail(self) -> None:
        cv = self.cv
        cv.create_rectangle(0, 0, RAIL_W, H, fill=RAIL, outline="")
        # mark: two offset proposal sheets with a folded corner
        cv.create_rectangle(26, 22, 56, 60, fill=LIME, outline="")
        cv.create_polygon(34, 16, 58, 16, 66, 24, 66, 54, 34, 54, fill=PAPER, outline="")
        cv.create_polygon(58, 16, 58, 24, 66, 24, fill=RULE, outline="")
        for k in range(3):
            cv.create_line(40, 30 + k * 7, 60 - (k == 2) * 8, 30 + k * 7, fill=RAIL2, width=2)
        cv.create_text(78, 30, text="BidDesk", anchor="w", font=self.f_brand, fill=PAPER)
        cv.create_text(79, 54, text="Opportunity Workspace", anchor="w", font=self.f_rail, fill=RAIL_TXT)
        cv.create_text(24, 94, text="PIPELINE", anchor="w", font=self.f_kicker, fill=LIME)
        top, row = 110, 39
        for i, wf in enumerate(self.workflows):
            y = top + i * row
            active = i == self.index
            saved = wf["id"] in self.saved
            if active:
                cv.create_rectangle(0, y, RAIL_W, y + row - 3, fill=RAIL2, outline="")
                cv.create_rectangle(0, y, 5, y + row - 3, fill=LIME, outline="")
            cx, cy = 34, y + (row - 3) / 2
            if saved:
                cv.create_oval(cx - 9, cy - 9, cx + 9, cy + 9, fill=LIME, outline="")
                cv.create_line(cx - 4, cy, cx - 1, cy + 4, cx + 5, cy - 4, fill=RAIL, width=2)
            else:
                cv.create_oval(cx - 9, cy - 9, cx + 9, cy + 9, outline=RAIL_TXT if active else "#6f7c69", width=2)
            label = f"{i + 1:02d}  {wf['client']}"
            cv.create_text(54, cy, text=label, anchor="w",
                           font=self.f_rail_b if active else self.f_rail,
                           fill=PAPER if active else RAIL_TXT)
            self.boxes[f"rail:{i}"] = (0, y, RAIL_W, y + row - 3)
        n = len(self.saved)
        cv.create_text(24, H - 44, text=f"{n} of 16 saved", anchor="w", font=self.f_rail_b, fill=PAPER)
        cv.create_rectangle(24, H - 26, RAIL_W - 24, H - 18, fill=RAIL2, outline="")
        if n:
            cv.create_rectangle(24, H - 26, 24 + (RAIL_W - 48) * n / 16, H - 18, fill=LIME, outline="")

    def _desk(self) -> None:
        cv = self.cv
        x0, x1 = RAIL_W, W
        # faint graph-paper ground
        for gx in range(x0 + 12, x1, 24):
            cv.create_line(gx, 0, gx, H, fill=GRID)
        for gy in range(12, H, 24):
            cv.create_line(x0, gy, x1, gy, fill=GRID)
        wf = self.workflows[self.index]
        lx, rx = x0 + 22, x1 - 22
        # brief sheet (sized once its contents are laid out)
        sheet = cv.create_rectangle(lx, 16, rx, 17, fill=PAPER, outline=RULE)
        cv.create_text(lx + 18, 34, text=f"{wf['client'].upper()}   ·   OPPORTUNITY {self.index + 1} OF 16",
                           anchor="w", font=self.f_kicker, fill=LIME_D)
        t = cv.create_text(lx + 18, 50, text=wf["title"], anchor="nw", font=self.f_title, fill=INK)
        y = cv.bbox(t)[3] + 6
        s = cv.create_text(lx + 18, y, text=wf["scenario"], anchor="nw", font=self.f_body, fill=INK,
                           width=rx - lx - 36)
        y = cv.bbox(s)[3] + 10
        # facts as chips (wrap to new line as needed)
        cx = lx + 18
        for fact in wf["facts"]:
            w = self.f_body.measure(fact) + 22
            if cx + w > rx - 18:
                cx, y = lx + 18, y + 32
            cv.create_rectangle(cx, y, cx + w, y + 26, fill=DESK, outline=RULE)
            cv.create_text(cx + 11, y + 13, text=fact, anchor="w", font=self.f_body, fill=MUTED)
            cx += w + 8
        y += 36
        n = cv.create_text(lx + 18, y, text="All listed options are commercially approved and feasible. "
                           "Choose a compensation package and delivery commitment, then save the proposal.",
                           anchor="nw", font=self.f_body, fill=MUTED, width=rx - lx - 36)
        y = cv.bbox(n)[3] + 12
        cv.coords(sheet, lx, 16, rx, y)
        cv.create_rectangle(lx, 16, lx + 6, y, fill=LIME, outline="")
        # decision panels
        top = y + 14
        colw = (rx - lx - 16) / 2
        for c, field in enumerate(wf["fields"]):
            self._field(field, lx + c * (colw + 16), top, colw)

    def _field(self, field: dict, x: float, y: float, w: float) -> None:
        cv = self.cv
        t = cv.create_text(x, y, text=field["label"], anchor="nw", font=self.f_label, fill=INK)
        h = cv.create_text(x, cv.bbox(t)[3] + 2, text=field["help"], anchor="nw", font=self.f_body,
                           fill=MUTED, width=w)
        yy = cv.bbox(h)[3] + 8
        chosen = self.current.get(field["id"])
        for pos, opt in enumerate(field["options"]):
            on = chosen == opt["id"]
            txt = cv.create_text(x + 48, yy + 11, text=opt["text"], anchor="nw", font=self.f_opt,
                                 fill=INK, width=w - 62)
            bot = max(cv.bbox(txt)[3] + 11, yy + 44)
            card = cv.create_rectangle(x, yy, x + w, bot, fill="#f3f6dc" if on else PAPER,
                                       outline=LIME_D if on else RULE, width=2 if on else 1)
            cv.tag_lower(card, txt)
            # radio + position letter
            rx_, ry_ = x + 24, yy + 21
            cv.create_oval(rx_ - 11, ry_ - 11, rx_ + 11, ry_ + 11, fill=PAPER,
                           outline=LIME_D if on else "#a9a58f", width=2)
            if on:
                cv.create_oval(rx_ - 6, ry_ - 6, rx_ + 6, ry_ + 6, fill=LIME_D, outline="")
            else:
                cv.create_text(rx_, ry_, text="ABCD"[pos], font=self.f_rail, fill=MUTED)
            self.boxes[f"opt:{field['id']}:{opt['id']}"] = (int(x), int(yy), int(x + w), int(bot))
            yy = bot + 7

    def _footer(self) -> None:
        cv = self.cv
        x0 = RAIL_W
        y0 = H - 70
        cv.create_rectangle(x0, y0, W, H, fill=INK, outline="")
        if self.submitted:
            cv.create_text(x0 + 24, y0 + 35, text="Portfolio submitted.", anchor="w", font=self.f_btn, fill=LIME)
        else:
            cv.create_text(x0 + 24, y0 + 35, text=self.status, anchor="w", font=self.f_body,
                           fill=AMBER if self.status_warn else "#e8ecdf", width=340)
        last = self.index == len(self.workflows) - 1
        buttons = [
            ("back", "Back", self.index > 0 and not self.submitted, RAIL2, PAPER),
            ("next", "Save proposal" if last else "Save & next", not self.submitted, "#e8ecdf", INK),
            ("submit", "Submit portfolio", len(self.saved) == 16 and not self.submitted, LIME, INK),
        ]
        bx = W - 18
        for key, label, enabled, bg, fg in reversed(buttons):
            bw = self.f_btn.measure(label) + 36
            bx0 = bx - bw
            cv.create_rectangle(bx0, y0 + 14, bx, y0 + 56, fill=bg if enabled else "#454d42", outline="")
            cv.create_text((bx0 + bx) / 2, y0 + 35, text=label, font=self.f_btn,
                           fill=fg if enabled else "#8b9486")
            if enabled:
                self.boxes[key] = (int(bx0), y0 + 14, int(bx), y0 + 56)
            bx = bx0 - 10

    # ----------------------------------------------------------------- input
    def _hit(self, x: int, y: int):
        for k, (a, b, c, d) in self.boxes.items():
            if a <= x <= c and b <= y <= d:
                return k
        return None

    def _click(self, e) -> None:
        k = self._hit(e.x, e.y)
        if not k or self.submitted:
            return
        if k.startswith("opt:"):
            _, fid, oid = k.split(":", 2)
            self.select(self.workflows[self.index]["id"], fid, oid)
        elif k.startswith("rail:"):
            i = int(k.split(":", 1)[1])
            if i != self.index:
                self._open(i)
        elif k == "next":
            self.save_and_next()
        elif k == "back":
            self.go_back()
        elif k == "submit":
            self.submit()

    def select(self, workflow_id: str, field_id: str, option_id: str) -> None:
        self.current[field_id] = option_id
        self.events.append(
            {
                "event": "select",
                "workflowId": workflow_id,
                "fieldId": field_id,
                "optionId": option_id,
            }
        )
        self._default_status()
        self.draw()

    def save_and_next(self) -> None:
        workflow = self.workflows[self.index]
        expected_fields = {field["id"] for field in workflow["fields"]}
        if set(self.current) != expected_fields:
            self.status = "Choose one option in both panels before saving."
            self.status_warn = True
            self.draw()
            return
        self.saved[workflow["id"]] = dict(self.current)
        self.events.append({"event": "save", "workflowId": workflow["id"]})
        if self.index < len(self.workflows) - 1:
            self._open(self.index + 1)
        else:
            unsaved = [i for i, wf in enumerate(self.workflows) if wf["id"] not in self.saved]
            self._default_status()
            if unsaved:
                self.status = f"Saved. Opportunity {unsaved[0] + 1:02d} still needs saving (see the pipeline)."
                self.status_warn = True
            self.draw()

    def go_back(self) -> None:
        if self.index > 0:
            self._open(self.index - 1)

    def submit(self) -> None:
        if len(self.saved) != len(self.workflows):
            self.status = "Save all 16 proposals before submitting."
            self.status_warn = True
            self.draw()
            return
        answers = [
            {"workflowId": workflow["id"], "choices": self.saved[workflow["id"]]}
            for workflow in self.workflows
        ]
        self.events.append({"event": "submit"})
        payload = {
            "schemaVersion": "biddesk-v2",
            "submitted": True,
            "workflows": answers,
            "events": self.events,
        }
        OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
        temporary = OUTPUT_DIR / "proposal_portfolio.json.tmp"
        destination = OUTPUT_DIR / "proposal_portfolio.json"
        temporary.write_text(
            json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8"
        )
        os.replace(temporary, destination)
        self.submitted = True
        self.draw()

    place_order = submit


if __name__ == "__main__":
    root = tk.Tk()
    BidDeskApp(root)
    root.mainloop()
