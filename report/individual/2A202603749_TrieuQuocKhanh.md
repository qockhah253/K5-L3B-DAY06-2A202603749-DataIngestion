# Báo cáo cá nhân — Day 6

- Học viên: Triệu Quốc Khánh — MSSV 2A202603749 — Lớp L3B
- Ngày chạy: 2026-11-14 (Asia/Saigon)
- Sử dụng AI: có. Claude (Anthropic) hỗ trợ viết mã, đề xuất câu benchmark, gợi ý nhãn chấm thủ công và soạn báo cáo. Tác giả đã kiểm tra lại từng câu benchmark, duyệt từng nhãn và chạy toàn bộ lệnh trên máy cá nhân. Chi tiết ở mục "Hạn chế".

## Dữ liệu và pipeline

- **Chủ đề, nguồn/quyền, số trang và quy tắc tính trang:**

| Mục | Giá trị |
|---|---|
| Tài liệu | "600 câu hỏi dùng cho sát hạch lái xe cơ giới đường bộ", Cục CSGT – Bộ Công an, bìa ghi Hà Nội 2025 |
| Ngôn ngữ / định dạng | Tiếng Việt, PDF có lớp chữ, không OCR |
| Quyền | Tài liệu công bố công khai; chưa tìm thấy giấy phép tái phân phối → không commit PDF, chỉ nộp manifest + sha256 + hướng dẫn tải (`data/manifest.json`) |
| Số trang vật lý | 188 (sha256 `6a6dab85…518575`) |
| Quy tắc tính trang nội dung | Loại trang 1–3 (bìa, lời nói đầu) và trang 4 (trống). Tính trang 5–188 có ≥ 800 ký tự sau chuẩn hóa → **61 trang** (≥ 30). Chi tiết từng trang: `data/manifest_pages.csv` |
| Cấu trúc | 600 câu, 6 chương theo số câu: I 1–180, II 181–205, III 206–263, IV 264–300, V 301–485, VI 486–600 |

- **Chuẩn hóa, lỗi và giới hạn:**

| Bước | Xử lý |
|---|---|
| Đọc PDF | PyMuPDF. pypdf tách sai từ tiếng Việt (58 chỗ nghi lỗi trên trang 5–70, ví dụ "phương ti ện"); PyMuPDF 0 chỗ (`docs/NOTES.md`) |
| Chuẩn hóa | Unicode NFC, bỏ ký tự zero-width, NBSP → dấu cách, gộp khoảng trắng mỗi dòng, gộp ≥ 3 dòng trống |
| Số trang in | Dòng đầu mỗi trang là số trang in (= trang PDF − 4) → tách vào metadata `printed_page` |
| Tách câu hỏi | Regex `Câu N.`; xử lý 3 lỗi trình bày của nguồn (câu 507 dùng dấu hai chấm, câu 512 thiếu dấu cách, câu 352 dồn 3 phương án một dòng). Kiểm tra: đủ 600 câu, số câu từng chương khớp lời nói đầu |
| Giới hạn 1 | Đáp án đúng chỉ được đánh dấu bằng **gạch chân**, mất khi trích văn bản. Chunk của mọi chiến lược chỉ chứa các phương án, không chỉ ra phương án đúng |
| Giới hạn 2 | Chương V–VI phụ thuộc hình biển báo/sa hình (không có trong văn bản); benchmark chỉ dùng câu Chương I–IV, không câu nào cần hình |

- **Embedding, vector store, metric, lệnh chạy, chi phí:**

| Mục | Giá trị |
|---|---|
| Embedding | OpenRouter, model `baai/bge-m3`, 1024 chiều, không dùng tiền tố query/passage; cùng model cho A/B/C và cho truy vấn |
| Vector store | PostgreSQL 16.16 + pgvector 0.8.7 (Docker, image `pgvector/pgvector:0.8.7-pg16`), lưu bền trên volume |
| Metric | Cosine distance (`<=>`), quét chính xác (≈ 1.600 dòng, không cần index) |
| Lệnh chạy | `python -m src.run` (ingest + dev); `python -m src.run --splits dev,test --skip-ingest` (sau khi chốt chiến lược) |
| Chi phí ingest | A: 50.161 token, 0,000502 USD, 29,7 s; B/C (dùng chung vector): 46.758 token, 0,000468 USD, 51,7 s (`starter/results/ingest_stats.json`) |
| Chi phí truy vấn | Lần chạy dev+test: 20 lần gọi, 383 token, ≈ 0,000004 USD |
| Lỗi API | Không fallback: lỗi mạng/HTTP/sai số chiều → `EmbeddingError`, dừng pipeline; chỉ thử lại lỗi tạm thời (429/5xx/mạng) tối đa 4 lần |

