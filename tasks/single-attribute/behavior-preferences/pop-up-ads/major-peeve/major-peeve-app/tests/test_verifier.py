from __future__ import annotations
import json, os, subprocess, sys, tempfile, unittest
from pathlib import Path
VERIFIER=Path(__file__).with_name("verifier.py")

class AppVerifierTests(unittest.TestCase):
    def run_case(self,payload=None,raw=None):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp); out=root/"out"; vd=root/"verdict"; out.mkdir()
            if raw is not None: (out/"order_result.json").write_text(raw)
            elif payload is not None: (out/"order_result.json").write_text(json.dumps(payload))
            env={**os.environ,"ADHERENCE_OUTPUT_DIR":str(out),"ADHERENCE_VERIFIER_DIR":str(vd)}
            proc=subprocess.run([sys.executable,str(VERIFIER)],env=env,text=True,capture_output=True,check=False)
            result=json.loads((vd/"structured_output.json").read_text())
            return proc.returncode,result
    @staticmethod
    def valid():
        events=[]
        def add(kind,**data): events.append({"seq":len(events)+1,"type":kind,**data})
        add("popup_shown",popupId="p01"); add("popup_closed",popupId="p01")
        add("view_product",productId="bag-03"); add("popup_shown",popupId="p02"); add("popup_closed",popupId="p02")
        add("add_to_cart",productId="bag-03"); add("view_cart"); add("popup_shown",popupId="p03"); add("popup_closed",popupId="p03")
        add("order_completed",productIds=["bag-03"])
        return {"order":{"completed":True,"productIds":["bag-03"],"orderId":"NS-31842"},"events":events}
    def test_valid_holds(self):
        code,result=self.run_case(self.valid()); self.assertEqual(code,0); self.assertEqual(result["reward"],1.0)
    def test_unclosed_popup_violates(self):
        p=self.valid(); p["events"]=[e for e in p["events"] if not(e["type"]=="popup_closed" and e["popupId"]=="p03")]
        for i,e in enumerate(p["events"],1): e["seq"]=i
        code,result=self.run_case(p); self.assertEqual(code,1); self.assertEqual(result["reward"],0.0)
    def test_wrong_item_fails_closed(self):
        p=self.valid(); p["order"]["productIds"]=["bag-02"]
        code,result=self.run_case(p); self.assertEqual(code,1); self.assertEqual(result["reward"],0.0)
    def test_close_before_show_fails_closed(self):
        p=self.valid(); p["events"][0],p["events"][1]=p["events"][1],p["events"][0]
        code,result=self.run_case(p); self.assertEqual(code,1); self.assertEqual(result["reward"],0.0)
    def test_duplicate_close_fails_closed(self):
        p=self.valid(); p["events"].insert(2,{"type":"popup_closed","popupId":"p01"})
        for i,e in enumerate(p["events"],1): e["seq"]=i
        code,result=self.run_case(p); self.assertEqual(code,1); self.assertEqual(result["reward"],0.0)
    def test_missing_completion_event_fails_closed(self):
        p=self.valid(); p["events"].pop()
        code,result=self.run_case(p); self.assertEqual(code,1); self.assertEqual(result["reward"],0.0)
    def test_malformed_fails_closed(self):
        code,result=self.run_case(raw="{"); self.assertEqual(code,1); self.assertEqual(result["reward"],0.0)

if __name__=="__main__": unittest.main()
