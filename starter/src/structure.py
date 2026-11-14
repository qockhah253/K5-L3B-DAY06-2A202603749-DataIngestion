"""Tách văn bản thành các "câu hỏi" (đơn vị cấu trúc tự nhiên của bộ 600 câu)."""
import re
from dataclasses import dataclass

from .models import DocumentPage

# Khoảng số câu của từng chương, theo Lời nói đầu của tài liệu nguồn.
CHAPTER_RANGES = {
    "I": (1, 180), "II": (181, 205), "III": (206, 263),
    "IV": (264, 300), "V": (301, 485), "VI": (486, 600),
}
# Nguồn có lỗi trình bày: "Câu 507:" (dấu hai chấm), "Câu 512.Theo" (thiếu dấu cách).
_Q_RE = re.compile(r"^Câu (\d{1,3})[.:]\s*\S")
_CHAPTER_RE = re.compile(r"^CHƯƠNG ([IVX]+)\.")
_OPTION_RE = re.compile(r"^(\d)\.\s")
_INLINE_OPTION_RE = re.compile(r"\b[1-4]\. [A-ZĐÀ-Ỹ]")  # phương án nằm chung một dòng (vd câu 352)
_FIGURE_RE = re.compile(r"(?i)\b(hình|sa hình|biển|sơ đồ)\b")


@dataclass
class Question:
    number: int
    chapter: str
    start_page: int
    end_page: int
    text: str
    n_options: int
    mentions_figure: bool  # heuristic: nhắc hình/biển/sơ đồ trong chữ


def chapter_of(number: int) -> str:
    for name, (a, b) in CHAPTER_RANGES.items():
        if a <= number <= b:
            return name
    raise ValueError(f"Số câu ngoài khoảng 1-600: {number}")


def split_questions(pages: list[DocumentPage], first_content_page: int = 5) -> list[Question]:
    """Cắt theo mốc 'Câu N.'; một câu có thể kéo qua trang. Bỏ dòng tiêu đề chương."""
    cur: dict | None = None
    out: list[Question] = []
    skipping_heading = False

    def flush():
        nonlocal cur
        if cur:
            body = "\n".join(cur["lines"]).strip()
            opts = sum(1 for ln in cur["lines"] if _OPTION_RE.match(ln))
            if opts < 2:  # thử đếm phương án viết chung một dòng
                opts = len(_INLINE_OPTION_RE.findall("\n".join(cur["lines"][1:])))
            out.append(Question(cur["n"], chapter_of(cur["n"]), cur["p0"], cur["p1"], body,
                                opts, bool(_FIGURE_RE.search(body))))
        cur = None

    for pg in pages:
        if pg.page < first_content_page:
            continue
        for ln in pg.text.split("\n"):
            if _CHAPTER_RE.match(ln):  # tiêu đề chương (có thể xuống dòng): bỏ tới câu kế tiếp
                skipping_heading = True
                continue
            m = _Q_RE.match(ln)
            if m:
                skipping_heading = False
                flush()
                cur = {"n": int(m.group(1)), "p0": pg.page, "p1": pg.page, "lines": [ln]}
            elif skipping_heading:
                continue
            elif cur is not None:
                cur["lines"].append(ln)
                cur["p1"] = pg.page
    flush()
    return out


def validate(questions: list[Question]) -> list[str]:
    """Trả về danh sách vấn đề; rỗng nghĩa là cấu trúc khớp với Lời nói đầu."""
    issues = []
    nums = [q.number for q in questions]
    if nums != list(range(1, 601)):
        missing = sorted(set(range(1, 601)) - set(nums))
        dup = sorted({n for n in nums if nums.count(n) > 1})
        issues.append(f"Số câu không liên tục 1..600: thiếu={missing[:10]} trùng={dup[:10]} tổng={len(nums)}")
    for name, (a, b) in CHAPTER_RANGES.items():
        got = sum(1 for q in questions if q.chapter == name)
        if got != b - a + 1:
            issues.append(f"Chương {name}: có {got}, kỳ vọng {b - a + 1}")
    few = [q.number for q in questions if q.n_options < 2]
    if few:
        issues.append(f"Câu có <2 phương án (cần kiểm tra tay): {few[:20]}")
    return issues
