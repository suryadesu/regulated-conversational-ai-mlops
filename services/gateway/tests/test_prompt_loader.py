"""Unit tests for versioned prompt loading and rendering."""

from pathlib import Path

import pytest

from gateway.prompts.loader import PromptTemplate, load_prompt, render_system_prompt


def test_load_real_pinned_prompt() -> None:
    template = load_prompt(Path("prompts"), "customer-support", "v1.0.0")
    assert template.id == "customer-support"
    assert template.version == "v1.0.0"
    assert "{bank_name}" in template.system
    assert set(template.variables) == {"bank_name", "tone"}


def test_render_with_runtime_override() -> None:
    template = load_prompt(Path("prompts"), "customer-support", "v1.0.0")
    rendered = render_system_prompt(template, {"bank_name": "Acme Bank"})
    assert "Acme Bank" in rendered
    assert "{bank_name}" not in rendered
    assert "{tone}" not in rendered  # default filled from template variables


def test_missing_prompt_raises_file_not_found() -> None:
    with pytest.raises(FileNotFoundError, match="no prompt customer-support/v9.9.9"):
        load_prompt(Path("prompts"), "customer-support", "v9.9.9")


def test_unfilled_placeholder_raises_key_error() -> None:
    template = PromptTemplate(
        id="x", version="v0.0.1", system="Hello {missing_var}", variables={}
    )
    with pytest.raises(KeyError):
        render_system_prompt(template, {})
