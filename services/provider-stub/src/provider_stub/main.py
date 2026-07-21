"""Deterministic OpenAI-compatible provider stub with runtime fault injection."""

import asyncio
import json
import os
import uuid
from pathlib import Path

from fastapi import FastAPI, Response
from fastapi.responses import JSONResponse
from sse_starlette.sse import EventSourceResponse

from provider_stub.faults import FaultConfig, should_inject_fault
from provider_stub.responses import chunk_response, deterministic_response, judge_verdict_response

_fault_config = FaultConfig()
_canned_dir = Path(
    os.environ.get("PROVIDER_STUB_CANNED_DIR", Path(__file__).resolve().parents[2] / "canned")
)


def create_app() -> FastAPI:
    """Construct the stub app exposing /v1/chat/completions and the POST /__faults control endpoint.

    Returns:
        FastAPI — the configured stub application.
    """
    app = FastAPI(title="provider-stub")
    app.post("/v1/chat/completions")(chat_completions)
    app.post("/__faults")(set_faults)
    app.get("/healthz")(healthz)
    return app


async def healthz() -> dict[str, str]:
    """Liveness/readiness probe target for compose and k8s."""
    return {"status": "ok"}


async def chat_completions(payload: dict) -> Response:
    """Return a deterministic OpenAI-compatible completion, honoring stream and injected faults.

    Args:
        payload: dict — OpenAI-style chat completion request body.

    Returns:
        Response — JSON completion, an SSE stream when stream=True, or an injected error.
    """
    model = payload.get("model", "qwen2.5-0.5b-instruct")
    messages = payload["messages"]
    stream = payload.get("stream", False)

    if _fault_config.latency_ms:
        await asyncio.sleep(_fault_config.latency_ms / 1000)

    code = should_inject_fault(_fault_config)
    if code is not None:
        return JSONResponse(
            {"error": {"message": f"stub injected fault {code}"}}, status_code=code
        )

    if model == "judge":
        text = judge_verdict_response(messages[-1]["content"])
    else:
        text = deterministic_response(messages, _canned_dir)

    completion_id = f"stub-{uuid.uuid4()}"
    if not stream:
        prompt_tokens = sum(len(m["content"].split()) for m in messages)
        completion_tokens = len(text.split())
        return JSONResponse(
            {
                "id": completion_id,
                "object": "chat.completion",
                "model": model,
                "choices": [
                    {
                        "index": 0,
                        "message": {"role": "assistant", "content": text},
                        "finish_reason": "stop",
                    }
                ],
                "usage": {
                    "prompt_tokens": prompt_tokens,
                    "completion_tokens": completion_tokens,
                    "total_tokens": prompt_tokens + completion_tokens,
                },
            }
        )

    async def event_stream():
        for piece in chunk_response(text, 5):
            yield json.dumps(
                {
                    "id": completion_id,
                    "object": "chat.completion.chunk",
                    "model": model,
                    "choices": [
                        {"index": 0, "delta": {"content": piece}, "finish_reason": None}
                    ],
                }
            )
        yield json.dumps(
            {
                "id": completion_id,
                "object": "chat.completion.chunk",
                "model": model,
                "choices": [{"index": 0, "delta": {}, "finish_reason": "stop"}],
            }
        )
        yield "[DONE]"

    return EventSourceResponse(event_stream())


async def set_faults(config: FaultConfig) -> dict[str, str]:
    """Update the active fault-injection configuration (POST /__faults).

    Args:
        config: FaultConfig — new fault-injection parameters.

    Returns:
        dict[str, str] — acknowledgement document.
    """
    global _fault_config
    _fault_config = config
    return {"status": "updated"}
