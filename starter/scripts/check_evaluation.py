"""Kiem tra logic evaluation.py bang hit tu tay (khong goi API, khong lien quan vector)."""
import sys
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8")
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src.evaluation import evaluate_query, summarize  # noqa: E402

Q = {
    "id": "t1", "split": "dev", "type": "no_filter", "question": "?",
    "gold_source_id": "S", "gold_question_no": 40, "gold_pages": [12, 13],
    "evidence_quote": "Dừng lại trước vạch dừng; trường hợp đang đi trên vạch dừng",
}


def hit(cid, page, text, end=None):
    md = {"end_page": end} if end else {}
    return {"chunk_id": cid, "page": page, "source": "S", "text": text, "score": 0.5, "metadata": md}


# 1) top1 dung trang + chua quote (co xuong dong/khoang trang du)
r = evaluate_query(Q, [hit("a", 12, "Câu 40. ... Dừng lại trước vạch dừng;\ntrường hợp đang đi  trên vạch dừng ..."),
                       hit("b", 50, "x"), hit("c", 51, "y")])
print("1)", r["hit1"], r["evidence_hit1"], r["evidence_hit3"], r["evidence_split"], "(ky vong True True True False)")

# 2) top1 sai, dung o hang 3
r = evaluate_query(Q, [hit("a", 50, "x"), hit("b", 51, "y"),
                       hit("c", 12, "Dừng lại trước vạch dừng; trường hợp đang đi trên vạch dừng")])
print("2)", r["hit1"], r["evidence_hit3"], "(ky vong False True)")

# 3) trang dung nhung khong co quote (A cat giua cau) + bang chung bi cat doi
r = evaluate_query(Q, [hit("a", 12, "... Dừng lại trước vạch dừng; trường hợp"),
                       hit("b", 12, "đang đi trên vạch dừng ... ")])
print("3)", r["hit1"], r["evidence_hit3"], r["evidence_split"], "(ky vong True False False)")

# 4) chunk B nhieu trang: page=11 nhung end_page=12 -> van khop trang
r = evaluate_query(Q, [hit("a", 11, "z", end=12)])
print("4)", r["hit1"], "(ky vong True)")

# 5) tong hop
t = [dict(evaluate_query(Q, [hit("a", 12, Q["evidence_quote"])]), strategy="X"),
     dict(evaluate_query(Q, [hit("a", 50, "x")]), strategy="X")]
print("5)", summarize(t)["X"]["dev"], "(ky vong n=2 hit1=1 evidence_hit3=1)")
