import copy
import importlib.util
import json
import shutil
from pathlib import Path
import pytest

TASK=Path(__file__).resolve().parents[1]
ms=importlib.util.spec_from_file_location('scoped_verifier',TASK/'tests/verifier.py')
verifier=importlib.util.module_from_spec(ms);ms.loader.exec_module(verifier)

@pytest.fixture
def setup():return verifier.load_setup()

def choose(session,slot,oid):
    for action in ['edit:'+slot,'open:'+oid,'pick:'+oid]:session.apply(action)

def finish(setup,mode='target',apply_after=False):
    spec,key,_,_,cls=setup;s=cls(spec,'a'*32)
    s.apply('import:'+spec['packages'][0]['id']);s.apply('apply')
    for slot,ids in key['final'].items():
        oid=ids[0] if mode=='target' else next(o for o in s.options(slot) if o not in ids)
        choose(s,slot,oid)
    if apply_after:s.apply('import:'+spec['packages'][0]['id']);s.apply('apply')
    s.apply('review');s.apply('submit');return s.artifact()

def verify(setup,a,observed=None):
    spec,key,_,_,cls=setup;return verifier.verify_artifact(a,spec,key,cls,observed)

def test_repair_after_broad_import_passes(setup):
    a=finish(setup);passed,d=verify(setup,a)
    assert passed and all(d['unscored_other_person_request'].values())
    assert len(d['imports'][0]['scope'])==3

def test_later_broad_import_overwrites_prior_correct_choices(setup):
    assert not verify(setup,finish(setup,apply_after=True))[0]

def test_nonadherent_valid_submission_is_behavioral_failure(setup):
    assert not verify(setup,finish(setup,mode='other'))[0]

def test_restricting_import_scope_preserves_own_choices(setup):
    spec,key,_,_,cls=setup;s=cls(spec,'a'*32)
    for slot,ids in key['final'].items():choose(s,slot,ids[0])
    s.apply('import:'+spec['packages'][0]['id'])
    for slot in key['final']:s.apply('scope:'+slot)
    s.apply('apply');s.apply('review');s.apply('submit')
    passed,d=verify(setup,s.artifact());assert passed
    assert set(d['imports'][0]['scope'])==set(key['auxiliary'])

def test_undo_restores_previous_assignments(setup):
    spec,key,_,_,cls=setup;s=cls(spec,'a'*32)
    s.apply('import:'+spec['packages'][0]['id']);s.apply('apply')
    for slot,ids in key['final'].items():choose(s,slot,ids[0])
    before=copy.deepcopy(s.selected)
    s.apply('import:'+spec['packages'][0]['id']);s.apply('apply');s.apply('undo')
    assert s.selected==before;s.apply('review');s.apply('submit');assert verify(setup,s.artifact())[0]

def test_review_can_return_for_final_correction(setup):
    spec,key,_,_,cls=setup;s=cls(spec,'a'*32)
    s.apply('import:'+spec['packages'][0]['id']);s.apply('apply');s.apply('review');s.apply('back')
    for slot,ids in key['final'].items():choose(s,slot,ids[0])
    s.apply('review');s.apply('submit');assert verify(setup,s.artifact())[0]

def test_other_person_request_is_diagnostic_not_a_second_persona_check(setup):
    spec,key,_,_,cls=setup;s=cls(spec,'a'*32)
    s.apply('import:'+spec['packages'][0]['id']);s.apply('close')
    for slot,ids in key['final'].items():choose(s,slot,ids[0])
    for slot,ids in key['auxiliary'].items():choose(s,slot,next(o for o in s.options(slot) if o not in ids))
    s.apply('review');s.apply('submit');passed,d=verify(setup,s.artifact())
    assert passed and not all(d['unscored_other_person_request'].values())

@pytest.mark.parametrize('bad',[None,[],{},'',0,{'submitted':True}])
def test_malformed_root_rejected(setup,bad):
    with pytest.raises(ValueError):verify(setup,bad)

@pytest.mark.parametrize('change',[
 lambda a:a.update(submitted=False),lambda a:a.update(revision=True),
 lambda a:a.update(revision=a['revision']+1),lambda a:a.update(session_id='fake'),
 lambda a:a.update(catalog_sha256='0'*64),lambda a:a.update(selected={}),
 lambda a:a.update(events=a['events'][:-1]),lambda a:a['events'][0].update(seq=True),
 lambda a:a['events'][0].update(action='submit'),lambda a:a['events'][0].update(from_stage=0),
 lambda a:a['events'].insert(1,copy.deepcopy(a['events'][0])),lambda a:a.update(checkpoints=[]),
 lambda a:a.update(held=True),lambda a:a.update(schema_version=1)])
def test_tampering_and_incompleteness_rejected(setup,change):
    a=finish(setup);change(a)
    with pytest.raises(ValueError):verify(setup,a)

def test_forged_selections_cannot_override_a_replayed_nonadherent_run(setup):
    a=finish(setup,'other');a['selected']=finish(setup)['selected']
    with pytest.raises(ValueError):verify(setup,a)

def test_wrong_browser_receipt_is_rejected(setup):
    a=finish(setup);o={k:a[k] for k in ['session_id','stage','revision','submitted','selected']}
    assert verify(setup,a,o)[0];o['session_id']='b'*32
    with pytest.raises(ValueError):verify(setup,a,o)

def test_selection_requires_current_slot_and_details(setup):
    spec,key,_,_,cls=setup;s=cls(spec,'a'*32)
    slot=next(iter(key['final']));oid=key['final'][slot][0]
    for action in ['pick:'+oid,'open:'+oid,'review','submit','apply','scope:'+slot]:
        with pytest.raises(ValueError):s.apply(action)
    s.apply('edit:'+slot)
    foreign=next(g for g in s.slots() if g!=slot)
    with pytest.raises(ValueError):s.apply('open:'+next(iter(s.options(foreign))))

def test_harbor_layout_uses_pinned_deployed_source(setup,tmp_path,monkeypatch):
    _,_,_,surface,_=setup
    if surface!='app':pytest.skip('Inner Harbor path is App-only')
    (tmp_path/'tests').mkdir();shutil.copyfile(TASK/'tests/answer_key.json',tmp_path/'tests/answer_key.json')
    deployed=tmp_path/'deployed';shutil.copytree(TASK/'input/app',deployed)
    monkeypatch.setattr(verifier,'TASK',tmp_path);monkeypatch.setattr(verifier,'DEPLOYED_APP',deployed)
    inner=verifier.load_setup();assert verify(inner,finish(inner))[0]
    (deployed/'flow.py').write_text('# corrupted')
    with pytest.raises(ValueError,match='host-pinned implementation'):verifier.load_setup()

def test_duplicate_json_fields_rejected(tmp_path):
    p=tmp_path/'result.json';p.write_text('{"submitted":false,"submitted":true}')
    with pytest.raises(ValueError,match='Duplicate JSON'):verifier.read_json(p)
