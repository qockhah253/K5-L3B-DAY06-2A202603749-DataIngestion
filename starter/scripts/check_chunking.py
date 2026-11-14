"""Thống kê chunk A và B: python scripts/check_chunking.py (chạy từ thư mục starter/)"""
import statistics as st
import sys
from collections import Counter
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8")
ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from src.chunking import by_question, fixed_size  # noqa: E402
from src.ingestion import load_pdf  # noqa: E402
from src.structure import split_questions  # noqa: E402

DOC, SRC = "csgt-600-cau-2025", "csgt-600-cau-2025.pdf"
pages = [p for p in load_pdf(ROOT / "data" / "raw" / SRC, DOC, SRC) if p.page >= 5 and not p.metadata["empty"]]
A = [c for p in pages for c in fixed_size(p, 500, 50)]
B = by_question(split_questions(pages), DOC, SRC)


def stats(name, ch):
    L = [len(c.text) for c in ch]
    print(f"{name}: {len(ch)} chunk | tổng {sum(L)} ký tự | độ dài min {min(L)} / trung vị {int(st.median(L))} / max {max(L)}")


stats("A (cố định 500, overlap 50)", A)
stats("B (theo câu)", B)
print("B theo chương:", dict(Counter(c.metadata["chapter"] for c in B)))
print("ID A bị trùng:", len(A) - len({c.chunk_id for c in A}), "| ID B bị trùng:", len(B) - len({c.chunk_id for c in B}))
nq = sum(1 for c in A if c.text.lstrip()[:4] != "Câu ")
print(f"A: {nq}/{len(A)} chunk KHÔNG mở đầu bằng 'Câu N.' (cắt giữa câu)")
print("\n--- ví dụ chunk A (trang 8) ---")
for c in [c for c in A if c.page == 8][:2]:
    print(f"[{c.chunk_id}]\n{c.text}\n")
print("--- ví dụ chunk B (câu 22) ---")
c = B[21]; print(f"[{c.chunk_id}] trang {c.page}-{c.metadata['end_page']} chương {c.metadata['chapter']}\n{c.text}")
