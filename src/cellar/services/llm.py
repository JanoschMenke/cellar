import os
from pathlib import Path

from anthropic import Anthropic, AnthropicBedrock

from cellar.config import ModelProvider, Settings
from cellar.schemas.services import LlmClient

__all__ = [
    "LlmClient",
    "build_client",
    "has_api_key",
    "needs_api_key",
    "write_api_key_to_env",
]

_ANTHROPIC_API_KEY_ENV_VAR = "ANTHROPIC_API_KEY"


def build_client(settings: Settings, api_key: str | None = None) -> LlmClient:
    if settings.provider is ModelProvider.BEDROCK:
        return AnthropicBedrock(aws_region=settings.aws_region)
    if api_key is not None:
        return Anthropic(api_key=api_key)
    return Anthropic()


def has_api_key() -> bool:
    return bool(os.environ.get(_ANTHROPIC_API_KEY_ENV_VAR))


def needs_api_key(settings: Settings) -> bool:
    return settings.provider is ModelProvider.DIRECT_API and not has_api_key()


def write_api_key_to_env(key: str, path: Path) -> None:
    prefix = f"{_ANTHROPIC_API_KEY_ENV_VAR}="
    existing_lines = path.read_text().splitlines() if path.exists() else []
    updated_lines: list[str] = []
    replaced = False
    for line in existing_lines:
        if not replaced and line.startswith(prefix):
            updated_lines.append(f"{prefix}{key}")
            replaced = True
        else:
            updated_lines.append(line)
    if not replaced:
        updated_lines.append(f"{prefix}{key}")
    path.write_text("\n".join(updated_lines) + "\n")
