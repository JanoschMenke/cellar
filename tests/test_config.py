from cellar.config import Settings


def test_verifier_tuning_defaults() -> None:
    settings = Settings()

    assert settings.verifier_max_tool_rounds == 4
    assert settings.verifier_max_tokens == 3000
