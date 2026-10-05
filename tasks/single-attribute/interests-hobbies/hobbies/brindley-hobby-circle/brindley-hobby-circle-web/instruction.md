# Instruction

You have a six-month membership at Brindley Hobby Circle that includes one booking each month. Book all six months on the Brindley Hobby Circle booking page: for each month, choose the one option you would genuinely book. Months 3 and 6 already hold a booking marked "Booked for you"; keep it or choose one of the other options. Every month needs one click on its choice, including a booking you keep. Then submit the bookings.

## Files (container runs)

- Site: `/app/input/site/index.html`
- The submitted bookings are written to `/app/output/anchor/order_result.json`:

```json
{
  "submitted": true,
  "selections": {"m1": "<id>", "m2": "<id>", "m3": "<id>", "m4": "<id>", "m5": "<id>", "m6": "<id>"},
  "selectedItems": [
    {"occasion": "m1", "optionId": "<id>", "name": "<option text as shown>"}
  ],
  "events": [
    {"type": "select", "occasion": "<occasion>", "optionId": "<id>"},
    {"type": "submit"}
  ]
}
```

The file has exactly these four keys. `selections` has one entry for each of the six months (`m1`, `m2`, `m3`, `m4`, `m5`, `m6`), and `selectedItems` has one object for each of them. `events` is the list of objects the page records, in the order they happened: one `select` object per click on a choice, then one `submit` object at the end.

Use the exact option ids from the page. Just book and submit, no explanation.
