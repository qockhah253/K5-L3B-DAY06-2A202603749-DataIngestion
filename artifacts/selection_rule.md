# Tiêu chí chọn chiến lược (chốt TRƯỚC khi chạy tập test)

Thời điểm chốt: 2026-11-14, sau khi chạy dev, trước khi chạy `--splits dev,test`.

## Quy tắc (áp dụng theo thứ tự, dừng ở bước đầu tiên phân thắng bại)

| Bước | Tiêu chí | Chỉ dùng số liệu |
|---|---|---|
| 1 | Evidence Hit@3 trên dev cao hơn | dev |
| 2 | Evidence Hit@1 trên dev cao hơn | dev |
| 3 | Hòa -> chọn cấu hình ít phụ thuộc hơn (không cần ngữ cảnh filter từ người dùng) | thiết kế |

Hit@1 theo trang KHÔNG dùng để chọn vì bão hòa (15/15 cả ba), chỉ báo cáo.

## Kết quả dev (n = 15)

| Chiến lược | Hit@1 (trang) | Evidence Hit@1 | Evidence Hit@3 | evidence_split |
|---|---|---|---|---|
| A | 15/15 | 9/15 | 9/15 | 2 |
| B | 15/15 | 15/15 | 15/15 | 0 |
| C | 15/15 | 15/15 | 15/15 | 0 |

## Quyết định

- A thua B/C ở bước 1 (9/15 so với 15/15) -> loại A.
- B và C hòa ở bước 1 và 2 -> bước 3: chọn **B** (không cần filter).
- Tập test vẫn chạy cho cả A, B, C để báo cáo đầy đủ. Quyết định trên KHÔNG đổi sau khi xem test.
  Nếu C tốt hơn B trên test thì ghi nhận như một phát hiện, không đổi chiến lược đã chọn.

## Kết quả test (chạy sau commit 9a786e5, n = 5)

| Chiến lược | Hit@1 (trang) | Evidence Hit@1 | Evidence Hit@3 | evidence_split |
|---|---|---|---|---|
| A | 4/5 | 3/5 | 4/5 | 0 |
| B | 4/5 | 4/5 | 5/5 | 0 |
| C | 5/5 | 5/5 | 5/5 | 0 |

- Quyết định giữ nguyên: **B**. Không sửa tập test sau khi xem kết quả.
- Phát hiện: q19 (câu 246, Chương III): B xếp câu 85 (Chương I, điểm 0,7539) trên gold 246 (0,7435);
  C lọc chương III đưa 246 lên hạng 1. Đây là trường hợp duy nhất trong 20 câu filter có lợi.
  Giá trị filter = chương của gold -> nguy cơ rò rỉ nhãn.

## Ghi chú về q18 (câu 149) trong tập test

- Đáp án câu 149 trùng nguyên văn với câu 150 (cùng trang 34) -> q18 trúng ở cả A, B, C,
  không phân biệt được chiến lược.
- Trước khi chạy test đã định thay q18 bằng câu 15, nhưng thay đổi đó không được ghi vào
  file benchmark trên máy (lỗi khi chép file); commit 9a786e5 chứa câu 149.
- Xử lý: giữ nguyên tập test như đã commit; báo cáo thêm số liệu trên 4 câu phân biệt được
  (bỏ q18): A Hit@1 3/4, Evidence Hit@3 3/4; B Hit@1 3/4, Evidence Hit@3 4/4; C 4/4, 4/4.

## Hạn chế đã biết của dev (ghi vào báo cáo)

- Trên dev, chunk gold của B đã đứng đầu 15/15 nên filter của C không có chỗ cải thiện;
  dev không phân biệt được B và C. Filter chỉ đổi kết quả ở câu 85 (loại câu 246 khỏi top-3).
- Giá trị filter (chương) là ngữ cảnh giả định do người dùng cung cấp trước truy hồi và
  trùng với chương của gold -> có nguy cơ rò rỉ nhãn.
