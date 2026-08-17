import re
from dataclasses import dataclass
from typing import cast

from cellar.schemas.matchmaker import FactsSummary, MatchmakerQuery, ModelTier, SeedModel
from cellar.schemas.recommendation import RecommendationReport, ScoredDimension, Strength
from cellar.schemas.scoring import (
    AGGREGATE_DEPENDENCY_SIGNAL_DEFAULT,
    AGGREGATE_DISEASE_FEATURES_DEFAULT,
    AGGREGATE_DISEASE_FEATURES_DRIVER,
    AGGREGATE_DISEASE_FEATURES_MUTATED,
    AGGREGATE_DISEASE_FEATURES_NO_MUTATIONS,
    AGGREGATE_GENETIC_TRACTABLE_AVAILABLE,
    AGGREGATE_GENETIC_TRACTABLE_DEFAULT,
    AGGREGATE_ISOFORM_MATCH_DEFAULT,
    AGGREGATE_ISOFORM_MATCH_HIGH_RISK,
    AGGREGATE_ISOFORM_MATCH_LOW_RISK,
    AGGREGATE_MRNA_EXPRESSED_SEED,
    AGGREGATE_PRIOR_USE_DIVISOR,
    AGGREGATE_PROTEIN_PRESENT_DEFAULT,
    MAX_CANDIDATES,
    PROPOSED_TIER_PROFILE,
)
from cellar.schemas.tool_names import ToolName
from cellar.services.derivation.matchmaker import run_matchmaker
from cellar.services.evidence_store import EvidenceStore
from cellar.services.sources import cellosaurus


@dataclass
class _DictRecord:
    input: dict[str, object]
    data: dict[str, object]


def _norm(value: object) -> str:
    return "".join(ch for ch in str(value).lower() if ch.isalnum())


def _dict_records(store: EvidenceStore, tool: str) -> list[_DictRecord]:
    return [
        _DictRecord(input=r.input, data=r.data)
        for r in store.by_tool(tool)
        if isinstance(r.data, dict)
    ]


def _tier_from(category: object, model_type: object) -> ModelTier:
    text = f"{category or ''} {model_type or ''}".lower()
    if "organoid" in text:
        return ModelTier.ORGANOID
    return ModelTier.TWO_D_LINE


def _target_protein_present(store: EvidenceStore) -> float:
    record = store.latest(ToolName.PROTEIN_EVIDENCE)
    if record and isinstance(record.data, dict):
        synthesis = record.data.get("synthesis") or {}
        value = synthesis.get("protein_present")
        if isinstance(value, (int, float)):
            return float(value)
    return AGGREGATE_PROTEIN_PRESENT_DEFAULT


def _target_isoform_match(store: EvidenceStore) -> float:
    record = store.latest(ToolName.ISOFORM_RISK)
    if record and isinstance(record.data, dict):
        return (
            AGGREGATE_ISOFORM_MATCH_HIGH_RISK
            if record.data.get("isoform_specificity_risk") == "high"
            else AGGREGATE_ISOFORM_MATCH_LOW_RISK
        )
    return AGGREGATE_ISOFORM_MATCH_DEFAULT


def _find_by_name(store: EvidenceStore, tool: str, key: str, norm: str) -> dict[str, object]:
    for record in _dict_records(store, tool):
        if _norm(record.input.get(key, "")) == norm and record.data.get("found"):
            return record.data
    return {}


def _dependency_rec(store: EvidenceStore, symbol_norm: str, model_norm: str) -> dict[str, object]:
    for record in _dict_records(store, ToolName.GENE_DEPENDENCY):
        if (
            _norm(record.input.get("model", "")) == model_norm
            and _norm(record.input.get("gene_symbol", "")) == symbol_norm
            and record.data.get("found")
        ):
            return record.data
    return {}


