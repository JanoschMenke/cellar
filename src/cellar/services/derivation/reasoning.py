from functools import lru_cache

from anthropic.types import TextBlock

from cellar.config import Settings, load_settings
from cellar.services.llm import LlmClient, build_client


@lru_cache(maxsize=1)
def _client_and_settings() -> tuple[LlmClient, Settings]:
    settings = load_settings()
    return build_client(settings), settings


_JSON_SYSTEM = (
    "When asked to return JSON, output only strict valid JSON: no markdown fences, "
    "no comments, no trailing commas, and never truncate the structure."
)


def llm(prompt: str, model: str | None = None) -> dict[str, str]:
    client, settings = _client_and_settings()
    response = client.messages.create(
        model=model or settings.model_name,
        max_tokens=4096,
        system=_JSON_SYSTEM,
        messages=[{"role": "user", "content": prompt}],
    )
    text = "".join(block.text for block in response.content if isinstance(block, TextBlock))
    return {"text": text}
