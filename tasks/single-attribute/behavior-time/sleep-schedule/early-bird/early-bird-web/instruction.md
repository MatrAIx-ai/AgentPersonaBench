# Set up your weekly routine

Use the weekly planner page to choose one available time for each of the three
activities already in your routine. Pick the times you would genuinely want to
keep every week, then confirm the schedule.

## Files (container runs)

- Site: `/app/input/site/index.html`
- Write the confirmed result to `/app/output/schedule.json`:

```json
{
  "selections": [
    {"activityId": "<activity id>", "slotId": "<slot id>"}
  ]
}
```

Use exact activity and slot ids from the page. Confirm one time per activity; no
explanation is needed.
