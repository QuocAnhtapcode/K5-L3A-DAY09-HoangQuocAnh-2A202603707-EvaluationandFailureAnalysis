# Judge audit — Hoàng Quốc Anh — 2A202603707 — L3A

FAIL là positive class; floors κ≥0.6, P≥0.8, R≥0.7.

| Judge | n | TP/FP/FN/TN | κ | P | R | Quyết định |
|---|---:|---|---:|---:|---:|---|
| tone | 100 | 24/4/6/66 | 0.757 | 0.857 | 0.8 | Dùng cho tone |
| helpful | 100 | 9/0/21/70 | 0.375 | 1.0 | 0.3 | Loại khỏi gate |

Năm bất đồng tone đối chiếu theo rubric/ghi chú human trong CSV công khai:

| Case | Reply | Human/Judge | Ai đúng theo rubric | Sửa rubric |
|---|---|---|---|---|
| H-008 | Em đã hoàn tiền cho anh rồi nha, anh check giúp em. | FAIL/PASS | Human: xưng 'em' + 'nha', quá suồng sã với khách; judge coi là thân thiện | Cấm em/nha trong ngữ cảnh CS trang trọng. |
| H-017 | Dạ, bạn ơi LogiX đã hoàn 25.000đ cho đơn O-606 rồi nha. | FAIL/PASS | Human: xưng 'bạn' với khách lớn tuổi; judge coi là thân thiện | Quy định xưng hô anh/chị, tránh bạn ơi/nha. |
| H-029 | Dạ, vui lòng chờ. Hệ thống đang xử lý, không cần nhắn thêm. | FAIL/PASS | Human: giọng ra lệnh ('không cần nhắn thêm'); judge chỉ thấy 'Dạ, vui lòng' | Đánh fail lời ra lệnh/ngăn khách hỏi thêm dù mở đầu lịch sự. |
| H-042 | Dạ, đơn O-808 đã hoàn 120.000đ. Tiền về trong 3–5 ngày ạ. | PASS/FAIL | Human: ngắn nhưng đủ ý; judge phạt vì 'thiếu xin lỗi' | Không bắt buộc xin lỗi khi phản hồi đã đủ lịch sự/đủ ý. |
| H-051 | Dạ, LogiX đã refund 90.000đ cho đơn O-202 ạ. | PASS/FAIL | Human: dùng từ 'refund' — CS LogiX cho phép; judge phạt vì tiếng Anh | Cho phép từ refund theo glossary CS LogiX. |

Rogan–Gladen: tone observed 0.28 → 0.3; helpful 0.09 → 0.3.
Helpful bỏ sót 21/30 lỗi, recall 0.3, κ 0.375; precision 1.0 không bù được false negative. Không dùng làm gate. Tone chỉ chấm phong cách, không quyết tiền/phê duyệt. Replay công khai chưa thay thế held-out có nhãn mới.
