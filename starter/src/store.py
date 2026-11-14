"""PostgreSQL + pgvector: luu vector va tim kiem cosine (exact scan, ~600 chunk nen khong can index).

Bang `chunks`: khoa (strategy, chunk_id). Moi chien luoc A/B/C nam trong cung bang,
tach bang cot `strategy`. Metadata luu jsonb; filter chi cho phep khoa trong ALLOWED_FILTERS.
"""
import json
from typing import Any

import psycopg

from .models import Chunk

ALLOWED_FILTERS = {"chapter", "source", "document_id"}


def _vec(v: list[float]) -> str:
    """Vector -> literal pgvector '[x,y,...]' (truyen qua tham so, ep kieu trong SQL)."""
    return "[" + ",".join(repr(float(x)) for x in v) + "]"


class PgVectorStore:
    def __init__(self, database_url: str, dimensions: int) -> None:
        if not database_url:
            raise ValueError("Thieu DATABASE_URL")
        if dimensions <= 0:
            raise ValueError("dimensions phai > 0")
        self.database_url = database_url
        self.dimensions = dimensions

    def _connect(self) -> psycopg.Connection:
        return psycopg.connect(self.database_url)

    def create_schema(self) -> None:
        with self._connect() as conn:
            conn.execute("CREATE EXTENSION IF NOT EXISTS vector")
            conn.execute(
                f"""
                CREATE TABLE IF NOT EXISTS chunks (
                    strategy    text NOT NULL,
                    chunk_id    text NOT NULL,
                    document_id text NOT NULL,
                    source      text NOT NULL,
                    page        integer NOT NULL,
                    text        text NOT NULL,
                    metadata    jsonb NOT NULL DEFAULT '{{}}'::jsonb,
                    embedding   vector({int(self.dimensions)}) NOT NULL,
                    PRIMARY KEY (strategy, chunk_id)
                )
                """
            )
            # Neu bang da ton tai voi so chieu khac -> bao loi, khong ghi de im lang.
            row = conn.execute(
                "SELECT atttypmod FROM pg_attribute "
                "WHERE attrelid = 'chunks'::regclass AND attname = 'embedding'"
            ).fetchone()
            if row and row[0] != self.dimensions:
                raise RuntimeError(
                    f"Bang chunks co vector({row[0]}) nhung model dung {self.dimensions} chieu"
                )
            conn.execute("CREATE INDEX IF NOT EXISTS chunks_strategy_idx ON chunks (strategy)")

    def upsert(self, strategy: str, chunks: list[Chunk], vectors: list[list[float]]) -> None:
        if len(chunks) != len(vectors):
            raise ValueError(f"{len(chunks)} chunk nhung {len(vectors)} vector")
        ids = [c.chunk_id for c in chunks]
        if len(set(ids)) != len(ids):
            raise ValueError("chunk_id bi trung trong cung mot lan ingest")
        for v in vectors:
            if len(v) != self.dimensions:
                raise ValueError(f"Vector {len(v)} chieu, can {self.dimensions}")
        with self._connect() as conn:  # mot giao dich: loi thi rollback toan bo
            # Xoa chunk cu khong con trong lan ingest nay (nguon doi/chunking doi)
            conn.execute(
                "DELETE FROM chunks WHERE strategy = %s AND NOT (chunk_id = ANY(%s))",
                (strategy, ids),
            )
            with conn.cursor() as cur:
                cur.executemany(
                    """
                    INSERT INTO chunks
                        (strategy, chunk_id, document_id, source, page, text, metadata, embedding)
                    VALUES (%s, %s, %s, %s, %s, %s, %s::jsonb, %s::vector)
                    ON CONFLICT (strategy, chunk_id) DO UPDATE SET
                        document_id = EXCLUDED.document_id,
                        source = EXCLUDED.source,
                        page = EXCLUDED.page,
                        text = EXCLUDED.text,
                        metadata = EXCLUDED.metadata,
                        embedding = EXCLUDED.embedding
                    """,
                    [
                        (
                            strategy,
                            c.chunk_id,
                            c.document_id,
                            c.source,
                            c.page,
                            c.text,
                            json.dumps(c.metadata, ensure_ascii=False),
                            _vec(v),
                        )
                        for c, v in zip(chunks, vectors)
                    ],
                )

    def count(self, strategy: str) -> int:
        with self._connect() as conn:
            return conn.execute(
                "SELECT count(*) FROM chunks WHERE strategy = %s", (strategy,)
            ).fetchone()[0]

    def delete_strategy(self, strategy: str) -> None:
        with self._connect() as conn:
            conn.execute("DELETE FROM chunks WHERE strategy = %s", (strategy,))

    def search(
        self,
        strategy: str,
        query_vector: list[float],
        top_k: int = 3,
        filters: dict[str, Any] | None = None,
    ) -> list[dict[str, Any]]:
        if len(query_vector) != self.dimensions:
            raise ValueError(f"Query {len(query_vector)} chieu, can {self.dimensions}")
        where = ["strategy = %s"]
        params: list[Any] = [strategy]
        for key, value in (filters or {}).items():
            if key not in ALLOWED_FILTERS:
                raise ValueError(f"Filter khong duoc phep: {key!r} (cho phep {sorted(ALLOWED_FILTERS)})")
            if key in ("source", "document_id"):
                where.append(f"{key} = %s")
            else:
                where.append("metadata ->> %s = %s")
                params.append(key)
            params.append(str(value))
        qv = _vec(query_vector)
        sql = (
            "SELECT chunk_id, text, page, source, metadata, "
            "1 - (embedding <=> %s::vector) AS score "
            f"FROM chunks WHERE {' AND '.join(where)} "
            "ORDER BY embedding <=> %s::vector, chunk_id LIMIT %s"
        )
        with self._connect() as conn:
            rows = conn.execute(sql, [qv, *params, qv, top_k]).fetchall()
        return [
            {
                "chunk_id": r[0],
                "text": r[1],
                "page": r[2],
                "source": r[3],
                "metadata": r[4],
                "score": float(r[5]),
            }
            for r in rows
        ]
