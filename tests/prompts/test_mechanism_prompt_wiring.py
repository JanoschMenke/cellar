from cellar.prompts.mechanism import moa_context_prompt
from cellar.schemas.domain import CONTEXT_CONDITIONS, NECESSITY
from cellar.services.derivation.mechanism import build_moa_context


def _fake_mcp(server: str, tool: str, **kwargs: object) -> dict[str, object]:
    if tool == "search_articles":
        return {"pmids": ["222"]}
    return {
        "articles": [
            {
                "identifiers": {"pmid": "222"},
                "title": "A Paper About Mechanism",
                "abstract": "Some abstract content about the mechanism.",
            }
        ]
    }


def test_build_moa_context_sends_the_prompt_built_by_moa_context_prompt() -> None:
    captured_prompts: list[str] = []

    def fake_llm(prompt: str, **kwargs: object) -> dict[str, str]:
        captured_prompts.append(prompt)
        return {"text": "[]"}

    build_moa_context(
        "ZDHHC20",
        "pancreatic cancer",
        mcp=_fake_mcp,
        llm=fake_llm,
    )

    evidence = "[PMID 222] A Paper About Mechanism\nSome abstract content about the mechanism."
    expected_prompt = moa_context_prompt(
        target="ZDHHC20",
        disease="pancreatic cancer",
        evidence=evidence,
        context_conditions=CONTEXT_CONDITIONS,
        necessity=NECESSITY,
    )

    assert captured_prompts[0] == expected_prompt
