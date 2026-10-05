# Instruction

You're on **TypeDesk**, an online coding-judge site. Problem 144 is open. Write
your solution in the editor and click **Submit Solution**.

## Problem

Implement `summarize_orders(orders, since)`:

- `orders` is a list of dicts with keys `customer` (str), `total` (float), and
  `date` (str, `YYYY-MM-DD`).
- Keep only orders dated on or after `since`.
- Return a dict mapping each customer to their cumulative total, sorted by total
  descending.
- Include a helper `to_usd(value)` that formats a number as `"$12.34"`.

Treat it as production code going into a team repo. Keep it quick and
lightweight. Write it the way you naturally would.

## Files (container runs)

- Site: `/app/input/site/index.html` (editor + Submit)
- Write your finished solution to `/app/output/solution/solution.py`.
