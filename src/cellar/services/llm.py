from anthropic import Anthropic, AnthropicBedrock

from cellar.config import ModelProvider, Settings

LlmClient = Anthropic | AnthropicBedrock


def build_client(settings: Settings, api_key: str | None = None) -> LlmClient:
    if settings.provider is ModelProvider.BEDROCK:
        return AnthropicBedrock(aws_region=settings.aws_region)
    if api_key is not None:
        return Anthropic(api_key=api_key)
    return Anthropic()