def _dependency_signal(store: EvidenceStore, symbol_norm: str, model_norm: str) -> float:
    dep = _dependency_rec(store, symbol_norm, model_norm)
    value = dep.get("dependency_signal")
    if isinstance(value, (int, float)):
        return float(value)
    for record in _dict_records(store, ToolName.GENE_DEPENDENCY):
        if (
            not record.input.get("model")
            and _norm(record.input.get("gene_symbol", "")) == symbol_norm
            and record.data.get("found")
        ):
            across = record.data.get("dependency_signal")
            if isinstance(across, (int, float)):
                return float(across)
    return AGGREGATE_DEPENDENCY_SIGNAL_DEFAULT


def _disease_features(store: EvidenceStore, norm: str) -> float:
    for record in _dict_records(store, ToolName.CELL_MODEL_GENE_MUTATIONS):
        if _norm(record.input.get("model", "")) == norm and record.data.get("found"):
            mutations = cast("list[object]", record.data.get("mutations") or [])
            if any(isinstance(m, dict) and m.get("cancer_driver") for m in mutations):
                return AGGREGATE_DISEASE_FEATURES_DRIVER
            return (
                AGGREGATE_DISEASE_FEATURES_MUTATED
                if mutations
                else AGGREGATE_DISEASE_FEATURES_NO_MUTATIONS
            )
    return AGGREGATE_DISEASE_FEATURES_DEFAULT


def _prior_use(store: EvidenceStore, norm: str) -> float:
    count = 0
    for record in _dict_records(store, ToolName.LITERATURE_SEARCH):
        for paper in cast("list[object]", record.data.get("papers") or []):
            if not isinstance(paper, dict):
                continue
            blob = _norm(str(paper.get("title", "")) + str(paper.get("abstract", "")))
            if norm and norm in blob:
                count += 1
    return min(1.0, count / AGGREGATE_PRIOR_USE_DIVISOR)


def _provenance(store: EvidenceStore, name: str, norm: str) -> dict[str, object]:
    found = _find_by_name(store, ToolName.CELL_LINE_PROVENANCE, "name", norm)
    if found:
        return found
    try:
        return cellosaurus.provenance(name) or {}
    except Exception:
        return {}


def _sourcing(provenance: dict[str, object]) -> tuple[str, str]:
    listings = cast(
        "dict[str, object]",
        provenance.get("commercial_listings") or provenance.get("catalog") or {},
    )
    fallback_url = str(provenance.get("cellosaurus_url", ""))
    for supplier, info in listings.items():
        if isinstance(info, dict):
            accession = str(info.get("accession", "")).strip()
            return f"{supplier} {accession}".strip(), str(info.get("url") or fallback_url)
        return f"{supplier} {info}".strip(), fallback_url
    return str(provenance.get("category") or "Cellosaurus"), fallback_url


def _seed_for(
    store: EvidenceStore,
    name: str,
    target_symbol: str,
    protein_present: float,
    isoform_match: float,
    category_hint: object = None,
) -> SeedModel:
    norm = _norm(name)
    provenance = _provenance(store, name, norm)
    facts = _find_by_name(store, ToolName.FIND_CELL_MODEL, "name", norm)
    tier = _tier_from(provenance.get("category") or category_hint, facts.get("model_type"))
    source, catalog_url = _sourcing(provenance)
    return SeedModel(
        name=name,
        tier=tier,
        source=source,
        catalog_url=catalog_url,
        mrna_expressed=AGGREGATE_MRNA_EXPRESSED_SEED,
        protein_present=protein_present,
        isoform_match=isoform_match,
        disease_features_match=_disease_features(store, norm),
        dependency_signal=_dependency_signal(store, _norm(target_symbol), norm),
        genetic_tractable=(
            AGGREGATE_GENETIC_TRACTABLE_AVAILABLE
            if facts.get("crispr_ko_available")
            else AGGREGATE_GENETIC_TRACTABLE_DEFAULT
        ),
        provenance_ok=float(cast("float | int", provenance.get("provenance_ok", 1.0))),
        prior_use=_prior_use(store, norm),
        coexpression={},
        catalytic_domain_ok=True,
    )


