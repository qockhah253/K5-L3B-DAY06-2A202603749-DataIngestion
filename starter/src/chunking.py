"""Chia chunk cho hai cách tiếp cận (cấu hình A và B/C).

A: cửa sổ ký tự cố định (kích thước, overlap) trên từng trang, KHÔNG biết cấu trúc.
B (và C): mỗi "câu hỏi" (câu + các phương án) là một chunk, theo cấu trúc của tài liệu.
"""
from .models import Chunk, DocumentPage
from .structure import Question


def fixed_size(page: DocumentPage, size: int, overlap: int) -> list[Chunk]:
    """Cửa sổ trượt `size` ký tự, gối `overlap` ký tự, trong phạm vi một trang.

    Cố ý cắt thẳng theo ký tự (không tôn trọng ranh giới từ/câu): đây là baseline.
    Chunk mang metadata nguồn + trang, không có chapter/question_no.
    """
    if not 0 <= overlap < size:
        raise ValueError("overlap phải >= 0 và < size")
    text, step, chunks = page.text, size - overlap, []
    for idx, start in enumerate(range(0, max(len(text), 1), step)):
        piece = text[start:start + size].strip()
        if not piece:
            continue
        chunks.append(Chunk(
            chunk_id=f"A:{page.document_id}:p{page.page:03d}:c{idx:03d}",
            document_id=page.document_id,
            source=page.source,
            page=page.page,
            text=piece,
            metadata={"char_start": start, "char_end": start + len(piece)},
        ))
        if start + size >= len(text):
            break
    return chunks


def by_question(questions: list[Question], document_id: str, source: str,
                max_size: int = 1200) -> list[Chunk]:
    """Mỗi câu hỏi là một chunk; metadata có chapter, question_no, trang đầu/cuối.

    max_size chỉ là chốt an toàn: câu dài nhất trong nguồn là 1011 ký tự nên thực tế không
    chunk nào bị cắt. Nếu có câu vượt ngưỡng thì báo lỗi, không cắt âm thầm.
    """
    chunks = []
    for q in questions:
        if len(q.text) > max_size:
            raise ValueError(f"Câu {q.number} dài {len(q.text)} > max_size={max_size}")
        chunks.append(Chunk(
            chunk_id=f"B:{document_id}:q{q.number:03d}",
            document_id=document_id,
            source=source,
            page=q.start_page,
            text=q.text,
            metadata={
                "chapter": q.chapter,
                "question_no": q.number,
                "end_page": q.end_page,
                "n_options": q.n_options,
                "mentions_figure": q.mentions_figure,
            },
        ))
    return chunks
