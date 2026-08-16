import urllib.parse
from typing import cast

from cellar.config import PRIDE_UNIPROT_URL as _UNIPROT
from cellar.schemas.sources import UniprotHit
from cellar.utils import http


def resolve_uniprot(symbol: str) -> UniprotHit | None:
    query = f"gene_exact:{symbol} AND organism_id:9606 AND reviewed:true"
    url = f"{_UNIPROT}?" + urllib.parse.urlencode(
        {"query": query, "fields": "accession,protein_existence", "format": "json", "size": "1"}
    )
    response = cast(
        "dict[str, object]",
        http.get_json(url, headers={"Accept": "application/json"}, timeout=30),
    )
    results = cast("list[dict[str, object]]", response.get("results") or [])
    if not results:
        return None
    entry = results[0]
    existence = str(entry.get("proteinExistence", ""))
    level = int(existence[0]) if existence[:1].isdigit() else None
    accession = entry.get("primaryAccession")
    return UniprotHit(
        accession=str(accession) if accession is not None else None,
        protein_existence_level=level,
    )


def _existence_tier(level: int | None) -> str:
    if level == 1:
        return "high"
    if level == 2:
        return "low"
    return "undetected"


def derive_pride(target_symbol: str) -> dict[str, object] | None:
    resolved = resolve_uniprot(target_symbol)
    if resolved is None or resolved.accession is None:
        return None
    tier = _existence_tier(resolved.protein_existence_level)
    return {
        "uniprot": resolved.accession,
        "n_projects": None,
        "tier": tier,
        "is_detectable": tier != "undetected",
        "projects": [],
        "source": "uniprot_protein_existence",
        "protein_existence_level": resolved.protein_existence_level,
    }
