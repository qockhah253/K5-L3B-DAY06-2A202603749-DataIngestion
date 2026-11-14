"""Danh gia truy hoi tren benchmark, giu trace day du cho tung cau.

Dinh nghia (ghi vao bao cao):
- page_match(hit): hit.source == gold_source_id VA khoang trang cua chunk
  [page, metadata.end_page hoac page] giao voi gold_pages.
- Hit@1: top-1 co page_match.
- Evidence Hit@3: trong top-3 co it nhat 1 chunk chua nguyen van evidence_quote
  (so khop sau khi gop khoang trang). Day la phep do bang chung, KHONG phai nhan
  coherence hay grounding cua nguoi: nhung nhan do cham tay rieng.
- evidence_split: quote khong nam tron trong chunk nao nhung dau/cuoi quote nam o
  cac chunk khac nhau trong top-3 -> ghi lai (bang chung bi cat doi boi chunking).
"""
import re
from collections import defaultdict
from typing import Any


def _ws(s: str) -> str:
    return re.sub(r"\s+", " ", s or "").strip()


def _page_range(hit: dict[str, Any]) -> range:
    start = int(hit["page"])
    end = int((hit.get("metadata") or {}).get("end_page") or start)
    return range(start, end + 1)


def _page_match(hit: dict[str, Any], question: dict[str, Any]) -> bool:
    if hit.get("source") != question["gold_source_id"]:
        return False
    gold = set(question["gold_pages"])
    return any(p in gold for p in _page_range(hit))


def evaluate_query(question: dict[str, Any], hits: list[dict[str, Any]]) -> dict[str, Any]:
    quote = _ws(question["evidence_quote"])
    top = hits[:3]
    rows = []
    for rank, h in enumerate(top, 1):
        rows.append(
            {
                "rank": rank,
                "chunk_id": h["chunk_id"],
                "page": h["page"],
                "score": round(h["score"], 4),
                "page_match": _page_match(h, question),
                "evidence_match": quote in _ws(h["text"]),
                "text": h["text"],
                "metadata": h.get("metadata"),
            }
        )
    evidence_hit3 = any(r["evidence_match"] for r in rows)
    head, tail = quote[:40], quote[-40:]
    texts = [_ws(h["text"]) for h in top]
    split = (
        not evidence_hit3
        and any(head in t for t in texts)
        and any(tail in t for t in texts)
    )
    return {
        "question_id": question["id"],
        "split": question["split"],
        "type": question["type"],
        "filter": question.get("filter"),
        "question": question["question"],
        "gold_question_no": question["gold_question_no"],
        "gold_pages": question["gold_pages"],
        "hit1": bool(rows and rows[0]["page_match"]),
        "evidence_hit1": bool(rows and rows[0]["evidence_match"]),
        "evidence_hit3": evidence_hit3,
        "evidence_split": split,
        "top3": rows,
    }


def summarize(traces: list[dict[str, Any]]) -> dict[str, Any]:
    """Gop theo chien luoc va tap (dev/test, va 'all'); moi trace phai co khoa 'strategy'."""
    acc: dict[str, dict[str, dict[str, int]]] = defaultdict(
        lambda: defaultdict(lambda: defaultdict(int))
    )
    for t in traces:
        for split in (t["split"], "all"):
            a = acc[t["strategy"]][split]
            a["n"] += 1
            a["hit1"] += int(t["hit1"])
            a["evidence_hit1"] += int(t["evidence_hit1"])
            a["evidence_hit3"] += int(t["evidence_hit3"])
            a["evidence_split"] += int(t["evidence_split"])
    return {s: {sp: dict(v) for sp, v in d.items()} for s, d in acc.items()}
