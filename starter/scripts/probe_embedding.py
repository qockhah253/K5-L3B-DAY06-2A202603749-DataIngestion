"""Gọi thử OpenRouter embeddings: xác nhận key, đo số chiều, đọc usage. Không in key."""
import json
import os
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path

from dotenv import load_dotenv

sys.stdout.reconfigure(encoding="utf-8")
load_dotenv(Path(__file__).resolve().parent.parent / ".env")

key = os.getenv("OPENROUTER_API_KEY", "").strip()
model = os.getenv("EMBEDDING_MODEL", "").strip()
if not key or not model:
    sys.exit("Thiếu OPENROUTER_API_KEY hoặc EMBEDDING_MODEL trong .env")

texts = [
    "Khi gặp đèn tín hiệu màu vàng, người lái xe phải làm gì?",
    "Dừng lại trước vạch dừng; nếu đã đi qua vạch dừng thì được đi tiếp.",
]
req = urllib.request.Request(
    "https://openrouter.ai/api/v1/embeddings",
    data=json.dumps({"model": model, "input": texts, "encoding_format": "float"}).encode("utf-8"),
    headers={"Authorization": f"Bearer {key}", "Content-Type": "application/json"},
    method="POST",
)
t0 = time.time()
try:
    with urllib.request.urlopen(req, timeout=60) as r:
        body = json.loads(r.read().decode("utf-8"))
        status = r.status
except urllib.error.HTTPError as e:
    sys.exit(f"HTTP {e.code}: {e.read().decode('utf-8', 'replace')[:500]}")
except Exception as e:  # lỗi mạng: báo rõ, không giả lập vector
    sys.exit(f"Lỗi gọi API: {type(e).__name__}: {e}")

vecs = [d["embedding"] for d in body["data"]]
print("HTTP status      :", status)
print("model (yêu cầu)  :", model)
print("model (phản hồi) :", body.get("model"))
print("số vector        :", len(vecs))
print("số chiều         :", {len(v) for v in vecs})
print("usage            :", body.get("usage"))
print(f"thời gian        : {time.time() - t0:.2f}s")
