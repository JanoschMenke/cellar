import json
import os
from typing import cast

from cellar.prompts.pathway import relation_map_prompt
from cellar.schemas.derivation import PathwayCoherence, PathwayMember
from cellar.schemas.domain import GATING_TYPES, REL_TYPES
from cellar.schemas.matchmaker import PathwayMemberStatus
from cellar.schemas.scoring import (
    COHERENCE_DEFAULT,
    COHERENCE_STRONG,
    COHERENCE_WEAK,
    PRESENCE_MIN,
    REL_WEIGHT,
    REL_WEIGHT_DEFAULT,
)
from cellar.schemas.services import McpTool, ReasoningFn


def build_relation_map(
    target: str,
    partners: list[str],
    aliases: dict[str, list[str]] | None = None,
    *,
    mcp: McpTool,
    llm: ReasoningFn,
    reasoning_model: str | None = None,
) -> dict[str, dict[str, object]]:
    import re

    aliases = aliases or {}
    out: dict[str, dict[str, object]] = {}
    for p in partners:
        al = aliases.get(p, [])
        alias_q = "(" + " OR ".join([p] + al) + ")"
        sr = mcp(
            "pubmed",
            "search_articles",
            query=f"{target} AND {alias_q}",
            max_results=6,
            sort="relevance",
        )
        pmids = cast("list[str]", sr.get("pmids", []))
        abs_: list[dict[str, object]] = []
        if pmids:
            md = mcp("pubmed", "get_article_metadata", pmids=pmids)
            for a in cast("list[dict[str, object]]", md.get("articles", [])):
                ids = cast("dict[str, object]", a.get("identifiers", {}))
                abs_.append(
                    {
                        "pmid": str(ids.get("pmid")),
                        "doi": ids.get("doi"),
                        "title": a.get("title"),
                        "abstract": str(a.get("abstract") or "")[:1200],
                    }
                )
        evidence = (
            "\n".join(f"[PMID {a['pmid']}] {a['title']}\n{a['abstract']}" for a in abs_)
            or "NO CO-MENTIONING PAPERS FOUND."
        )
        prompt = relation_map_prompt(
            target=target,
            partner=p,
            aliases=al,
            evidence=evidence,
            rel_types=REL_TYPES,
        )
        res = llm(prompt, model=reasoning_model) if reasoning_model else llm(prompt)
        m = re.search(r"\{.*\}", res["text"], re.S)
        rel: dict[str, object] = (
            json.loads(m.group(0))
            if m
            else {"relation_type": "no_direct_functional_link", "gates_model_selection": False}
        )
        rel["_pmids_scanned"] = [a["pmid"] for a in abs_]
        rel["_search_total"] = sr.get("total_count", 0)
        out[p] = rel
    return out


def load_relation_map(path: str) -> dict[str, object]:
    if os.path.exists(path):
        with open(path) as f:
            return cast("dict[str, object]", json.load(f))
    return {}


def pathway_coherence(
    model_expression: dict[str, float],
    relations: dict[str, dict[str, object]],
    target_present: float | None = None,
    catalytic_domain_ok: bool | None = None,
) -> PathwayCoherence:
    rows: list[PathwayMember] = []
    hard_fail = []
    relevance_num, relevance_den = 0.0, 0.0
    for gene, rel in relations.items():
        rtype = str(rel.get("relation_type", "no_direct_functional_link"))
        gates = bool(rel.get("gates_model_selection")) and rtype in GATING_TYPES
        present = model_expression.get(gene)
        status = (
            PathwayMemberStatus.UNKNOWN
            if present is None
            else (
                PathwayMemberStatus.PRESENT
                if present >= PRESENCE_MIN
                else PathwayMemberStatus.ABSENT
            )
        )
        rows.append(
            PathwayMember(
                gene=gene,
                relation_type=rtype,
                gates=gates,
                expression=present,
                status=status,
                evidence_pmids=cast("list[str]", rel.get("evidence_pmids", [])),
                note=str(rel.get("note", "")),
            )
        )
        if gates and present is not None and present < PRESENCE_MIN:
            hard_fail.append(gene)
        w = REL_WEIGHT.get(rtype, REL_WEIGHT_DEFAULT)
        if w > 0 and present is not None:
            relevance_num += w * present
            relevance_den += w
    if target_present is not None and target_present < PRESENCE_MIN:
        hard_fail.append("TARGET_PROTEIN")
    if catalytic_domain_ok is False:
        hard_fail.append("CATALYTIC_DOMAIN")

    relevance = round(relevance_num / relevance_den, 3) if relevance_den else None
    if hard_fail:
        pretty = "/".join(hard_fail)
        verdict = (
            f"SCIENCE GATE FAIL: {pretty} absent/broken — target present but "
            f"non-functional or context missing in this model."
        )
        passed = False
    elif relevance is None and target_present is None:
        verdict = "Pathway context unknown for this model — verify before use."
        passed = None
    else:
        base = relevance if relevance is not None else COHERENCE_DEFAULT
        if base >= COHERENCE_STRONG:
            verdict = "Science gate PASS: enzyme intact and substrate/context co-expressed."
        elif base >= COHERENCE_WEAK:
            verdict = "Science gate PASS (guarded): enzyme intact but weak substrate/context co-expression."
        else:
            verdict = "Science gate PASS (low relevance): enzyme present but little substrate/context support."
        passed = True
    return PathwayCoherence(
        pathway_coherence=relevance,
        passed_science_gate=passed,
        hard_fail=hard_fail,
        members=rows,
        verdict=verdict,
    )
