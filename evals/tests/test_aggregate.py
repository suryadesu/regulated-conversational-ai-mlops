"""Unit tests for vote aggregation and suite math."""

import pytest

from eval_harness.aggregate import aggregate_votes, classify_failure, suite_pass_rate
from eval_harness.runner import CaseResult


def _result(passed: bool) -> CaseResult:
    return CaseResult(
        case_id="c", passed=passed, votes=[], details="", kind="deterministic"
    )


def test_aggregate_votes_majority() -> None:
    assert aggregate_votes([True, True, True, True, False], min_pass=4) is True
    assert aggregate_votes([True, True, True, False, False], min_pass=4) is False


def test_suite_pass_rate() -> None:
    results = [_result(True), _result(True), _result(False), _result(True)]
    assert suite_pass_rate(results) == pytest.approx(0.75)


def test_classify_failure_bands() -> None:
    assert classify_failure([False] * 5) == "regression"
    assert classify_failure([True] + [False] * 4) == "regression"
    assert classify_failure([True, True, False, False, False]) == "variance"  # 2 passes
    assert classify_failure([True, True, True, True, False]) == "variance"  # 4 passes
