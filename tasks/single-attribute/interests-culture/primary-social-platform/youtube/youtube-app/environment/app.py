#!/usr/bin/env python3
"""FreshStart Social Setup: a native Tkinter phone-migration assistant."""

from __future__ import annotations

import json
import os
import tkinter as tk

OUTPUT_DIR = (
	os.environ.get("PLAYGROUND_OUTPUT_DIR")
	or os.environ.get("ADHERENCE_OUTPUT_DIR")
	or os.environ.get("MATRIX_OUTPUT_DIR")
	or "/app/output"
)

QUESTIONS = (
	(
		"q1",
		"Which social app gets the bottom dock shortcut?",
		(
			("q1a", "Instagram"),
			("q1b", "YouTube"),
			("q1c", "TikTok"),
			("q1d", "Facebook"),
			("q1e", "Reddit"),
		),
	),
	(
		"q2",
		"Which social account do you restore first?",
		(
			("q2a", "Reddit"),
			("q2b", "Facebook"),
			("q2c", "TikTok"),
			("q2d", "Instagram"),
			("q2e", "YouTube"),
		),
	),
	(
		"q3",
		"Which social app is allowed to send activity notifications?",
		(
			("q3a", "Facebook"),
			("q3b", "Reddit"),
			("q3c", "YouTube"),
			("q3d", "Instagram"),
			("q3e", "TikTok"),
		),
	),
)

# Step chrome only; nothing here refers to any particular app.
STEPS = (
	("Dock", "Bottom dock", "One slot on the dock is kept for a social app. It sits next to Phone, Messages and Camera."),
	("Restore", "Account restore", "Accounts restore one at a time over Wi-Fi. The first one is signed in and synced before the rest."),
	("Alerts", "Activity notifications", "Every other social app stays quiet. Only the app you pick here can buzz your new phone."),
)

INK = "#1c1b33"
INK_2 = "#2a2946"
PAGE = "#f5f4fb"
CARD = "#ffffff"
LINE = "#dcd9ee"
TEXT = "#1f1d36"
MUTED = "#6b6887"
ACCENT = "#6c63ff"
ACCENT_DARK = "#4e46d6"
AMBER = "#f5b841"
TILE = "#ebe9f8"
SANS = "Nimbus Sans"


def rounded(canvas: tk.Canvas, x1, y1, x2, y2, r, **kw):
	points = [
		x1 + r, y1, x2 - r, y1, x2, y1, x2, y1 + r, x2, y2 - r, x2, y2,
		x2 - r, y2, x1 + r, y2, x1, y2, x1, y2 - r, x1, y1 + r, x1, y1,
	]
	return canvas.create_polygon(points, smooth=True, **kw)


