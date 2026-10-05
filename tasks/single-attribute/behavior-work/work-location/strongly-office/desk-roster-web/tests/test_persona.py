import hashlib
import json
from pathlib import Path
import yaml

TASK=Path(__file__).resolve().parents[1]
def values():return {k:v['value'] for k,v in yaml.safe_load((TASK/'persona.yaml').read_text())['attributes'].items()}

def test_complete_unchanged_published_profile():
    v=values();p=json.loads((TASK/'tests/persona_provenance.json').read_text())
    assert len(v)==p['populated_attribute_count']==1290
    assert hashlib.sha256(json.dumps(v,sort_keys=True,separators=(',',':'),ensure_ascii=False).encode()).hexdigest()==p['decoded_values_sha256']

def test_relevant_language_and_accessibility_fields_are_consistent():
    v=values();assert v['english_proficiency']==v['lang_english']=='Native'
    assert v['primary_language']=='English';assert v['health_vision']==v['health_hearing']=='Normal';assert v['accessibility_needs']=='None'

def test_construct_specific_profile_requirements():
    v=values();k=json.loads((TASK/'tests/answer_key.json').read_text())
    assert v[k['dimension_id']]==k['value']
    if k['dimension_id']=='bookg_travel_writing':
        assert all(v[d]=='Neutral' for d in ['bookg_mystery','bookg_history','bookg_poetry'])
        assert v['lstyle_reading_freq'] in ['Daily','Weekly']
    else:
        assert v['demo_employment_status']=='Full-time';assert v['lstyle_work_schedule']=='9-to-5';assert v['health_mobility']=='Full'
