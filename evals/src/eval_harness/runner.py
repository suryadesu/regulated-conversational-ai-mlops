"""Eval case model, loading, and per-case execution against the gateway."""

import math
from pathlib import Path

import httpx
import yaml
from pydantic import BaseModel, Field

from eval_harness.assertions import assert_contains, assert_json_schema, assert_regex


class EvalCase(BaseModel):
    """A single eval case: a prompt plus deterministic assertions and/or a judge rubric."""

    id: str  # unique case identifier
    prompt: str  # user prompt sent to the gateway
    assertions: list[dict] = Field(default_factory=list)  # deterministic assertion specs
    rubric: str | None = None  # judge rubric for LLM-as-judge cases
    repeats: int = 1  # judge repetitions for majority voting


class CaseResult(BaseModel):
    """The outcome of running one eval case."""

    case_id: str  # id of the case that produced this result
    passed: bool  # overall pass/fail after aggregation
    votes: list[bool]  # per-repeat pass/fail votes (judged cases)
    details: str  # human-readable explanation of the outcome
    kind: str  # "deterministic" | "judged" — the gate applies different criteria per kind


def load_cases(cases_dir: Path) -> list[EvalCase]:
    """Load and validate all eval cases from a directory of YAML files.

    Args:
        cases_dir: Path — directory containing deterministic.yaml and judged.yaml.

    Returns:
        list[EvalCase] — the parsed, validated cases (empty files yield nothing).
    """
    cases: list[EvalCase] = []
    for path in sorted(cases_dir.glob("*.yaml")):
        data = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
        for raw in data.get("cases") or []:
            cases.append(EvalCase(**raw))
    return cases


def _check_assertion(response: str, spec: dict) -> bool:
    kind = spec["type"]
    if kind == "contains":
        return assert_contains(response, spec["expected"])
    if kind == "regex":
        return assert_regex(response, spec["pattern"])
    if kind == "json_schema":
        return assert_json_schema(response, spec["schema"])
    raise ValueError(f"unknown assertion type: {kind}")


async def run_case(case: EvalCase, gateway_url: str, judge_url: str | None) -> CaseResult:
    """Run a single case against the gateway and evaluate assertions and/or the judge.

    A judged case generates ONE response and judges it ``repeats`` times —
    judge-vote variance is isolated from response-generation variance.

    Args:
        case: EvalCase — the case to run.
        gateway_url: str — base URL of the gateway under test.
        judge_url: str | None — judge base URL; None runs deterministic assertions only.

    Returns:
        CaseResult — the case outcome including per-repeat votes.
    """
    from eval_harness.aggregate import aggregate_votes
    from eval_harness.judge import judge_response

    async with httpx.AsyncClient(base_url=gateway_url, timeout=60.0) as client:
        reply = await client.post(
            "/v1/chat/completions",
            json={"messages": [{"role": "user", "content": case.prompt}]},
        )
        reply.raise_for_status()
        response_text = reply.json()["content"]

    if case.rubric is None or judge_url is None:
        passed = all(_check_assertion(response_text, spec) for spec in case.assertions)
        return CaseResult(
            case_id=case.id,
            passed=passed,
            votes=[],
            details=response_text[:500],
            kind="deterministic",
        )

    votes = [
        (await judge_response(judge_url, case.rubric, case.prompt, response_text)).passed
        for _ in range(case.repeats)
    ]
    min_pass = max(1, math.ceil(0.8 * case.repeats))
    return CaseResult(
        case_id=case.id,
        passed=aggregate_votes(votes, min_pass),
        votes=votes,
        details=response_text[:500],
        kind="judged",
    )
