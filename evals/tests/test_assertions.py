"""Unit tests for deterministic assertion helpers."""

from eval_harness.assertions import assert_contains, assert_json_schema, assert_regex


def test_contains_all_present() -> None:
    assert assert_contains("hello wonderful world", ["hello", "world"]) is True


def test_contains_missing_substring() -> None:
    assert assert_contains("hello world", ["hello", "absent"]) is False


def test_regex_match_and_miss() -> None:
    assert assert_regex("[stub:abcdef0123456789]", r"\[stub:[0-9a-f]{16}\]") is True
    assert assert_regex("no tag here", r"\[stub:[0-9a-f]{16}\]") is False


def test_json_schema_valid() -> None:
    schema = {"type": "object", "properties": {"a": {"type": "integer"}}, "required": ["a"]}
    assert assert_json_schema('{"a": 1}', schema) is True


def test_json_schema_violation() -> None:
    schema = {"type": "object", "properties": {"a": {"type": "integer"}}, "required": ["a"]}
    assert assert_json_schema('{"a": "not-int"}', schema) is False


def test_json_schema_invalid_json() -> None:
    assert assert_json_schema("not json at all", {}) is False
