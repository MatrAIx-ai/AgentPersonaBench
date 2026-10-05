# Knitting content choice — review revision

The missing-PyYAML path now writes an infrastructure error without a behavioral
verdict; the task name matches `interested-survey`. Questions, complete persona,
answer key and 5/6 rule are unchanged. Prior gpt-5-mini runs remain historical
alternate-model evidence, not a new configured-arm trial.

The full target also carries Avid quilting/embroidery and Curious knitting/crocheting.
A same-row counterfactual must change the `topic_knitting` value in BOTH its scratch
persona and check pin, and neutralize that textile cluster before rendering.
The previously tested different full persona does not isolate this cluster.
A fresh configured-arm target and appropriately rendered contrast are pending.

### Design and scope

This task observes voluntary content selection, not a direct declaration of
interest or subject-matter knowledge. The six decisions concern a feature to
borrow, a session to reserve, a feature to request, an archive to explore,
an interview to hear, and a story to save. No option offers a price, duration,
accessibility, or competence advantage. Every subject appears once per item.

The unchanged complete persona is `hf-4386921459`, copied from accepted source
`tasks/multi-attribute/archive-not-away/archive-not-away-app/persona.yaml` at upstream `d72bd92e7b8d1cacd686268c84a601d0835d04e4`.
Its `topic_knitting` value is Interested; the three competing subjects are
social_media (Indifferent), tv_series (Indifferent), history (Neutral).
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
full-persona contrast uses `matraix-dev-0147` with topic_knitting =
Indifferent; its other traits differ, so this is not a causal
single-variable intervention.

Run the local tests with `python tests/test_fixtures.py -v` from this directory.
