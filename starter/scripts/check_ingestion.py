"""Kiểm tra bước đọc PDF + tách câu: chạy từ thư mục starter/ -> python scripts/check_ingestion.py"""
import statistics as st
import sys
from collections import Counter
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8")
ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from src.ingestion import load_pdf  # noqa: E402
from src.structure import split_questions, validate  # noqa: E402

pdf = ROOT / "data" / "raw" / "csgt-600-cau-2025.pdf"
pages = load_pdf(pdf, "csgt-600-cau-2025", pdf.name)
print("số trang:", len(pages), "| trang rỗng:", [p.page for p in pages if p.metadata["empty"]])
qs = split_questions(pages)
print("số câu:", len(qs))
print("vấn đề cấu trúc:", validate(qs) or "KHÔNG CÓ")
print("câu theo chương:", dict(Counter(q.chapter for q in qs)))
print("câu kéo qua 2 trang:", sum(1 for q in qs if q.end_page > q.start_page))
lens = [len(q.text) for q in qs]
print(f"độ dài câu (ký tự): min {min(lens)} | trung vị {int(st.median(lens))} | max {max(lens)}")
for n in (22, 507, 512, 352):
    q = qs[n - 1]
    print(f"\n--- câu {q.number} | chương {q.chapter} | trang {q.start_page}-{q.end_page} | {q.n_options} phương án")
    print(q.text)
