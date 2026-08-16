import json
import os
import re
from typing import cast

from cellar.prompts.mechanism import moa_context_prompt
from cellar.schemas.derivation import MoaAction, MoaContext, MoaMember, MoaVerify
from cellar.schemas.domain import CONTEXT_CONDITIONS, NECESSITY, TIER_CAPABILITIES
from cellar.schemas.matchmaker import Necessity
from cellar.schemas.recommendation import ConditionState
from cellar.schemas.scoring import (
    CONTEXT_FIT_DEFAULT,
    CREDIT_NATIVE,
    CREDIT_RETROFIT,
    NECESSITY_WEIGHT,
    NECESSITY_WEIGHT_DEFAULT,
)
from cellar.schemas.services import McpTool, ReasoningFn


def model_capabilities(
    tier: str, overrides: dict[str, list[str]] | None = None
) -> dict[str, object]:
    base = TIER_CAPABILITIES.get(tier, {"native": set(), "retrofit": {}})
    native = set(cast("set[str]", base["native"]))
    retrofit = dict(cast("dict[str, tuple[str, str]]", base["retrofit"]))
    if overrides:
        native |= set(overrides.get("add_native", []))
        native -= set(overrides.get("remove_native", []))
        retrofit.update(cast("dict[str, tuple[str, str]]", overrides.get("add_retrofit", {})))
        for k in overrides.get("remove_retrofit", []):
            retrofit.pop(k, None)
    return {"native": native, "retrofit": retrofit}


def build_moa_context(
    target: str,
    disease: str,
    *,
    mcp: McpTool,
    llm: ReasoningFn,
    reasoning_model: str | None = None,
    extra_queries: list[str] | None = None,
) -> dict[str, object]:
    queries = [
        f"{target} mechanism {disease}",
        f"{target} palmitoylation signaling",
        f"{target} tumor microenvironment OR immune OR stroma",
    ]
    queries += extra_queries or []
    seen: set[str] = set()
    abs_: list[dict[str, object]] = []
    for q in queries:
        sr = mcp("pubmed", "search_articles", query=q, max_results=5, sort="relevance")
        pmids = [p for p in cast("list[str]", sr.get("pmids", [])) if p not in seen]
        seen.update(pmids)
        if not pmids:
            continue
        md = mcp("pubmed", "get_article_metadata", pmids=pmids)
        for a in cast("list[dict[str, object]]", md.get("articles", [])):
            ids = cast("dict[str, object]", a.get("identifiers", {}))
            abs_.append(
                {
                    "pmid": str(ids.get("pmid")),
                    "title": a.get("title"),
                    "abstract": str(a.get("abstract") or "")[:1100],
                }
            )
    evidence = (
        "\n".join(f"[PMID {a['pmid']}] {a['title']}\n{a['abstract']}" for a in abs_)
        or "NO ABSTRACTS FOUND."
    )
    prompt = moa_context_prompt(
        target=target,
        disease=disease,
        evidence=evidence,
        context_conditions=CONTEXT_CONDITIONS,
        necessity=[str(n) for n in NECESSITY],
    )
    res = llm(prompt, model=reasoning_model) if reasoning_model else llm(prompt)
    m = re.search(r"\[.*\]", res["text"], re.S)
    reqs: list[object] = json.loads(m.group(0)) if m else []
    return {
        "target": target,
        "disease": disease,
        "pmids_scanned": [a["pmid"] for a in abs_],
        "requirements": reqs,
    }


def load_moa_context(path: str) -> dict[str, object]:
    if os.path.exists(path):
        with open(path) as f:
            return cast("dict[str, object]", json.load(f))
    return {}


def requirements_for_question(
    moa_context: dict[str, object], question_type: str
) -> list[dict[str, object]]:
    out: list[dict[str, object]] = []
    for r in cast("list[dict[str, object]]", moa_context.get("requirements", [])):
        aq = cast("list[str]", r.get("applies_to_questions", ["all"]))
        if "all" in aq or question_type in aq:
            out.append(r)
    return out


