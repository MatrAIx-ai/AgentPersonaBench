# Design and scope

This task observes voluntary content selection, not a direct declaration of
interest or subject-matter knowledge. The six decisions concern a feature to
borrow, a session to reserve, a feature to request, an archive to explore,
an interview to hear, and a story to save. No option offers a price, duration,
accessibility, or competence advantage. Every subject appears once per item.

The unchanged complete persona is `hf-270713884`, copied from accepted source
`tasks/single-attribute/health-physical/color-vision/color-blind/color-blind-app/persona.yaml` at upstream `d72bd92e7b8d1cacd686268c84a601d0835d04e4`.
Its `topic_theater` value is Interested; the three competing subjects are
tea (Indifferent), volunteering (Indifferent), history (Indifferent).
This is a contextual ranking probe, not a calibration distinguishing Interested
from Passionate, and not proof that the target attribute alone causes choices.
The items share one topic preference and are not six independent latent traits.
The 5/6 threshold tolerates one plausible alternative; it is provisional.
With four choices per item, uniform independent random selection passes with
probability 19/4096 (0.464%). However, selecting one of the four topics uniformly
and sticking to it across all items passes with probability 1/4. The latter
captures the topic correlation; the smaller independent-choice number is not
an empirical blind baseline. Repeated persona-blind controls are essential.
Position, length and lexical shortcuts are tested.

The key is frozen under tests/ and unavailable to the solver. Behavioral
validation results belong in the PR, not in this source directory. The separate
full-persona contrast uses `matraix-dev-0147` with topic_theater =
Indifferent; its other traits differ, so this is not a causal
single-variable intervention.

Run the local tests with `python tests/test_fixtures.py -v` from this directory.
