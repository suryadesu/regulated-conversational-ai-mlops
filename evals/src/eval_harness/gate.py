"""CI eval gate: run the suite, write the report, and decide pass/fail."""

from pathlib import Path

from pydantic import BaseModel

from eval_harness.runner import CaseResult


class GateDecision(BaseModel):
    """The blocking gate decision for a suite run."""

    passed: bool  # whether the suite cleared the gate threshold
    pass_rate: float  # observed suite pass rate in [0, 1]
    failures: list[str]  # ids of cases that blocked the gate


def evaluate_gate(results: list[CaseResult], threshold: float) -> GateDecision:
    """Decide whether the suite passes the gate.

    Args:
        results: list[CaseResult] — all case results.
        threshold: float — minimum suite pass rate required to pass the gate.

    Returns:
        GateDecision — the gate outcome and blocking failures.
    """
    raise NotImplementedError


def write_report(results: list[CaseResult], path: Path) -> None:
    """Write the per-case report artifact, including per-repeat vote counts.

    Args:
        results: list[CaseResult] — all case results.
        path: Path — output path for the report artifact.
    """
    raise NotImplementedError


def main() -> int:
    """CLI entrypoint: run the suite, write the report, exit non-zero on gate failure.

    Returns:
        int — process exit code; non-zero when the gate fails.
    """
    raise NotImplementedError
