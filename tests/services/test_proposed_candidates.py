from cellar.schemas.matchmaker import ModelCandidate, ModelTier, QuestionType
from cellar.services.derivation.aggregate import build_panel_from_evidence
from cellar.services.evidence_store import EvidenceStore
from cellar.tools.propose_candidate import ProposeModelCandidateTool
from cellar.tools.scoring import rank

_ORGANOID = "Patient-derived intestinal organoid"
_SUPPLIER_URL = "https://www.stemcell.com/intesticult-organoid-growth-medium-human.html"


def _proposal(
    name: str = _ORGANOID, tier: str = "organoid", url: str = _SUPPLIER_URL
) -> dict[str, object]:
    return {
        "found": True,
        "name": name,
        "tier": tier,
        "basis": "3D crypt architecture is required for the differentiation gradient.",
        "supplier_or_cro": "STEMCELL Technologies",
        "sourcing_url": url,
    }


def _store_with_line_and_organoid() -> EvidenceStore:
    store = EvidenceStore()
    store.record("find_cell_model", {"name": "HT-29"}, {"found": True, "model_type": "Cell Line"})
    store.record("propose_model_candidate", {"name": _ORGANOID}, _proposal())
    return store


def test_proposed_organoid_enters_the_panel_alongside_cell_lines() -> None:
    panel = build_panel_from_evidence(_store_with_line_and_organoid(), "ATOH1")

    tiers = {seed.name: seed.tier for seed in panel}
    assert tiers[_ORGANOID] is ModelTier.ORGANOID
    assert tiers["HT-29"] is ModelTier.TWO_D_LINE


def test_proposed_candidate_carries_its_web_search_sourcing() -> None:
    panel = build_panel_from_evidence(_store_with_line_and_organoid(), "ATOH1")

    organoid = next(seed for seed in panel if seed.name == _ORGANOID)
    assert organoid.source == "STEMCELL Technologies"
    assert organoid.catalog_url == _SUPPLIER_URL


def test_2d_line_tier_cannot_be_smuggled_in_through_a_proposal() -> None:
    store = EvidenceStore()
    store.record("propose_model_candidate", {"name": "HeLa"}, _proposal("HeLa", tier="2d_line"))

    assert build_panel_from_evidence(store, "ATOH1") == []


def test_repeated_proposals_of_the_same_model_collapse_to_one_seed() -> None:
    store = EvidenceStore()
    store.record("propose_model_candidate", {"name": _ORGANOID}, _proposal())
    store.record("propose_model_candidate", {"name": _ORGANOID.lower()}, _proposal())

    assert len(build_panel_from_evidence(store, "ATOH1")) == 1


def test_organoid_outranks_a_2d_line_when_the_mechanism_needs_3d_context() -> None:
    monolayer = ModelCandidate(
        name="HT-29", tier=str(ModelTier.TWO_D_LINE), context_fit=0.0, context_required_unmet=True
    )
    organoid = ModelCandidate(name=_ORGANOID, tier=str(ModelTier.ORGANOID), context_fit=1.0)

    ranked = rank([monolayer, organoid], str(QuestionType.MECHANISM)).ranked

    assert ranked[0].name == _ORGANOID
    assert ranked[0].scores is not None and ranked[0].scores.gate == "passed"
    assert ranked[1].scores is not None and ranked[1].scores.gate == "moa_context_unmet"


def test_proposal_without_a_usable_url_reports_no_sourcing() -> None:
    result = ProposeModelCandidateTool().dispatch(
        {
            "name": _ORGANOID,
            "tier": "organoid",
            "basis": "3D architecture",
            "sourcing_url": "ftp://x",
        }
    )

    assert not result.is_error
    assert '"sourcing_url": ""' in result.content
    assert "sourcing_warning" in result.content
