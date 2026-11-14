# Ghi chú kỹ thuật (Day 06)

## Chọn thư viện đọc PDF
- So sánh trên trang 5-70 (các trang chữ) của `csgt-600-cau-2025.pdf`, đếm các chỗ nghi từ bị tách
  bằng regex heuristic (khoảng trắng chen vào trước các vần như "ện", "ờng", "ười"):
  - pypdf 6.17.0: 58 chỗ (vd "phương ti ện", "đư ờng").
  - PyMuPDF: 0 chỗ. poppler `pdftotext`: 0 chỗ.
- Chọn PyMuPDF (cài bằng pip, chạy được trên Windows). Lưu ý: PyMuPDF dùng giấy phép AGPL.
- Heuristic chỉ phát hiện một số kiểu lỗi; chưa đánh giá toàn bộ chất lượng trích xuất.

## Lỗi trình bày trong tài liệu nguồn (đã xử lý bằng regex)
- Câu 507 viết "Câu 507:" (dấu hai chấm thay vì dấu chấm).
- Câu 512 viết dính "Câu 512.Theo" (thiếu dấu cách).
- Câu 352 có 3 phương án nằm chung một dòng.

## Cấu trúc
- Số trang in trong sách = trang PDF - 4 (dòng đầu mỗi trang); được tách ra metadata `printed_page`.
- Số câu từng chương khớp Lời nói đầu: I=180, II=25, III=58, IV=37, V=185, VI=115 (tổng 600).
