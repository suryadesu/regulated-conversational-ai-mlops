"""PII scrubbing applied to any exported telemetry."""

import re

PATTERNS: dict[str, re.Pattern[str]] = {}  # name -> compiled regex (email/phone/pan/iban)


def scrub_text(text: str) -> str:
    """Redact PII matches (email, phone, PAN via Luhn, IBAN/account) from a string.

    Args:
        text: str — raw text possibly containing PII.

    Returns:
        str — text with PII spans replaced by redaction tokens.
    """
    raise NotImplementedError


def scrub_attributes(attributes: dict[str, str]) -> dict[str, str]:
    """Apply scrub_text to every value in a span/log attribute mapping.

    Args:
        attributes: dict[str, str] — telemetry attributes to sanitize.

    Returns:
        dict[str, str] — attributes with values scrubbed.
    """
    raise NotImplementedError