_MODEL_LOOKUP_TOOLS: tuple[tuple[str, str], ...] = (
    (ToolName.FIND_CELL_MODEL, "name"),
    (ToolName.CELL_LINE_PROVENANCE, "name"),
    (ToolName.CELL_MODEL_GENE_MUTATIONS, "model"),
    (ToolName.GENE_DEPENDENCY, "model"),
)
_IDENTITY_KEYS = ("sidm_id", "model_id", "accession")
_SYNONYM_KEYS = ("names", "model_names")


def _identity_tokens(record: _DictRecord, input_key: str) -> set[str]:
    tokens: set[str] = set()
    raw = record.input.get(input_key)
    if isinstance(raw, str):
        tokens.add(_norm(raw))
    for key in _IDENTITY_KEYS:
        value = record.data.get(key)
        if isinstance(value, str) and value:
            tokens.add(_norm(value))
    for key in _SYNONYM_KEYS:
        for value in cast("list[object]", record.data.get(key) or []):
            if isinstance(value, str) and value:
                tokens.add(_norm(value))
    cross_ids = record.data.get("cross_ids")
    if isinstance(cross_ids, dict):
        for value in cast("dict[str, object]", cross_ids).values():
            if isinstance(value, str) and value:
                tokens.add(_norm(value))
    return {token for token in tokens if token}


def _merge(groups: dict[str, str], tokens: set[str]) -> None:
    resolved = {_resolve(groups, token) for token in tokens}
    leader = sorted(resolved)[0]
    for token in resolved:
        groups[token] = leader


def _resolve(groups: dict[str, str], token: str) -> str:
    while groups.get(token, token) != token:
        token = groups[token]
    return token


def _identity_groups(store: EvidenceStore) -> dict[str, str]:
    groups: dict[str, str] = {}
    for tool, input_key in _MODEL_LOOKUP_TOOLS:
        for record in _dict_records(store, tool):
            tokens = _identity_tokens(record, input_key)
            if tokens:
                _merge(groups, tokens)
    return groups


def _looks_like_database_id(name: str) -> bool:
    return bool(re.fullmatch(r"(sidm|cvcl|ach)\d+", _norm(name)))


def _gathered_model_names(store: EvidenceStore) -> list[str]:
    groups = _identity_groups(store)
    by_identity: dict[str, list[str]] = {}
    for tool, key in _MODEL_LOOKUP_TOOLS:
        for record in store.by_tool(tool):
            raw = record.input.get(key)
            if not isinstance(raw, str) or not raw.strip():
                continue
            by_identity.setdefault(_resolve(groups, _norm(raw)), []).append(raw.strip())
    return [
        next((name for name in candidates if not _looks_like_database_id(name)), candidates[0])
        for candidates in by_identity.values()
    ]


def _proposed_records(store: EvidenceStore) -> list[dict[str, object]]:
    by_name: dict[str, dict[str, object]] = {}
    for record in _dict_records(store, ToolName.PROPOSE_MODEL_CANDIDATE):
        data = record.data
        name = str(data.get("name") or "").strip()
        tier = str(data.get("tier") or "")
        if not name or tier not in PROPOSED_TIER_PROFILE:
            continue
        by_name[_norm(name)] = data
    return list(by_name.values())


def _proposed_seed(
    store: EvidenceStore,
    proposal: dict[str, object],
    target_symbol: str,
    protein_present: float,
    isoform_match: float,
) -> SeedModel:
    name = str(proposal["name"]).strip()
    tier = ModelTier(str(proposal["tier"]))
    profile = PROPOSED_TIER_PROFILE[str(tier)]
    return SeedModel(
        name=name,
        tier=tier,
        source=str(proposal.get("supplier_or_cro") or ""),
        catalog_url=str(proposal.get("sourcing_url") or ""),
        mrna_expressed=profile["mrna_expressed"],
        protein_present=protein_present,
        isoform_match=isoform_match,
        disease_features_match=profile["disease_features_match"],
        dependency_signal=_dependency_signal(store, _norm(target_symbol), _norm(name)),
        genetic_tractable=profile["genetic_tractable"],
        provenance_ok=profile["provenance_ok"],
        prior_use=_prior_use(store, _norm(name)),
        coexpression={},
        catalytic_domain_ok=True,
    )


