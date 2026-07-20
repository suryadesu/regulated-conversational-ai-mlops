"""LLM-as-judge scoring of model responses."""

from pydantic import BaseModel


class JudgeVerdict(BaseModel):
    """A single judge verdict for one response."""

    passed: bool  # whether the response satisfied the rubric
    score: int  # numeric score assigned by the judge
    rationale: str  # judge explanation


async def judge_response(judge_url: str, rubric: str, prompt: str, response: str) -> JudgeVerdict:
    """Score a response against a rubric using the judge model.

    Args:
        judge_url: str — base URL of the judge model.
        rubric: str — grading rubric for this case.
        prompt: str — the original prompt shown to the model.
        response: str — the model response to grade.

    Returns:
        JudgeVerdict — the parsed judge verdict.
    """
    raise NotImplementedError


def parse_verdict(raw: str) -> JudgeVerdict:
    """Parse a judge model's raw text output into a structured verdict.

    Args:
        raw: str — raw judge output (expected JSON).

    Returns:
        JudgeVerdict — the parsed verdict.
    """
    raise NotImplementedError