- **Metadata bắt buộc, trường lọc, nguồn giá trị, lý do:**

| Trường | A | B/C | Nguồn giá trị | Lý do |
|---|---|---|---|---|
| `document_id`, `source`, `page` | có | có | Tên file, số trang vật lý PDF | Truy vết về trang gốc |
| `char_start`, `char_end` | có | – | Vị trí cắt trên trang | Truy vết vị trí chunk A |
| `question_no`, `end_page` | – | có | Regex tách câu; trang cuối khi câu vắt qua 2 trang | Truy vết đúng câu; 48 câu nằm trên 2 trang |
| `chapter` (trường lọc) | – | có | Suy từ số câu theo bảng phân chương của lời nói đầu (giá trị đáng tin, không tạo giả) | Phạm vi phân biệt được: cùng chủ đề (lùi xe, điện thoại, phanh) xuất hiện ở nhiều chương |
| `n_options`, `mentions_figure` | – | có | Đếm phương án; có chữ "hình" | Phân tích lỗi |

## Cấu hình và benchmark

- **A / B / C:**

| Cấu hình | Chunking | Metadata | Filter | Số chunk |
|---|---|---|---|---|
| A | Cố định 500 ký tự, chồng lấn 50, theo từng trang | source, page, char_start/end | không | 433 |
| B | Một chunk = một câu hỏi (đề + mọi phương án), tối đa 1.200 ký tự | + chapter, question_no, end_page, n_options, mentions_figure | không | 600 |
| C | Giống hệt B (dùng chung vector) | giống B | SQL `metadata->>'chapter' = %s`, chỉ ở câu có khóa `filter` | 600 |

  So sánh A–B chỉ khác cách chunking. So sánh B–C chỉ khác filter. Chiến lược B thay `by_paragraph` của starter bằng `by_question` vì đơn vị nghĩa của tài liệu là câu hỏi.

- **Benchmark (`benchmark/questions.json`):**

| Mục | Giá trị |
|---|---|
| Số câu | 20: 15 dev / 5 test, chia trước khi chạy (commit `9a786e5`) |
| Câu có filter | 5 câu (3 dev: câu 85, 52, 284; 2 test: câu 246, 254). Mỗi câu có "câu song sinh" cùng chủ đề ở chương khác |
| Giá trị filter | Chương, coi là ngữ cảnh người dùng cung cấp trước truy xuất (người ôn theo chương). Bằng chương của gold → **nguy cơ rò rỉ nhãn** |
| Kiểm chứng evidence | Script kiểm tra `evidence_quote` có nguyên văn trong câu gold và trên `gold_pages`; `expected_answer` trùng phương án gạch chân (trích tự động bằng vị trí nét gạch chân). Tác giả xác minh bằng mắt trên PDF: câu 40, 114, 249 |
| Loại trừ khi chọn câu | Câu 204 (không có gạch chân), đáp án "Cả … ý trên", câu cần hình, câu 213/223 (gần trùng nhau) |
| Ghi chú q18 | Câu 149: `evidence_quote` trùng nguyên văn ở câu 150–156 nên không phân biệt được chiến lược. Định thay bằng câu 15 trước khi chạy test nhưng thay đổi không được ghi vào file; giữ nguyên tập test như đã commit (`artifacts/selection_rule.md`) |

- **Tiêu chí chọn chiến lược (chốt trước khi chạy test, `artifacts/selection_rule.md`):** (1) Evidence Hit@3 dev cao hơn; (2) Evidence Hit@1 dev cao hơn; (3) hòa → chọn cấu hình không cần ngữ cảnh filter. Hit@1 theo trang không dùng để chọn vì bão hòa trên dev.

