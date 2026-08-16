import json
import os
from typing import cast

from cellar.schemas.derivation import HpaProteinEvidence, ProteinSynthesis
from cellar.schemas.domain import TIER_WEIGHT
from cellar.schemas.matchmaker import EvidenceTier, MsDetectabilityTier
from cellar.schemas.scoring import (
    CONF_BASE,
    CONF_GATED_CAP,
    CONF_MAX,
    CONF_PER_SIGNAL,
    CONF_TUMOR_BONUS,
    DEPMAP_LOW,
    HPA_SIG_FULL,
    HPA_SIG_PARTIAL,
    HPA_SIG_WEAK,
    MS_LOW_MAX,
    MS_MODERATE_MAX,
    MS_TIER_SIGNAL,
)
from cellar.schemas.services import McpTool
from cellar.services.sources import hpa


def protein_evidence_note(synthesis: ProteinSynthesis | None) -> str:
    if synthesis is None or not synthesis.provenance:
        return ""
    evidence = "; ".join(synthesis.provenance)
    if EvidenceTier.MODEL_SPECIFIC in synthesis.per_tier:
        return (
            f"{evidence}. The protein has been reported measured in this model, so a "
            "lysate-based protein assay is a demonstrated route here."
        )
    return f"{evidence}. No report of the protein measured in this model."


def hpa_protein_evidence(ensembl_id: str, disease_hint: str = "Pancreatic") -> HpaProteinEvidence:
    d = hpa.raw_profile(ensembl_id, timeout=60)
    subloc = cast(
        "list[str]", d.get("Subcellular location") or d.get("Subcellular main location") or []
    )
    rna_dist = d.get("RNA tissue distribution")
    prot_dist = d.get("Protein tissue distribution")
    discordant = (rna_dist == "Detected in all") and (prot_dist not in (None, "Detected in all"))
    prog = {
        k: v
        for k, v in d.items()
        if k.startswith("Cancer prognostics") and disease_hint.lower() in k.lower()
    }
    protein_class = cast("list[str] | None", d.get("Protein class"))
    return HpaProteinEvidence(
        subcellular=subloc,
        protein_class=protein_class,
        rna_tissue_distribution=rna_dist,
        protein_tissue_distribution=prot_dist,
        mrna_protein_discordant=discordant,
        protein_cell_type_intensity=d.get("Protein cell type specific Intensity"),
        disease_protein_prognostic=prog,
    )


def pride_ms_detectability(uniprot_accession: str, mcp: McpTool) -> dict[str, object]:
    r = mcp(
        "omics-archives", "pride_find_projects_for_protein", protein_accession=uniprot_accession
    )
    recs = cast("list[dict[str, object]]", r.get("records", []) or [])
    n = cast(int, r.get("n_records", len(recs)))
    return {
        "uniprot": uniprot_accession,
        "n_projects": n,
        "tier": ms_detectability_tier(n),
        "is_detectable": n > 0,
        "projects": [x.get("accession") or x.get("project_accession") for x in recs[:20]],
    }


def ms_detectability_tier(n_projects: int) -> MsDetectabilityTier:
    if n_projects == 0:
        return MsDetectabilityTier.UNDETECTED
    if n_projects < MS_LOW_MAX:
        return MsDetectabilityTier.LOW
    if n_projects < MS_MODERATE_MAX:
        return MsDetectabilityTier.MODERATE
    return MsDetectabilityTier.HIGH


def load_pride_cache(path: str) -> dict[str, object]:
    if os.path.exists(path):
        with open(path) as f:
            return cast("dict[str, object]", json.load(f))
    return {}


def cptac_tumor_quant(
    gene: str,
    tumor: str = "PDAC",
    detected: bool | None = None,
    log2fc: float | None = None,
    phosphosites: object | None = None,
    n_tumors: int | None = None,
) -> dict[str, object]:
    return {
        "gene": gene,
        "tumor": tumor,
        "detected": detected,
        "tumor_vs_normal_log2fc": log2fc,
        "phosphosites": phosphosites,
        "n_tumors": n_tumors,
        "wired": detected is not None,
        "note": (
            "cached/live PDC quant"
            if detected is not None
            else "wire PDC GraphQL or cache CPTAC PDAC protein quant CSV"
        ),
    }


def depmap_proteomics(
    gene: str, line_intensities: dict[str, float] | None = None
) -> dict[str, object]:
    return {
        "gene": gene,
        "lines": line_intensities or {},
        "wired": bool(line_intensities),
        "note": (
            "cached DepMap/CCLE proteomics intensities"
            if line_intensities
            else "wire DepMap 'proteomics' (Gygi TMT) table by cell line"
        ),
    }


_UNIPROT_EXISTENCE_SOURCE = "uniprot_protein_existence"


def _ms_provenance(pride: dict[str, object], n_projects: int, tier: MsDetectabilityTier) -> str:
    if pride.get("source") == _UNIPROT_EXISTENCE_SOURCE:
        level = pride.get("protein_existence_level")
        return f"UniProt protein existence level {level} (protein-level evidence)"
    return f"PRIDE MS projects n={n_projects} (tier={tier})"


def _is_ms_hard_class(protein_class: list[str] | None, subcellular: list[str] | None) -> bool:
    cls = " ".join(protein_class or []).lower()
    loc = " ".join(subcellular or []).lower()
    return "membrane" in cls or any(
        h in loc for h in ("membrane", "vesicle", "golgi", "endoplasmic", "er")
    )


