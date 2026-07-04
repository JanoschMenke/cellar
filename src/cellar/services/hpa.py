"""
Human Protein Atlas (HPA) — protein-level expression, subcellular localization,
and cancer prognostic evidence. Promotes proteomics.hpa_protein_evidence to a
proper client exposing the fuller field set the live API actually returns.

HPA's role in the matchmaker (tier 3 of the protein-evidence hierarchy, see
proteomics.py): it is human-TISSUE antibody/RNA-seq evidence, not a specific cell
line or organoid — it cannot tell you whether a given model expresses the target,
only whether the protein is known to exist, where, and how tissue-specific. Its
two distinguishing signals:

  * mRNA-vs-protein discordance — RNA broadly detected but protein narrowly
    detected means don't trust RNA-seq alone as a presence proxy (verified live:
    ZDHHC20 RNA "Detected in all" vs protein "Detected in some").
  * cancer prognostic significance — is expression of this target associated
    with patient outcome in a specific tumour type (TCGA + independent
    validation cohorts), a disease-relevance signal no other source here has.

Endpoint: https://www.proteinatlas.org/{ensembl_id}.json (public, no auth,
undocumented but stable — the same endpoint the HPA website itself renders
from). An unknown Ensembl id returns HTTP 404 with a plain-text body.
"""
import json
import urllib.error
import urllib.request

from cellar.services import retrieval

API_URL = "https://www.proteinatlas.org/{ensembl_id}.json"


def _fetch(ensembl_id: str, timeout: int = 40) -> dict[str, object] | None:
    request = urllib.request.Request(API_URL.format(ensembl_id=ensembl_id))
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            return json.loads(response.read().decode())
    except urllib.error.HTTPError as error:
        if error.code == 404:
            return None
        raise


def _mrna_protein_discordant(rna_distribution: str | None, protein_distribution: str | None) -> bool:
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
    """Protein-level HPA profile for a target: expression distribution,
    subcellular localization, antibody reliability, and cancer prognostic
    significance (optionally filtered to diseases matching disease_hint)."""
    ensembl_id = retrieval.ot_resolve_target(target_symbol)
    if ensembl_id is None:
        return {"found": False, "reason": f"target not found: {target_symbol}"}
    record = _fetch(ensembl_id)
    if record is None:
        return {"found": False, "reason": f"no HPA record for {ensembl_id}"}
    rna_distribution = record.get("RNA tissue distribution")
    protein_distribution = record.get("Protein tissue distribution")
    prognostics = _cancer_prognostics(record, disease_hint)
    significant = {
        disease: entry for disease, entry in prognostics.items() if entry.get("is_prognostic")
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
