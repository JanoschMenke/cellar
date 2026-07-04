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
import json
import urllib.request

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
    """Grade whether picking the wrong protein-coding isoform could change the
    readout. Risk is driven by whether a SUBSTANTIALLY truncated isoform exists
    (one short enough to likely drop a functional/catalytic domain) — not merely
    by how many isoforms there are. functional_len_min, when given, flags any
    isoform below that amino-acid length as domain-losing."""
    coding = [i for i in isoforms if i.get("aa_length")]
    canonical = next((i for i in isoforms if i.get("is_canonical")), None)
    canonical_aa = canonical.get("aa_length") if canonical else None
    lens = [i["aa_length"] for i in coding]
    span = (min(lens), max(lens)) if lens else (None, None)
    n_alt = len(coding) - (1 if canonical and canonical.get("aa_length") else 0)

    alternatives = [i for i in coding if not i.get("is_canonical")]
    # Ensembl labels many tiny ORFs / NMD / partial transcripts 'protein_coding'.
    # They are almost never the expressed functional protein, so judge risk only on
    # PLAUSIBLE isoforms (>= half the canonical length); count the rest as fragments.
    plausible = [
        i for i in alternatives if not canonical_aa or i["aa_length"] >= 0.5 * canonical_aa
    ]
    n_fragments = len(alternatives) - len(plausible)
    shortest = min(plausible, key=lambda i: i["aa_length"], default=None)
    frac = shortest["aa_length"] / canonical_aa if shortest and canonical_aa else None
    short_label = (shortest.get("name") or shortest["transcript_id"]) if shortest else None
    fragment_note = f" ({n_fragments} short fragment transcript(s) ignored)" if n_fragments else ""
    functional = ([canonical] if canonical and canonical.get("aa_length") else []) + plausible
    func_lens = [i["aa_length"] for i in functional]
    func_span = (min(func_lens), max(func_lens)) if func_lens else (None, None)
    n_functional = len(functional)
    n_substantial = len(plausible)
    # Only a caller-supplied domain boundary is a reliable domain-loss signal; Ensembl
    # transcript length alone over-flags because almost every gene has some mid-length form.
    below_functional = [i for i in plausible if functional_len_min and i["aa_length"] < functional_len_min]

    if below_functional:
        risk = "high"
        s = min(below_functional, key=lambda i: i["aa_length"])
        s_label = s.get("name") or s["transcript_id"]
        message = (
            f"A substantial isoform {s_label} ({s['aa_length']} aa) is below the functional length "
            f"({functional_len_min} aa) and likely lacks the required domain — confirm the model "
            f"expresses the full-length canonical {canonical.get('name')} ({canonical_aa} aa) with an "
            "isoform-specific antibody or junction-level RNA-seq."
        )
    else:
        risk = "low"
        if n_substantial == 0:
            core = (
                f"The canonical {canonical.get('name')} ({canonical_aa} aa) is the only full-length "
                "protein-coding isoform"
            )
        else:
            core = (
                f"Ensembl annotates {n_functional} protein-coding isoforms ({func_span[0]}-{func_span[1]} aa), "
                f"mostly minor/predicted forms; the canonical {canonical.get('name')} ({canonical_aa} aa) "
                "is assumed to be the expressed protein"
            )
        message = (
            f"{core}{fragment_note}. Isoform choice is treated as low-risk — a firmer call would need "
            "the expressed isoform (junction-level RNA-seq) or a known functional-domain length "
            "(pass functional_len_min)."
        )

    return {
        "canonical": canonical.get("name") if canonical else None,
        "canonical_aa": canonical_aa,
        "n_protein_coding": len(coding),
        "n_alternative": n_alt,
        "aa_span": span,
        "shortest_isoform": (
            {
                "name": short_label,
                "transcript_id": shortest["transcript_id"],
                "aa_length": shortest["aa_length"],
                "pct_of_canonical": round(frac * 100) if frac is not None else None,
            }
            if shortest
            else None
        ),
        "isoform_specificity_risk": risk,
        "message": message,
    }
