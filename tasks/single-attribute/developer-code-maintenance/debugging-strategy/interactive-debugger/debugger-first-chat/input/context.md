# Batch Desk maintenance handoff

You and a colleague have set aside time to review three independent reports
before working on the code. Each report has a small local reproduction using
synthetic data. Both of you can read the Python source in your editor. Local
breakpoints with variable inspection, temporary print statements or trace probes,
and ordinary test runs are already available and take similar effort to start.
There is no production restriction, deadline, or cost difference between those
tools. You can also reason from the source and make a direct repair.

**Receipt adjustment:** A receipt combines a per-line discount with an order
coupon. A supplied example totals 2,000 cents, but applying the documented order
of adjustments gives 2,160 cents. The report does not establish which
intermediate amount is wrong. The relevant calculation has a line amount,
discounted amount, subtotal, and order adjustment.

**Group summary:** Rows sorted by group are summarized into one total per group.
The first group's total is correct; a later group's total includes extra value.
Each row has a group name and an amount. A running total and the current group
are updated as the loop crosses a group boundary. A reproduction contains three
groups so you can check more than one transition.

**Duplicate normalization:** A contact import counts two differently formatted
versions of the same address as separate entries. The intended rule trims
surrounding whitespace and compares without case differences. A loop forms a
normalized key and checks a collection of previously seen keys. The reproduction
also includes two genuinely distinct addresses.

Choose what you would do and what information would guide a repair for each
report. You have not yet run these reproductions or changed the code. Agree on
the work, including how you would check the result, before ending the handoff.
