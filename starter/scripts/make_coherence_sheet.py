"""Tao bang cham thu cong coherence (GUIDE muc 2).

Vi tri nguon co dinh, chon TRUOC khi cham va khong phu thuoc diem so:
10 trang cach deu trong Chuong I-IV (trang PDF 6, 12, ..., 60), vi tri = ky tu giua trang.
Voi moi vi tri, lay chunk chua vi tri do o A va B. C dung chunk giong het B
(chi khac filter) nen nhan C = nhan B, ghi ro trong cot note.

Chay (tu starter/): python scripts/make_coherence_sheet.py
Ket qua: ../artifacts/manual_coherence.csv (UTF-8 BOM de mo bang Excel)
"""
import csv
import re
import sys
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8")
ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from src.chunking import by_question, fixed_size  # noqa: E402
from src.ingestion import load_pdf  # noqa: E402
from src.structure import split_questions  # noqa: E402

DOC, SRC = "csgt-600-cau-2025", "csgt-600-cau-2025.pdf"
POSITION_PAGES = [6, 12, 18, 24, 30, 36, 42, 48, 54, 60]
ws = lambda s: re.sub(r"\s+", " ", s).strip()  # noqa: E731

pages = [p for p in load_pdf(ROOT / "data" / "raw" / SRC, DOC, SRC) if p.page >= 5 and not p.metadata["empty"]]
by_page = {p.page: p for p in pages}
B = by_question(split_questions(pages), DOC, SRC)

rows = []
for i, pg in enumerate(POSITION_PAGES, 1):
    page = by_page[pg]
    off = len(page.text) // 2
    anchor = page.text[max(0, off - 15): off + 15]
    a = [c for c in fixed_size(page, 500, 50) if c.metadata["char_start"] <= off < c.metadata["char_end"]][0]
    # Cau chua vi tri: "Cau N." cuoi cung bat dau truoc vi tri tren trang nay;
    # neu khong co, vi tri thuoc cau bat dau tu trang truoc va keo sang trang nay.
    starts = [(m.start(), int(m.group(1))) for m in re.finditer(r"(?m)^Câu (\d{1,3})[.:]", page.text)]
    before = [n for s_, n in starts if s_ <= off]
    if before:
        qno = before[-1]
    else:
        qno = [c for c in B if c.page < pg <= c.metadata["end_page"]][0].metadata["question_no"]
    b = [c for c in B if c.metadata["question_no"] == qno][0]
    for strat, c, note in (("A", a, ""), ("B", b, ""), ("C", b, "chunk giong het B -> nhan C = nhan B")):
        rows.append({
            "position_id": f"P{i:02d}", "page": pg, "anchor": ws(anchor), "strategy": strat,
            "chunk_id": c.chunk_id, "chunk_text": c.text, "label_0_2": "", "reason": "", "note": note,
        })

out = ROOT.parent / "artifacts" / "manual_coherence.csv"
with out.open("w", encoding="utf-8-sig", newline="") as f:
    w = csv.DictWriter(f, fieldnames=list(rows[0]))
    w.writeheader()
    w.writerows(rows)
print(f"Da ghi {len(rows)} dong vao {out}")
