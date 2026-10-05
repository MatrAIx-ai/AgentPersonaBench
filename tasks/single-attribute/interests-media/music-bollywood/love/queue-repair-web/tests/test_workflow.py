import copy
import importlib.util
import json
import shutil
from pathlib import Path

import pytest

ROOT=Path(__file__).resolve().parent
module_spec=importlib.util.spec_from_file_location('workflow_verifier',ROOT/'verifier.py')
verifier=importlib.util.module_from_spec(module_spec)
module_spec.loader.exec_module(verifier)


@pytest.fixture
def setup():
    return verifier.load_setup()


def finish(setup, final='target', draft='target', accept_offer=False):
    spec,key,_,_,cls=setup
    session=cls(spec,'a'*32)
    for stage in range(len(spec['stages'])):
        desired=key['draft'] if stage==0 else key['final']
        mode=draft if stage==0 else final
        for group in session.current['groups']:
            allowed=desired[group['id']]
            candidates=[o['id'] for o in group['options'] if (o['id'] in allowed)==(mode=='target')]
            session.apply('open:'+candidates[0]);session.apply('pick:'+candidates[0])
        if stage==2 and accept_offer:
            offer=session.current['offers'][0]['id']
            session.apply('offer:'+offer);session.apply('accept:'+offer)
        session.apply('submit' if stage==2 else 'next')
    return session.artifact()


def verify(setup,artifact,observed=None):
    spec,key,_,_,cls=setup
    return verifier.verify_artifact(artifact,spec,key,cls,observed)


def test_adherent_flow_has_real_state_transitions(setup):
    artifact=finish(setup)
    assert verify(setup,artifact)[0]
    assert [x['stage'] for x in artifact['checkpoints']]==['draft','refresh','review']


def test_valid_nonadherent_output_is_behavioral_failure(setup):
    passed,detail=verify(setup,finish(setup,final='other'))
    assert not passed and not all(detail['final_by_slot'].values())


def test_final_correction_is_allowed(setup):
    passed,detail=verify(setup,finish(setup,draft='other'))
    assert passed and not all(detail['initial_by_slot'].values())


def test_accepting_final_suggestion_changes_actual_result(setup):
    passed,detail=verify(setup,finish(setup,accept_offer=True))
    assert not passed and all(detail['initial_by_slot'].values())


@pytest.mark.parametrize('bad',[None,[],{},'',0,{'submitted':True}])
def test_malformed_root_rejected(setup,bad):
    with pytest.raises(ValueError):verify(setup,bad)


@pytest.mark.parametrize('change',[
    lambda a:a.update(submitted=False),
    lambda a:a.update(revision=True),
    lambda a:a.update(revision=a['revision']+1),
    lambda a:a.update(session_id='fake-session'),
    lambda a:a.update(catalog_sha256='0'*64),
    lambda a:a.update(selected={}),
    lambda a:a.update(events=a['events'][:-1]),
    lambda a:a['events'][0].update(seq=True),
    lambda a:a['events'][0].update(action='submit'),
    lambda a:a['events'].insert(1,copy.deepcopy(a['events'][0])),
    lambda a:a.update(checkpoints=[]),
    lambda a:a.update(held=True),
])
def test_tampering_and_incomplete_results_rejected(setup,change):
    artifact=finish(setup);change(artifact)
    with pytest.raises(ValueError):verify(setup,artifact)


def test_forged_final_selection_cannot_override_nonadherent_history(setup):
    artifact=finish(setup,final='other')
    artifact['selected']=finish(setup)['selected']
    with pytest.raises(ValueError):verify(setup,artifact)


def test_browser_receipt_must_agree_with_app_state(setup):
    artifact=finish(setup)
    observed={k:artifact[k] for k in ['session_id','stage','revision','submitted','selected']}
    assert verify(setup,artifact,observed)[0]
    observed['session_id']='b'*32
    with pytest.raises(ValueError):verify(setup,artifact,observed)


def test_cannot_select_before_opening_details_or_select_stale_ids(setup):
    spec,key,_,_,cls=setup
    session=cls(spec,'a'*32)
    old_id=next(iter(key['draft'].values()))[0]
    with pytest.raises(ValueError):session.apply('pick:'+old_id)
    for group,ids in key['draft'].items():
        session.apply('open:'+ids[0]);session.apply('pick:'+ids[0])
    session.apply('next')
    with pytest.raises(ValueError):session.apply('open:'+old_id)


def test_harbor_layout_without_manifest_uses_pinned_deployed_app(setup,tmp_path,monkeypatch):
    spec,key,_,surface,cls=setup
    if surface!='app':pytest.skip('Only Apps have an inner Harbor verifier')
    original=verifier.TASK
    (tmp_path/'tests').mkdir()
    shutil.copyfile(original/'tests/answer_key.json',tmp_path/'tests/answer_key.json')
    deployed=tmp_path/'deployed-app'
    shutil.copytree(original/'input/app',deployed)
    monkeypatch.setattr(verifier,'TASK',tmp_path)
    monkeypatch.setattr(verifier,'DEPLOYED_APP',deployed)
    inner=verifier.load_setup()
    assert verify(inner,finish(inner))[0]
    (deployed/'flow.py').write_text('# corrupt state machine')
    with pytest.raises(ValueError,match='host-pinned implementation'):
        verifier.load_setup()


def test_duplicate_json_fields_are_not_silently_overwritten(tmp_path):
    path=tmp_path/'result.json'
    path.write_text('{"submitted":false,"submitted":true}')
    with pytest.raises(ValueError,match='Duplicate JSON'):
        verifier.read_json(path)
