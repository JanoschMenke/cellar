from cellar.prompts.pathway import relation_map_prompt
from cellar.schemas.domain import REL_TYPES
from cellar.services.derivation.pathway import build_relation_map


def _fake_mcp(server: str, tool: str, **kwargs: object) -> dict[str, object]:
    if tool == "search_articles":
        return {"pmids": ["111"], "total_count": 1}
    return {
        "articles": [
            {
                "identifiers": {"pmid": "111", "doi": "10.1/xyz"},
                "title": "A Paper About Partners",
                "abstract": "Some abstract content about the partner gene.",
            }
        ]
    }


def test_build_relation_map_sends_the_prompt_built_by_relation_map_prompt() -> None:
    captured_prompts: list[str] = []

    def fake_llm(prompt: str, **kwargs: object) -> dict[str, str]:
        captured_prompts.append(prompt)
        return {"text": '{"relation_type": "substrate", "gates_model_selection": false}'}

    build_relation_map(
        "ZDHHC20",
        ["GOLGA7"],
        aliases={"GOLGA7": ["GOLPH4"]},
        mcp=_fake_mcp,
        llm=fake_llm,
    )

    evidence = "[PMID 111] A Paper About Partners\nSome abstract content about the partner gene."
    expected_prompt = relation_map_prompt(
        target="ZDHHC20",
        partner="GOLGA7",
        aliases=["GOLPH4"],
        evidence=evidence,
        rel_types=REL_TYPES,
    )

    assert captured_prompts == [expected_prompt]
