from cellar.schemas.labels import REJECT_LABELS, VERDICT_LABELS
from cellar.schemas.matchmaker import GateStatus


def test_verdict_labels_cover_every_gate_status_with_distinct_wording() -> None:
    assert VERDICT_LABELS == {
        GateStatus.PASSED: "Recommended",
        GateStatus.SCIENCE_GATE_FAILED: "Rejected — science gate",
        GateStatus.MOA_CONTEXT_UNMET: "Rejected — wrong model for this mechanism",
        GateStatus.NO_PROTEIN_EVIDENCE: "Rejected — no protein evidence",
        GateStatus.PATHWAY_INCOHERENT: "Rejected — pathway incoherent",
    }


def test_reject_labels_use_different_wording_from_verdict_labels() -> None:
    assert REJECT_LABELS == {
        "science_gate_failed": "REJECTED — science gate",
        "moa_context_unmet": "REJECTED — wrong model for this mechanism",
        "no_protein_evidence": "REJECTED — no protein evidence",
        "pathway_incoherent": "REJECTED — pathway incoherent",
    }
    for gate in GateStatus:
        if gate is GateStatus.PASSED:
            continue
        assert REJECT_LABELS[gate.value] != VERDICT_LABELS[gate]
