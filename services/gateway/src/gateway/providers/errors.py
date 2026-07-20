"""Provider error hierarchy and mapping to the gateway HTTP error envelope."""

from fastapi.responses import JSONResponse


class ProviderError(Exception):
    """Base class for provider-side failures surfaced by the gateway."""


class ProviderTimeout(ProviderError):
    """Raised when a provider attempt or the total budget exceeds its timeout (HTTP 504)."""


class ProviderRateLimited(ProviderError):
    """Raised when the provider returns 429 after retries are exhausted (HTTP 429)."""


class ProviderUnavailable(ProviderError):
    """Raised on a non-retryable 5xx or exhausted retries (HTTP 502)."""


def to_error_response(exc: Exception, request_id: str) -> JSONResponse:
    """Map a provider exception to the gateway JSON error envelope and HTTP status.

    Args:
        exc: Exception — the raised provider error (or unexpected exception).
        request_id: str — correlation id echoed to the client.

    Returns:
        JSONResponse — {"error": {code, message, retryable, request_id}} with mapped HTTP status.
    """
    raise NotImplementedError
