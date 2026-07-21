"""Provider error hierarchy and mapping to the gateway HTTP error envelope."""

from fastapi.responses import JSONResponse


class ProviderError(Exception):
    """Base class for provider-side failures surfaced by the gateway."""

    def __init__(self, message: str, retryable: bool = True) -> None:
        super().__init__(message)
        self.message = message
        self.retryable = retryable


class ProviderTimeout(ProviderError):
    """Raised when a provider attempt or the total budget exceeds its timeout (HTTP 504)."""


class ProviderRateLimited(ProviderError):
    """Raised when the provider returns 429 after retries are exhausted (HTTP 429)."""

    def __init__(
        self, message: str, retryable: bool = True, retry_after: float | None = None
    ) -> None:
        super().__init__(message, retryable)
        self.retry_after = retry_after  # seconds, from a Retry-After header when present


class ProviderUnavailable(ProviderError):
    """Raised on a non-retryable 5xx or exhausted retries (HTTP 502)."""


_ENVELOPE_MAP: list[tuple[type[Exception], str, int, bool]] = [
    (ProviderTimeout, "provider_timeout", 504, True),
    (ProviderRateLimited, "provider_rate_limited", 429, True),
    (ProviderUnavailable, "provider_unavailable", 502, True),
]


def to_error_response(exc: Exception, request_id: str) -> JSONResponse:
    """Map a provider exception to the gateway JSON error envelope and HTTP status.

    Args:
        exc: Exception — the raised provider error (or unexpected exception).
        request_id: str — correlation id echoed to the client.

    Returns:
        JSONResponse — {"error": {code, message, retryable, request_id}} with mapped HTTP status.
    """
    code, status, retryable = "bad_request", 400, False
    for exc_type, mapped_code, mapped_status, mapped_retryable in _ENVELOPE_MAP:
        if isinstance(exc, exc_type):
            code, status, retryable = mapped_code, mapped_status, mapped_retryable
            break
    message = getattr(exc, "message", str(exc))
    return JSONResponse(
        {
            "error": {
                "code": code,
                "message": message,
                "retryable": retryable,
                "request_id": request_id,
            }
        },
        status_code=status,
    )
