import os
from enum import StrEnum

from pydantic import BaseModel


class ModelProvider(StrEnum):
    DIRECT_API = "direct_api"
    BEDROCK = "bedrock"


_DEFAULT_MODEL_BY_PROVIDER: dict[ModelProvider, str] = {
    ModelProvider.DIRECT_API: "claude-sonnet-4-6",
    ModelProvider.BEDROCK: "eu.anthropic.claude-sonnet-4-6",
}


class Settings(BaseModel):
    provider: ModelProvider = ModelProvider.DIRECT_API
    model_name: str = "claude-sonnet-4-6"
    aws_region: str = "eu-west-2"
    max_output_tokens: int = 8192
    max_agent_steps: int = 20
    workspace_dir: str = ".cellar"


def load_settings() -> Settings:
    provider = ModelProvider(os.environ.get("CELLAR_PROVIDER", ModelProvider.DIRECT_API))
    model_name = os.environ.get("CELLAR_MODEL_NAME", _DEFAULT_MODEL_BY_PROVIDER[provider])
    return Settings(
        provider=provider,
        model_name=model_name,
        aws_region=os.environ.get("AWS_REGION", "eu-west-2"),
        workspace_dir=os.environ.get("CELLAR_WORKSPACE_DIR", ".cellar"),
    )
