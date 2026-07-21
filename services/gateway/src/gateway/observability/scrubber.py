"""PII scrubbing applied to any exported telemetry."""

import re

PATTERNS: dict[str, re.Pattern[str]] = {
    "email": re.compile(r"[\w.+-]+@[\w-]+\.[\w.-]+"),
    "iban": re.compile(r"\b[A-Z]{2}\d{2}[A-Z0-9]{10,30}\b"),
    # Phone requires a leading + or an internal separator, so bare digit runs
    # (PAN candidates, reference numbers) are never phone false-positives.
    "phone": re.compile(r"\+\d[\d\s\-()]{7,}\d|\b\d{3}[\s\-]\d{3}[\s\-]\d{4}\b"),
    "pan": re.compile(r"\b(?:\d[ -]?){13,19}\b"),
}

# Application order: email/iban first so their digit runs aren't partially
# consumed by the phone/pan patterns.
_ORDER = ("email", "iban", "phone", "pan")


def _luhn_ok(digits: str) -> bool:
    """Whether a digit string passes the Luhn checksum (PAN plausibility gate)."""
    total = 0
    for i, ch in enumerate(reversed(digits)):
        d = ord(ch) - 48
        if i % 2 == 1:
            d *= 2
            if d > 9:
                d -= 9
        total += d
    return total % 10 == 0


def _redact_pan(match: re.Match[str]) -> str:
    digits = re.sub(r"[ -]", "", match.group(0))
    if 13 <= len(digits) <= 19 and _luhn_ok(digits):
        return "[REDACTED_PAN]"
    return match.group(0)


def scrub_text(text: str) -> str:
    """Redact PII matches (email, phone, PAN via Luhn, IBAN/account) from a string.

    Args:
        text: str — raw text possibly containing PII.

    Returns:
        str — text with PII spans replaced by redaction tokens.
    """
    for name in _ORDER:
        if name == "pan":
            text = PATTERNS[name].sub(_redact_pan, text)
        else:
            text = PATTERNS[name].sub(f"[REDACTED_{name.upper()}]", text)
    return text


def scrub_attributes(attributes: dict[str, str]) -> dict[str, str]:
    """Apply scrub_text to every value in a span/log attribute mapping.

    Args:
        attributes: dict[str, str] — telemetry attributes to sanitize.

    Returns:
        dict[str, str] — attributes with values scrubbed.
    """
    return {key: scrub_text(value) for key, value in attributes.items()}
