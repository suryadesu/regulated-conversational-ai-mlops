"""Deterministic response generation for the provider stub."""

from pathlib import Path


def deterministic_response(messages: list[dict], canned_dir: Path) -> str:
    """Return a deterministic assistant reply keyed on a hash of the last user message.

    Args:
        messages: list[dict] — OpenAI-style message list.
        canned_dir: Path — directory of canned responses indexed by message hash.

    Returns:
        str — the deterministic assistant reply text.
    """
    raise NotImplementedError


def judge_verdict_response(prompt: str) -> str:
    """Return a deterministic judge-verdict JSON string for judge-mode requests.

    Args:
        prompt: str — the judge prompt being scored.

    Returns:
        str — JSON verdict {"passed", "score", "rationale"}.
    """
    raise NotImplementedError


def chunk_response(text: str, n_chunks: int) -> list[str]:
    """Split a response into N chunks for SSE streaming.

    Args:
        text: str — full response text.
        n_chunks: int — number of chunks to split into.

    Returns:
        list[str] — the text split into n_chunks pieces.
    """
    raise NotImplementedError
