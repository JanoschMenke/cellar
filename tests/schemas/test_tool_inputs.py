import pytest
from pydantic import ValidationError

from cellar.schemas import tool_inputs as ti
from cellar.schemas.matchmaker import QuestionType


def test_literature_defaults_and_forbid_extra() -> None:
    model = ti.LiteratureSearchInput(query="ZDHHC20 PDAC")
    assert model.max_results == 10
    assert model.min_year is None
    with pytest.raises(ValidationError):
        ti.LiteratureSearchInput(query="x", unexpected=1)


def test_literature_rejects_missing_required() -> None:
    with pytest.raises(ValidationError):
        ti.LiteratureSearchInput()


def test_matchmaker_question_type_is_enum() -> None:
    model = ti.MatchmakerRequestInput(
        target_symbol="ZDHHC20",
        disease="PDAC",
        question_type=list(QuestionType)[0],
    )
    assert isinstance(model.question_type, QuestionType)
    with pytest.raises(ValidationError):
        ti.MatchmakerRequestInput(target_symbol="A", disease="B", question_type="not_a_real_type")


def test_annotate_nested_rationales() -> None:
    model = ti.AnnotateRecommendationsInput(rationales=[{"model": "PANC-1", "why": "because"}])
    assert model.rationales[0].model == "PANC-1"


def test_json_schema_forbids_additional_properties() -> None:
    schema = ti.LiteratureSearchInput.model_json_schema()
    assert schema.get("additionalProperties") is False
    assert "query" in schema["required"]


def test_annotate_schema_emits_defs_for_nested_model() -> None:
    schema = ti.AnnotateRecommendationsInput.model_json_schema()
    assert "$defs" in schema
