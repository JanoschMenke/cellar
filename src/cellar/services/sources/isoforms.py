from typing import cast

from cellar.config import ENSEMBL_URL as E
from cellar.schemas.sources import (
    Isoform,
    IsoformRiskSummary,
    IsoformSpecificityRisk,
    ShortestIsoform,
)
from cellar.utils import http


def protein_coding_isoforms(ensembl_gene_id: str) -> list[Isoform]:
    g = cast(
        "dict[str, object]",
        http.get_json(
            f"{E}/lookup/id/{ensembl_gene_id}?expand=1;content-type=application/json",
            headers={"Content-Type": "application/json"},
            timeout=60,
        ),
    )
    out: list[Isoform] = []
    for t in cast("list[dict[str, object]]", g.get("Transcript", [])):
        if t.get("biotype") != "protein_coding":
            continue
        tr = cast("dict[str, object]", t.get("Translation") or {})
        out.append(
            Isoform(
                transcript_id=str(t["id"]),
                name=cast("str | None", t.get("display_name")),
                aa_length=cast("int | None", tr.get("length")),
                is_canonical=bool(t.get("is_canonical")),
            )
        )
    out.sort(key=lambda i: (-int(i.is_canonical), -(i.aa_length or 0)))
    return out


def _aa_length(record: Isoform) -> int:
    return cast(int, record.aa_length)


def isoform_risk_summary(
    isoforms: list[Isoform], functional_len_min: int | None = None
) -> IsoformRiskSummary:
    coding = [i for i in isoforms if i.aa_length]
    canonical = next((i for i in isoforms if i.is_canonical), None)
    canonical_aa = canonical.aa_length if canonical else None
    canonical_aa_int = canonical_aa if canonical_aa else None
    lens = [_aa_length(i) for i in coding]
    span = (min(lens), max(lens)) if lens else (None, None)
    n_alt = len(coding) - (1 if canonical and canonical.aa_length else 0)

    alternatives = [i for i in coding if not i.is_canonical]
    plausible = [
        i for i in alternatives if not canonical_aa_int or _aa_length(i) >= 0.5 * canonical_aa_int
    ]
    n_fragments = len(alternatives) - len(plausible)
    shortest = min(plausible, key=_aa_length, default=None)
    frac = _aa_length(shortest) / canonical_aa_int if shortest and canonical_aa_int else None
    short_label = (shortest.name or shortest.transcript_id) if shortest else None
    fragment_note = f" ({n_fragments} short fragment transcript(s) ignored)" if n_fragments else ""
    functional = ([canonical] if canonical and canonical.aa_length else []) + plausible
    func_lens = [_aa_length(i) for i in functional]
    func_span = (min(func_lens), max(func_lens)) if func_lens else (None, None)
    n_functional = len(functional)
    n_substantial = len(plausible)
    below_functional = [
        i for i in plausible if functional_len_min and _aa_length(i) < functional_len_min
    ]

    if below_functional:
        risk = IsoformSpecificityRisk.HIGH
        s = min(below_functional, key=_aa_length)
        s_label = s.name or s.transcript_id
        message = (
            f"A substantial isoform {s_label} ({_aa_length(s)} aa) is below the functional length "
            f"({functional_len_min} aa) and likely lacks the required domain — confirm the model "
            f"expresses the full-length canonical {canonical.name if canonical else None} "
            f"({canonical_aa_int} aa) with an isoform-specific antibody or junction-level RNA-seq."
        )
    else:
        risk = IsoformSpecificityRisk.LOW
        if n_substantial == 0:
            core = (
                f"The canonical {canonical.name if canonical else None} "
                f"({canonical_aa_int} aa) is the only full-length protein-coding isoform"
            )
        else:
            core = (
                f"Ensembl annotates {n_functional} protein-coding isoforms "
                f"({func_span[0]}-{func_span[1]} aa), mostly minor/predicted forms; the canonical "
                f"{canonical.name if canonical else None} ({canonical_aa_int} aa) "
                "is assumed to be the expressed protein"
            )
        message = (
            f"{core}{fragment_note}. Isoform choice is treated as low-risk — a firmer call would need "
            "the expressed isoform (junction-level RNA-seq) or a known functional-domain length "
            "(pass functional_len_min)."
        )

    return IsoformRiskSummary(
        canonical=canonical.name if canonical else None,
        canonical_aa=canonical_aa,
        n_protein_coding=len(coding),
        n_alternative=n_alt,
        aa_span=span,
        shortest_isoform=(
            ShortestIsoform(
                name=cast(str, short_label),
                transcript_id=shortest.transcript_id,
                aa_length=cast(int, shortest.aa_length),
                pct_of_canonical=round(frac * 100) if frac is not None else None,
            )
            if shortest
            else None
        ),
        isoform_specificity_risk=risk,
        message=message,
    )
