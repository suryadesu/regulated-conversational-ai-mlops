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
    raise NotImplementedError


def suite_pass_rate(results: list[CaseResult]) -> float:
    """Compute the fraction of cases that passed across the suite.

    Args:
        results: list[CaseResult] — all case results.

    Returns:
        float — pass rate in [0, 1].
    """
    raise NotImplementedError


def classify_failure(votes: list[bool]) -> str:
    """Classify a judged failure as regression or variance from its vote split.

    Args:
        votes: list[bool] — per-repeat pass/fail votes (out of 5).

    Returns:
        str — "regression" for 0-1 passes, "variance" for 3-4 passes.
    """
    raise NotImplementedError
