"""Unit tests for the gate decision and report artifact."""

import json
from pathlib import Path

from eval_harness.gate import GateDecision, evaluate_gate, write_report
from eval_harness.runner import CaseResult


def _r(case_id: str, passed: bool, kind: str, votes: list[bool] | None = None) -> CaseResult:
    return CaseResult(case_id=case_id, passed=passed, votes=votes or [], details="", kind=kind)


def test_empty_suite_fails_gate() -> None:
    decision = evaluate_gate([], threshold=0.9)
    assert decision.passed is False
    assert decision.pass_rate == 0.0
    assert "no eval cases loaded" in decision.failures


def test_rate_above_threshold_with_clean_deterministic_passes() -> None:
    results = [_r(f"d{i}", True, "deterministic") for i in range(10)] + [
        _r("j1", True, "judged", [True] * 5),
        _r("j2", False, "judged", [True, True, False, False, False]),
    ]
    decision = evaluate_gate(results, threshold=0.9)
    assert decision.pass_rate > 0.9
    assert decision.passed is True
    assert decision.failures == ["j2"]


def test_single_deterministic_failure_blocks_regardless_of_rate() -> None:
    results = [_r(f"d{i}", True, "deterministic") for i in range(19)] + [
        _r("d-broken", False, "deterministic")
    ]
    decision = evaluate_gate(results, threshold=0.9)
    assert decision.pass_rate == 0.95
    assert decision.passed is False
    assert "d-broken" in decision.failures


def test_write_report_roundtrip(tmp_path: Path) -> None:
    results = [
        _r("d1", True, "deterministic"),
        _r("j1", False, "judged", [False] * 5),
    ]
    out = tmp_path / "report.json"
    write_report(results, out)
    data = json.loads(out.read_text(encoding="utf-8"))
    by_id = {r["case_id"]: r for r in data["results"]}
    assert by_id["d1"]["classification"] is None
    assert by_id["j1"]["classification"] == "regression"
    assert by_id["j1"]["votes"] == [False] * 5


def test_gate_decision_model_shape() -> None:
    d = GateDecision(passed=True, pass_rate=1.0, failures=[])
    assert d.model_dump() == {"passed": True, "pass_rate": 1.0, "failures": []}
