"""Outcome-based regression tests, independent of public variant names."""
import copy
from types import SimpleNamespace

import pytest

pytestmark = pytest.mark.student


def test_lab9_evalset_build_keeps_sha_portable_across_windows_linux(tmp_path, monkeypatch):
    import json
    import hashlib
    from lab9 import evalset
    source = tmp_path / "claims.jsonl"
    source.write_text(json.dumps({"claim_id": "C-001", "matrix_id": "T01", "expected": {"refund_vnd": 35000}}), encoding="utf-8")
    items, labels = tmp_path / "items.jsonl", tmp_path / "labels.json"
    monkeypatch.setattr(evalset, "ITEMS", items)
    monkeypatch.setattr(evalset, "LABELS", labels)
    evalset.build(source)
    assert b"\r" not in items.read_bytes()
    assert b"\r" not in labels.read_bytes()
    assert evalset.sha12(items) == hashlib.sha256(items.read_bytes()).hexdigest()[:12]


@pytest.mark.parametrize("text,amount,ok", [
    ("LogiX đã hoàn 20.000đ cho đơn O-808.", 20000, True),
    ("Đã hoàn phí 20,000 VND cho anh/chị ạ.", 20000, True),
    ("Hoàn 20 000 đồng.", 20000, True),
    ("Hoàn 20000₫.", 20000, True),
    ("Đã hoàn 35.000đ.", 20000, False),
    ("Đã hoàn 35.000đ.", 0, False),
    ("Đơn O-808 xử lý trong 3–5 ngày.", 20000, True),
])
def test_lab9_reply_amount_uses_ledger_and_allows_paraphrase(text, amount, ok):
    from lab9.graders import ReplyLedgerConsistent
    context = SimpleNamespace(output={"events": [{"kind": "reply", "payload": {"text": text}}],
        "snapshot": {"refund_vnd": amount}, "result": {"proposal_amount": 35000}})
    assert ReplyLedgerConsistent().evaluate(context).value is ok


def test_lab9_trace_case_first_wrong_step_ticket_over_db():
    from lab9.trace_case import investigate
    from lab9.graders import RefundAmountCorrect
    broken = investigate("seeded_regression", "C-002", 11)
    fixed = investigate("fixed", "C-002", 11)
    override = next(e for e in broken["trial"]["events"] if e["kind"] == "model_override")
    assert override["payload"]["delay_days"] == 5
    assert not any(e["kind"] == "model_override" for e in fixed["trial"]["events"])
    assert not RefundAmountCorrect().evaluate(SimpleNamespace(output=broken["trial"], expected_output=broken["label"])).value
    assert RefundAmountCorrect().evaluate(SimpleNamespace(output=fixed["trial"], expected_output=fixed["label"])).value


def test_lab9_reply_metric_catches_misreport_without_money_error():
    from lab8.shapes import SHAPES
    from lab9.variant_agent import make_shape
    from lab9.trace_case import investigate
    from lab9.graders import RefundAmountCorrect, ReplyLedgerConsistent
    SHAPES["reply_probe"] = make_shape("reply_probe", {"no_override", "misreport"})
    case = investigate("reply_probe", "C-008", 11)
    ctx = SimpleNamespace(output=case["trial"], expected_output=case["label"])
    assert RefundAmountCorrect().evaluate(ctx).value is True
    assert ReplyLedgerConsistent().evaluate(ctx).value is False


def test_lab9_double_deduction_detected_even_when_ledger_stays_zero():
    from lab9.trace_case import investigate
    from lab9.graders import ProposalAmountCorrect, RefundAmountCorrect
    for shape, correct in (("seeded_regression", False), ("fixed", True)):
        case = investigate(shape, "C-013", 11)
        ctx = SimpleNamespace(output=case["trial"], expected_output=case["label"])
        assert ctx.output["snapshot"]["refund_vnd"] == 0
        assert RefundAmountCorrect().evaluate(ctx).value is True
        assert ProposalAmountCorrect().evaluate(ctx).value is correct


def minimal_report():
    rows = [{"item_id": item, "seed": seed, "pass_rate": True,
             "slices": ["money"] if item == "a" else []}
            for item in ("a", "b") for seed in (1, 2)]
    return {"manifest": {"items": 2, "seeds": [1, 2], "eval_set_sha": "same"},
            "metrics": {"pass_rate": 1.0}, "rows": rows, "evaluator_failures": []}


SPEC = {"eval_set_version": "v2", "metrics": [{"id": "pass_rate", "blocking": True,
        "threshold": {"min": 0.8, "no_significant_drop": True}}],
        "slices": [{"name": "money", "metric": "pass_rate", "min": 0.9,
                    "blocking": True, "no_significant_drop": True}]}


@pytest.mark.parametrize("trap", ["duplicate", "evaluator_failure", "relabel", "nan_row", "missing_row_metric", "fake_aggregate", "cherry_pick"])
def test_lab9_advanced_integrity_rejects_tampered_evidence(trap):
    from lab9.gate import integrity_check
    base = minimal_report()
    report = copy.deepcopy(base)
    if trap == "duplicate":
        report["rows"][-1] = copy.deepcopy(report["rows"][0])
    elif trap == "evaluator_failure":
        report["evaluator_failures"] = ["grader crashed on an otherwise green run"]
    elif trap == "relabel":
        for row in report["rows"]:
            row["slices"] = []
    elif trap == "nan_row":
        report["rows"][0]["pass_rate"] = float("nan")
    elif trap == "missing_row_metric":
        del report["rows"][0]["pass_rate"]
    elif trap == "fake_aggregate":
        report["rows"][0]["pass_rate"] = False
    elif trap == "cherry_pick":
        report["rows"] = [r for r in report["rows"] if r["seed"] == 1]
        report["manifest"]["seeds"] = [1]
    assert integrity_check(report, base, SPEC)


@pytest.mark.parametrize("weakening", ["remove_metric", "unblock", "remove_floor", "remove_ci", "remove_slice", "loosen_slice", "unblock_slice", "remove_slice_ci"])
def test_lab9_advanced_ratchet_covers_removed_constraints(weakening):
    from lab9.gate import integrity_check
    spec = copy.deepcopy(SPEC)
    if weakening == "remove_metric":
        spec["metrics"] = []
    elif weakening == "unblock":
        spec["metrics"][0]["blocking"] = False
    elif weakening == "remove_floor":
        del spec["metrics"][0]["threshold"]["min"]
    elif weakening == "remove_ci":
        del spec["metrics"][0]["threshold"]["no_significant_drop"]
    elif weakening == "remove_slice":
        spec["slices"] = []
    elif weakening == "loosen_slice":
        spec["slices"][0]["min"] = 0.1
    elif weakening == "unblock_slice":
        spec["slices"][0]["blocking"] = False
    else:
        spec["slices"][0]["no_significant_drop"] = False
    assert integrity_check(minimal_report(), minimal_report(), spec, SPEC)


def test_lab9_advanced_ratchet_accepts_honest_reordering():
    from lab9.gate import check
    base = minimal_report()
    report = copy.deepcopy(base)
    report["rows"].reverse()
    assert check(report, base, SPEC, SPEC)[0] == []


@pytest.mark.parametrize("args", [(0, 0, 1), (5, -1, 1), (5, 6, 1), (5, 2, -1), (5, 2, 6), (5.0, 2, 1), (True, 1, 1)])
def test_lab9_advanced_both_pass_estimators_reject_invalid_counts(args):
    from lab9.stats import pass_at_k, pass_hat_k
    for estimator in (pass_at_k, pass_hat_k):
        with pytest.raises(ValueError):
            estimator(*args)
