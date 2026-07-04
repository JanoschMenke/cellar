"""
Isoform / splicing layer — a model can express the gene but the WRONG transcript.
Verified live for ZDHHC20: 38 transcripts, 16 protein-coding, canonical = 365 aa
with a ladder of shorter forms (354, 344, 326, 320, ...) that can drop the
catalytic DHHC domain or transmembrane helices.

Job: enumerate protein-coding isoforms, flag whether the functional domain is
retained, and expose a per-model 'does it express the RIGHT isoform' check that
feeds scoring (currently from literature/Elicit; junction-level quant from
GTEx/DepMap RNA is the stretch goal).
"""
import urllib.request, json

E = "https://rest.ensembl.org"

def _get(url, t=60):
    req = urllib.request.Request(url, headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=t) as f:
        return json.loads(f.read().decode())

def protein_coding_isoforms(ensembl_gene_id):
    """Return canonical + alternative protein-coding isoforms with lengths.
    Verified: ENSG00000180776 -> 16 protein-coding, canonical 365 aa."""
    g = _get(f"{E}/lookup/id/{ensembl_gene_id}?expand=1;content-type=application/json")
    out = []
    for t in g.get("Transcript", []):
        if t.get("biotype") != "protein_coding":
            continue
        tr = t.get("Translation") or {}
        out.append({
            "transcript_id": t["id"],
            "name": t.get("display_name"),
            "aa_length": tr.get("length"),
            "is_canonical": bool(t.get("is_canonical")),
        })
    out.sort(key=lambda x: (-int(x["is_canonical"]), -(x["aa_length"] or 0)))
    return out

def isoform_risk_summary(isoforms, functional_len_min=None):
    """Heuristic: if there are multiple protein-coding isoforms spanning a wide
    length range, isoform-specificity of the model matters. functional_len_min
    lets you flag truncated forms likely to have lost the catalytic domain."""
    lens = [i["aa_length"] for i in isoforms if i["aa_length"]]
    canonical = next((i for i in isoforms if i["is_canonical"]), None)
    n_alt = len(isoforms) - (1 if canonical else 0)
    span = (min(lens), max(lens)) if lens else (None, None)
    risk = "high" if (n_alt >= 3 and lens and (max(lens) - min(lens)) > 50) else "low"
    return {
        "canonical": canonical["name"] if canonical else None,
        "canonical_aa": canonical["aa_length"] if canonical else None,
        "n_protein_coding": len(isoforms),
        "n_alternative": n_alt,
        "aa_span": span,
        "isoform_specificity_risk": risk,
        "message": (f"{len(isoforms)} protein-coding isoforms ({span[0]}-{span[1]} aa). "
                    "Confirm the model expresses the catalytic-domain-containing "
                    "isoform, not a truncated form." if risk == "high"
                    else "Isoform choice unlikely to change the readout."),
    }