def build_panel_from_evidence(store: EvidenceStore, target_symbol: str) -> list[SeedModel]:
    protein_present = _target_protein_present(store)
    isoform_match = _target_isoform_match(store)
    proposed = [
        _proposed_seed(store, proposal, target_symbol, protein_present, isoform_match)
        for proposal in _proposed_records(store)
    ][:MAX_CANDIDATES]
    taken = {_norm(seed.name) for seed in proposed}
    gathered = [name for name in _gathered_model_names(store) if _norm(name) not in taken]
    room = MAX_CANDIDATES - len(proposed)
    lines = [
        _seed_for(store, name, target_symbol, protein_present, isoform_match)
        for name in gathered[:room]
    ]
    return proposed + lines


def _no_models_report(query: MatchmakerQuery) -> RecommendationReport:
    return RecommendationReport(
        query=query,
        verdict=(
            f"No candidate models have been investigated for "
            f"{query.target_symbol} in {query.disease}. Look up specific cell lines with "
            f"find_cell_model, gene_dependency, or cell_line_provenance, add any organoid, "
            f"co-culture or in-vivo model with propose_model_candidate, then aggregate again."
        ),
        in_vivo_recommended=False,
        facts=FactsSummary(),
        cards=[],
    )


_CMP = "Cell Model Passports"


def _num(value: object) -> str:
    return f"{value:g}" if isinstance(value, (int, float)) else str(value)


def _rec_for(store: EvidenceStore, tool: str, key: str, norm: str) -> dict[str, object]:
    for record in _dict_records(store, tool):
        if _norm(record.input.get(key, "")) == norm and record.data.get("found"):
            return record.data
    return {}


def _pro(key: str, label: str, source: str, url: str | None) -> ScoredDimension:
    return ScoredDimension(
        key=key, label=label, value=1.0, strength=Strength.STRONG, source=source, source_url=url
    )


def _con(key: str, label: str, source: str, url: str | None) -> ScoredDimension:
    return ScoredDimension(
        key=key, label=label, value=0.0, strength=Strength.WEAK, source=source, source_url=url
    )