def synthesize_protein_evidence(
    hpa: HpaProteinEvidence | None = None,
    pride: dict[str, object] | None = None,
    cptac: dict[str, object] | None = None,
    depmap: dict[str, object] | None = None,
    cell_line: str | None = None,
) -> ProteinSynthesis:
    per_tier: dict[EvidenceTier, object] = {}
    provenance: list[str] = []
    caveats: list[str] = []
    signals: list[tuple[EvidenceTier, float, float]] = []

    subloc = hpa.subcellular if hpa else []
    pclass = hpa.protein_class if hpa else []
    ms_hard = _is_ms_hard_class(pclass, subloc)

    depmap_lines = cast("dict[str, float]", (depmap or {}).get("lines") or {})
    if depmap and depmap.get("wired") and cell_line in depmap_lines:
        v = depmap_lines[cell_line]
        per_tier[EvidenceTier.MODEL_SPECIFIC] = v
        signals.append((EvidenceTier.MODEL_SPECIFIC, TIER_WEIGHT[EvidenceTier.MODEL_SPECIFIC], v))
        provenance.append(f"DepMap proteomics ({cell_line}) intensity={v:.2f}")
        if v < DEPMAP_LOW:
            caveats.append(
                f"{cell_line}: low protein intensity in DepMap proteomics "
                "— model-level negative, not just an MS gap."
            )

    if cptac and cptac.get("wired"):
        det = 1.0 if cptac.get("detected") else 0.0
        per_tier[EvidenceTier.TUMOR_QUANT] = cptac
        signals.append((EvidenceTier.TUMOR_QUANT, TIER_WEIGHT[EvidenceTier.TUMOR_QUANT], det))
        fc = cptac.get("tumor_vs_normal_log2fc")
        provenance.append(
            f"CPTAC {cptac.get('tumor')} detected={bool(cptac.get('detected'))}"
            + (f", log2FC={fc}" if fc is not None else "")
        )

    if hpa:
        prot_dist = hpa.protein_tissue_distribution
        prot_dist_str = prot_dist if isinstance(prot_dist, str) else None
        hpa_sig = (
            HPA_SIG_FULL
            if prot_dist_str == "Detected in all"
            else HPA_SIG_PARTIAL
            if prot_dist_str and "Detected in" in prot_dist_str
            else HPA_SIG_WEAK
            if prot_dist_str
            else None
        )
        if hpa_sig is not None:
            per_tier[EvidenceTier.LOCALIZATION_AB] = prot_dist
            signals.append(
                (EvidenceTier.LOCALIZATION_AB, TIER_WEIGHT[EvidenceTier.LOCALIZATION_AB], hpa_sig)
            )
            provenance.append(f"HPA protein '{prot_dist}', subcellular={subloc}")
        if hpa.mrna_protein_discordant:
            caveats.append(
                "mRNA broad but protein narrow (HPA) — confirm protein "
                "by WB/IF in your lot; do not rely on RNA-seq."
            )

    if pride is not None:
        n = cast(int, pride.get("n_projects", 0))
        tier = MsDetectabilityTier(str(pride["tier"]))
        ms_sig = MS_TIER_SIGNAL[tier]
        per_tier[EvidenceTier.MS_DETECTABILITY] = pride
        provenance.append(_ms_provenance(pride, n, tier))
        if tier in (MsDetectabilityTier.UNDETECTED, MsDetectabilityTier.LOW):
            if ms_hard:
                caveats.append(
                    f"MS-absence guard: {tier} MS detectability (PRIDE n={n}) "
                    "is expected for a membrane/low-abundance target and is NOT "
                    "evidence of absence — weighted down, not used to reject."
                )
            else:
                signals.append(
                    (
                        EvidenceTier.MS_DETECTABILITY,
                        TIER_WEIGHT[EvidenceTier.MS_DETECTABILITY],
                        ms_sig,
                    )
                )
                caveats.append(
                    f"MS detectability low (PRIDE n={n}) for a normally MS-visible "
                    "class — treat protein presence as unconfirmed."
                )
        else:
            signals.append(
                (EvidenceTier.MS_DETECTABILITY, TIER_WEIGHT[EvidenceTier.MS_DETECTABILITY], ms_sig)
            )

    if not signals:
        return ProteinSynthesis(
            protein_present=None,
            confidence=0.0,
            provenance=provenance,
            caveats=caveats or ["No protein-level evidence available."],
            ms_absence_guard_applied=bool(
                ms_hard
                and (pride or {}).get("tier")
                in (MsDetectabilityTier.UNDETECTED, MsDetectabilityTier.LOW)
            ),
            per_tier=per_tier,
        )

    num = sum(w * s for _, w, s in signals)
    den = sum(w for _, w, s in signals)
    protein_present = round(num / den, 3)

    have_direct = any(
        t in (EvidenceTier.MODEL_SPECIFIC, EvidenceTier.TUMOR_QUANT) for t, _, _ in signals
    )
    base_conf = CONF_BASE + CONF_PER_SIGNAL * len(signals)
    if have_direct:
        base_conf += CONF_TUMOR_BONUS
    if ms_hard and not have_direct:
        base_conf = min(base_conf, CONF_GATED_CAP)
    confidence = round(min(base_conf, CONF_MAX), 3)

    return ProteinSynthesis(
        protein_present=protein_present,
        confidence=confidence,
        provenance=provenance,
        caveats=caveats,
        ms_absence_guard_applied=bool(
            ms_hard
            and (pride or {}).get("tier")
            in (MsDetectabilityTier.UNDETECTED, MsDetectabilityTier.LOW)
        ),
        per_tier=per_tier,
        tiers_used=[t for t, _, _ in signals],
    )
