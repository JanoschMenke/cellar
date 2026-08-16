from cellar.schemas.labels import VERIFICATION_STATUS_LABELS
from cellar.schemas.verification import VerificationStatus, classify_verification_status


def test_classifies_sound_status_with_bold_prefix_and_trailing_text() -> None:
    verdict = "**Verified: sound**\n\n- Checked the top pick's dependency evidence."
    assert classify_verification_status(verdict) is VerificationStatus.SOUND


def test_classifies_caveats_status_with_bullet_prefix() -> None:
    verdict = "- Verified with caveats\n\n- One claim lacked a direct source link."
    assert classify_verification_status(verdict) is VerificationStatus.CAVEATS


def test_classifies_needs_attention_status_with_heading_prefix() -> None:
    verdict = "# Needs attention\n\n- The dependency claim for the top pick is unsupported."
    assert classify_verification_status(verdict) is VerificationStatus.NEEDS_ATTENTION


def test_unrecognized_leading_line_falls_back_to_caveats() -> None:
    verdict = "Something unexpected the model said first.\n\n- Detail."
    assert classify_verification_status(verdict) is VerificationStatus.CAVEATS


def test_empty_verdict_falls_back_to_caveats() -> None:
    assert classify_verification_status("") is VerificationStatus.CAVEATS


def test_verification_status_labels_cover_every_status_with_distinct_wording() -> None:
    assert VERIFICATION_STATUS_LABELS == {
        VerificationStatus.SOUND: "Verified — no issues found",
        VerificationStatus.CAVEATS: "Verified with caveats",
        VerificationStatus.NEEDS_ATTENTION: "Needs attention",
    }
