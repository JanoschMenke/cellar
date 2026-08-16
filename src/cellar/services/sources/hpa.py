from typing import cast

from cellar.config import HPA_URL_TEMPLATE as API_URL
from cellar.services.sources import open_targets
from cellar.utils import http


def raw_profile(ensembl_id: str, timeout: int = 40) -> dict[str, object]:
    return cast(
        "dict[str, object]",
        http.get_json(API_URL.format(ensembl_id=ensembl_id), timeout=timeout),
    )


def _fetch(ensembl_id: str, timeout: int = 40) -> dict[str, object] | None:
    try:
        return raw_profile(ensembl_id, timeout=timeout)
    except http.HttpError as error:
        if error.status == 404:
            return None
        raise


def _mrna_protein_discordant(
    rna_distribution: str | None, protein_distribution: str | None
) -> bool:
    return rna_distribution == "Detected in all" and protein_distribution not in (
        None,
        "Detected in all",
    )


def _cancer_prognostics(record: dict[str, object], disease_hint: str | None) -> dict[str, object]:
    out: dict[str, object] = {}
    for key, value in record.items():
        if not key.startswith("Cancer prognostics"):
            continue
        disease = key.removeprefix("Cancer prognostics - ")
        if disease_hint and disease_hint.lower() not in disease.lower():
            continue
        out[disease] = value
    return out


def protein_profile(target_symbol: str, disease_hint: str | None = None) -> dict[str, object]:
    ensembl_id = open_targets.ot_resolve_target(target_symbol)
    if ensembl_id is None:
        return {"found": False, "reason": f"target not found: {target_symbol}"}
    record = _fetch(ensembl_id)
    if record is None:
        return {"found": False, "reason": f"no HPA record for {ensembl_id}"}
    rna_distribution = cast("str | None", record.get("RNA tissue distribution"))
    protein_distribution = cast("str | None", record.get("Protein tissue distribution"))
    prognostics = _cancer_prognostics(record, disease_hint)
    significant = {
        disease: entry
        for disease, entry in prognostics.items()
        if cast("dict[str, object]", entry).get("is_prognostic")
    }
    return {
        "found": True,
        "gene": record.get("Gene"),
        "ensembl_id": ensembl_id,
        "gene_description": record.get("Gene description"),
        "evidence_level": record.get("Evidence"),
        "protein_class": record.get("Protein class"),
        "subcellular_location": record.get("Subcellular location"),
        "rna_tissue_distribution": rna_distribution,
        "rna_tissue_specificity": record.get("RNA tissue specificity"),
        "protein_tissue_distribution": protein_distribution,
        "protein_tissue_specificity": record.get("Protein tissue specificity"),
        "mrna_protein_discordant": _mrna_protein_discordant(rna_distribution, protein_distribution),
        "antibody_reliability": {
            "immunofluorescence": record.get("Reliability (IF)"),
            "immunohistochemistry": record.get("Reliability (IH)"),
        },
        "cell_type_specificity": {
            "protein": record.get("Protein cell type distribution"),
            "rna_single_cell": record.get("RNA single cell type distribution"),
        },
        "cancer_prognostics": prognostics,
        "significant_cancer_prognostics": significant,
    }
