"""Runtime fault-injection configuration for the provider stub."""

from pydantic import BaseModel


class FaultConfig(BaseModel):
    """Fault-injection parameters controlling stub failures and latency."""

    error_rate: float = 0.0  # probability [0,1] of injecting a 5xx error
    rate_limit_rate: float = 0.0  # probability [0,1] of injecting a 429
    latency_ms: int = 0  # artificial latency added to each response, in milliseconds
    fail_next: int = 0  # number of subsequent requests to fail deterministically


def should_inject_fault(config: FaultConfig) -> int | None:
    """Decide whether to inject a fault for the current request.

    Args:
        config: FaultConfig — active fault-injection configuration.

    Returns:
        int | None — HTTP status code to inject, or None to proceed normally.
    """
    raise NotImplementedError
