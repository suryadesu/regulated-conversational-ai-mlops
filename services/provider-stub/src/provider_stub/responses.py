"""Deterministic response generation for the provider stub."""

import hashlib
import json
from pathlib import Path


def deterministic_response(messages: list[dict], canned_dir: Path) -> str:
    """Return a deterministic assistant reply keyed on a hash of the last user message.

    A canned file ``<canned_dir>/<sha256[:16]>.txt`` wins when present; otherwise a
    stable hash-tagged echo is returned, so every prompt has an assertable reply
    without pre-authoring.

    Args:
        messages: list[dict] — OpenAI-style message list.
        canned_dir: Path — directory of canned responses indexed by message hash.

    Returns:
        str — the deterministic assistant reply text.
    """
    content = messages[-1]["content"]
    digest = hashlib.sha256(content.encode()).hexdigest()[:16]
    canned = canned_dir / f"{digest}.txt"
    if canned.is_file():
        return canned.read_text(encoding="utf-8").strip()
    return f"[stub:{digest}] Acknowledged: {content}"


def judge_verdict_response(prompt: str) -> str:
    """Return a deterministic judge-verdict JSON string for judge-mode requests.

    Args:
        prompt: str — the judge prompt being scored.

    Returns:
        str — JSON verdict {"passed", "score", "rationale"}.
    """
    if "FAIL_JUDGE" in prompt:
        return json.dumps(
            {"passed": False, "score": 1, "rationale": "stub: forced failure marker present"}
        )
    return json.dumps({"passed": True, "score": 5, "rationale": "stub: deterministic pass"})


def chunk_response(text: str, n_chunks: int) -> list[str]:
    """Split a response into N chunks for SSE streaming.

    Args:
        text: str — full response text.
        n_chunks: int — number of chunks to split into.

    Returns:
        list[str] — the text split into at most n_chunks pieces (never empty).
    """
    if n_chunks <= 1 or not text:
        return [text]
    n = min(n_chunks, len(text))
    size = len(text) // n
    chunks = [text[i * size : (i + 1) * size] for i in range(n - 1)]
    chunks.append(text[(n - 1) * size :])
    return chunks
