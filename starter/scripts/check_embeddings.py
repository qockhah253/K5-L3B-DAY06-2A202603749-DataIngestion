"""Kiem tra MyEmbedder: so chieu, thu tu, cosine hop ly, loi duoc bao ro. Khong in key."""
import math
import sys
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8")
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src.embeddings import EmbeddingError, MyEmbedder  # noqa: E402


def cos(a, b):
    return sum(x * y for x, y in zip(a, b)) / (
        math.sqrt(sum(x * x for x in a)) * math.sqrt(sum(y * y for y in b))
    )


emb = MyEmbedder()
docs = [
    "Dừng lại trước vạch dừng; nếu đã đi qua vạch dừng thì được đi tiếp.",
    "Giảm tốc độ, về số thấp, giữ đều ga khi qua đường ngập nước.",
    "Máy phát điện phát điện năng cung cấp cho các phụ tải và nạp ắc quy.",
]
q = "Gặp đèn vàng thì phải xử lý thế nào?"
dv = emb.embed_documents(docs)
qv = emb.embed_query(q)
print("model:", emb.model_name, "| dims:", emb.dimensions, "| so vector:", len(dv))
sims = [cos(qv, v) for v in dv]
for d, s in zip(docs, sims):
    print(f"  cos={s:.4f}  {d[:60]}")
print("gan nhat voi query:", sims.index(max(sims)) + 1, "(ky vong: 1)")
print("tokens:", emb.total_tokens, "| cost USD:", emb.total_cost, "| api_calls:", emb.api_calls)
try:
    emb.embed_query("   ")
except EmbeddingError as e:
    print("Van ban rong -> EmbeddingError:", e)
