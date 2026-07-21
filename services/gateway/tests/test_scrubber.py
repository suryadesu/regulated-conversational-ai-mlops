"""Unit tests for the PII scrubber."""

from gateway.observability.scrubber import PATTERNS, scrub_attributes, scrub_text


def test_patterns_registry_has_the_four_kinds() -> None:
    assert set(PATTERNS) == {"email", "phone", "pan", "iban"}


def test_email_redacted() -> None:
    assert "a@b.com" not in scrub_text("contact a@b.com now")
    assert "[REDACTED_EMAIL]" in scrub_text("contact a@b.com now")


def test_phone_redacted() -> None:
    out = scrub_text("call me at +1 415-555-0100 today")
    assert "415-555-0100" not in out
    assert "[REDACTED_PHONE]" in out


def test_luhn_valid_pan_redacted() -> None:
    out = scrub_text("my card is 4532015112830366 ok")
    assert "4532015112830366" not in out
    assert "[REDACTED_PAN]" in out


def test_non_luhn_digits_not_redacted() -> None:
    out = scrub_text("reference number 1234567812345678 attached")
    assert "1234567812345678" in out


def test_iban_redacted() -> None:
    out = scrub_text("transfer to DE89370400440532013000 please")
    assert "DE89370400440532013000" not in out
    assert "[REDACTED_IBAN]" in out


def test_clean_text_unchanged() -> None:
    text = "hello, my order is late and I am unhappy"
    assert scrub_text(text) == text


def test_scrub_attributes_values_only() -> None:
    attrs = {"user.email": "a@b.com", "note": "clean"}
    out = scrub_attributes(attrs)
    assert set(out) == {"user.email", "note"}
    assert out["user.email"] == "[REDACTED_EMAIL]"
    assert out["note"] == "clean"
