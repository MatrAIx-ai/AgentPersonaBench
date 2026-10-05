"""A scoped shared-draft editor. All data here is ordinary customer-facing state."""
from __future__ import annotations
import copy
import hashlib
import json
from pathlib import Path

class InvalidAction(ValueError):
    pass

def canonical(value):
    return json.dumps(value,sort_keys=True,separators=(',',':'),ensure_ascii=False).encode('utf-8')

def write_artifact(path: Path, artifact: dict):
    path.parent.mkdir(parents=True,exist_ok=True)
    temporary=path.with_suffix('.tmp')
    temporary.write_text(json.dumps(artifact,indent=2,ensure_ascii=False))
    temporary.replace(path)

class Session:
    def __init__(self,spec,session_id):
        self.spec=copy.deepcopy(spec);self.session_id=session_id
        self.stage='board';self.active=None;self.detail=None;self.package=None
        self.scope=[];self.reviewed=[];self.selected={g['id']:g.get('default') for g in self.spec['slots']}
        self.submitted=False;self.events=[];self.checkpoints=[];self.undo_state=None

    def slots(self):return {g['id']:g for g in self.spec['slots']}
    def options(self,slot):return {o['id']:o for o in self.slots()[slot]['options']}
    def packages(self):return {p['id']:p for p in self.spec['packages']}
    def complete(self):return all(self.selected[g] in self.options(g) for g in self.slots())
    def _remember(self):self.undo_state=copy.deepcopy(self.selected)

    def actions(self):
        if self.submitted:return []
        if self.stage=='review':return [{'id':'back','label':'Back to editing'},{'id':'submit','label':self.spec['submit']}]
        if self.package:
            p=self.packages()[self.package]
            result=[{'id':'scope:'+g,'label':('Exclude · ' if g in self.scope else 'Include · ')+self.slots()[g]['title']} for g in p['selections']]
            if self.scope:result.append({'id':'apply','label':f'Apply to {len(self.scope)} selected entries'})
            return result+[{'id':'close','label':'Close without applying'}]
        if self.detail:
            return [{'id':'pick:'+self.detail,'label':'Choose for '+self.slots()[self.active]['title']},{'id':'close','label':'Back to options'}]
        if self.active:
            return [{'id':'open:'+o,'label':'Details · '+v['title']} for o,v in self.options(self.active).items()]+[{'id':'close','label':'Back to draft'}]
        result=[{'id':'edit:'+g,'label':'Edit · '+v['title']} for g,v in self.slots().items()]
        result += [{'id':'import:'+p,'label':v['button']} for p,v in self.packages().items()]
        if self.undo_state is not None:result.append({'id':'undo','label':'Undo last selection change'})
        if self.complete() and set(self.reviewed)==set(self.packages()):result.append({'id':'review','label':'Review complete draft'})
        return result

    def apply(self,action):
        if not isinstance(action,str) or action not in {a['id'] for a in self.actions()}:
            raise InvalidAction('That control is not available on this screen.')
        before=self.stage
        if action.startswith('edit:'):self.active=action.partition(':')[2]
        elif action.startswith('open:'):self.detail=action.partition(':')[2]
        elif action.startswith('pick:'):
            self._remember();self.selected[self.active]=self.detail;self.active=self.detail=None
        elif action.startswith('import:'):
            self.package=action.partition(':')[2];self.scope=list(self.packages()[self.package]['selections'])
            if self.package not in self.reviewed:self.reviewed.append(self.package)
        elif action.startswith('scope:'):
            slot=action.partition(':')[2]
            if slot in self.scope:self.scope.remove(slot)
            else:self.scope.append(slot)
            self.scope=[g for g in self.slots() if g in self.scope]
        elif action=='apply':
            self._remember()
            proposal=self.packages()[self.package]['selections']
            for slot in self.scope:
                if proposal[slot] not in self.options(slot):raise InvalidAction('An imported choice is unavailable.')
                self.selected[slot]=proposal[slot]
            self.checkpoints.append({'kind':'import','package':self.package,'scope':list(self.scope),'selected':copy.deepcopy(self.selected)})
            self.package=None;self.scope=[]
        elif action=='close':
            if self.package:self.package=None;self.scope=[]
            elif self.detail:self.detail=None
            else:self.active=None
        elif action=='undo':self.selected=self.undo_state;self.undo_state=None
        elif action=='review':
            self.checkpoints.append({'kind':'review','selected':copy.deepcopy(self.selected)});self.stage='review'
        elif action=='back':self.stage='board'
        elif action=='submit':self.submitted=True;self.stage='confirmed'
        self.events.append({'seq':len(self.events)+1,'action':action,'from_stage':before,'to_stage':self.stage})

    def view(self):
        view={'app':self.spec['app'],'subtitle':self.spec['subtitle'],'title':self.spec['title'],
              'intro':self.spec['intro'],'notice':self.spec['notice'],'receipt':self.spec['receipt'],
              'groups':copy.deepcopy(self.spec['slots']),'stage_id':self.stage,'submitted':self.submitted,
              'selected':dict(self.selected),'active':self.active,'detail':None,'package':None,
              'scope':list(self.scope),'reviewed':list(self.reviewed),'actions':self.actions()}
        if self.detail:view['detail']=copy.deepcopy(self.options(self.active)[self.detail])
        if self.package:view['package']=copy.deepcopy(self.packages()[self.package])
        return view

    def artifact(self):
        return {'schema_version':2,'workflow':self.spec['workflow'],'session_id':self.session_id,
                'submitted':self.submitted,'stage':self.stage,'revision':len(self.events),
                'selected':copy.deepcopy(self.selected),'checkpoints':copy.deepcopy(self.checkpoints),
                'events':copy.deepcopy(self.events),'catalog_sha256':hashlib.sha256(canonical(self.spec)).hexdigest()}
