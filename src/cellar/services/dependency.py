"""
CRISPR gene-dependency layer — the "is my target essential here" signal.

There is no open REST API for the Broad DepMap portal (it sits behind a
verification wall; its data ships as bulk CSVs). The equivalent CRISPR-dependency
database that IS queryable live is the **Sanger Cancer Dependency Map / Project
Score**, exposed through the same Cell Model Passports JSON:API as `crispr_ko`
gene-effect measurements. This module is a thin domain layer over that dataset
(see services.cell_model_passports for the raw client).

Endpoint: /datasets/crispr_ko  (~19.5M rows). Filter by the gene and model
RELATIONSHIPS using nested `has` filters (the row has no model_id/gene_id
columns). Each measurement carries:
  fc_clean_qn  quantile-normalised, corrected log fold-change — the gene-effect
               score. NEGATIVE = knockout depletes the cells = dependency
               (analogous to a DepMap Chronos score). ~0 = no effect.
  bf, bf_scaled  BAGEL Bayes Factor (dependency confidence).
  qc_pass, source, mageck_fdr.

There are typically several measurements per (gene, model) — different screen
libraries/sources — so we aggregate by mean.

Verified live: KRAS in KRAS-mutant MIA-PaCa-2 -> fc_clean_qn ~ -3.3 (strong
dependency); KRAS is screened across ~1100 models with a selective pattern.
"""
from statistics import fmean

from cellar.services import cell_model_passports as cmp

CRISPR_KO_DATASET = "datasets/crispr_ko"
GENE_EFFECT_FIELD = "fc_clean_qn"
DEPENDENCY_THRESHOLD = -0.5


def _gene_model_filter(gene_id: str, model_id: str | None = None) -> list[cmp.Filter]:
    filters: list[cmp.Filter] = [
        {"name": "gene", "op": "has", "val": {"name": "id", "op": "eq", "val": gene_id}}
    ]
    if model_id is not None:
        filters.append(
            {"name": "model", "op": "has", "val": {"name": "id", "op": "eq", "val": model_id}}
        )
    return filters


def _resolve_model_id(model: str, **kwargs: object) -> tuple[str | None, object]:
    if model.upper().startswith("SIDM"):
        return model, None
    found = cmp.find_model(model, **kwargs)
    if found is None:
        return None, None
    return found["id"], found.get("names")


def _dependency_signal(gene_effect: float | None) -> float | None:
    if gene_effect is None:
        return None
    return round(min(max(-gene_effect / 2.0, 0.0), 1.0), 3)


def _effects(records: list[dict[str, object]]) -> list[float]:
    return [r[GENE_EFFECT_FIELD] for r in records if r.get(GENE_EFFECT_FIELD) is not None]


def gene_effect_in_model(gene_symbol: str, model: str, **kwargs: object) -> dict[str, object]:
    """Per-model CRISPR gene-effect for a target: is knocking it out lethal in
    this specific cell model. `model` is a name or SIDM id."""
    gene = cmp.find_gene(gene_symbol, **kwargs)
    if gene is None:
        return {"found": False, "reason": f"gene not found: {gene_symbol}"}
    model_id, model_names = _resolve_model_id(model, **kwargs)
    if model_id is None:
        return {"found": False, "reason": f"model not found: {model}"}
    result = cmp.get_collection(
        CRISPR_KO_DATASET,
        filters=_gene_model_filter(gene["id"], model_id),
        max_pages=2,
        **kwargs,
    )
    records = result["records"]
    effects = _effects(records)
    if not effects:
        return {
            "found": True,
            "gene_symbol": gene_symbol,
            "gene_id": gene["id"],
            "model_id": model_id,
            "model_names": model_names,
            "n_measurements": 0,
            "screened": False,
            "note": "no CRISPR knockout screen for this gene in this model",
        }
    gene_effect = round(fmean(effects), 3)
    bf_values = [r["bf_scaled"] for r in records if r.get("bf_scaled") is not None]
    return {
        "found": True,
        "gene_symbol": gene_symbol,
        "gene_id": gene["id"],
        "model_id": model_id,
        "model_names": model_names,
        "n_measurements": len(records),
        "screened": True,
        "gene_effect": gene_effect,
        "bf_scaled": round(fmean(bf_values), 3) if bf_values else None,
        "qc_pass": all(bool(r.get("qc_pass")) for r in records),
        "source": sorted({r.get("source") for r in records if r.get("source")}),
        "is_dependency": gene_effect < DEPENDENCY_THRESHOLD,
        "dependency_signal": _dependency_signal(gene_effect),
    }


def gene_dependency_summary(
    gene_symbol: str, page_size: int = 100, max_pages: int = 15, **kwargs: object
) -> dict[str, object]:
    """Across-model view: in how many screened models is the target a dependency,
    and how strong. Aggregates the per-model mean gene-effect over all screens."""
    gene = cmp.find_gene(gene_symbol, **kwargs)
    if gene is None:
        return {"found": False, "reason": f"gene not found: {gene_symbol}"}
    result = cmp.get_collection(
        CRISPR_KO_DATASET,
        filters=_gene_model_filter(gene["id"]),
        page_size=page_size,
        max_pages=max_pages,
        **kwargs,
    )
    by_model: dict[str, list[float]] = {}
    for record in result["records"]:
        effect = record.get(GENE_EFFECT_FIELD)
        model_id = (record.get("relationships") or {}).get("model")
        if effect is not None and isinstance(model_id, str):
            by_model.setdefault(model_id, []).append(effect)
    per_model = {model_id: fmean(values) for model_id, values in by_model.items()}
    if not per_model:
        return {
            "found": True,
            "gene_symbol": gene_symbol,
            "gene_id": gene["id"],
            "n_models": 0,
            "screened": False,
            "note": "gene not present in the CRISPR screen dataset",
        }
    dependent = {m: e for m, e in per_model.items() if e < DEPENDENCY_THRESHOLD}
    strongest_model = min(per_model, key=per_model.get)
    mean_effect = round(fmean(per_model.values()), 3)
    return {
        "found": True,
        "gene_symbol": gene_symbol,
        "gene_id": gene["id"],
        "n_models": len(per_model),
        "screened": True,
        "truncated": result["truncated"],
        "mean_gene_effect": mean_effect,
        "n_dependent_models": len(dependent),
        "fraction_dependent": round(len(dependent) / len(per_model), 3),
        "strongest": {
            "model_id": strongest_model,
            "gene_effect": round(per_model[strongest_model], 3),
        },
        "dependency_signal": _dependency_signal(mean_effect),
    }
