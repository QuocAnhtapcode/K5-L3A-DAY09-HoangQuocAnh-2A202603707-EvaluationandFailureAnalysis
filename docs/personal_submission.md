# Bài nộp cá nhân — Hoàng Quốc Anh — 2A202603707 — L3A

Repo: https://github.com/QuocAnhtapcode/K5-L3A-DAY09-HoangQuocAnh-2A202603707-EvaluationandFailureAnalysis. Nhánh làm bài: starter/d09; PR vào main trong chính fork cá nhân.
Nguồn Day08: https://github.com/VinUni-AI20k/K5-Day8-From-Workflows-to-Agents, commit `034c6c421c198dae67a9211d15e2587d5a378972`. Chỉ nhập src/ của giảng viên; harness_map bổ sung section eval.

| Mốc | Bài làm và bằng chứng |
|---|---|
| M0 | smoke M0 PASS; provenance kiểm mã nguồn Day08 |
| M1 | Taxonomy FM-01…09, năm coding anchors, v1 14 item và v2 28 item, nhãn tách riêng |
| M2 | Tone đạt, helpful bị loại; 5 bất đồng có lý do/sửa rubric |
| M3 | ApprovalBypass, RefundAmountCorrect, FM-08 reply metric, ProposalAmountCorrect; regression test |
| M4 | Bootstrap, baseline v1, fixed merge, seeded regression block; harness_map eval |
| M5 | fm_map đủ; slice money_movement/adversarial/denial blocking |
| M6 | pass@k/pass^k, A/A hai bộ seed, sàn pass_hat_5=0.80 |
| M7 | Integrity/ratchet, mutation 3/3, bốn trap exit 1 |

Tài liệu: [eval card](eval_card.md), [PRD v1.1](PRD_v1.1.md), [taxonomy](failure_taxonomy.md), [judge audit](judge_audit.md), [trace case](trace_case.md), [log](../src/reports/lab9_validation.log).
Chạy lại từ gốc repo: `./.venv/Scripts/python.exe scripts/reproduce_lab9.py`; trên Linux/macOS dùng `.venv/bin/python`.
