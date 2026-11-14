"""Đọc và chuẩn hóa nguồn dữ liệu (PDF có text sẵn).

Chọn PyMuPDF thay pypdf: trên các trang chữ của bộ 600 câu (trang 5-70), pypdf làm vỡ
từ tiếng Việt (vd "phương ti ện", "đư ờng"), còn PyMuPDF thì không (xem docs/NOTES.md).
"""
import re
import unicodedata
from pathlib import Path

import pymupdf

from .models import DocumentPage

# Dòng đầu mỗi trang của file nguồn là số trang in trong sách (= trang PDF - 4).
_PRINTED_PAGE_RE = re.compile(r"^\s*(\d{1,3})\s*$")
_ZERO_WIDTH = dict.fromkeys(map(ord, "​‌‍﻿"), None)


def normalize_text(text: str) -> str:
    """Chuẩn hóa Unicode (NFC) và khoảng trắng, giữ ngắt dòng vì cấu trúc câu/phương án."""
    text = unicodedata.normalize("NFC", text).translate(_ZERO_WIDTH)
    text = text.replace(" ", " ").replace("\r\n", "\n").replace("\r", "\n")
    lines = [re.sub(r"[ \t]+", " ", ln).strip() for ln in text.split("\n")]
    text = "\n".join(lines)
    return re.sub(r"\n{3,}", "\n\n", text).strip()


def load_pdf(path: Path, document_id: str, source: str) -> list[DocumentPage]:
    """Trích từng trang vật lý, giữ số trang và nguồn; ghi cờ cho trang rỗng/ít chữ.

    page = số trang vật lý PDF (bắt đầu từ 1). Trang không có chữ vẫn được trả về
    (text rỗng, metadata['empty']=True) để log lỗi, không bị bỏ qua âm thầm.
    """
    pages: list[DocumentPage] = []
    with pymupdf.open(path) as doc:
        for i, pg in enumerate(doc, start=1):
            raw = pg.get_text("text")
            lines = raw.split("\n")
            printed = None
            if lines and (m := _PRINTED_PAGE_RE.match(lines[0])):
                printed = int(m.group(1))
                lines = lines[1:]  # bỏ số trang in khỏi nội dung
            text = normalize_text("\n".join(lines))
            pages.append(DocumentPage(
                document_id=document_id,
                source=source,
                page=i,
                text=text,
                metadata={
                    "printed_page": printed,
                    "chars": len(text),
                    "empty": len(text) == 0,
                    "has_images": bool(pg.get_images()),
                },
            ))
    return pages
