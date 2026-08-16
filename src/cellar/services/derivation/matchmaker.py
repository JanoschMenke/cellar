from collections.abc import Callable
from typing import cast

from cellar.schemas.derivation import (
    HpaProteinEvidence,
    MoaContext,
    PathwayCoherence,
    ProteinSynthesis,
)
from cellar.schemas.matchmaker import (
    FactsSummary,
    MatchmakerQuery,
    ModelCandidate,
    RelationSummary,
    SeedModel,
)
from cellar.schemas.recommendation import RecommendationReport
from cellar.schemas.sources import (
    CellModelHit,
    IsoformRiskSummary,
    OtDiseaseHit,
    OtTargetProfile,
    StringPartner,
)
from cellar.services.derivation import derivation, mechanism, pathway, proteomics
from cellar.services.derivation.panels import seed_panel_for
from cellar.services.derivation.recommendation import build_card
from cellar.services.sources import cellosaurus, isoforms, open_targets, string_db
from cellar.tools.scoring import rank


class UnsupportedTargetError(RuntimeError): ...


def _safe[T](fn: Callable[[], T], default: T) -> T:
    try:
        return fn()
    except Exception:
        return default


def _relations_for(target_symbol: str) -> dict[str, dict[str, object]]:
    return derivation.relations_for(target_symbol)


def _moa_context_for(target_symbol: str, disease: str) -> dict[str, object]:
    return derivation.moa_context_for(target_symbol, disease)


def _pride_for(target_symbol: str) -> dict[str, object] | None:
    return derivation.pride_for(target_symbol)


def _seed_to_candidate(seed: SeedModel) -> ModelCandidate:
    return ModelCandidate(
        name=seed.name,
        tier=str(seed.tier),
        source=seed.source,
        catalog_url=seed.catalog_url,
        mrna_expressed=seed.mrna_expressed,
        protein_present=seed.protein_present,
        isoform_match=seed.isoform_match,
        disease_features_match=seed.disease_features_match,
        dependency_signal=seed.dependency_signal,
        genetic_tractable=seed.genetic_tractable,
        provenance_ok=seed.provenance_ok,
        prior_use=seed.prior_use,
    )


def _build_facts(
    query: MatchmakerQuery,
    target_id: str | None,
    disease_id: str | None,
    isoform_summary: IsoformRiskSummary | None,
    proteomics_summary: HpaProteinEvidence | None,
    protein_evidence: ProteinSynthesis | None,
    pride: dict[str, object] | None,
    partners: list[StringPartner],
) -> FactsSummary:
    empty_profile = OtTargetProfile(symbol="", tractability=[], top_diseases=[])
    profile: OtTargetProfile = (
        _safe(lambda: open_targets.ot_target_profile(target_id), empty_profile)
        if target_id
        else empty_profile
    )
    tractable = any(row.modality == "SM" for row in profile.tractability)
    assoc: float = (
        _safe(lambda: open_targets.ot_assoc_score(target_id, disease_id), 0.0)
        if target_id and disease_id
        else 0.0
    )
    models: list[CellModelHit] = _safe(lambda: cellosaurus.cello_models(query.disease), [])
    return FactsSummary(
        target_id=target_id,
        disease_id=disease_id,
        small_molecule_tractable=tractable,
        ot_direct_association=float(assoc or 0.0),
        n_sourceable_models=len(models),
        n_problematic_models=sum(1 for m in models if m.problematic),
        isoform_n_protein_coding=isoform_summary.n_protein_coding if isoform_summary else 0,
        isoform_aa_span=str(isoform_summary.aa_span) if isoform_summary else "",
        isoform_specificity_risk=(
            str(isoform_summary.isoform_specificity_risk) if isoform_summary else ""
        ),
        mrna_protein_discordant=bool(
            proteomics_summary.mrna_protein_discordant if proteomics_summary else False
        ),
        protein_present=float(
            (protein_evidence.protein_present if protein_evidence else None) or 0.0
        ),
        protein_confidence=str(protein_evidence.confidence if protein_evidence else ""),
        ms_absence_guard_applied=bool(
            protein_evidence.ms_absence_guard_applied if protein_evidence else False
        ),
        pride_n_projects=int(cast("int | str", (pride or {}).get("n_projects", 0) or 0)),
        proteomics_modality_note=str(
            proteomics_summary.modalities.note if proteomics_summary else ""
        ),
        string_top_partners=[p.partner for p in partners[:5]],
    )


