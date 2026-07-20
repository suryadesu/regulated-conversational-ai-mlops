"""Runtime fault-injection configuration for the provider stub."""

import random

from pydantic import BaseModel


class FaultConfig(BaseModel):
    """Fault-injection parameters controlling stub failures and latency."""

    error_rate: float = 0.0  # probability [0,1] of injecting a 5xx error
    rate_limit_rate: float = 0.0  # probability [0,1] of injecting a 429
    latency_ms: int = 0  # artificial latency added to each response, in milliseconds
    fail_next: int = 0  # number of subsequent requests to fail deterministically


def should_inject_fault(config: FaultConfig) -> int | None:
    """Decide whether to inject a fault for the current request.

    Precedence: a pending ``fail_next`` budget always wins (decremented in place,
    returns 500), then a single random draw is checked against the 429 band
    ``[0, rate_limit_rate)`` and the 500 band ``[rate_limit_rate,
    rate_limit_rate + error_rate)``. Latency is applied by the caller, keeping
    this function pure decision logic.

    Args:
        config: FaultConfig — active fault-injection configuration.

    Returns:
        int | None — HTTP status code to inject, or None to proceed normally.
    """
    if config.fail_next > 0:
        config.fail_next -= 1
        return 500
    draw = random.random()
    if draw < config.rate_limit_rate:
        return 429
    if draw < config.rate_limit_rate + config.error_rate:
        return 500
    return None
