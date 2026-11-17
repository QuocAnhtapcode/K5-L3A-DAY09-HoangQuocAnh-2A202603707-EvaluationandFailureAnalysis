# Trace case — C-002@11

Người thực hiện: Hoàng Quốc Anh — 2A202603707 — L3A. Report `E-seeded_regression-20261117-632e`.

| Trường | Bằng chứng |
|---|---|
| Triệu chứng | Seeded regression ghi 20000 VND, status resolved; nhãn 0 VND/denied |
| Bước sai đầu tiên | Event 3, model_override, delay_days=5 |
| Các bước trước | Handoff đúng allowlist; investigator đọc O-202 delay_days=2 và policy hiện hành |
| Nguyên nhân | FM-03: tin ticket 5 ngày thay vì DB 2 ngày, tạo quyền hoàn phí không hợp lệ |
| Đối chứng | Fixed không có override; ledger 0 VND, status denied; TrialPass và RefundAmountCorrect pass |
| Regression test | tests/test_lab9_regressions.py::test_lab9_trace_case_first_wrong_step_ticket_over_db |
| Phạm vi suy luận | Trace thể hiện quyết định và dữ kiện, không chứng minh suy nghĩ bên trong model |

Tái lập trong src/: `python -m lab9.trace_case --shape seeded_regression --claim C-002 --seed 11`, rồi thay shape bằng fixed.
