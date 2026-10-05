# Instruction

Complete the four pending reviews in CodeHarbor. Open each ticket, inspect the
functionally equivalent implementation proposals, select the one you would
personally approve, and submit the review batch.

## Files (container runs)

- Site: `/app/input/site/index.html`
- Write the submitted page state to `/app/output/anchor/reviews.json`:

```json
{ "reviews": [{"ticketId": "<id>", "proposalId": "<id>"}] }
```

Use the exact ids from the page. Just complete the reviews; no explanation.