## Kết quả

Định nghĩa: **Hit@1** = chunk top-1 đúng nguồn và khoảng trang giao với `gold_pages`. **Evidence Hit@3** = top-3 có chunk chứa nguyên văn `evidence_quote` (so khớp sau khi gộp khoảng trắng).

| Strategy | Split | Hit@1 (n/N) | Evidence Hit@3 (n/N) | Chunk count | Thời gian embed | Chi phí embed |
|---|---|---|---|---|---|---|
| A | dev | 15/15 | 9/15 | 433 | 29,7 s | 0,000502 USD |
| A | test | 4/5 | 4/5 | 433 | | |
| B | dev | 15/15 | 15/15 | 600 | 51,7 s | 0,000468 USD |
| B | test | 4/5 | 5/5 | 600 | | |
| C | dev | 15/15 | 15/15 | 600 | dùng chung vector B | 0 |
| C | test | 5/5 | 5/5 | 600 | | |

Test bỏ q18 (4 câu phân biệt được): A Hit@1 3/4, Evidence Hit@3 3/4; B 3/4, 4/4; C 4/4, 4/4.

| Strategy | Coherence trung bình /2 (n) | Metadata đủ và đúng (n/N) | Filter tuân thủ (n/N hoặc N/A) | Grounding 0/1/2 (số câu) và trung bình /2 |
|---|---|---|---|---|
| A | 0,8 (10): 4×0, 4×1, 2×2 | 9/15 | N/A (không có trường chapter) | 0 / 2 / 3 → 1,6 |
| B | 2,0 (10): 10×2 | 15/15 | 0/2 (không lọc; top-3 lẫn câu chương I, II) | 0 / 0 / 5 → 2,0 |
| C | 2,0 (10): giống B | 15/15 | 2/2 | 0 / 0 / 5 → 2,0 |

**Đường dẫn và cách chọn mẫu:**

| Nội dung | File |
|---|---|
| Trace top-3 đầy đủ | `starter/results/traces_dev.jsonl`, `starter/results/traces_dev_test.jsonl` |
| Chỉ số | `starter/results/metrics_dev.json`, `starter/results/metrics_dev_test.json` |
| Nhật ký thí nghiệm | `artifacts/experiment_log.csv` |
| Coherence | `artifacts/manual_coherence.csv` (.xlsx). 10 vị trí cố định chọn trước khi chấm: ký tự giữa trang PDF 6, 12, …, 60; mỗi vị trí chấm chunk chứa nó ở A và B; C = B. Script `starter/scripts/make_coherence_sheet.py` |
| Metadata | `artifacts/manual_metadata_test.csv`: 5 câu test × top-3 × 3 chiến lược. Kiểm tra văn bản chunk có trên trang ghi; chương khớp số câu |
| Grounding | `artifacts/manual_grounding_test.csv`: 5 câu test × 3 chiến lược. 2 = top-3 có đủ đề + toàn văn phương án đúng và truy được trang |

## Phân tích và kết luận

- **So sánh A–B (chỉ khác chunking):**
  - Dev: Evidence Hit@3 A 9/15, B 15/15. Hit@1 theo trang bằng nhau (15/15) vì chunk A đúng trang nhưng bị cắt.
  - A trượt 6 câu dev: 2 câu bằng chứng bị cắt đôi qua hai chunk (q10 câu 40 trang 12, q13 câu 85 trang 21); 4 câu đúng trang nhưng không chunk nào chứa trọn quote (q04 câu 103, q07 câu 226, q09 câu 292, q11 câu 114).
  - Coherence A 0,8 so với B 2,0: 302/433 chunk A không bắt đầu bằng "Câu N."; 4/10 vị trí mất đề nên không biết đang hỏi gì (P03–P06).
  - Ví dụ sai 1, **q16 (câu 42, trang 13)**: A đưa đúng trang lên top-1 nhưng chunk dừng ở "Không được cho trẻ…", thiếu phần còn lại của đáp án → grounding 1. B trả trọn câu 42 → grounding 2.
  - Tài nguyên: B có nhiều chunk hơn (600 so với 433) nhưng ít ký tự hơn (166.027 so với 179.108, do không chồng lấn), token embed ít hơn (46.758 so với 50.161); thời gian embed dài hơn (51,7 s so với 29,7 s) do nhiều lần gọi API hơn.

