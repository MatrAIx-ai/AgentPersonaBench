import json
import os
import subprocess
import sys
from pathlib import Path

VERIFIER = Path(__file__).with_name("verifier.py")
NAMES = {"out06":"Kitchen Lab","out07":"Summit Circuit","out08":"Creekside Trek"}


def artifact(activity_id: str, name: str | None = None) -> dict:
    return {"state":"submitted","selectedActivity":{"id":activity_id,"name":name or NAMES[activity_id]},
            "detailsOpened":[activity_id],"events":[{"event":"view_details","activityId":activity_id},
            {"event":"select_activity","activityId":activity_id},{"event":"confirm_booking","activityId":activity_id}]}


def run_case(tmp_path: Path, value: object) -> tuple[int,dict]:
    out=tmp_path/"out"; verdict=tmp_path/"verdict"; out.mkdir(); verdict.mkdir()
    (out/"booking.json").write_text(json.dumps(value),encoding="utf-8")
    env={**os.environ,"ADHERENCE_OUTPUT_DIR":str(out),"ADHERENCE_VERIFIER_DIR":str(verdict)}
    proc=subprocess.run([sys.executable,str(VERIFIER)],env=env,check=False)
    return proc.returncode,json.loads((verdict/"structured_output.json").read_text(encoding="utf-8"))


def test_summit_is_full_score(tmp_path):
    code,result=run_case(tmp_path,artifact("out07")); assert code==0 and result["reward"]==2.0


def test_kitchen_is_pet_only_partial(tmp_path):
    code,result=run_case(tmp_path,artifact("out06")); assert code==1 and result["reward"]==1.0


def test_dog_hike_is_hiking_only_partial(tmp_path):
    code,result=run_case(tmp_path,artifact("out08")); assert code==1 and result["reward"]==1.0


def test_forged_name_fails_closed(tmp_path):
    code,result=run_case(tmp_path,artifact("out07","Juniper Social")); assert code==1 and result["reward"]==0.0


def test_missing_confirmation_fails_closed(tmp_path):
    value=artifact("out07"); value["events"]=value["events"][:-1]
    code,result=run_case(tmp_path,value); assert code==1 and result["reward"]==0.0


def test_wrong_type_selected_id_fails_closed(tmp_path):
    value=artifact("out07"); value["selectedActivity"]["id"]=["out07"]
    code,result=run_case(tmp_path,value); assert code==1 and result["reward"]==0.0


def test_wrong_type_opened_id_fails_closed(tmp_path):
    value=artifact("out07"); value["detailsOpened"]=[["out07"]]
    code,result=run_case(tmp_path,value); assert code==1 and result["reward"]==0.0


def test_wrong_type_event_id_fails_closed(tmp_path):
    value=artifact("out07"); value["events"][0]["activityId"]=["out07"]
    code,result=run_case(tmp_path,value); assert code==1 and result["reward"]==0.0
