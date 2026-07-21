"""Unit tests for fault-injection decision logic."""

from provider_stub.faults import FaultConfig, should_inject_fault


def test_no_faults_configured_returns_none() -> None:
    config = FaultConfig()
    for _ in range(20):
        assert should_inject_fault(config) is None


def test_fail_next_decrements_and_returns_500_exactly_n_times() -> None:
    config = FaultConfig(fail_next=3)
    codes = [should_inject_fault(config) for _ in range(5)]
    assert codes[:3] == [500, 500, 500]
    assert codes[3:] == [None, None]
    assert config.fail_next == 0


def test_fail_next_takes_precedence_over_probabilities(monkeypatch) -> None:
    # Even with rate_limit_rate=1.0 (which alone would give 429), fail_next wins with 500.
    config = FaultConfig(fail_next=1, rate_limit_rate=1.0)
    assert should_inject_fault(config) == 500
    # fail_next exhausted; now the probability path applies.
    assert should_inject_fault(config) == 429


def test_rate_limit_band_then_error_band(monkeypatch) -> None:
    config = FaultConfig(rate_limit_rate=0.3, error_rate=0.3)
    monkeypatch.setattr("provider_stub.faults.random.random", lambda: 0.2)
    assert should_inject_fault(config) == 429  # inside [0, 0.3)
    monkeypatch.setattr("provider_stub.faults.random.random", lambda: 0.5)
    assert should_inject_fault(config) == 500  # inside [0.3, 0.6)
    monkeypatch.setattr("provider_stub.faults.random.random", lambda: 0.9)
    assert should_inject_fault(config) is None  # outside both bands
