from unittest.mock import patch

import pytest

from cellar.services.sources import hpa
from cellar.utils import http


def test_raw_profile_propagates_404() -> None:
    with (
        patch.object(hpa.http, "get_json", side_effect=http.HttpError(404, "u", "")),
        pytest.raises(http.HttpError),
    ):
        hpa.raw_profile("ENSG0")


def test_raw_profile_propagates_non_404_errors() -> None:
    with (
        patch.object(hpa.http, "get_json", side_effect=http.HttpError(500, "u", "x")),
        pytest.raises(http.HttpError),
    ):
        hpa.raw_profile("ENSG0")


def test_protein_profile_returns_not_found_on_404() -> None:
    with (
        patch.object(hpa.open_targets, "ot_resolve_target", return_value="ENSG0"),
        patch.object(hpa.http, "get_json", side_effect=http.HttpError(404, "u", "")),
    ):
        result = hpa.protein_profile("EGFR")
    assert result == {"found": False, "reason": "no HPA record for ENSG0"}


def test_raw_profile_returns_raw_hpa_dict_on_success() -> None:
    fake_record: dict[str, object] = {
        "Gene": "EGFR",
        "Subcellular location": ["Plasma membrane"],
    }
    with patch.object(hpa.http, "get_json", return_value=fake_record):
        result = hpa.raw_profile("ENSG00000146648")

    assert result == fake_record
