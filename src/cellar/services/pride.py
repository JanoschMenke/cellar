import json
import urllib.parse
import urllib.request

_UNIPROT = "https://rest.uniprot.org/uniprotkb/search"


def _get(url: str, timeout: int = 30) -> dict[str, object]:
    request = urllib.request.Request(url, headers={"Accept": "application/json"})
    with urllib.request.urlopen(request, timeout=timeout) as response:
        return json.loads(response.read().decode())


def resolve_uniprot(symbol: str) -> dict[str, object] | None:
    query = f"gene_exact:{symbol} AND organism_id:9606 AND reviewed:true"
    url = f"{_UNIPROT}?" + urllib.parse.urlencode(
        {"query": query, "fields": "accession,protein_existence", "format": "json", "size": "1"}
    )
    results = _get(url).get("results") or []
    if not results:
        return None
    entry = results[0]
    existence = str(entry.get("proteinExistence", ""))
    level = int(existence[0]) if existence[:1].isdigit() else None
    return {"accession": entry.get("primaryAccession"), "protein_existence_level": level}


def _existence_tier(level: int | None) -> str:
    if level == 1:
        return "high"
    if level == 2:
        return "low"
    return "undetected"


def derive_pride(target_symbol: str) -> dict[str, object] | None:
    resolved = resolve_uniprot(target_symbol)
    if not resolved or not resolved.get("accession"):
        return None
    level = resolved.get("protein_existence_level")
    tier = _existence_tier(level if isinstance(level, int) else None)
    return {
        "uniprot": str(resolved["accession"]),
        "n_projects": None,
        "tier": tier,
        "is_detectable": tier != "undetected",
        "projects": [],
        "source": "uniprot_protein_existence",
        "protein_existence_level": level,
    }
