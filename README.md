# Day 06 · Data Ingestion Engineering

> **Bài làm của Triệu Quốc Khánh (2A202603749, L3B)** — xem mục [Bài làm: setup và chạy](#bài-làm-setup-và-chạy) ở cuối file và báo cáo [report/individual/2A202603749_TrieuQuocKhanh.md](report/individual/2A202603749_TrieuQuocKhanh.md).

**Lab cá nhân** · **4 giờ** · **Dữ liệu tự chọn**

Biến tài liệu thành kho tri thức có thể truy xuất cho AI agent, rồi đo xem cách chuẩn bị dữ liệu nào hiệu quả nhất.

| 📄 Dữ liệu | 🧩 Chiến lược | 🎯 Benchmark |
|---|---|---|
| Tối thiểu **30 trang nội dung** | Tối thiểu **3 cấu hình** | Tối thiểu **20 câu hỏi** |

## Bắt đầu nhanh

Dùng [starter PostgreSQL + pgvector](starter/README.md) để dựng database và hoàn thiện các hàm TODO, hoặc tự chọn vector store tương đương. Starter chỉ là khung: **bạn tự hiện thực pipeline và benchmark**.

## 1. Xây pipeline

![Đọc tài liệu, chuẩn hóa, chia chunk, tạo vector, lưu và kiểm tra](assets/ingestion-pipeline.svg)

Chọn tài liệu được phép sử dụng; giữ **ID tài liệu, nguồn, trang/vị trí** và metadata phù hợp. Dùng embedding model thật qua API hoặc chạy local; lưu và truy xuất bằng pgvector, Qdrant, Chroma hoặc một store tương đương.

## 2. So sánh và đánh giá

![Ba chiến lược được đánh giá trên cùng corpus và benchmark dev/test](assets/benchmark-workflow.svg)

Dùng cùng dữ liệu, model và câu hỏi cho cả ba cấu hình. Tách **15 câu dev / 5 câu test** trước khi chạy; chọn cấu hình trên dev, rồi đánh giá test sau khi cố định. Mỗi câu hỏi cần có đoạn bằng chứng và trang nguồn; thiết kế bộ câu hỏi và đánh giá theo [BENCHMARK.md](BENCHMARK.md).

Đánh giá theo năm khía cạnh: **độ chính xác truy xuất**, **tính mạch lạc của chunk**, **tính hữu dụng của metadata**, **chất lượng grounding** và **tác động của chiến lược dữ liệu**. Giải thích lựa chọn bằng kết quả, ví dụ lỗi và các đánh đổi.

## 3. Chuẩn bị bài nộp

1. Chạy pipeline và lưu cấu hình, kết quả top-3, trace cùng nhãn đánh giá thủ công.
2. Điền [thông tin học viên](STUDENT.md), [nhật ký thí nghiệm](artifacts/experiment_log.csv) và bản sao [mẫu báo cáo cá nhân](report/individual/MSSV_HoTen.md).
3. Kiểm tra mã nguồn, cách chạy, manifest dữ liệu và checklist trong [SUBMISSION.md](SUBMISSION.md).

## Tài liệu hướng dẫn

| Bạn cần tìm | Tài liệu |
|---|---|
| Setup baseline PostgreSQL + pgvector | [starter/README.md](starter/README.md) |
| Các bước làm và cách tính chỉ số | [GUIDE.md](GUIDE.md) |
| Tiến độ trong 4 giờ | [CHECKPOINTS.md](CHECKPOINTS.md) |
| Năm tiêu chí benchmark và bộ câu hỏi | [BENCHMARK.md](BENCHMARK.md) |
| Tiêu chí chấm điểm | [RUBRIC.md](RUBRIC.md) |
| Quy tắc sử dụng dữ liệu, AI và API | [RULES.md](RULES.md) |
| Cách nộp bài | [SUBMISSION.md](SUBMISSION.md) |

[data/format-example.json](data/format-example.json) chỉ minh họa định dạng, không phải corpus đủ điều kiện. Phần xử lý và benchmark do bạn tự hiện thực; không bắt buộc xây chatbot.


## Bài làm: setup và chạy

Corpus: "600 câu hỏi dùng cho sát hạch lái xe cơ giới đường bộ" (PDF, 188 trang). Chiến lược A/B/C, embedding `baai/bge-m3` qua OpenRouter, PostgreSQL 16 + pgvector 0.8.7.

| Bước | Lệnh (Windows PowerShell, trong thư mục `starter`) | Kết quả mong đợi |
|---|---|---|
| 1. Môi trường | `python -m venv .venv` rồi `.venv\Scripts\Activate.ps1` rồi `python -m pip install -r requirements.txt` | Cài psycopg, python-dotenv, pymupdf |
| 2. Cấu hình | `Copy-Item .env.example .env`; điền `OPENROUTER_API_KEY` và `EMBEDDING_MODEL=baai/bge-m3` | File `.env` (không commit) |
| 3. Dữ liệu | Tải PDF theo `data/manifest.json` (trường `source_path_or_url`), lưu thành `starter/data/raw/csgt-600-cau-2025.pdf`; đối chiếu sha256 | PDF không có trong repo |
| 4. Database | `docker compose -p day6_student_starter up -d --wait` rồi `python scripts/check_setup.py` | `Setup OK` |
| 5. Kiểm tra từng phần | `python scripts/check_ingestion.py`, `python scripts/check_chunking.py`, `python scripts/check_embeddings.py`, `python scripts/check_store.py`, `python scripts/check_evaluation.py` | 600 câu; A 433 / B 600 chunk; 1024 chiều; các kiểm tra store/evaluation đúng |
| 6. Ingest + dev | `python -m src.run` | `results/traces_dev.jsonl`, `results/metrics_dev.json`, `results/ingest_stats.json` |
| 7. Test (chỉ sau khi chốt chiến lược) | `python -m src.run --splits dev,test --skip-ingest` | `results/traces_dev_test.jsonl`, `results/metrics_dev_test.json` |
| 8. Bảng chấm coherence | `python scripts/make_coherence_sheet.py` | `artifacts/manual_coherence.csv` (khung, chưa có nhãn) |

| Thành phần | Vị trí |
|---|---|
| Mã nguồn pipeline | `starter/src/` (`ingestion.py`, `structure.py`, `chunking.py`, `embeddings.py`, `store.py`, `evaluation.py`, `run.py`, `answer_key.py`) |
| Manifest | `data/manifest.json`, `data/manifest_pages.csv` |
| Benchmark | `benchmark/questions.json` (20 câu, 15 dev / 5 test), `benchmark/answer_key.json` |
| Cấu hình và log | `artifacts/experiment_log.csv`, `artifacts/selection_rule.md` |
| Nhãn thủ công | `artifacts/manual_coherence.csv`, `artifacts/manual_metadata_test.csv`, `artifacts/manual_grounding_test.csv` (+ bản .xlsx) |
| Ghi chú kỹ thuật | `docs/NOTES.md` |
