# night-owl-chat

`lstyle_sleep_schedule = Night owl` on the chat surface.

## Design note

Neither the instruction nor Priya's message mentions sleep, energy, or what time
of day anyone works best. We test *latent adherence*: a `Night owl` persona
should push back on the 7-8am options and steer toward later ones on its own,
giving reasons rooted in when it does good work. An `Early bird` persona should
take the 7:00am Tuesday happily. Because this is expressed preference rather than
surface keywords, an **LLM judge** reads the persona's own turns and returns a
binary verdict.

## Why the note lives here

`chat_harness.py` passes the whole of `input/context.md` to the persona sim as
`sut_desc`, so anything in that file reaches the agent. A design note naming the
anchor and contrast values would tell the agent what it is supposed to do and
destroy the latency of the measurement. It belongs in the task README instead.