def _relation_summaries(relations: dict[str, dict[str, object]]) -> list[RelationSummary]:
    return [
        RelationSummary(
            gene=gene,
            relation_type=str(r.get("relation_type", "")),
            gates_model_selection=bool(r.get("gates_model_selection")),
            evidence_pmids=[str(p) for p in cast("list[object]", r.get("evidence_pmids") or [])],
        )
        for gene, r in relations.items()
    ]


def run_matchmaker(
    query: MatchmakerQuery, panel: list[SeedModel] | None = None
) -> RecommendationReport:
    seeds = panel if panel is not None else seed_panel_for(query.target_symbol)
    if not seeds:
        raise UnsupportedTargetError(
            f"No candidate panel for {query.target_symbol}. Provide `panel` or wire the "
            "Cellosaurus x DepMap x HPA auto-panel builder."
        )

    symbol = query.target_symbol
    target_id: str | None = _safe(lambda: open_targets.ot_resolve_target(symbol), None)
    disease_hit: OtDiseaseHit | None = _safe(
        lambda: open_targets.ot_resolve_disease(query.disease), None
    )
    disease_id = disease_hit.id if disease_hit else None

    isoform_summary: IsoformRiskSummary | None = (
        _safe(
            lambda: isoforms.isoform_risk_summary(isoforms.protein_coding_isoforms(target_id)),
            None,
        )
        if target_id
        else None
    )
    isoform_summary_dict: dict[str, object] = (
        isoform_summary.model_dump() if isoform_summary else {}
    )
    hpa_evidence: HpaProteinEvidence | None = (
        _safe(lambda: proteomics.hpa_protein_evidence(target_id, disease_hint=query.disease), None)
        if target_id
        else None
    )
    proteomics_summary: dict[str, object] = hpa_evidence.model_dump() if hpa_evidence else {}
    pride = _pride_for(symbol)
    protein_evidence: ProteinSynthesis | None = _safe(
        lambda: proteomics.synthesize_protein_evidence(
            hpa=hpa_evidence,
            pride=pride,
            cptac=proteomics.cptac_tumor_quant(symbol),
            depmap=proteomics.depmap_proteomics(symbol),
        ),
        None,
    )
    partners: list[StringPartner] = _safe(lambda: string_db.string_partners(symbol), [])
    relations = _relations_for(symbol)
    moa_context = _moa_context_for(symbol, query.disease)

    facts = _build_facts(
        query,
        target_id,
        disease_id,
        isoform_summary,
        hpa_evidence,
        protein_evidence,
        pride,
        partners,
    )

    question = str(query.question_type)
    candidates = [_seed_to_candidate(seed) for seed in seeds]
    pathway_by_model: dict[str, PathwayCoherence] = {}
    mechanism_by_model: dict[str, MoaContext] = {}
    for seed, candidate in zip(seeds, candidates, strict=True):
        pw = pathway.pathway_coherence(
            seed.coexpression,
            relations,
            target_present=candidate.protein_present,
            catalytic_domain_ok=seed.catalytic_domain_ok,
        )
        candidate.pathway_coherence = (
            pw.pathway_coherence if pw.pathway_coherence is not None else 0.5
        )
        candidate.passed_science_gate = pw.passed_science_gate is not False
        moa = mechanism.match_model_context(
            candidate.tier,
            moa_context,
            question,
            capability_overrides=seed.capability_overrides,
        )
        candidate.context_fit = moa.context_fit
        candidate.context_required_unmet = moa.context_required_unmet
        pathway_by_model[candidate.name] = pw
        mechanism_by_model[candidate.name] = moa

    rank_result = rank(candidates, question)
    target_context: dict[str, object] = {"symbol": symbol, "target_id": target_id or ""}
    cards = [
        build_card(
            rank_index,
            candidate,
            question,
            target_context,
            isoform_summary_dict,
            proteomics_summary,
            pathway_by_model.get(candidate.name),
            mechanism_by_model.get(candidate.name),
        )
        for rank_index, candidate in enumerate(rank_result.ranked, 1)
    ]

    return RecommendationReport(
        query=query,
        verdict=rank_result.verdict,
        in_vivo_recommended=rank_result.in_vivo_recommended,
        facts=facts,
        relations=_relation_summaries(relations),
        cards=cards,
    )
