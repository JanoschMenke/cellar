import urllib.parse
from typing import cast

from cellar.config import STRING_URL
from cellar.schemas.sources import StringPartner
from cellar.utils import http


def _get_json(url: str, t: int = 40) -> list[dict[str, object]]:
    return cast(
        "list[dict[str, object]]",
        http.get_json(url, headers={"Accept": "application/json"}, timeout=t),
    )


def string_partners(
    symbol: str, species: int = 9606, limit: int = 15, min_score: float = 0.4
) -> list[StringPartner]:
    qs = urllib.parse.urlencode({"identifiers": symbol, "species": species, "limit": limit})
    url = f"{STRING_URL}/interaction_partners?{qs}"
    parts = _get_json(url)
    return [
        StringPartner(
            partner=cast(str, p["preferredName_B"]), score=round(cast(float, p["score"]), 3)
        )
        for p in parts
        if cast(float, p["score"]) >= min_score
    ]