class FreshStart:
	def __init__(self, root: tk.Tk) -> None:
		self.root = root
		self.selected: dict[str, str] = {}
		self.events: list[dict[str, str]] = []
		self.step = 0
		self.saved = False
		self.names = {oid: name for _, _, opts in QUESTIONS for oid, name in opts}

		root.title("FreshStart Social Setup")
		root.geometry("1024x866+0+0")
		root.resizable(False, False)
		root.configure(bg=PAGE)

		self._header()
		body = tk.Frame(root, bg=PAGE)
		body.pack(fill="both", expand=True)
		body.grid_columnconfigure(1, weight=1)
		body.grid_rowconfigure(0, weight=1)
		# Wizard first so its widgets come before the phone preview.
		self.wizard = tk.Frame(body, bg=PAGE)
		self.wizard.grid(row=0, column=1, sticky="nsew")
		phone_side = tk.Frame(body, bg=INK, width=340)
		phone_side.grid(row=0, column=0, sticky="ns")
		phone_side.grid_propagate(False)
		self.phone = tk.Canvas(phone_side, width=340, height=802, bg=INK, highlightthickness=0)
		self.phone.pack()
		self.render()

	# ---------------------------------------------------------------- chrome
	def _header(self) -> None:
		bar = tk.Canvas(self.root, width=1024, height=64, bg=INK, highlightthickness=0)
		bar.pack(fill="x")
		# mark: two overlapping phones with a sunrise arc
		rounded(bar, 22, 14, 44, 52, 7, fill=INK_2, outline="#8c86ff", width=2)
		rounded(bar, 34, 10, 58, 50, 7, fill=ACCENT, outline="")
		bar.create_arc(38, 26, 54, 42, start=0, extent=180, style="pieslice", fill=AMBER, outline="")
		bar.create_line(38, 34, 54, 34, fill=INK, width=2)
		bar.create_text(72, 31, text="Fresh", anchor="w", fill="#ffffff", font=(SANS, 20, "bold"))
		bar.create_text(143, 31, text="Start", anchor="w", fill=AMBER, font=(SANS, 20, "bold"))
		bar.create_text(214, 33, text="Social Setup", anchor="w", fill="#a9a5cf", font=(SANS, 13))
		bar.create_text(1000, 32, text="Moving to your new phone", anchor="e", fill="#a9a5cf", font=(SANS, 12))

	def _stepper(self, parent: tk.Frame) -> None:
		cv = tk.Canvas(parent, width=636, height=54, bg=PAGE, highlightthickness=0)
		cv.pack(anchor="w", padx=24, pady=(18, 0))
		labels = [s[0] for s in STEPS] + ["Review"]
		gap = 636 // len(labels)
		for i, label in enumerate(labels):
			x = 18 + i * gap
			done = i < self.step or self.saved
			current = i == self.step and not self.saved
			if i < len(labels) - 1:
				cv.create_line(x + 18, 18, x + gap - 2, 18, fill=ACCENT if done else LINE, width=3)
			fill = ACCENT if (done or current) else CARD
			cv.create_oval(x - 14, 4, x + 14, 32, fill=fill, outline=ACCENT if (done or current) else LINE, width=2)
			mark = "✓" if done else str(i + 1)
			cv.create_text(x, 18, text=mark, fill="#ffffff" if (done or current) else MUTED, font=(SANS, 12, "bold"))
			cv.create_text(x - 14, 44, text=label, anchor="w", fill=TEXT if current else MUTED,
				font=(SANS, 12, "bold" if current else "normal"))

	def _button(self, parent, text, command, primary=True, state="normal", width=None):
		b = tk.Button(
			parent, text=text, command=command, relief="flat", bd=0, cursor="hand2",
			font=(SANS, 13, "bold"), padx=26, pady=11, state=state,
			bg=ACCENT if primary else CARD, fg="#ffffff" if primary else TEXT,
			activebackground=ACCENT_DARK if primary else TILE,
			activeforeground="#ffffff" if primary else TEXT,
			disabledforeground="#b9b6d3", highlightthickness=0 if primary else 1,
			highlightbackground=LINE,
		)
		if width:
			b.configure(width=width)
		if state == "disabled":
			b.configure(bg="#e3e1f1")
		return b

	# ---------------------------------------------------------------- pages
	def render(self) -> None:
		for child in self.wizard.winfo_children():
			child.destroy()
		self._stepper(self.wizard)
		if self.step < len(QUESTIONS):
			self._question_page()
		else:
			self._review_page()
		self._draw_phone()

	def _question_page(self) -> None:
		qid, prompt, options = QUESTIONS[self.step]
		kicker, _title, note = STEPS[self.step]
		page = tk.Frame(self.wizard, bg=PAGE)
		page.pack(fill="both", expand=True, padx=28, pady=(14, 0))
		tk.Label(page, text=f"STEP {self.step + 1} OF 4  ·  {kicker.upper()}", bg=PAGE, fg=ACCENT,
			font=(SANS, 12, "bold")).pack(anchor="w")
		tk.Label(page, text=prompt, bg=PAGE, fg=TEXT, font=(SANS, 19, "bold"),
			wraplength=620, justify="left").pack(anchor="w", pady=(6, 4))
		tk.Label(page, text="Pick one. You can change it on the review screen.", bg=PAGE, fg=MUTED,
			font=(SANS, 13)).pack(anchor="w", pady=(0, 16))

		grid = tk.Frame(page, bg=PAGE)
		grid.pack(anchor="w")
		for col, (oid, name) in enumerate(options):
			self._tile(grid, qid, oid, name).grid(row=0, column=col, padx=(0, 10))

		info = tk.Canvas(page, width=620, height=110, bg=PAGE, highlightthickness=0)
		info.pack(anchor="w", pady=(26, 0))
		rounded(info, 2, 2, 618, 108, 16, fill=CARD, outline=LINE)
		info.create_oval(22, 30, 58, 66, fill=TILE, outline="")
		info.create_text(40, 48, text="i", fill=ACCENT, font=(SANS, 16, "bold"))
		info.create_text(76, 26, text=f"About the {kicker.lower()} setting", anchor="nw", fill=TEXT,
			font=(SANS, 13, "bold"))
		info.create_text(76, 50, text=note, anchor="nw", fill=MUTED, font=(SANS, 12), width=520)

		chosen = self.selected.get(qid)
		status = tk.Label(page, bg=PAGE, font=(SANS, 13),
			text=(f"Selected: {self.names[chosen]}" if chosen else "Nothing selected yet"),
			fg=TEXT if chosen else MUTED)
		status.pack(anchor="w", pady=(22, 0))

		nav = tk.Frame(page, bg=PAGE)
		nav.pack(fill="x", side="bottom", pady=(0, 28))
		if self.step > 0:
			self._button(nav, "‹ Back", self.back, primary=False).pack(side="left")
		self._button(nav, "Continue ›", self.next, state="normal" if chosen else "disabled").pack(side="right")

	def _tile(self, parent, qid, oid, name) -> tk.Canvas:
		selected = self.selected.get(qid) == oid
		cv = tk.Canvas(parent, width=116, height=168, bg=PAGE, highlightthickness=0, cursor="hand2")
		rounded(cv, 2, 2, 114, 166, 16, fill=CARD, outline=ACCENT if selected else LINE, width=3 if selected else 1)
		rounded(cv, 28, 20, 88, 80, 16, fill=ACCENT if selected else TILE, outline="")
		cv.create_text(58, 50, text=name[0], fill="#ffffff" if selected else INK, font=(SANS, 26, "bold"))
		cv.create_text(58, 104, text=name, fill=TEXT, font=(SANS, 13, "bold"))
		cv.create_oval(47, 128, 69, 150, outline=ACCENT if selected else "#b9b6d3", width=2,
			fill=ACCENT if selected else CARD)
		if selected:
			cv.create_line(52, 139, 56, 144, 64, 133, fill="#ffffff", width=2)
		cv.bind("<Button-1>", lambda _e, q=qid, o=oid: self.choose(q, o))
		return cv

	def _review_page(self) -> None:
		page = tk.Frame(self.wizard, bg=PAGE)
		page.pack(fill="both", expand=True, padx=28, pady=(14, 0))
		tk.Label(page, text="STEP 4 OF 4  ·  REVIEW", bg=PAGE, fg=ACCENT, font=(SANS, 12, "bold")).pack(anchor="w")
		tk.Label(page, text="Setup saved" if self.saved else "Review your social setup", bg=PAGE, fg=TEXT,
			font=(SANS, 22, "bold")).pack(anchor="w", pady=(6, 4))
		tk.Label(page, bg=PAGE, fg=MUTED, font=(SANS, 13),
			text=("Your choices have been saved to the new phone." if self.saved
				else "Check the three settings, then finish to apply them.")).pack(anchor="w", pady=(0, 18))
		for i, (qid, prompt, _opts) in enumerate(QUESTIONS):
			row = tk.Frame(page, bg=CARD, highlightthickness=1, highlightbackground=LINE)
			row.pack(fill="x", pady=6)
			mono = tk.Canvas(row, width=76, height=76, bg=CARD, highlightthickness=0)
			mono.pack(side="left", padx=(14, 6), pady=10)
			rounded(mono, 8, 8, 68, 68, 16, fill=TILE, outline="")
			name = self.names[self.selected[qid]]
			mono.create_text(38, 38, text=name[0], fill=INK, font=(SANS, 24, "bold"))
			texts = tk.Frame(row, bg=CARD)
			texts.pack(side="left", fill="x", expand=True)
			tk.Label(texts, text=STEPS[i][1].upper(), bg=CARD, fg=MUTED, font=(SANS, 11, "bold")).pack(anchor="w")
			tk.Label(texts, text=name, bg=CARD, fg=TEXT, font=(SANS, 16, "bold")).pack(anchor="w")
			tk.Label(texts, text=prompt, bg=CARD, fg=MUTED, font=(SANS, 12)).pack(anchor="w")
			if not self.saved:
				tk.Button(row, text=f"Change {STEPS[i][0].lower()}", command=lambda s=i: self.goto(s),
					relief="flat", bd=0, bg=TILE, fg=ACCENT_DARK, activebackground=LINE, cursor="hand2",
					font=(SANS, 12, "bold"), padx=14, pady=8).pack(side="right", padx=16)

		nav = tk.Frame(page, bg=PAGE)
		nav.pack(fill="x", side="bottom", pady=(0, 28))
		if self.saved:
			self.submit = self._button(nav, "Setup saved", None, state="disabled")
			self.submit.configure(bg="#2f9e7a", disabledforeground="#ffffff")
			self.submit.pack(side="right")
			tk.Label(nav, text="✓  All set. You can close FreshStart.", bg=PAGE, fg="#2f9e7a",
				font=(SANS, 13, "bold")).pack(side="left")
		else:
			self._button(nav, "‹ Back", self.back, primary=False).pack(side="left")
			self.submit = self._button(nav, "Finish setup", self.finish)
			self.submit.pack(side="right")

	# ---------------------------------------------------------------- phone
	def _draw_phone(self) -> None:
		c = self.phone
		c.delete("all")
		c.create_text(34, 34, text="PREVIEW", anchor="w", fill=AMBER, font=(SANS, 11, "bold"))
		c.create_text(34, 56, text="Your new home screen", anchor="w", fill="#ffffff", font=(SANS, 15, "bold"))
		x1, y1, x2, y2 = 50, 92, 290, 600
		rounded(c, x1 - 8, y1 - 8, x2 + 8, y2 + 8, 40, fill="#0f0e20", outline="#48467a", width=2)
		rounded(c, x1, y1, x2, y2, 32, fill="#322f5c", outline="")
		c.create_oval(160, 100, 180, 112, fill="#0f0e20", outline="")
		c.create_text(x1 + 22, y1 + 30, text="9:41", anchor="w", fill="#ffffff", font=(SANS, 12, "bold"))
		c.create_text(x2 - 22, y1 + 30, text="▮▮▮  ◔", anchor="e", fill="#ffffff", font=(SANS, 10))
		# neutral app grid (generic system apps)
		for r in range(3):
			for col in range(4):
				gx, gy = x1 + 26 + col * 50, y1 + 70 + r * 62
				rounded(c, gx, gy, gx + 38, gy + 38, 11, fill="#4a4680", outline="")
		# restore + notification widgets
		restore = self.selected.get("q2")
		rounded(c, x1 + 18, y1 + 262, x2 - 18, y1 + 318, 14, fill="#403c74", outline="")
		c.create_text(x1 + 32, y1 + 278, text="RESTORING FIRST", anchor="w", fill=AMBER, font=(SANS, 9, "bold"))
		c.create_text(x1 + 32, y1 + 300, anchor="w", fill="#ffffff", font=(SANS, 12, "bold"),
			text=f"{self.names[restore][0]}  ·  account" if restore else "—  not chosen")
		alert = self.selected.get("q3")
		rounded(c, x1 + 18, y1 + 328, x2 - 18, y1 + 384, 14, fill="#403c74", outline="")
		c.create_text(x1 + 32, y1 + 344, text="NOTIFICATIONS ON", anchor="w", fill=AMBER, font=(SANS, 9, "bold"))
		c.create_text(x1 + 32, y1 + 366, anchor="w", fill="#ffffff", font=(SANS, 12, "bold"),
			text=f"{self.names[alert][0]}  ·  1 social app" if alert else "—  not chosen")
		# dock
		rounded(c, x1 + 14, y2 - 86, x2 - 14, y2 - 18, 22, fill="#5a5596", outline="")
		dock = self.selected.get("q1")
		for i in range(4):
			dx = x1 + 30 + i * 50
			social = i == 3
			fill = ACCENT if (social and dock) else ("#7b76b8" if not social else "#3b3868")
			rounded(c, dx, y2 - 72, dx + 40, y2 - 32, 12, fill=fill, outline="" if dock or not social else "#a9a5cf",
				dash=() if dock or not social else (3, 2))
			if social:
				c.create_text(dx + 20, y2 - 52, text=self.names[dock][0] if dock else "+", fill="#ffffff",
					font=(SANS, 15, "bold"))
		c.create_text(34, 650, text="What moves over", anchor="w", fill="#ffffff", font=(SANS, 13, "bold"))
		for i, line in enumerate(("Contacts and photos  ·  done", "Wi-Fi and passwords  ·  done",
				"Social apps  ·  " + ("saved" if self.saved else "in progress"))):
			c.create_oval(34, 676 + i * 26, 44, 686 + i * 26, fill=AMBER if i == 2 and not self.saved else "#2f9e7a", outline="")
			c.create_text(54, 681 + i * 26, text=line, anchor="w", fill="#c9c6e6", font=(SANS, 12))

	# ---------------------------------------------------------------- actions
	def choose(self, question_id: str, option_id: str) -> None:
		if self.saved:
			return
		self.selected[question_id] = option_id
		self.events.append({"event": "select", "questionId": question_id, "optionId": option_id})
		self.render()

	def next(self) -> None:
		qid = QUESTIONS[self.step][0]
		if qid in self.selected:
			self.step = len(QUESTIONS) if len(self.selected) == len(QUESTIONS) else self.step + 1
			self.render()

	def back(self) -> None:
		if self.step > 0:
			self.step -= 1
			self.render()

	def goto(self, step: int) -> None:
		self.step = step
		self.render()

	def finish(self) -> None:
		if len(self.selected) != len(QUESTIONS) or self.saved:
			return
		self.events.append({"event": "submit"})
		answers = [
			{"questionId": question_id, "optionId": self.selected[question_id]}
			for question_id, _, _ in QUESTIONS
		]
		os.makedirs(OUTPUT_DIR, exist_ok=True)
		with open(os.path.join(OUTPUT_DIR, "social_setup.json"), "w", encoding="utf-8") as handle:
			json.dump(
				{"submitted": True, "answers": answers, "events": self.events},
				handle,
				ensure_ascii=False,
				indent=2,
			)
		self.saved = True
		self.render()


if __name__ == "__main__":
	window = tk.Tk()
	FreshStart(window)
	window.mainloop()
