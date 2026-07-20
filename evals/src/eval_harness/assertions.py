"""Deterministic assertion helpers for eval cases."""

import json
import re

import jsonschema


def assert_contains(response: str, expected: list[str]) -> bool:
    """Whether the response contains every expected substring.

    Args:
        response: str — model response text.
        expected: list[str] — substrings that must all be present.

    Returns:
        bool — True when every expected substring occurs.
    """
    return all(item in response for item in expected)


def assert_regex(response: str, pattern: str) -> bool:
    """Whether the response matches a regular expression.

    Args:
        response: str — model response text.
        pattern: str — regex searched anywhere in the response.

    Returns:
        bool — True when the pattern matches.
    """
    return re.search(pattern, response) is not None


def assert_json_schema(response: str, schema: dict) -> bool:
    """Whether the response parses as JSON conforming to a schema.

    Args:
        response: str — model response text (expected to be JSON).
        schema: dict — JSON-Schema document to validate against.

    Returns:
        bool — True when the response is valid JSON satisfying the schema.
    """
    try:
        jsonschema.validate(json.loads(response), schema)
    except (json.JSONDecodeError, jsonschema.ValidationError):
        return False
    return True
