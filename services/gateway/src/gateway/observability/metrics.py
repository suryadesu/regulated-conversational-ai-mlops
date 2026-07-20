"""Prometheus metrics and cost accounting for the gateway."""

from contextlib import AbstractContextManager
from pathlib import Path

from fastapi import FastAPI


def setup_metrics(app: FastAPI) -> None:
    """Register Prometheus metrics and mount the /metrics endpoint on the app.

    Args:
        app: FastAPI — the gateway application to instrument.
    """
    raise NotImplementedError


def record_completion(
    route: str,
    provider: str,
    model: str,
    prompt_tokens: int,
    completion_tokens: int,
    latency_s: float,
    ttft_s: float | None,
    cost_usd: float,
) -> None:
    """Record token, latency, TTFT, and cost metrics for one completion.

    Args:
        route: str — logical route/intent label.
        provider: str — provider adapter label.
        model: str — model identifier label.
        prompt_tokens: int — tokens consumed by the prompt.
        completion_tokens: int — tokens produced in the completion.
        latency_s: float — end-to-end request latency in seconds.
        ttft_s: float | None — time-to-first-token for streams, None for unary.
        cost_usd: float — estimated request cost in USD.
    """
    raise NotImplementedError


def estimate_cost_usd(
    model: str,
    prompt_tokens: int,
    completion_tokens: int,
    price_table: dict[str, dict[str, float]],
) -> float:
    """Estimate request cost from token counts and the repo-versioned price table.

    Args:
        model: str — model identifier keyed into the price table.
        prompt_tokens: int — tokens consumed by the prompt.
        completion_tokens: int — tokens produced in the completion.
        price_table: dict[str, dict[str, float]] — model -> {prompt, completion} $/1k-token prices.

    Returns:
        float — estimated cost in USD.
    """
    raise NotImplementedError


def load_price_table(path: Path) -> dict[str, dict[str, float]]:
    """Load the per-model price table from YAML.

    Args:
        path: Path — path to prices.yaml.

    Returns:
        dict[str, dict[str, float]] — model -> {prompt, completion} $/1k-token prices.
    """
    raise NotImplementedError


def track_inflight(route: str) -> AbstractContextManager[None]:
    """Return a context manager that increments then decrements the in-flight gauge for a route.

    Args:
        route: str — logical route/intent label.

    Returns:
        AbstractContextManager[None] — scope whose exit decrements the gauge.
    """
    raise NotImplementedError
