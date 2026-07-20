"""LLM-as-judge scoring of model responses."""

import json

import httpx
from pydantic import BaseModel, ValidationError


class JudgeVerdict(BaseModel):
    """A single judge verdict for one response."""

    passed: bool  # whether the response satisfied the rubric
    score: int  # numeric score assigned by the judge
    rationale: str  # judge explanation


async def judge_response(judge_url: str, rubric: str, prompt: str, response: str) -> JudgeVerdict:
    """Score a response against a rubric using the judge model.

    The judge is addressed as ``model: "judge"`` on the OpenAI-compatible chat
    endpoint — the deterministic stub recognizes that model name in CI; a real
    model serves it in nightly runs.

    Args:
        judge_url: str — base URL of the judge model.
        rubric: str — grading rubric for this case.
        prompt: str — the original prompt shown to the model.
        response: str — the model response to grade.

    Returns:
        JudgeVerdict — the parsed judge verdict.
    """
    grading_prompt = (
        "Grade the following response against the rubric. Reply with JSON "
        '{"passed": bool, "score": 1-5, "rationale": str} only.\n'
        f"Rubric: {rubric}\nPrompt: {prompt}\nResponse: {response}"
    )
    async with httpx.AsyncClient(base_url=judge_url, timeout=30.0) as client:
        reply = await client.post(
            "/v1/chat/completions",
            json={"model": "judge", "messages": [{"role": "user", "content": grading_prompt}]},
        )
        reply.raise_for_status()
    return parse_verdict(reply.json()["choices"][0]["message"]["content"])


def parse_verdict(raw: str) -> JudgeVerdict:
    """Parse a judge model's raw text output into a structured verdict.

    A malformed judge reply is a FAILED VOTE, never a crashed suite.

    Args:
        raw: str — raw judge output (expected JSON, possibly markdown-fenced).

    Returns:
        JudgeVerdict — the parsed verdict, or a failed vote on parse errors.
    """
    cleaned = raw.strip()
    if cleaned.startswith("```"):
        cleaned = cleaned.removeprefix("```json").removeprefix("```")
        cleaned = cleaned.removesuffix("```").strip()
    try:
        return JudgeVerdict(**json.loads(cleaned))
    except (json.JSONDecodeError, TypeError, ValidationError):
        return JudgeVerdict(
            passed=False, score=0, rationale=f"unparseable judge output: {raw[:200]}"
        )
