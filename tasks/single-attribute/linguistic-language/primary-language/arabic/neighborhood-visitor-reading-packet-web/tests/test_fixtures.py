"""Local verifier and shortcut tests; no API calls."""
import contextlib,importlib.util,io,json,os
from pathlib import Path
import tempfile,unittest
from unittest.mock import patch
HERE=Path(__file__).resolve().parent
spec=importlib.util.spec_from_file_location("survey_verifier",HERE/"verifier.py")
v=importlib.util.module_from_spec(spec);spec.loader.exec_module(v)
class Tests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.addCleanup(self.temp.cleanup)
        self.root=Path(self.temp.name);self.qs,self.structure,self.expected=v.task_data();self.perfect=dict(self.expected)
    def obj(self,picks=None):
        picks=self.perfect if picks is None else picks
        return {"answers":[{"questionId":q,"selectedOptionId":o} for q,o in picks.items()]}
    def run_case(self,obj=None,raw=None):
        path=self.root/"selection.json"
        if raw is not None:path.write_bytes(raw)
        elif obj is not None:path.write_text(json.dumps(obj),encoding="utf-8")
        dest=self.root/"verdict"
        with patch.dict(os.environ,{"ADHERENCE_OUTPUT_DIR":str(self.root),"ADHERENCE_VERIFIER_DIR":str(dest)}),contextlib.redirect_stdout(io.StringIO()),self.assertRaises(SystemExit) as cm:v.main()
        result=json.loads((dest/"structured_output.json").read_text(encoding="utf-8"))
        self.assertEqual(float((dest/"reward.txt").read_text(encoding="utf-8")),result["reward"])
        return cm.exception.code,result
    def wrong(self,q):return next(x for x in self.structure[q] if x!=self.expected[q])
    def test_perfect(self):
        code,r=self.run_case(self.obj());self.assertEqual((code,r["reward"],r["keyed_choices"]),(0,1,6))
    def test_five_of_six_boundary(self):
        p=dict(self.perfect);q=next(iter(p));p[q]=self.wrong(q)
        code,r=self.run_case(self.obj(p));self.assertEqual((code,r["reward"],r["keyed_choices"]),(0,1,5))
    def test_four_of_six_fails(self):
        p=dict(self.perfect)
        for q in list(p)[:2]:p[q]=self.wrong(q)
        code,r=self.run_case(self.obj(p));self.assertEqual((code,r["reward"],r["keyed_choices"]),(1,0,4))
    def test_fixed_position_shortcuts_fail(self):
        for pos in range(min(len(q["options"]) for q in self.qs)):
            p={q["id"]:q["options"][pos]["id"] for q in self.qs}
            with self.subTest(pos=pos):
                code,r=self.run_case(self.obj(p));self.assertEqual((code,r["reward"]),(1,0))
    def test_missing_and_malformed(self):
        for raw in [None,b"",b"not json",b"\xff",b"x"*256001,b'{"answers":[],"answers":[]}']:
            with self.subTest(raw=str(raw)[:30]):
                code,r=self.run_case() if raw is None else self.run_case(raw=raw)
                self.assertEqual((code,r["reward"]),(1,0))
    def test_bad_top_levels(self):
        for obj in [[],{},{"answers":"x"},{"answers":[],"extra":1}]:
            with self.subTest(obj=obj):
                code,r=self.run_case(obj);self.assertEqual((code,r["reward"]),(1,0))
    def test_bad_entries(self):
        q=list(self.perfect)[0]
        cases=[{"answers":[None]},{"answers":[{"questionId":q}]},{"answers":[{"questionId":q,"selectedOptionId":self.expected[q],"extra":1}]},{"answers":[{"questionId":[],"selectedOptionId":"x"}]},{"answers":[{"questionId":"unknown","selectedOptionId":"x"}]},{"answers":[{"questionId":q,"selectedOptionId":"unknown"}]}]
        for obj in cases:
            with self.subTest(obj=str(obj)):
                code,r=self.run_case(obj);self.assertEqual((code,r["reward"]),(1,0))
    def test_partial_duplicate_extra_and_cross_question(self):
        rows=self.obj()["answers"]
        variants=[{"answers":rows[:-1]},{"answers":rows+[rows[0]]},{"answers":rows+[{"questionId":"q7","selectedOptionId":"q7a"}]},{"answers":[{"questionId":rows[0]["questionId"],"selectedOptionId":rows[1]["selectedOptionId"]}]+rows[1:]}]
        for obj in variants:
            with self.subTest(kind=len(obj["answers"])):
                code,r=self.run_case(obj);self.assertEqual((code,r["reward"]),(1,0))
    def test_task_integrity_and_key_positions(self):
        self.assertEqual(len(self.qs),6)
        positions=[[o["id"] for o in q["options"]].index(self.expected[q["id"]]) for q in self.qs]
        self.assertGreaterEqual(len(set(positions)),4);self.assertLessEqual(max(positions.count(i) for i in set(positions)),2)

    def test_all_length_word_and_lexical_ranks(self):
        for measure in [lambda o:len(o['text']),lambda o:len(o['text'].split()),lambda o:o['text'].lower()]:
            for rank in range(4):
                picks={q['id']:sorted(q['options'],key=measure)[rank]['id'] for q in self.qs}
                code,r=self.run_case(self.obj(picks));self.assertEqual((code,r['reward']),(1,0))

if __name__=="__main__":unittest.main()
