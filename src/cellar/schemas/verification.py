from enum import StrEnum


class VerificationStatus(StrEnum):
    SOUND = "sound"
    CAVEATS = "caveats"
    NEEDS_ATTENTION = "needs_attention"

    __repr__ = str.__repr__


def _strip_leading_markdown(line: str) -> str:
    stripped = line.strip()
    while stripped and stripped[0] in "*-#":
        stripped = stripped[1:].strip()
    return stripped


def classify_verification_status(verdict_markdown: str) -> VerificationStatus:
    for line in verdict_markdown.splitlines():
        if not line.strip():
            continue
        normalized = _strip_leading_markdown(line).lower()
        if normalized.startswith("verified: sound"):
            return VerificationStatus.SOUND
        if normalized.startswith("verified with caveats"):
            return VerificationStatus.CAVEATS
        if normalized.startswith("needs attention"):
            return VerificationStatus.NEEDS_ATTENTION
        return VerificationStatus.CAVEATS
    return VerificationStatus.CAVEATS
