from cellar.schemas.matchmaker import FactsSummary, MatchmakerQuery, ModelTier, SeedModel
from cellar.schemas.recommendation import RecommendationReport, ScoredDimension, Strength
from cellar.services import cellosaurus
from cellar.services.evidence_store import EvidenceStore
from cellar.services.matchmaker import run_matchmaker

_MAX_CANDIDATES = 8


def _norm(value: object) -> str:
    return "".join(ch for ch in str(value).lower() if ch.isalnum())


def _dict_records(store: EvidenceStore, tool: str) -> list:
    return [r for r in store.by_tool(tool) if isinstance(r.data, dict)]


def _tier_from(category: object, model_type: object) -> ModelTier:
    text = f"{category or ''} {model_type or ''}".lower()
    if "organoid" in text:
        return ModelTier.ORGANOID
    return ModelTier.TWO_D_LINE


def _target_protein_present(store: EvidenceStore) -> float:
    record = store.latest("protein_evidence")
    if record and isinstance(record.data, dict):
        synthesis = record.data.get("synthesis") or {}
        value = synthesis.get("protein_present")
        if isinstance(value, (int, float)):
            return float(value)
    return 0.6


def _target_isoform_match(store: EvidenceStore) -> float:
    record = store.latest("isoform_risk")
    if record and isinstance(record.data, dict):
        return 0.5 if record.data.get("isoform_specificity_risk") == "high" else 0.85
    return 0.7


def _find_by_name(store: EvidenceStore, tool: str, key: str, norm: str) -> dict:
    for record in _dict_records(store, tool):
        if _norm(record.input.get(key, "")) == norm and record.data.get("found"):
            return record.data
    return {}


def _dependency_signal(store: EvidenceStore, norm: str) -> float:
    for record in _dict_records(store, "gene_dependency"):
        if _norm(record.input.get("model", "")) == norm and record.data.get("found"):
            value = record.data.get("dependency_signal")
            if isinstance(value, (int, float)):
                return float(value)
    for record in _dict_records(store, "gene_dependency"):
        if not record.input.get("model") and record.data.get("found"):
            value = record.data.get("dependency_signal")
            if isinstance(value, (int, float)):
                return float(value)
    return 0.5


def _disease_features(store: EvidenceStore, norm: str) -> float:
    for record in _dict_records(store, "cell_model_gene_mutations"):
        if _norm(record.input.get("model", "")) == norm and record.data.get("found"):
            mutations = record.data.get("mutations") or []
            if any(isinstance(m, dict) and m.get("cancer_driver") for m in mutations):
                return 0.85
            return 0.7 if mutations else 0.6
    return 0.65


def _prior_use(store: EvidenceStore, norm: str) -> float:
    count = 0
    for record in _dict_records(store, "literature_search"):
        for paper in record.data.get("papers") or []:
            if not isinstance(paper, dict):
                continue
            blob = _norm(str(paper.get("title", "")) + str(paper.get("abstract", "")))
            if norm and norm in blob:
                count += 1
    return min(1.0, count / 3.0)


def _provenance(store: EvidenceStore, name: str, norm: str) -> dict:
    found = _find_by_name(store, "cell_line_provenance", "name", norm)
    if found:
        return found
    try:
        return cellosaurus.provenance(name) or {}
    except Exception:
        return {}


def _sourcing(provenance: dict) -> tuple[str, str]:
    listings = provenance.get("commercial_listings") or provenance.get("catalog") or {}
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
    protein_present: float,
    isoform_match: float,
    category_hint: object = None,
) -> SeedModel:
    norm = _norm(name)
    provenance = _provenance(store, name, norm)
    facts = _find_by_name(store, "find_cell_model", "name", norm)
    tier = _tier_from(provenance.get("category") or category_hint, facts.get("model_type"))
    source, catalog_url = _sourcing(provenance)
    return SeedModel(
        name=name,
        tier=tier,
        source=source,
        catalog_url=catalog_url,
        mrna_expressed=0.6,
        protein_present=protein_present,
        isoform_match=isoform_match,
        disease_features_match=_disease_features(store, norm),
        dependency_signal=_dependency_signal(store, norm),
        genetic_tractable=0.9 if facts.get("crispr_ko_available") else 0.6,
        provenance_ok=float(provenance.get("provenance_ok", 1.0)),
        prior_use=_prior_use(store, norm),
        coexpression={},
        catalytic_domain_ok=True,
    )


def _gathered_model_names(store: EvidenceStore) -> list[str]:
    names: list[str] = []
    seen: set[str] = set()
    for tool, key in (
        ("find_cell_model", "name"),
        ("cell_line_provenance", "name"),
        ("cell_model_gene_mutations", "model"),
        ("gene_dependency", "model"),
    ):
        for record in store.by_tool(tool):
            raw = record.input.get(key)
            if isinstance(raw, str) and raw.strip() and _norm(raw) not in seen:
                seen.add(_norm(raw))
                names.append(raw.strip())
    return names


def build_panel_from_evidence(store: EvidenceStore) -> list[SeedModel]:
    protein_present = _target_protein_present(store)
    isoform_match = _target_isoform_match(store)
    gathered = _gathered_model_names(store)
    return [
        _seed_for(store, name, protein_present, isoform_match)
        for name in gathered[:_MAX_CANDIDATES]
    ]


