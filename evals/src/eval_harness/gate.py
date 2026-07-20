"""CI eval gate: run the suite, write the report, and decide pass/fail."""

import asyncio
import json
import os
import sys
from datetime import UTC, datetime
from pathlib import Path

from pydantic import BaseModel

from eval_harness.aggregate import classify_failure, suite_pass_rate
from eval_harness.runner import CaseResult, load_cases, run_case


class GateDecision(BaseModel):
    """The blocking gate decision for a suite run."""

    passed: bool  # whether the suite cleared the gate threshold
    pass_rate: float  # observed suite pass rate in [0, 1]
    failures: list[str]  # ids of cases that blocked the gate


def evaluate_gate(results: list[CaseResult], threshold: float) -> GateDecision:
    """Decide whether the suite passes the gate.

    An empty suite FAILS (a pipeline that collected zero cases is broken, not
    vacuously green), and a single deterministic failure blocks regardless of
    the overall rate — deterministic cases must pass 100%.

    Args:
        results: list[CaseResult] — all case results.
        threshold: float — minimum suite pass rate required to pass the gate.

    Returns:
        GateDecision — the gate outcome and blocking failures.
    """
    if not results:
        return GateDecision(passed=False, pass_rate=0.0, failures=["no eval cases loaded"])
    rate = suite_pass_rate(results)
    deterministic_failures = [
        r.case_id for r in results if r.kind == "deterministic" and not r.passed
    ]
    judged_failures = [r.case_id for r in results if r.kind == "judged" and not r.passed]
    passed = rate >= threshold and not deterministic_failures
    return GateDecision(
        passed=passed, pass_rate=rate, failures=deterministic_failures + judged_failures
    )


def write_report(results: list[CaseResult], path: Path) -> None:
    """Write the per-case report artifact, including per-repeat vote counts.

    Args:
        results: list[CaseResult] — all case results.
        path: Path — output path for the report artifact.
    """
    payload = {
        "generated_at": datetime.now(UTC).isoformat(),
        "results": [
            {
                "case_id": r.case_id,
                "kind": r.kind,
                "passed": r.passed,
                "votes": r.votes,
                "classification": classify_failure(r.votes) if r.votes else None,
                "details": r.details,
            }
            for r in results
        ],
    }
    path.write_text(json.dumps(payload, indent=2), encoding="utf-8")


def main() -> int:
    """CLI entrypoint: run the suite, write the report, exit non-zero on gate failure.

    Environment: EVAL_GATEWAY_URL (default http://localhost:8000), EVAL_JUDGE_URL
    (default http://localhost:8080), EVAL_CASES_DIR (default evals/cases),
    EVAL_THRESHOLD (default 0.90), EVAL_REPORT_PATH (default eval-report.json).

    Returns:
        int — process exit code; non-zero when the gate fails.
    """
    gateway_url = os.environ.get("EVAL_GATEWAY_URL", "http://localhost:8000")
    judge_url = os.environ.get("EVAL_JUDGE_URL", "http://localhost:8080")
    cases_dir = Path(os.environ.get("EVAL_CASES_DIR", "evals/cases"))
    threshold = float(os.environ.get("EVAL_THRESHOLD", "0.90"))
    report_path = Path(os.environ.get("EVAL_REPORT_PATH", "eval-report.json"))

    async def run_suite() -> list[CaseResult]:
        cases = load_cases(cases_dir)
        return [await run_case(case, gateway_url, judge_url) for case in cases]

    results = asyncio.run(run_suite())
    decision = evaluate_gate(results, threshold)
    write_report(results, report_path)
    print(
        f"eval gate: pass_rate={decision.pass_rate:.2%} passed={decision.passed} "
        f"failures={decision.failures} report={report_path}"
    )
    return 0 if decision.passed else 1


if __name__ == "__main__":
    sys.exit(main())
