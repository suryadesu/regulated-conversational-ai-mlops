"""Deterministic assertion helpers for eval cases."""


def assert_contains(response: str, expected: list[str]) -> bool:
    """Whether the response contains every expected substring.

    Args:
        response: str — the model response under test.
        expected: list[str] — substrings that must all be present.

    Returns:
        bool — True if all expected substrings are present.
    """
    raise NotImplementedError


def assert_regex(response: str, pattern: str) -> bool:
    """Whether the response matches a regular expression.

    Args:
        response: str — the model response under test.
        pattern: str — regular expression to search for.

    Returns:
        bool — True if the pattern matches.
    """
    raise NotImplementedError


def assert_json_schema(response: str, schema: dict) -> bool:
    """Whether the response parses as JSON conforming to a schema.

    Args:
        response: str — the model response under test.
        schema: dict — JSON schema the parsed response must satisfy.

    Returns:
        bool — True if the response is valid JSON matching the schema.
    """
    raise NotImplementedError
