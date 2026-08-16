from cellar.schemas.domain import NECESSITY, TIER_WEIGHT
from cellar.schemas.matchmaker import (
    EvidenceTier,
    MsDetectabilityTier,
    Necessity,
    PathwayMemberStatus,
)
from cellar.schemas.scoring import MS_TIER_SIGNAL, NECESSITY_WEIGHT


def test_necessity_values_are_byte_identical() -> None:
    assert Necessity.REQUIRED == "required"
    assert Necessity.ENHANCING == "enhancing"
    assert Necessity.HYPOTHESIS == "hypothesis"
    assert list(NECESSITY) == [Necessity.REQUIRED, Necessity.ENHANCING, Necessity.HYPOTHESIS]


def test_ms_detectability_tier_values_are_byte_identical() -> None:
    assert MsDetectabilityTier.UNDETECTED == "undetected"
    assert MsDetectabilityTier.LOW == "low"
    assert MsDetectabilityTier.MODERATE == "moderate"
    assert MsDetectabilityTier.HIGH == "high"


def test_pathway_member_status_values_are_byte_identical() -> None:
    assert PathwayMemberStatus.UNKNOWN == "unknown"
    assert PathwayMemberStatus.PRESENT == "present"
    assert PathwayMemberStatus.ABSENT == "absent"


def test_evidence_tier_values_are_byte_identical() -> None:
    assert EvidenceTier.MODEL_SPECIFIC == "model_specific"
    assert EvidenceTier.TUMOR_QUANT == "tumor_quant"
    assert EvidenceTier.LOCALIZATION_AB == "localization_ab"
    assert EvidenceTier.MS_DETECTABILITY == "ms_detectability"


def test_tier_weight_resolves_by_enum_and_by_plain_string_key() -> None:
    assert TIER_WEIGHT[EvidenceTier.MODEL_SPECIFIC] == TIER_WEIGHT["model_specific"]
    assert TIER_WEIGHT[EvidenceTier.TUMOR_QUANT] == TIER_WEIGHT["tumor_quant"]
    assert TIER_WEIGHT[EvidenceTier.LOCALIZATION_AB] == TIER_WEIGHT["localization_ab"]
    assert TIER_WEIGHT[EvidenceTier.MS_DETECTABILITY] == TIER_WEIGHT["ms_detectability"]


def test_necessity_weight_resolves_by_enum_and_by_plain_string_key() -> None:
    assert NECESSITY_WEIGHT[Necessity.REQUIRED] == NECESSITY_WEIGHT["required"]
    assert NECESSITY_WEIGHT[Necessity.ENHANCING] == NECESSITY_WEIGHT["enhancing"]
    assert NECESSITY_WEIGHT[Necessity.HYPOTHESIS] == NECESSITY_WEIGHT["hypothesis"]


def test_ms_tier_signal_resolves_by_enum_and_by_plain_string_key() -> None:
    assert MS_TIER_SIGNAL[MsDetectabilityTier.UNDETECTED] == MS_TIER_SIGNAL["undetected"]
    assert MS_TIER_SIGNAL[MsDetectabilityTier.LOW] == MS_TIER_SIGNAL["low"]
    assert MS_TIER_SIGNAL[MsDetectabilityTier.MODERATE] == MS_TIER_SIGNAL["moderate"]
    assert MS_TIER_SIGNAL[MsDetectabilityTier.HIGH] == MS_TIER_SIGNAL["high"]
