"""Gateway runtime configuration."""

from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Environment-driven configuration for the gateway service."""

    model_config = SettingsConfigDict(env_prefix="GATEWAY_", env_file=".env", extra="ignore")

    provider: str = "openai_compat"  # adapter selector: "openai_compat" | "bedrock"
    provider_base_url: str = "http://provider-stub:8080/v1"  # base URL for openai_compat adapter
    bedrock_model_id: str = "anthropic.claude-3-haiku-20240307-v1:0"  # Bedrock Converse model id
    bedrock_endpoint_url: str | None = None  # floci endpoint locally; None uses real AWS
    request_timeout_s: float = 10.0  # per-attempt provider timeout in seconds
    total_timeout_s: float = 30.0  # total retry budget across attempts in seconds
    max_retries: int = 3  # total attempts including the first
    prompt_name: str = "customer-support"  # prompt family under the prompt dir
    prompt_version: str = "v1.0.0"  # pinned prompt version (never "latest")
    prompt_dir: Path = Path("prompts")  # repo-relative root of the versioned prompt store
    price_table_path: Path = Path("services/gateway/config/prices.yaml")  # $/1k-token price table
    otlp_endpoint: str | None = None  # OTLP collector endpoint; None disables trace export
    drain_timeout_s: float = 160.0  # max seconds to wait for in-flight streams on shutdown


def get_settings() -> Settings:
    """Build and return the process-wide settings singleton.

    Returns:
        Settings — configuration parsed from environment and defaults.
    """
    raise NotImplementedError
