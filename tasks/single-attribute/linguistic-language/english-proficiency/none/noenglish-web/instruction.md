# Instruction

Put the order together for your new card terminal by adding **4 lines** you'd
genuinely buy from the Rowan add-ons page. Each need (setup, support, staff
training, which edition to run, change alerts) can be covered more than one way —
pick what you'd actually put on the order.

## Files (container runs)

- Site: `/app/input/site/index.html`
- Write your result to `/app/output/anchor/order.json`:

```json
{ "orderedItemIds": ["<id>", "<id>", "<id>", "<id>"] }
```

Use exact element ids from the page. Just build the order — no explanation.
