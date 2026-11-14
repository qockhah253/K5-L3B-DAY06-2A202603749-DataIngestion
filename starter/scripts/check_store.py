"""Kiem tra PgVectorStore voi embedding that (chien luoc tam 'TEST', xoa sau khi xong)."""
import os
import sys
from pathlib import Path

from dotenv import load_dotenv

sys.stdout.reconfigure(encoding="utf-8")
ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
load_dotenv(ROOT / ".env")

from src.embeddings import MyEmbedder  # noqa: E402
from src.models import Chunk  # noqa: E402
from src.store import PgVectorStore  # noqa: E402

emb = MyEmbedder()
store = PgVectorStore(os.environ["DATABASE_URL"], emb.dimensions)
store.create_schema()
store.create_schema()  # chay lai khong loi
S = "TEST"
store.delete_strategy(S)

texts = [
    ("Câu 40. Đèn vàng: dừng lại trước vạch dừng.", "I"),
    ("Câu 246. Khi lùi xe phải quan sát phía sau, lùi với tốc độ phù hợp.", "III"),
    ("Câu 85. Khi lùi xe phải quan sát hai bên và phía sau xe, có tín hiệu lùi.", "I"),
]
chunks = [
    Chunk(f"T:q{i}", "doc", "src", 10 + i, t, {"chapter": ch}) for i, (t, ch) in enumerate(texts)
]
vecs = emb.embed_documents([c.text for c in chunks])
q = emb.embed_query("Khi lùi xe thì phải làm gì?")

store.upsert(S, chunks, vecs)
store.upsert(S, chunks, vecs)
print("1) upsert 2 lan, so dong:", store.count(S), "(ky vong 3)")

hits = store.search(S, q, top_k=3)
print("2) khong filter:", [(h["chunk_id"], round(h["score"], 3)) for h in hits])
hits = store.search(S, q, top_k=3, filters={"chapter": "III"})
print("3) filter chapter=III:", [h["chunk_id"] for h in hits], "(ky vong ['T:q1'])")

try:
    store.search(S, q, filters={"text; DROP TABLE chunks": "x"})
except ValueError as e:
    print("4) khoa filter la -> ValueError:", e)
try:
    store.upsert(S, chunks[:1], [[0.0] * 10])
except ValueError as e:
    print("5) sai so chieu -> ValueError:", e)

store.upsert(S, chunks[:2], vecs[:2])
print("6) ingest lai chi 2 chunk, so dong:", store.count(S), "(ky vong 2, chunk cu bi xoa)")
store.delete_strategy(S)
print("7) don dep, so dong:", store.count(S), "(ky vong 0)")
