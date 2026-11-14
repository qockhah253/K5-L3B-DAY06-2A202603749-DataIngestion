"""Embedding adapter: OpenRouter /embeddings (mac dinh baai/bge-m3, 1024 chieu).

Nguyen tac (RULES.md): khong vector gia, khong fallback am tham.
Moi loi mang/HTTP/dinh dang -> raise EmbeddingError de pipeline dung lai.
"""
import json
import os
import time
import urllib.error
import urllib.request
from pathlib import Path
from typing import Protocol

from dotenv import load_dotenv

load_dotenv(Path(__file__).resolve().parent.parent / ".env")

ENDPOINT = "https://openrouter.ai/api/v1/embeddings"
BATCH_SIZE = 32
MAX_RETRIES = 4  # chi retry loi tam thoi (429/5xx/mang)


class EmbeddingError(RuntimeError):
    """Loi goi embedding: khong duoc nuot, khong duoc thay bang vector khac."""


class Embedder(Protocol):
    model_name: str
    dimensions: int

    def embed_documents(self, texts: list[str]) -> list[list[float]]:
        """Return one vector per input text, in the same order."""
        ...

    def embed_query(self, question: str) -> list[float]:
        """Return a query vector compatible with the stored document vectors."""
        ...


class MyEmbedder:
    """OpenRouter embeddings. bge-m3 khong can tien to query/passage."""

    def __init__(self, model_name: str | None = None, dimensions: int = 1024) -> None:
        self.model_name = (model_name or os.getenv("EMBEDDING_MODEL", "")).strip()
        self._key = os.getenv("OPENROUTER_API_KEY", "").strip()
        if not self.model_name:
            raise EmbeddingError("Thieu EMBEDDING_MODEL trong .env")
        if not self._key:
            raise EmbeddingError("Thieu OPENROUTER_API_KEY trong .env")
        self.dimensions = dimensions
        self.total_tokens = 0  # cong don tu usage cua API
        self.total_cost = 0.0  # USD, neu API tra ve usage.cost
        self.api_calls = 0

    # ---- goi API ----
    def _post(self, texts: list[str]) -> dict:
        payload = json.dumps(
            {"model": self.model_name, "input": texts, "encoding_format": "float"}
        ).encode("utf-8")
        last_err: Exception | None = None
        for attempt in range(MAX_RETRIES + 1):
            req = urllib.request.Request(
                ENDPOINT,
                data=payload,
                headers={
                    "Authorization": f"Bearer {self._key}",
                    "Content-Type": "application/json",
                },
                method="POST",
            )
            try:
                with urllib.request.urlopen(req, timeout=60) as r:
                    return json.loads(r.read().decode("utf-8"))
            except urllib.error.HTTPError as e:
                body = e.read().decode("utf-8", "replace")[:300]
                if e.code in (429, 500, 502, 503, 504) and attempt < MAX_RETRIES:
                    last_err = EmbeddingError(f"HTTP {e.code}: {body}")
                    time.sleep(2**attempt)
                    continue
                raise EmbeddingError(f"HTTP {e.code}: {body}") from e
            except (urllib.error.URLError, TimeoutError) as e:
                last_err = e
                if attempt < MAX_RETRIES:
                    time.sleep(2**attempt)
                    continue
                raise EmbeddingError(f"Loi mang: {type(e).__name__}: {e}") from e
        raise EmbeddingError(f"Het so lan thu lai: {last_err}")

    def _embed_batch(self, texts: list[str]) -> list[list[float]]:
        body = self._post(texts)
        data = body.get("data")
        if not data or len(data) != len(texts):
            raise EmbeddingError(
                f"So vector tra ve ({len(data or [])}) khac so van ban ({len(texts)})"
            )
        data = sorted(data, key=lambda d: d.get("index", 0))
        vecs = [d["embedding"] for d in data]
        for v in vecs:
            if len(v) != self.dimensions:
                raise EmbeddingError(f"Sai so chieu: {len(v)} != {self.dimensions}")
        usage = body.get("usage") or {}
        self.total_tokens += int(usage.get("total_tokens") or usage.get("prompt_tokens") or 0)
        self.total_cost += float(usage.get("cost") or 0.0)
        self.api_calls += 1
        return vecs

    # ---- giao dien Embedder ----
    def embed_documents(self, texts: list[str]) -> list[list[float]]:
        if any(not t or not t.strip() for t in texts):
            raise EmbeddingError("Co van ban rong trong danh sach can embed")
        out: list[list[float]] = []
        for i in range(0, len(texts), BATCH_SIZE):
            out.extend(self._embed_batch(texts[i : i + BATCH_SIZE]))
        return out

    def embed_query(self, question: str) -> list[float]:
        if not question or not question.strip():
            raise EmbeddingError("Cau hoi rong")
        return self._embed_batch([question])[0]
