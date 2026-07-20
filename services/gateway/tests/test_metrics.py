"""Unit tests for Prometheus metrics and cost accounting."""

from pathlib import Path

import pytest

from gateway.observability import metrics as m

PRICES = Path("services/gateway/config/prices.yaml")


def test_load_real_price_table() -> None:
    table = m.load_price_table(PRICES)
    assert table["anthropic.claude-3-haiku-20240307-v1:0"] == {
        "prompt": 0.00025,
        "completion": 0.00125,
    }
    assert table["qwen2.5-0.5b-instruct"] == {"prompt": 0.0, "completion": 0.0}


def test_load_price_table_missing_file_returns_empty(tmp_path) -> None:
    assert m.load_price_table(tmp_path / "nope.yaml") == {}


def test_estimate_cost_usd() -> None:
    table = m.load_price_table(PRICES)
    cost = m.estimate_cost_usd("anthropic.claude-3-haiku-20240307-v1:0", 1000, 500, table)
    assert cost == pytest.approx(0.000875)


def test_estimate_cost_unknown_model_is_zero() -> None:
    assert m.estimate_cost_usd("mystery-model", 1000, 500, {}) == 0.0


def test_record_completion_increments_counters() -> None:
    labels = {"route": "chat", "model": "m1", "provider": "p1"}
    before_prompt = m.TOKENS_TOTAL.labels(direction="prompt", **labels)._value.get()
    before_cost = m.COST_TOTAL.labels(route="chat", model="m1")._value.get()

    m.record_completion(
        route="chat",
        provider="p1",
        model="m1",
        prompt_tokens=10,
        completion_tokens=5,
        latency_s=0.2,
        ttft_s=0.05,
        cost_usd=0.001,
        code="200",
    )

    assert m.TOKENS_TOTAL.labels(direction="prompt", **labels)._value.get() == before_prompt + 10
    assert m.COST_TOTAL.labels(route="chat", model="m1")._value.get() == pytest.approx(
        before_cost + 0.001
    )


def test_request_duration_has_code_label() -> None:
    # The canary AnalysisTemplate's error-rate query slices on the code label.
    assert set(m.REQUEST_DURATION._labelnames) == {"route", "model", "provider", "code"}


def test_track_inflight_gauge_round_trip() -> None:
    gauge = m.INFLIGHT.labels(route="chat")
    baseline = gauge._value.get()
    with m.track_inflight("chat"):
        assert gauge._value.get() == baseline + 1
    assert gauge._value.get() == baseline


def test_canary_probe_gauge_exists_and_settable() -> None:
    m.CANARY_PROBE_SUCCESS.set(1.0)
    assert m.CANARY_PROBE_SUCCESS._value.get() == 1.0
    m.CANARY_PROBE_SUCCESS.set(0.0)
    assert m.CANARY_PROBE_SUCCESS._value.get() == 0.0


def test_track_upstream_inflight_round_trip() -> None:
    gauge = m.UPSTREAM_INFLIGHT.labels(upstream="model-serving")
    baseline = gauge._value.get()
    with m.track_upstream_inflight("model-serving"):
        assert gauge._value.get() == baseline + 1
    assert gauge._value.get() == baseline
