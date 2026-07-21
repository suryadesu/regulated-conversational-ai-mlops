"""Unit tests for the provider error envelope."""

import json

from gateway.providers.errors import (
    ProviderRateLimited,
    ProviderTimeout,
    ProviderUnavailable,
    to_error_response,
)


def _body(resp) -> dict:
    return json.loads(resp.body)


def test_timeout_maps_to_504() -> None:
    resp = to_error_response(ProviderTimeout("upstream timed out"), request_id="req-1")
    assert resp.status_code == 504
    err = _body(resp)["error"]
    assert err["code"] == "provider_timeout"
    assert err["message"] == "upstream timed out"
    assert err["retryable"] is True
    assert err["request_id"] == "req-1"


def test_rate_limited_maps_to_429() -> None:
    resp = to_error_response(ProviderRateLimited("rate limited"), request_id="req-2")
    assert resp.status_code == 429
    assert _body(resp)["error"]["code"] == "provider_rate_limited"


def test_unavailable_maps_to_502() -> None:
    resp = to_error_response(ProviderUnavailable("boom"), request_id="req-3")
    assert resp.status_code == 502
    assert _body(resp)["error"]["code"] == "provider_unavailable"


def test_unknown_exception_maps_to_bad_request_400() -> None:
    resp = to_error_response(ValueError("bad input"), request_id="req-4")
    assert resp.status_code == 400
    err = _body(resp)["error"]
    assert err["code"] == "bad_request"
    assert err["retryable"] is False