def _evidence_rows(
    store: EvidenceStore, symbol: str, name: str
) -> tuple[list[ScoredDimension], list[ScoredDimension]]:
    norm = _norm(name)
    symbol_norm = _norm(symbol)
    pros: list[ScoredDimension] = []
    cons: list[ScoredDimension] = []

    facts = _rec_for(store, ToolName.FIND_CELL_MODEL, "name", norm)
    passport = cast(
        "str | None",
        facts.get("catalog_url")
        or (
            f"https://cellmodelpassports.sanger.ac.uk/passports/{facts['sidm_id']}"
            if facts.get("sidm_id")
            else None
        ),
    )

    for record in _dict_records(store, ToolName.CELL_MODEL_GENE_MUTATIONS):
        if _norm(record.input.get("model", "")) != norm or not record.data.get("found"):
            continue
        gene = str(record.data.get("gene_symbol") or record.input.get("gene_symbol") or "").upper()
        raw_mutations = cast("list[object]", record.data.get("mutations") or [])
        mutations = [m for m in raw_mutations if isinstance(m, dict)]
        driver = next((m for m in mutations if m.get("cancer_driver")), None)
        if driver:
            vaf = driver.get("vaf")
            vaf_txt = f", VAF {vaf:.2f}" if isinstance(vaf, (int, float)) else ""
            detail = " ".join(x for x in (driver.get("protein"), driver.get("effect")) if x)
            pros.append(
                _pro(
                    f"mutation:{gene}",
                    f"{gene} {detail}{vaf_txt} — confirmed cancer driver",
                    _CMP,
                    passport,
                )
            )
        elif _norm(gene) != symbol_norm:
            cons.append(
                _con(
                    f"mutation:{gene}",
                    f"Wild-type {gene} — lacks this disease driver",
                    _CMP,
                    passport,
                )
            )

    dep = _dependency_rec(store, symbol_norm, norm)
    if dep and dep.get("is_dependency"):
        detail = f"{symbol} gene-effect {_num(dep.get('gene_effect'))}"
        if dep.get("bf_scaled") is not None:
            detail += f", Bayes factor {_num(dep.get('bf_scaled'))}"
        dep_url = f"https://depmap.org/portal/gene/{symbol}"
        pros.append(
            _pro(
                "dependency",
                f"{detail} — knockout is lethal here, so a loss-of-function phenotype is detectable",
                "DepMap",
                dep_url,
            )
        )

    datasets = [str(d) for d in cast("list[object]", facts.get("datasets_available") or [])]
    if datasets:
        pros.append(_pro("datasets", f"Data available: {', '.join(datasets)}", _CMP, passport))

    growth, ploidy = facts.get("growth_properties"), facts.get("ploidy")
    if growth or isinstance(ploidy, (int, float)):
        parts = [str(growth)] if growth else []
        if isinstance(ploidy, (int, float)):
            parts.append(f"ploidy ~{ploidy:.1f}")
        pros.append(
            _pro("growth", f"{', '.join(parts)} — straightforward to culture", _CMP, passport)
        )

    prov = _rec_for(store, ToolName.CELL_LINE_PROVENANCE, "name", norm)
    if prov:
        acc = prov.get("accession") or ""
        prov_url = cast("str | None", prov.get("cellosaurus_url"))
        if prov.get("problematic"):
            raw_problems = cast("list[object]", prov.get("problems") or [])
            problems = ", ".join(str(p) for p in raw_problems) or "flagged"
            cons.append(
                _con(
                    "provenance",
                    f"Flagged problematic: {problems} ({acc})",
                    "Cellosaurus",
                    prov_url,
                )
            )
        else:
            cons_or = (
                f"Clean provenance, not flagged ({acc})" if acc else "Clean provenance, not flagged"
            )
            pros.append(_pro("provenance", cons_or, "Cellosaurus", prov_url))

    return pros, cons


def _is_purchasable(store: EvidenceStore, name: str) -> bool:
    norm = _norm(name)
    for proposal in _proposed_records(store):
        if _norm(str(proposal.get("name", ""))) == norm:
            return bool(proposal.get("sourcing_url"))
    prov = _rec_for(store, ToolName.CELL_LINE_PROVENANCE, "name", norm)
    listings = prov.get("commercial_listings") or prov.get("catalog") or {}
    return bool(listings)


def _display_name(store: EvidenceStore, name: str) -> str | None:
    norm = _norm(name)
    for tool in (
        ToolName.FIND_CELL_MODEL,
        ToolName.CELL_LINE_PROVENANCE,
        ToolName.CELL_MODEL_GENE_MUTATIONS,
        ToolName.GENE_DEPENDENCY,
    ):
        for record in _dict_records(store, tool):
            data = record.data
            matches = (
                _norm(record.input.get("name", "")) == norm
                or _norm(record.input.get("model", "")) == norm
                or _norm(data.get("sidm_id", "")) == norm
                or _norm(data.get("model_id", "")) == norm
            )
            if matches:
                names = cast("list[object]", data.get("names") or data.get("model_names") or [])
                if names:
                    return str(names[0])
    return None


def aggregate_recommendations(store: EvidenceStore, query: MatchmakerQuery) -> RecommendationReport:
    panel = build_panel_from_evidence(store, query.target_symbol)
    if not panel:
        return _no_models_report(query)
    report = run_matchmaker(query, panel=panel)
    for card in report.cards:
        original = card.model_name
        pros, cons = _evidence_rows(store, query.target_symbol, original)
        if pros or cons:
            card.reasons = pros
            card.watch_outs = cons
        card.sourcing.purchasable = _is_purchasable(store, original)
        display = _display_name(store, original)
        if display:
            card.model_name = display
    return report
