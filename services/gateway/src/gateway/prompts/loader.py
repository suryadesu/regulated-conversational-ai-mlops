"""Versioned prompt loading and rendering."""

from pathlib import Path

from pydantic import BaseModel


class PromptTemplate(BaseModel):
    """A pinned, versioned prompt template loaded from prompts/<name>/vX.Y.Z.yaml."""

    id: str  # prompt family identifier
    version: str  # semantic version pinned by the environment overlay
    system: str  # system prompt text containing {placeholder} variables
    variables: dict[str, str]  # default values for template variables


def load_prompt(prompt_dir: Path, name: str, version: str) -> PromptTemplate:
    """Load and validate a pinned prompt version from the on-disk prompt store.

    Args:
        prompt_dir: Path — root directory of the versioned prompt store.
        name: str — prompt family name (subdirectory under prompt_dir).
        version: str — exact version file to load (e.g. "v1.0.0").

    Returns:
        PromptTemplate — the parsed, validated template.
    """
    raise NotImplementedError


def render_system_prompt(template: PromptTemplate, variables: dict[str, str]) -> str:
    """Render the template system prompt, with runtime variables overriding template defaults.

    Args:
        template: PromptTemplate — the loaded prompt template.
        variables: dict[str, str] — runtime variable overrides.

    Returns:
        str — the fully rendered system prompt.
    """
    raise NotImplementedError