- **So sánh B–C (chỉ khác filter):**
  - Dev: hòa tuyệt đối; chunk gold của B đã đứng đầu 15/15, filter chỉ đổi thứ hạng ở câu 85 (loại câu 246 khỏi top-3).
  - Ví dụ sai 2, **q19 (câu 246, Chương III, trang 57)**: B xếp câu 85 (Chương I, trang 21, cùng chủ đề lùi xe, điểm 0,7539) trên gold (0,7435) → Hit@1 sai. C lọc Chương III → gold lên hạng 1. Đây là trường hợp duy nhất trong 20 câu filter có lợi.
  - Filter tuân thủ: C 2/2, B 0/2. Tốn thêm: không (cùng vector, thêm một điều kiện SQL).

- **Chiến lược chọn, đánh đổi, điều kiện áp dụng:**
  - Chọn **B** theo tiêu chí đã chốt trên dev (A loại ở bước 1; B, C hòa ở bước 1–2; bước 3 chọn cấu hình không cần ngữ cảnh). Không đổi sau khi xem test.
  - C nên dùng khi ứng dụng **thực sự có** ngữ cảnh chương từ người dùng (ví dụ màn hình ôn theo chương); khi đó filter giảm nhầm lẫn giữa các câu cùng chủ đề ở chương khác (q19). Nếu không có ngữ cảnh, phải đoán chương → rủi ro lọc sai, loại mất câu đúng.
  - Kết luận chỉ áp dụng cho corpus dạng ngân hàng câu hỏi có cấu trúc "Câu N." rõ ràng; không suy rộng cho tài liệu văn xuôi.

- **Hạn chế:**

| Loại | Hạn chế |
|---|---|
| Dữ liệu | Đáp án (gạch chân) mất khi trích văn bản → không chunk nào chỉ ra phương án đúng; Chương V–VI phụ thuộc hình, không được đánh giá; quyền tái phân phối chưa xác nhận |
| Benchmark | Mẫu nhỏ (15 dev / 5 test): chênh 1 câu = 20 điểm % ở test. q18 không phân biệt được. Filter = chương của gold → rò rỉ nhãn. Đáp án lấy tự động từ gạch chân, tác giả mới xác minh bằng mắt 3 câu. Query do tác giả (với AI hỗ trợ) diễn đạt lại từ đề, khá sát đề gốc → có thể dễ hơn câu hỏi người dùng thật |
| Nhãn thủ công | Người chấm là tác giả, không độc lập. Coherence: tác giả chấm lần đầu (A trung bình 1,2), sau đó AI gợi ý thang chặt hơn và tác giả duyệt (A 0,8); cả hai bộ nhãn lưu ở cột `first_pass_label` và `label_0_2`. Metadata và grounding: AI gợi ý, tác giả duyệt |
| Thời gian/chi phí | Thời gian embed đo một lần, phụ thuộc mạng và độ trễ OpenRouter; chưa đo thời gian truy vấn riêng. Chi phí lấy từ trường `usage.cost` của API |

- **Nếu làm lại hoặc mở rộng:**
  1. Đưa đáp án đúng (trích từ gạch chân) vào metadata hoặc nội dung chunk B để chunk đủ trả lời mà không cần PDF.
  2. Thay q18 bằng câu không trùng đáp án và mở rộng tập test (≥ 15 câu) gồm nhiều cặp câu song sinh giữa các chương để đo filter đáng tin hơn.
  3. Viết query theo cách người học thật hỏi (ngắn, thiếu từ khóa) thay vì diễn đạt sát đề.
  4. Thử hybrid (BM25 + dense) cho các câu chỉ khác con số (câu 149–156: 90/80/70/60 km/h).
  5. Xử lý Chương V–VI bằng mô tả hình (caption) hoặc mô hình đa phương thức.
