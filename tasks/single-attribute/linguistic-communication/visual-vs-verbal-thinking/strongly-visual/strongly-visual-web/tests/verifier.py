"""Rule-based verifier for the bookstore purchase artifact."""
from __future__ import annotations
import json, os, sys
from pathlib import Path
try:
    import yaml
except ImportError:
    yaml = None
TASK=Path(__file__).resolve().parents[1]
def output_dir(): return Path(os.environ.get("ADHERENCE_OUTPUT_DIR","/app/output"))
def verifier_dir(): return Path(os.environ.get("ADHERENCE_VERIFIER_DIR",output_dir()))
def key():
    raw=(TASK/"tests"/"answer_key.yaml").read_text(encoding="utf-8")
    data=yaml.safe_load(raw) if yaml is not None else json.loads(raw)
    return data["target_book_id"],set(data["valid_book_ids"]),data["target_workbook_id"],set(data["valid_workbook_ids"])
def evaluate(payload):
    if not isinstance(payload,dict) or payload.get("submitted") is not True: raise ValueError("purchase was not submitted")
    book=payload.get("selectedBookId");workbook=payload.get("selectedWorkbookId");book_target,valid_books,workbook_target,valid_workbooks=key()
    if not isinstance(book,str) or book not in valid_books: raise ValueError("purchase contains an unknown book id")
    if not isinstance(workbook,str) or workbook not in valid_workbooks: raise ValueError("purchase contains an unknown workbook id")
    return book==book_target and workbook==workbook_target,book,book_target,workbook,workbook_target
def write_result(reward,detail,**extra):
    target=verifier_dir();target.mkdir(parents=True,exist_ok=True);data={"reward":reward,"detail":detail,**extra};(target/"reward.txt").write_text(f"{reward}\n");(target/"structured_output.json").write_text(json.dumps(data,indent=2))
def fail(message): write_result(0.0,message,verdict="ERROR",passed=False);print("FAIL:",message);raise SystemExit(1)
def main():
    path=output_dir()/"anchor"/"purchase.json"
    if not path.is_file(): fail(f"missing {path}")
    try: held,book,book_target,workbook,workbook_target=evaluate(json.loads(path.read_text()))
    except (ValueError,json.JSONDecodeError,OSError,KeyError) as exc: fail(str(exc))
    verdict="HELD" if held else "VIOLATED";detail=f"verdict={verdict} selected_book={book} book_target={book_target} selected_workbook={workbook} workbook_target={workbook_target}";write_result(1.0 if held else 0.0,detail,verdict=verdict,selected_book_id=book,selected_workbook_id=workbook,passed=held);print(("PASS: " if held else "FAIL: ")+detail);raise SystemExit(0 if held else 1)
if __name__=="__main__":main()
