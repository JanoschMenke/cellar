from unittest.mock import patch

import pytest

from cellar.schemas.sources import OtDiseaseHit, OtTargetProfile, OtTractabilityRow
from cellar.services.sources import open_targets

_FAKE_SEARCH_PAYLOAD: dict[str, object] = {
    "data": {"search": {"hits": [{"id": "ENSG00000000001", "name": "ZDHHC20"}]}}
}

_FAKE_ERROR_PAYLOAD: dict[str, object] = {"errors": [{"message": "boom"}]}


def test_resolve_target_calls_http_post_json_and_unwraps_data() -> None:
    with patch.object(
        open_targets.http, "post_json", return_value=_FAKE_SEARCH_PAYLOAD
    ) as mock_post_json:
        result = open_targets.resolve_target("ZDHHC20")

    assert mock_post_json.call_count == 1
    (called_url, called_body), called_kwargs = mock_post_json.call_args
    assert called_url == open_targets.API_URL
    assert set(called_body.keys()) == {"query", "variables"}
    assert called_body["variables"] == {"s": "ZDHHC20", "e": ["target"]}
    assert called_kwargs == {"timeout": 40}

    assert result == {"ensembl_id": "ENSG00000000001", "name": "ZDHHC20"}


def test_gql_raises_runtime_error_on_application_level_error() -> None:
    with (
        patch.object(open_targets.http, "post_json", return_value=_FAKE_ERROR_PAYLOAD),
        pytest.raises(RuntimeError, match=r"^Open Targets error: boom$"),
    ):
        open_targets._gql("query{}", {})


_FAKE_OT_TARGET_SEARCH: dict[str, object] = {
    "data": {"search": {"hits": [{"id": "ENSG00000001", "name": "ZDHHC20"}]}}
}


def test_ot_resolve_target_calls_http_post_json_with_expected_payload() -> None:
    with patch.object(
        open_targets.http, "post_json", return_value=_FAKE_OT_TARGET_SEARCH
    ) as mock_post_json:
        result = open_targets.ot_resolve_target("ZDHHC20")

    args, _ = mock_post_json.call_args
    assert args[0] == open_targets.API_URL
    assert args[1]["variables"] == {"s": "ZDHHC20"}
    assert result == "ENSG00000001"


_FAKE_OT_DISEASE_SEARCH: dict[str, object] = {
    "data": {"search": {"hits": [{"id": "EFO_0000305", "name": "breast carcinoma"}]}}
}

_FAKE_OT_DISEASE_SEARCH_EMPTY: dict[str, object] = {"data": {"search": {"hits": []}}}


def test_ot_resolve_disease_returns_typed_hit() -> None:
    with patch.object(open_targets.http, "post_json", return_value=_FAKE_OT_DISEASE_SEARCH):
        result = open_targets.ot_resolve_disease("breast carcinoma")

    assert result == OtDiseaseHit(id="EFO_0000305", name="breast carcinoma")


def test_ot_resolve_disease_returns_none_when_no_hits() -> None:
    with patch.object(open_targets.http, "post_json", return_value=_FAKE_OT_DISEASE_SEARCH_EMPTY):
        result = open_targets.ot_resolve_disease("nonexistent disease")

    assert result is None


_FAKE_OT_TARGET_PROFILE: dict[str, object] = {
    "data": {
        "target": {
            "approvedSymbol": "ZDHHC20",
            "tractability": [
                {"modality": "SM", "label": "Approved Drug", "value": True},
                {"modality": "AB", "label": "Predicted Tractable", "value": False},
            ],
            "associatedDiseases": {
                "rows": [
                    {"score": 0.8123, "disease": {"id": "EFO_1", "name": "pancreatic carcinoma"}},
                    {"score": 0.4512, "disease": {"id": "EFO_2", "name": "breast carcinoma"}},
                ]
            },
        }
    }
}


def test_ot_target_profile_returns_typed_profile() -> None:
    with patch.object(open_targets.http, "post_json", return_value=_FAKE_OT_TARGET_PROFILE):
        result = open_targets.ot_target_profile("ENSG00000001")

    assert result == OtTargetProfile(
        symbol="ZDHHC20",
        tractability=[OtTractabilityRow(modality="SM", label="Approved Drug", value=True)],
        top_diseases=[("pancreatic carcinoma", 0.812), ("breast carcinoma", 0.451)],
    )
