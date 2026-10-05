"""Customer workflow state. Contains only visible catalog data, never score labels."""
from __future__ import annotations

import copy
import hashlib
import json
from pathlib import Path


class InvalidAction(ValueError):
    pass


class Session:
    def __init__(self, spec: dict, session_id: str):
        self.spec = copy.deepcopy(spec)
        self.session_id = session_id
        self.stage = 0
        self.selected = {}
        self.detail = None
        self.offer = None
        self.submitted = False
        self.events = []
        self.checkpoints = []
        self._enter()

    @property
    def current(self):
        return self.spec['stages'][self.stage]

    def _enter(self):
        self.detail = self.offer = None
        for group in self.current['groups']:
            valid = {o['id'] for o in group['options']}
            if self.selected.get(group['id']) not in valid:
                self.selected[group['id']] = group.get('default')

    def options(self):
        return {o['id']: (g['id'], o) for g in self.current['groups'] for o in g['options']}

    def complete(self):
        return all(self.selected.get(g['id']) in {o['id'] for o in g['options']}
                   for g in self.current['groups'])

    def _offers(self):
        return {o['id']: o for o in self.current.get('offers', [])}

    def actions(self):
        if self.submitted:
            return []
        if self.detail:
            return [{'id': 'pick:' + self.detail, 'label': 'Use this option'},
                    {'id': 'close', 'label': 'Back to choices'}]
        if self.offer:
            return [{'id': 'accept:' + self.offer, 'label': 'Apply this suggestion'},
                    {'id': 'close', 'label': 'Keep my current choices'}]
        result = [{'id': 'open:' + oid, 'label': 'Details · ' + option['title']}
                  for oid, (_, option) in self.options().items()]
        result += [{'id': 'offer:' + o['id'], 'label': o['button']}
                   for o in self.current.get('offers', [])]
        if self.complete():
            result.append({'id': 'submit' if self.stage == len(self.spec['stages']) - 1 else 'next',
                           'label': self.current['continue']})
        return result

    def apply(self, action: str):
        if not isinstance(action, str) or action not in {a['id'] for a in self.actions()}:
            raise InvalidAction('That control is not available on this screen.')
        before = self.stage
        if action.startswith('open:'):
            self.detail = action.partition(':')[2]
        elif action.startswith('pick:'):
            oid = action.partition(':')[2]
            group, _ = self.options()[oid]
            self.selected[group] = oid
            self.detail = None
        elif action.startswith('offer:'):
            self.offer = action.partition(':')[2]
        elif action.startswith('accept:'):
            proposal = self._offers()[self.offer]
            for group, oid in proposal['selections'].items():
                if oid not in self.options() or self.options()[oid][0] != group:
                    raise ValueError('Catalog proposal references an unavailable option.')
                self.selected[group] = oid
            self.offer = None
        elif action == 'close':
            self.detail = self.offer = None
        elif action in ('next', 'submit'):
            self.checkpoints.append({'stage': self.current['id'], 'selected': dict(self.selected)})
            if action == 'submit':
                self.submitted = True
            else:
                self.stage += 1
                self._enter()
        self.events.append({'seq': len(self.events) + 1, 'action': action,
                            'from_stage': before, 'to_stage': self.stage})

    def view(self):
        data = {'app': self.spec['app'], 'subtitle': self.spec['subtitle'],
                'stage_index': self.stage, 'stage_count': len(self.spec['stages']),
                'stage_id': self.current['id'], 'title': self.current['title'],
                'intro': self.current['intro'], 'notice': self.current.get('notice', ''),
                'groups': copy.deepcopy(self.current['groups']),
                'selected': dict(self.selected), 'actions': self.actions(),
                'submitted': self.submitted, 'detail': None, 'offer': None,
                'receipt': self.spec['receipt']}
        if self.detail:
            data['detail'] = copy.deepcopy(self.options()[self.detail][1])
        if self.offer:
            proposal = copy.deepcopy(self._offers()[self.offer])
            proposal['items'] = [self.options()[oid][1] for oid in proposal['selections'].values()]
            data['offer'] = proposal
        return data

    def artifact(self):
        return {'schema_version': 1, 'workflow': self.spec['workflow'],
                'session_id': self.session_id, 'submitted': self.submitted,
                'stage': self.current['id'], 'revision': len(self.events),
                'selected': dict(self.selected), 'checkpoints': copy.deepcopy(self.checkpoints),
                'events': copy.deepcopy(self.events),
                'catalog_sha256': hashlib.sha256(canonical(self.spec)).hexdigest()}


def canonical(obj):
    return json.dumps(obj, sort_keys=True, separators=(',', ':'), ensure_ascii=False).encode('utf-8')


def write_artifact(path: Path, artifact: dict):
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix('.tmp')
    temporary.write_text(json.dumps(artifact, indent=2, ensure_ascii=False), encoding='utf-8')
    temporary.replace(path)
