"""Pipeline Day 06: ingest -> chunk A/B/C -> embed -> pgvector -> benchmark -> trace.

Chay (tu thu muc starter/):
    python -m src.run                      # ingest + danh gia tap DEV
    python -m src.run --skip-ingest        # dung lai du lieu da nap trong DB
    python -m src.run --splits dev,test    # CHI dung sau khi da chot chien luoc tren dev

Chien luoc:
  A = fixed-size 500/50 theo trang, khong filter
  B = mot chunk / mot cau hoi (metadata chapter,...), khong filter
  C = chunk giong het B + filter SQL theo `chapter` (chi cau co khoa 'filter')
B va C dung chung vector (cung chunk, cung model) nen chi embed mot lan.
"""
import argparse
import json
import os
import re
import sys
import time
from pathlib import Path

from dotenv import load_dotenv

from .chunking import by_question, fixed_size
from .embeddings import MyEmbedder
from .evaluation import evaluate_query, summarize
from .ingestion import load_pdf
from .store import PgVectorStore
from .structure import split_questions, validate

ROOT = Path(__file__).resolve().parent.parent  # .../starter
DOC, SRC = "csgt-600-cau-2025", "csgt-600-cau-2025.pdf"
PDF = ROOT / "data" / "raw" / SRC
BENCH = ROOT.parent / "benchmark" / "questions.json"
RESULTS = ROOT / "results"
MIN_CONTENT_PAGES = 30


def _ws(s: str) -> str:
    return re.sub(r"\s+", " ", s).strip()


def load_and_validate():
    pages = [p for p in load_pdf(PDF, DOC, SRC) if p.page >= 5 and not p.metadata["empty"]]
    content_pages = [p for p in pages if len(p.text) >= 800]
    if len(content_pages) < MIN_CONTENT_PAGES:
        raise SystemExit(f"Chi co {len(content_pages)} trang noi dung (< {MIN_CONTENT_PAGES})")
    questions = split_questions(pages)
    problems = validate(questions)
    if problems:
        raise SystemExit(f"Cau truc cau hoi loi: {problems[:5]}")

    bench = json.loads(BENCH.read_text(encoding="utf-8"))
    ids = [q["id"] for q in bench]
    assert len(set(ids)) == len(ids), "id benchmark bi trung"
    splits = {s: sum(1 for q in bench if q["split"] == s) for s in ("dev", "test")}
    assert len(bench) >= 20 and splits["dev"] >= 15 and splits["test"] >= 5, f"Benchmark thieu: {splits}"
    page_text = {p.page: _ws(p.text) for p in pages}
    for q in bench:
        assert q["gold_source_id"] == SRC, f"{q['id']}: gold_source_id != {SRC}"
        quote = _ws(q["evidence_quote"])
        assert any(quote in page_text.get(g, "") for g in q["gold_pages"]), (
            f"{q['id']}: evidence_quote khong nam tren gold_pages"
        )
    print(f"Corpus: {len(pages)} trang co chu, {len(content_pages)} trang noi dung (>=800 ky tu), "
          f"{len(questions)} cau hoi | Benchmark: {len(bench)} cau {splits}")
    return pages, questions, bench


def ingest(store: PgVectorStore, emb: MyEmbedder, pages, questions) -> dict:
    stats = {}
    A = [c for p in pages for c in fixed_size(p, 500, 50)]
    B = by_question(questions, DOC, SRC)
    for name, chunks, targets in (("A", A, ["A"]), ("B", B, ["B", "C"])):
        t0, tok0, cost0, calls0 = time.time(), emb.total_tokens, emb.total_cost, emb.api_calls
        vecs = emb.embed_documents([c.text for c in chunks])
        secs = time.time() - t0
        for s in targets:
            store.upsert(s, chunks, vecs)
        stats[name] = {
            "strategies_written": targets,
            "n_chunks": len(chunks),
            "chars": sum(len(c.text) for c in chunks),
            "embed_seconds": round(secs, 1),
            "tokens": emb.total_tokens - tok0,
            "cost_usd": emb.total_cost - cost0,
            "api_calls": emb.api_calls - calls0,
        }
        print(f"  Nap {name}: {len(chunks)} chunk -> {targets} | {secs:.1f}s | "
              f"{stats[name]['tokens']} token | {stats[name]['cost_usd']:.6f} USD")
    for s in ("A", "B", "C"):
        print(f"  DB strategy {s}: {store.count(s)} dong")
    return stats


def evaluate(store: PgVectorStore, emb: MyEmbedder, bench: list[dict], splits: set[str]):
    traces = []
    for q in bench:
        if q["split"] not in splits:
            continue
        qv = emb.embed_query(q["question"])  # cung vector truy van cho ca 3 chien luoc
        for strategy in ("A", "B", "C"):
            flt = q.get("filter") if strategy == "C" else None
            hits = store.search(strategy, qv, top_k=3, filters=flt)
            t = evaluate_query(q, hits)
            t["strategy"] = strategy
            t["applied_filter"] = flt
            traces.append(t)
    return traces


def report(traces: list[dict]) -> dict:
    summ = summarize(traces)
    print("\nstrategy | split | n | Hit@1 | EvidenceHit@3 | evidence_split")
    for s in sorted(summ):
        for sp in ("dev", "test", "all"):
            a = summ[s].get(sp)
            if a and (sp != "all" or len(summ[s]) > 2):
                print(f"   {s}     | {sp:4} | {a['n']:2} | {a['hit1']}/{a['n']} | "
                      f"{a['evidence_hit3']}/{a['n']} | {a['evidence_split']}")
    return summ


def main() -> None:
    sys.stdout.reconfigure(encoding="utf-8")
    ap = argparse.ArgumentParser()
    ap.add_argument("--splits", default="dev", help="dev | dev,test (test chi sau khi chot chien luoc)")
    ap.add_argument("--skip-ingest", action="store_true")
    args = ap.parse_args()
    splits = set(args.splits.split(","))
    if not splits <= {"dev", "test"}:
        raise SystemExit("--splits chi nhan dev va/hoac test")

    load_dotenv(ROOT / ".env")
    pages, questions, bench = load_and_validate()
    emb = MyEmbedder()
    store = PgVectorStore(os.environ["DATABASE_URL"], emb.dimensions)
    store.create_schema()
    RESULTS.mkdir(exist_ok=True)

    if not args.skip_ingest:
        print("Ingest:")
        stats = ingest(store, emb, pages, questions)
        stats["model"] = emb.model_name
        (RESULTS / "ingest_stats.json").write_text(
            json.dumps(stats, ensure_ascii=False, indent=2), encoding="utf-8")

    for s in ("A", "B", "C"):
        if store.count(s) == 0:
            raise SystemExit(f"Strategy {s} chua co du lieu: chay lai khong co --skip-ingest")

    traces = evaluate(store, emb, bench, splits)
    summ = report(traces)
    tag = "_".join(sorted(splits))
    with (RESULTS / f"traces_{tag}.jsonl").open("w", encoding="utf-8") as f:
        for t in traces:
            f.write(json.dumps(t, ensure_ascii=False) + "\n")
    (RESULTS / f"metrics_{tag}.json").write_text(
        json.dumps(summ, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"\nDa luu: {RESULTS}\\traces_{tag}.jsonl va metrics_{tag}.json")
    print(f"Embedding: {emb.api_calls} lan goi, {emb.total_tokens} token, {emb.total_cost:.6f} USD")


if __name__ == "__main__":
    main()
