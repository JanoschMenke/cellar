from cellar.schemas.scoring import (
    MAX_CANDIDATES,
    MAX_PARTNERS,
    MODERATE_MIN,
    PRO_MIN,
    SCIENCE_W,
    STRONG_MIN,
    TECH_W,
)


def test_science_weights_cover_expected_keys_and_sum() -> None:
    assert set(SCIENCE_W) == {
        "protein_present",
        "pathway_coherence",
        "context_fit",
        "isoform_match",
        "disease_features_match",
        "dependency_signal",
    }
    assert round(sum(SCIENCE_W.values()), 6) == 1.0


def test_tech_weights_cover_expected_keys_and_sum() -> None:
    assert set(TECH_W) == {
        "tier_fit",
        "genetic_tractable",
        "provenance_ok",
        "prior_use",
        "mrna_expressed",
    }
    assert round(sum(TECH_W.values()), 6) == 1.0


def test_thresholds_and_caps_are_unchanged() -> None:
    assert STRONG_MIN == 0.7
    assert MODERATE_MIN == 0.45
    assert PRO_MIN == 0.6
    assert MAX_CANDIDATES == 8
    assert MAX_PARTNERS == 6
