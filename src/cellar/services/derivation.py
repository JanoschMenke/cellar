import json
import os

from cellar.config import load_settings
from cellar.services import mechanism, pathway
from cellar.services.pride import derive_pride
from cellar.services.pubmed import pubmed_mcp
from cellar.services.reasoning import llm

_MAX_PARTNERS = 6


def _cache_dir() -> str:
    directory = os.path.join(load_settings().workspace_dir, "derived")
    os.makedirs(directory, exist_ok=True)
    return directory


def _slug(value: str) -> str:
    return "".join(ch if ch.isalnum() else "_" for ch in value.lower()).strip("_")


def _load(path: str) -> object | None:
    if os.path.exists(path):
        with open(path) as handle:
            return json.load(handle)
    return None


def _save(path: str, data: object) -> None:
    with open(path, "w") as handle:
        json.dump(data, handle)


def pride_for(target_symbol: str) -> dict[str, object] | None:
    path = os.path.join(_cache_dir(), f"pride_{_slug(target_symbol)}.json")
    cached = _load(path)
    if cached is not None:
        return cached
    derived = derive_pride(target_symbol)
    if derived is not None:
        _save(path, derived)
    return derived


def relations_for(target_symbol: str) -> dict[str, object]:
    path = os.path.join(_cache_dir(), f"relations_{_slug(target_symbol)}.json")
    cached = _load(path)
    if isinstance(cached, dict):
        return cached
    try:
        partners = [p["partner"] for p in pathway.string_partners(target_symbol)[:_MAX_PARTNERS]]
        relations = pathway.build_relation_map(
            target_symbol, partners, mcp=pubmed_mcp, llm=llm
        )
    except Exception:
        return {}
    _save(path, relations)
    return relations


def moa_context_for(target_symbol: str, disease: str) -> dict[str, object]:
    path = os.path.join(_cache_dir(), f"moa_{_slug(target_symbol)}_{_slug(disease)}.json")
    cached = _load(path)
    if isinstance(cached, dict):
        return cached
    try:
        context = mechanism.build_moa_context(target_symbol, disease, mcp=pubmed_mcp, llm=llm)
    except Exception:
        return {"target": target_symbol, "disease": disease, "requirements": []}
    _save(path, context)
    return context
