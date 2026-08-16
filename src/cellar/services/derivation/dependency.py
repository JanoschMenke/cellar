from statistics import fmean
from typing import cast

from cellar.schemas.derivation import (
    GeneDependencyMissing,
    GeneDependencyScreened,
    GeneDependencyUnscreened,
    GeneEffectMissing,
    GeneEffectScreened,
    GeneEffectUnscreened,
    StrongestModel,
)
from cellar.schemas.domain import CRISPR_KO_DATASET, DEPENDENCY_THRESHOLD, GENE_EFFECT_FIELD
from cellar.schemas.scoring import DEPENDENCY_SIGNAL_DIVISOR
from cellar.services.sources import cell_model_passports as cmp


def _gene_model_filter(gene_id: str, model_id: str | None = None) -> list[cmp.Filter]:
    filters: list[cmp.Filter] = [
        {"name": "gene", "op": "has", "val": {"name": "id", "op": "eq", "val": gene_id}}
    ]
    if model_id is not None:
        filters.append(
            {"name": "model", "op": "has", "val": {"name": "id", "op": "eq", "val": model_id}}
        )
    return filters


def _resolve_model_id(
    model: str, use_cache: bool = True, cache_dir: str = cmp.DEFAULT_CACHE_DIR
) -> tuple[str | None, object]:
    if model.upper().startswith("SIDM"):
        return model, None
    found = cmp.find_model(model, use_cache=use_cache, cache_dir=cache_dir)
    if found is None:
        return None, None
    return cast(str, found["id"]), found.get("names")


def _dependency_signal(gene_effect: float | None) -> float | None:
    if gene_effect is None:
        return None
    return round(min(max(-gene_effect / DEPENDENCY_SIGNAL_DIVISOR, 0.0), 1.0), 3)


def _effects(records: list[dict[str, object]]) -> list[float]:
    return [
        cast(float, r[GENE_EFFECT_FIELD]) for r in records if r.get(GENE_EFFECT_FIELD) is not None
    ]


def gene_effect_in_model(
    gene_symbol: str,
    model: str,
    use_cache: bool = True,
    cache_dir: str = cmp.DEFAULT_CACHE_DIR,
) -> GeneEffectMissing | GeneEffectUnscreened | GeneEffectScreened:
    gene = cmp.find_gene(gene_symbol, use_cache=use_cache, cache_dir=cache_dir)
    if gene is None:
        return GeneEffectMissing(reason=f"gene not found: {gene_symbol}")
    gene_id = cast(str, gene["id"])
    model_id, model_names = _resolve_model_id(model, use_cache=use_cache, cache_dir=cache_dir)
    if model_id is None:
        return GeneEffectMissing(reason=f"model not found: {model}")
    result = cmp.get_collection(
        CRISPR_KO_DATASET,
        filters=_gene_model_filter(gene_id, model_id),
        max_pages=2,
        use_cache=use_cache,
        cache_dir=cache_dir,
    )
    records = cast("list[dict[str, object]]", result["records"])
    effects = _effects(records)
    if not effects:
        return GeneEffectUnscreened(
            gene_symbol=gene_symbol,
            gene_id=gene_id,
            model_id=model_id,
            model_names=model_names,
            n_measurements=0,
            note="no CRISPR knockout screen for this gene in this model",
        )
    gene_effect = round(fmean(effects), 3)
    bf_values = [cast(float, r["bf_scaled"]) for r in records if r.get("bf_scaled") is not None]
    return GeneEffectScreened(
        gene_symbol=gene_symbol,
        gene_id=gene_id,
        model_id=model_id,
        model_names=model_names,
        n_measurements=len(records),
        gene_effect=gene_effect,
        bf_scaled=round(fmean(bf_values), 3) if bf_values else None,
        qc_pass=all(bool(r.get("qc_pass")) for r in records),
        source=sorted({str(r.get("source")) for r in records if r.get("source")}),
        is_dependency=gene_effect < DEPENDENCY_THRESHOLD,
        dependency_signal=_dependency_signal(gene_effect),
    )


def gene_dependency_summary(
    gene_symbol: str,
    page_size: int = 100,
    max_pages: int = 15,
    use_cache: bool = True,
    cache_dir: str = cmp.DEFAULT_CACHE_DIR,
) -> GeneDependencyMissing | GeneDependencyUnscreened | GeneDependencyScreened:
    gene = cmp.find_gene(gene_symbol, use_cache=use_cache, cache_dir=cache_dir)
    if gene is None:
        return GeneDependencyMissing(reason=f"gene not found: {gene_symbol}")
    gene_id = cast(str, gene["id"])
    result = cmp.get_collection(
        CRISPR_KO_DATASET,
        filters=_gene_model_filter(gene_id),
        page_size=page_size,
        max_pages=max_pages,
        use_cache=use_cache,
        cache_dir=cache_dir,
    )
    by_model: dict[str, list[float]] = {}
    for record in cast("list[dict[str, object]]", result["records"]):
        effect = record.get(GENE_EFFECT_FIELD)
        relationships = cast("dict[str, object]", record.get("relationships") or {})
        model_id = relationships.get("model")
        if effect is not None and isinstance(model_id, str):
            by_model.setdefault(model_id, []).append(cast(float, effect))
    per_model = {model_id: fmean(values) for model_id, values in by_model.items()}
    if not per_model:
        return GeneDependencyUnscreened(
            gene_symbol=gene_symbol,
            gene_id=gene_id,
            n_models=0,
            note="gene not present in the CRISPR screen dataset",
        )
    dependent = {m: e for m, e in per_model.items() if e < DEPENDENCY_THRESHOLD}
    strongest_model = min(per_model, key=lambda m: per_model[m])
    mean_effect = round(fmean(per_model.values()), 3)
    return GeneDependencyScreened(
        gene_symbol=gene_symbol,
        gene_id=gene_id,
        n_models=len(per_model),
        truncated=cast(bool, result["truncated"]),
        mean_gene_effect=mean_effect,
        n_dependent_models=len(dependent),
        fraction_dependent=round(len(dependent) / len(per_model), 3),
        strongest=StrongestModel(
            model_id=strongest_model,
            gene_effect=round(per_model[strongest_model], 3),
        ),
        dependency_signal=_dependency_signal(mean_effect),
    )
