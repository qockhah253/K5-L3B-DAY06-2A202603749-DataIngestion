"""Trích đáp án đúng từ gạch chân trong PDF (lớp text không chứa dấu gạch chân).

Gạch chân là hình chữ nhật đen rất mỏng đặt sát đáy dòng chữ. Kết quả là đáp án THAM CHIẾU
do code đoán; người làm benchmark phải đối chiếu mắt với PDF cho mọi câu dùng làm gold.
"""
import re
import unicodedata
from pathlib import Path

import pymupdf

_Q_RE = re.compile(r"^Câu (\d{1,3})[.:]\s*\S")
_OPT_RE = re.compile(r"^(\d)\.\s")
_CHAPTER_RE = re.compile(r"^CHƯƠNG [IVX]+\.")


def _underlines(page) -> list[tuple[float, float, float]]:
    """(x0, x1, y0) của các hình chữ nhật đen mỏng (gạch chân)."""
    out = []
    for d in page.get_drawings():
        r = d["rect"]
        if d.get("fill") == (0.0, 0.0, 0.0) and r.height < 1.6 and r.width > 8:
            out.append((r.x0, r.x1, r.y0))
    return out


def _lines(page):
    """Các dòng chữ theo thứ tự đọc: (text, bbox)."""
    for b in page.get_text("dict")["blocks"]:
        for ln in b.get("lines", []):
            text = "".join(s["text"] for s in ln["spans"])
            text = unicodedata.normalize("NFC", text).replace(" ", " ").strip()
            if text:
                yield text, ln["bbox"]


def _is_underlined(bbox, unders) -> bool:
    x0, y0, x1, y1 = bbox
    for ux0, ux1, uy in unders:
        if y1 - 3.5 <= uy <= y1 + 2.0 and min(x1, ux1) - max(x0, ux0) >= 0.5 * (x1 - x0):
            return True
    return False


def extract_answer_key(pdf_path: Path, first_page: int = 5) -> dict[int, dict]:
    """{số câu: {'options': [số phương án gạch chân], 'notes': [...]}}"""
    key: dict[int, dict] = {}
    cur = None
    opt = None
    with pymupdf.open(pdf_path) as doc:
        for pno in range(first_page, len(doc) + 1):
            page = doc[pno - 1]
            unders = _underlines(page)
            for i, (text, bbox) in enumerate(_lines(page)):
                if i == 0 and re.fullmatch(r"\d{1,3}", text):
                    continue  # số trang in
                if _CHAPTER_RE.match(text):
                    cur = None
                    continue
                if m := _Q_RE.match(text):
                    cur = int(m.group(1))
                    key[cur] = {"options": [], "notes": []}
                    opt = None
                    continue
                if cur is None:
                    continue
                if m := _OPT_RE.match(text):
                    opt = int(m.group(1))
                if _is_underlined(bbox, unders):
                    if opt is None:
                        key[cur]["notes"].append("gạch chân ở phần đề, không phải phương án")
                    elif opt not in key[cur]["options"]:
                        key[cur]["options"].append(opt)
    return key
