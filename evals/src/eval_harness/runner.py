"""Eval case model, loading, and per-case execution against the gateway."""

from pathlib import Path

from pydantic import BaseModel


class EvalCase(BaseModel):
    """A single eval case: a prompt plus deterministic assertions and/or a judge rubric."""

    id: str  # unique case identifier
    prompt: str  # user prompt sent to the gateway
    assertions: list[dict]  # deterministic assertion specs (type + args)
    rubric: str | None = None  # judge rubric for LLM-as-judge cases
    repeats: int = 1  # judge repetitions for majority voting


class CaseResult(BaseModel):
    """The outcome of running one eval case."""

    case_id: str  # id of the case that produced this result
    passed: bool  # overall pass/fail after aggregation
    votes: list[bool]  # per-repeat pass/fail votes (judged cases)
    details: str  # human-readable explanation of the outcome


def load_cases(cases_dir: Path) -> list[EvalCase]:
    """Load and validate all eval cases from a directory of YAML files.

    Args:
        cases_dir: Path — directory containing deterministic.yaml and judged.yaml.

    Returns:
        list[EvalCase] — the parsed, validated cases.
    """
    raise NotImplementedError


async def run_case(case: EvalCase, gateway_url: str, judge_url: str | None) -> CaseResult:
    """Run a single case against the gateway and evaluate assertions and/or the judge.

    Args:
        case: EvalCase — the case to run.
        gateway_url: str — base URL of the gateway under test.
        judge_url: str | None — judge base URL; None uses the deterministic judge stub.

    Returns:
        CaseResult — the case outcome including per-repeat votes.
    """
    raise NotImplementedError
