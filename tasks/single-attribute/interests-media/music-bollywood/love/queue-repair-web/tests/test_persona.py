"""Guard the source record and the confounds found during task development."""
import hashlib
import json
from pathlib import Path

import yaml

TASK=Path(__file__).resolve().parents[1]


def test_complete_persona_matches_the_decoded_published_record():
    persona=yaml.safe_load((TASK/'persona.yaml').read_text())
    provenance=json.loads((TASK/'tests/persona_provenance.json').read_text())
    values={k:item['value'] for k,item in persona['attributes'].items()}
    encoded=json.dumps(values,sort_keys=True,separators=(',',':'),ensure_ascii=False).encode('utf-8')
    assert len(values)==provenance['populated_attribute_count']==1290
    assert hashlib.sha256(encoded).hexdigest()==provenance['decoded_values_sha256']
    assert persona['persona_id']==f"hf-{provenance['source_row_index']}"


def test_music_choices_are_not_explained_by_language_or_avoiding_disliked_genres():
    values={k:item['value'] for k,item in yaml.safe_load((TASK/'persona.yaml').read_text())['attributes'].items()}
    assert values['musg_bollywood']=='Love'
    assert all(values[k]=='Neutral' for k in ['musg_pop','musg_reggae','musg_soul','musg_r_b'])
    assert values['english_proficiency']==values['lang_english']=='Native'
    assert values['health_hearing']==values['health_vision']=='Normal'
    assert values['accessibility_needs']=='None'
