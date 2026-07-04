from collections.abc import Callable
from typing import TypeVar

from cellar.services import isoforms, mechanism, pathway, proteomics, retrieval
from cellar.tools.scoring import rank

from cellar.schemas.matchmaker import (
    FactsSummary,
    MatchmakerQuery,
    ModelCandidate,
    RelationSummary,
    SeedModel,
)
from cellar.schemas.recommendation import RecommendationReport
from cellar.services.panels import seed_panel_for
from cellar.services.recommendation import build_card

_T = TypeVar("_T")


class UnsupportedTargetError(RuntimeError): ...


def _safe(fn: Callable[[], _T], default: _T) -> _T:
    try:
        return fn()
    except Exception:
        return default


def _relations_for(target_symbol: str) -> dict[str, dict[str, object]]:
    if target_symbol.upper() == "ZDHHC20":
        return pathway.ZDHHC20_RELATIONS
    return {}


def _moa_context_for(target_symbol: str, disease: str) -> dict[str, object]:
    if target_symbol.upper() == "ZDHHC20":
        return mechanism.ZDHHC20_MOA_CONTEXT
    return {"target": target_symbol, "disease": disease, "requirements": []}


def _pride_for(target_symbol: str) -> dict[str, object]:
    if target_symbol.upper() == "ZDHHC20":
        return proteomics.ZDHHC20_PRIDE
    return {"n_projects": 0, "tier": "unknown", "uniprot": None}


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
    isoform_summary: dict[str, object],
    proteomics_summary: dict[str, object],
    protein_evidence: dict[str, object],
    pride: dict[str, object],
    partners: list[dict[str, object]],
) -> FactsSummary:
    profile = (
        _safe(lambda: retrieval.ot_target_profile(target_id), {"tractability": []})
        if target_id
        else {"tractability": []}
    )
    tractable = any(x.get("modality") == "SM" for x in profile.get("tractability", []))
    assoc = (
        _safe(lambda: retrieval.ot_assoc_score(target_id, disease_id), 0.0)
        if target_id and disease_id
        else 0.0
    )
    models = _safe(lambda: retrieval.cello_models(query.disease), [])
    modalities = proteomics_summary.get("modalities", {}) or {}
    return FactsSummary(
        target_id=target_id,
        disease_id=disease_id,
        small_molecule_tractable=tractable,
        ot_direct_association=float(assoc or 0.0),
        n_sourceable_models=len(models),
        n_problematic_models=sum(1 for m in models if m.get("problematic")),
        isoform_n_protein_coding=int(isoform_summary.get("n_protein_coding", 0) or 0),
        isoform_aa_span=str(isoform_summary.get("aa_span", "")),
        isoform_specificity_risk=str(isoform_summary.get("isoform_specificity_risk", "")),
        mrna_protein_discordant=bool(proteomics_summary.get("mrna_protein_discordant")),
        protein_present=float(protein_evidence.get("protein_present", 0.0) or 0.0),
        protein_confidence=str(protein_evidence.get("confidence", "")),
        ms_absence_guard_applied=bool(protein_evidence.get("ms_absence_guard_applied")),
        pride_n_projects=int(pride.get("n_projects", 0) or 0),
        proteomics_modality_note=str(modalities.get("note", "")),
        string_top_partners=[str(p.get("partner")) for p in partners[:5]],
    )


def _relation_summaries(relations: dict[str, dict[str, object]]) -> list[RelationSummary]:
    return [
        RelationSummary(
            gene=gene,
            relation_type=str(r.get("relation_type", "")),
            gates_model_selection=bool(r.get("gates_model_selection")),
            evidence_pmids=[str(p) for p in (r.get("evidence_pmids") or [])],
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
    target_id = _safe(lambda: retrieval.ot_resolve_target(symbol), None)
    disease_row = _safe(lambda: retrieval.ot_resolve_disease(query.disease), None)
    disease_id = disease_row.get("id") if disease_row else None

    isoform_summary = (
        _safe(
            lambda: isoforms.isoform_risk_summary(isoforms.protein_coding_isoforms(target_id)),
            {},
        )
        if target_id
        else {}
    )
    proteomics_summary = (
        _safe(lambda: proteomics.hpa_protein_evidence(target_id, disease_hint=query.disease), {})
        if target_id
        else {}
    )
    pride = _pride_for(symbol)
    protein_evidence = _safe(
        lambda: proteomics.synthesize_protein_evidence(
            hpa=proteomics_summary,
            pride=pride,
            cptac=proteomics.cptac_tumor_quant(symbol),
            depmap=proteomics.depmap_proteomics(symbol),
        ),
        {},
    )
    partners = _safe(lambda: pathway.string_partners(symbol), [])
    relations = _relations_for(symbol)
    moa_context = _moa_context_for(symbol, query.disease)

    facts = _build_facts(
        query,
        target_id,
        disease_id,
        isoform_summary,
        proteomics_summary,
        protein_evidence,
        pride,
        partners,
    )

    question = str(query.question_type)
    candidates = [_seed_to_candidate(seed) for seed in seeds]
    pathway_by_model: dict[str, dict[str, object]] = {}
    mechanism_by_model: dict[str, dict[str, object]] = {}
    for seed, candidate in zip(seeds, candidates):
        pw = pathway.pathway_coherence(
            seed.coexpression,
            relations,
            target_present=candidate.protein_present,
            catalytic_domain_ok=seed.catalytic_domain_ok,
        )
        coherence = pw.get("pathway_coherence")
        candidate.pathway_coherence = coherence if coherence is not None else 0.5
        candidate.passed_science_gate = pw.get("passed_science_gate") is not False
        moa = mechanism.match_model_context(
            candidate.tier,
            moa_context,
            question,
            capability_overrides=seed.capability_overrides,
        )
        candidate.context_fit = moa["context_fit"]
        candidate.context_required_unmet = moa["context_required_unmet"]
        pathway_by_model[candidate.name] = pw
        mechanism_by_model[candidate.name] = moa

    ranked = rank(candidates, question)
    target_context = {"symbol": symbol}
    cards = [
        build_card(
            rank_index,
            candidate_dict,
            question,
            target_context,
            isoform_summary,
            proteomics_summary,
            pathway_by_model.get(candidate_dict["name"]),
            mechanism_by_model.get(candidate_dict["name"]),
        )
        for rank_index, candidate_dict in enumerate(ranked["ranked"], 1)
    ]

    return RecommendationReport(
        query=query,
        verdict=ranked["verdict"],
        in_vivo_recommended=ranked["in_vivo_recommended"],
        facts=facts,
        relations=_relation_summaries(relations),
        cards=cards,
    )