def match_model_context(
    tier: str,
    moa_context: dict[str, object],
    question_type: str,
    capability_overrides: dict[str, list[str]] | None = None,
) -> MoaContext:
    caps = model_capabilities(tier, capability_overrides)
    native = cast("set[str]", caps["native"])
    retrofit = cast("dict[str, tuple[str, str]]", caps["retrofit"])
    reqs = requirements_for_question(moa_context, question_type)

    members: list[MoaMember] = []
    actions: list[MoaAction] = []
    unmet_required: list[str] = []
    enhancing_missing: list[str] = []
    verify: list[MoaVerify] = []
    num, den = 0.0, 0.0
    w_by = NECESSITY_WEIGHT
    credit_native, credit_retrofit = CREDIT_NATIVE, CREDIT_RETROFIT

    for r in reqs:
        cond = str(r["condition"])
        nec = str(r.get("necessity", Necessity.ENHANCING))
        is_hyp = (nec == Necessity.HYPOTHESIS) or bool(r.get("needs_verification"))
        w = w_by.get(nec, NECESSITY_WEIGHT_DEFAULT)
        pmids = cast("list[str]", r.get("evidence_pmids") or [])
        cite = (
            f"[PMID {','.join(pmids)}]"
            if pmids
            else ("[hypothesis — verify]" if is_hyp else "[no direct paper]")
        )

        if cond in native:
            state, credit = ConditionState.NATIVE, credit_native
        elif cond in retrofit:
            action, cost = retrofit[cond]
            state, credit = ConditionState.RETROFIT, credit_retrofit
            actions.append(
                MoaAction(
                    condition=cond,
                    action=action,
                    cost=cost,
                    necessity=nec,
                    readout_hint=str(r.get("readout_hint", "")),
                    evidence_pmids=pmids,
                )
            )
        else:
            state, credit = ConditionState.UNMET, 0.0
            if nec == Necessity.REQUIRED and not is_hyp:
                unmet_required.append(cond)
            elif nec == Necessity.ENHANCING:
                enhancing_missing.append(cond)

        if is_hyp and state != ConditionState.NATIVE:
            verify.append(MoaVerify(condition=cond, rationale=str(r.get("rationale", ""))))

        if w > 0:
            num += w * credit
            den += w
        members.append(
            MoaMember(
                condition=cond,
                necessity=nec,
                state=state,
                retrofittable=bool(r.get("retrofittable")),
                rationale=str(r.get("rationale", "")),
                readout_hint=str(r.get("readout_hint", "")),
                evidence_pmids=pmids,
                cite=cite,
                needs_verification=bool(is_hyp),
            )
        )

    context_fit = round(num / den, 3) if den else CONTEXT_FIT_DEFAULT
    context_required_unmet = len(unmet_required) > 0
    if context_required_unmet:
        verdict = (
            "MECHANISM NOT OBSERVABLE HERE: required context "
            + "/".join(unmet_required)
            + f" cannot be provided by a '{tier}' model "
            "and is not retrofittable — right target, wrong model for this question."
        )
    elif actions:
        req_actions = [a.condition for a in actions if a.necessity == Necessity.REQUIRED]
        if req_actions:
            verdict = (
                "Mechanism observable ONLY with culture augmentation: "
                + "; ".join(
                    f"{a.condition} ({a.action})"
                    for a in actions
                    if a.necessity == Necessity.REQUIRED
                )
                + "."
            )
        else:
            verdict = (
                "Mechanism observable; optional augmentations available to strengthen the readout."
            )
    else:
        verdict = "Model natively supports the mechanism's context requirements."

    return MoaContext(
        context_fit=context_fit,
        context_required_unmet=context_required_unmet,
        actions=actions,
        unmet_required=unmet_required,
        enhancing_missing=enhancing_missing,
        verify=verify,
        members=members,
        verdict=verdict,
        question=question_type,
        tier=tier,
    )