def _no_models_report(query: MatchmakerQuery) -> RecommendationReport:
    return RecommendationReport(
        query=query,
        verdict=(
            f"No candidate cell-line models have been investigated for "
            f"{query.target_symbol} in {query.disease}. Look up specific models with "
            f"find_cell_model, gene_dependency, or cell_line_provenance, then aggregate again."
        ),
        in_vivo_recommended=False,
        facts=FactsSummary(),
        cards=[],
    )


_CMP = "Cell Model Passports"


def _num(value: object) -> str:
    return f"{value:g}" if isinstance(value, (int, float)) else str(value)


def _rec_for(store: EvidenceStore, tool: str, key: str, norm: str) -> dict:
    for record in _dict_records(store, tool):
        if _norm(record.input.get(key, "")) == norm and record.data.get("found"):
            return record.data
    return {}


def _pro(key: str, label: str, source: str, url: str | None) -> ScoredDimension:
    return ScoredDimension(key=key, label=label, value=1.0, strength=Strength.STRONG, source=source, source_url=url)


def _con(key: str, label: str, source: str, url: str | None) -> ScoredDimension:
    return ScoredDimension(key=key, label=label, value=0.0, strength=Strength.WEAK, source=source, source_url=url)


def _evidence_rows(
    store: EvidenceStore, symbol: str, name: str
) -> tuple[list[ScoredDimension], list[ScoredDimension]]:
    norm = _norm(name)
    symbol_norm = _norm(symbol)
    pros: list[ScoredDimension] = []
    cons: list[ScoredDimension] = []

    facts = _rec_for(store, "find_cell_model", "name", norm)
    passport = facts.get("catalog_url") or (
        f"https://cellmodelpassports.sanger.ac.uk/passports/{facts['sidm_id']}" if facts.get("sidm_id") else None
    )

    for record in _dict_records(store, "cell_model_gene_mutations"):
        if _norm(record.input.get("model", "")) != norm or not record.data.get("found"):
            continue
        gene = str(record.data.get("gene_symbol") or record.input.get("gene_symbol") or "").upper()
        mutations = [m for m in (record.data.get("mutations") or []) if isinstance(m, dict)]
        driver = next((m for m in mutations if m.get("cancer_driver")), None)
        if driver:
            vaf = driver.get("vaf")
            vaf_txt = f", VAF {vaf:.2f}" if isinstance(vaf, (int, float)) else ""
            detail = " ".join(x for x in (driver.get("protein"), driver.get("effect")) if x)
            pros.append(_pro(f"mutation:{gene}", f"{gene} {detail}{vaf_txt} — confirmed cancer driver", _CMP, passport))
        elif _norm(gene) != symbol_norm:
            cons.append(_con(f"mutation:{gene}", f"Wild-type {gene} — lacks this disease driver", _CMP, passport))

    dep = _rec_for(store, "gene_dependency", "model", norm)
    if dep:
        detail = f"Gene-effect {_num(dep.get('gene_effect'))}"
        if dep.get("bf_scaled") is not None:
            detail += f", Bayes factor {_num(dep.get('bf_scaled'))}"
        dep_url = f"https://depmap.org/portal/gene/{symbol}"
        if dep.get("is_dependency"):
            pros.append(_pro("dependency", f"{detail} — a strong essential dependency", "DepMap", dep_url))
        else:
            cons.append(_con("dependency", f"{detail} — not an essential dependency here", "DepMap", dep_url))

    datasets = [str(d) for d in (facts.get("datasets_available") or [])]
    if datasets:
        pros.append(_pro("datasets", f"Data available: {', '.join(datasets)}", _CMP, passport))

    growth, ploidy = facts.get("growth_properties"), facts.get("ploidy")
    if growth or isinstance(ploidy, (int, float)):
        parts = [str(growth)] if growth else []
        if isinstance(ploidy, (int, float)):
            parts.append(f"ploidy ~{ploidy:.1f}")
        pros.append(_pro("growth", f"{', '.join(parts)} — straightforward to culture", _CMP, passport))

    prov = _rec_for(store, "cell_line_provenance", "name", norm)
    if prov:
        acc = prov.get("accession") or ""
        prov_url = prov.get("cellosaurus_url")
        if prov.get("problematic"):
            problems = ", ".join(str(p) for p in (prov.get("problems") or [])) or "flagged"
            cons.append(_con("provenance", f"Flagged problematic: {problems} ({acc})", "Cellosaurus", prov_url))
        else:
            cons_or = f"Clean provenance, not flagged ({acc})" if acc else "Clean provenance, not flagged"
            pros.append(_pro("provenance", cons_or, "Cellosaurus", prov_url))

    return pros, cons


def _is_purchasable(store: EvidenceStore, name: str) -> bool:
    prov = _rec_for(store, "cell_line_provenance", "name", _norm(name))
    listings = prov.get("commercial_listings") or prov.get("catalog") or {}
    return bool(listings)


def _display_name(store: EvidenceStore, name: str) -> str | None:
    norm = _norm(name)
    for tool in ("find_cell_model", "cell_line_provenance", "cell_model_gene_mutations", "gene_dependency"):
        for record in _dict_records(store, tool):
            data = record.data
            matches = (
                _norm(record.input.get("name", "")) == norm
                or _norm(record.input.get("model", "")) == norm
                or _norm(data.get("sidm_id", "")) == norm
                or _norm(data.get("model_id", "")) == norm
            )
            if matches:
                names = data.get("names") or data.get("model_names")
                if names:
                    return str(names[0])
    return None


def aggregate_recommendations(
    store: EvidenceStore, query: MatchmakerQuery
) -> RecommendationReport:
    panel = build_panel_from_evidence(store)
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
