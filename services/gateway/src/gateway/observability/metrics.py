"""Prometheus metrics and cost accounting for the gateway."""

from collections.abc import Iterator
from contextlib import AbstractContextManager, contextmanager
from pathlib import Path

import yaml
from fastapi import FastAPI
from prometheus_client import Counter, Gauge, Histogram, make_asgi_app

# Module-level singletons: repeated create_app() calls in tests would otherwise
# hit prometheus_client's duplicate-timeseries registration error.
TOKENS_TOTAL = Counter(
    "gateway_tokens_total",
    "Tokens processed by the gateway.",
    ["direction", "route", "model", "provider"],
)
REQUEST_DURATION = Histogram(
    "gateway_request_duration_seconds",
    "End-to-end request latency. The code label feeds the canary error-rate analysis.",
    ["route", "model", "provider", "code"],
)
TTFT = Histogram(
    "gateway_ttft_seconds",
    "Time to first token for streaming requests.",
    ["route", "model"],
)
COST_TOTAL = Counter(
    "gateway_cost_usd_total",
    "Estimated cost of completions in USD.",
    ["route", "model"],
)
INFLIGHT = Gauge(
    "gateway_inflight_requests",
    "Requests currently in flight (KEDA scaling signal).",
    ["route"],
)


def setup_metrics(app: FastAPI) -> None:
    """Register Prometheus metrics and mount the /metrics endpoint on the app.

    Args:
        app: FastAPI — the gateway application to instrument.
    """
    app.mount("/metrics", make_asgi_app())


def record_completion(
    route: str,
    provider: str,
    model: str,
    prompt_tokens: int,
    completion_tokens: int,
    latency_s: float,
    ttft_s: float | None,
    cost_usd: float,
    code: str = "200",
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
        code: str — HTTP status label for the duration histogram (default "200").
    """
    TOKENS_TOTAL.labels(
        direction="prompt", route=route, model=model, provider=provider
    ).inc(prompt_tokens)
    TOKENS_TOTAL.labels(
        direction="completion", route=route, model=model, provider=provider
    ).inc(completion_tokens)
    REQUEST_DURATION.labels(route=route, model=model, provider=provider, code=code).observe(
        latency_s
    )
    if ttft_s is not None:
        TTFT.labels(route=route, model=model).observe(ttft_s)
    COST_TOTAL.labels(route=route, model=model).inc(cost_usd)


def estimate_cost_usd(
    model: str,
    prompt_tokens: int,
    completion_tokens: int,
    price_table: dict[str, dict[str, float]],
) -> float:
    """Estimate request cost from token counts and the repo-versioned price table.

    An unknown model costs $0 — cost is an observability signal, not a
    correctness gate.

    Args:
        model: str — model identifier keyed into the price table.
        prompt_tokens: int — tokens consumed by the prompt.
        completion_tokens: int — tokens produced in the completion.
        price_table: dict[str, dict[str, float]] — model -> {prompt, completion} $/1k-token prices.

    Returns:
        float — estimated cost in USD.
    """
    entry = price_table.get(model, {"prompt": 0.0, "completion": 0.0})
    return (prompt_tokens / 1000) * entry["prompt"] + (completion_tokens / 1000) * entry[
        "completion"
    ]


def load_price_table(path: Path) -> dict[str, dict[str, float]]:
    """Load the per-model price table from YAML.

    A missing file degrades to an empty table (cost=$0) rather than crashing
    startup.

    Args:
        path: Path — path to prices.yaml.

    Returns:
        dict[str, dict[str, float]] — model -> {prompt, completion} $/1k-token prices.
    """
    if not path.is_file():
        return {}
    return yaml.safe_load(path.read_text(encoding="utf-8")) or {}


def track_inflight(route: str) -> AbstractContextManager[None]:
    """Return a context manager that increments then decrements the in-flight gauge for a route.

    Args:
        route: str — logical route/intent label.

    Returns:
        AbstractContextManager[None] — scope whose exit decrements the gauge.
    """

    @contextmanager
    def scope() -> Iterator[None]:
        gauge = INFLIGHT.labels(route=route)
        gauge.inc()
        try:
            yield
        finally:
            gauge.dec()

    return scope()
