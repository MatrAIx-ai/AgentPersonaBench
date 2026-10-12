#!/usr/bin/env python3
"""Exact chance and declared surface/convenience policies, not live agents."""
from __future__ import annotations
import json
import re
from itertools import product
from pathlib import Path
import yaml
HERE = Path(__file__).resolve().parent
questions = yaml.safe_load((HERE.parent / 'input/questionnaire.yaml').read_text(encoding='utf-8'))['questions']
key = json.loads((HERE / 'answer_key.json').read_text(encoding='utf-8'))
support = key['supportChoices']
facts = key['optionFacts']
def score(selected: dict[str, str]) -> int:
    return sum(oid in support[qid] for qid, oid in selected.items())
policies = {}
for position in range(4):
    policies[f'fixed_position_{position + 1}'] = {q['id']: q['options'][position]['id'] for q in questions}
for name, metric in (
    ('characters', lambda o: len(o['text'])),
    ('words', lambda o: len(re.findall(r'\b\w+\b', o['text']))),
    ('personal_fee', lambda o: facts[o['id']]['personal_fee_dollars']),
    ('waiting_or_handling', lambda o: facts[o['id']]['minutes']),
):
    for direction, select in (('minimum', min), ('maximum', max)):
        policies[f'{direction}_{name}_first_tie'] = {q['id']: select(q['options'], key=metric)['id'] for q in questions}
policies['free_then_no_equipment_then_shortest_wait'] = {
    q['id']: min(q['options'], key=lambda o: (facts[o['id']]['personal_fee_dollars'], facts[o['id']]['equipment'], facts[o['id']]['minutes']))['id'] for q in questions
}
scores = {name: score(selected) for name, selected in policies.items()}
assert len(scores) == 13
assert all(value < 6 for value in scores.values()), scores
assert [scores[f'fixed_position_{i}'] for i in range(1, 5)] == [3] * 4
uniform_total = uniform_held = 0
for positions in product(range(4), repeat=len(questions)):
    uniform_total += 1
    selected = {q['id']: q['options'][p]['id'] for q, p in zip(questions, positions)}
    uniform_held += score(selected) == 6
assert (uniform_held, uniform_total) == (64, 4096)
print(f'13 declared policies below 6/6: {scores}; exact chance {uniform_held}/{uniform_total}')
