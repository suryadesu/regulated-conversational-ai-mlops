"""Vote aggregation and suite-level gating math."""

from eval_harness.runner import CaseResult


def aggregate_votes(votes: list[bool], min_pass: int) -> bool:
    """Whether a judged case passes by majority vote.

    Args:
        votes: list[bool] — per-repeat pass/fail votes.
        min_pass: int — minimum passing votes required (e.g. 4 of 5).

    Returns:
        bool — True if passing votes meet or exceed min_pass.
    """
    return sum(votes) >= min_pass


def suite_pass_rate(results: list[CaseResult]) -> float:
    """Compute the fraction of cases that passed across the suite.

    Raises ZeroDivisionError on an empty list by design — the empty-suite
    decision belongs to evaluate_gate, not here.

    Args:
        results: list[CaseResult] — all case results.

    Returns:
        float — pass rate in [0, 1].
    """
    return sum(1 for r in results if r.passed) / len(results)


def classify_failure(votes: list[bool]) -> str:
    """Classify a judged failure as regression or variance from its vote split.

    0–1 passing votes is a consistent failure (regression); any wider split is
    judge variance. The 2-of-5 boundary counts as variance.

    Args:
        votes: list[bool] — per-repeat pass/fail votes (out of 5).

    Returns:
        str — "regression" for 0-1 passes, "variance" otherwise.
    """
    return "regression" if sum(votes) <= 1 else "variance"
