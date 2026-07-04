# Model Matchmaker — hackathon proposal (2 people, 1 day)

**Pick the right in-vitro model (or the honest "go in vivo") for a target in a
disease, with a cited rationale and a supplier/CRO lead.**

Anchored on a worked example: **ZDHHC20 in PDAC.**

---

## 1. Is there already a tool? (the gap)

Everything you'd need exists as *lookups*, siloed and cancer-weighted — none
make the decision:

| Resource | Gives you | API |
|---|---|---|
| Cell Model Passports (Sanger) | cell/organoid models by tissue, genetics, data availability | REST |
| DepMap | CRISPR dependency + drug sensitivity — *is my target essential here* | REST/CSV |
| Cellosaurus | model identity, disease mapping, contamination flags | REST |
| Open Targets | target–disease evidence + tractability | GraphQL |
| HPA / GTEx | target expression across tissues/cells | REST |

**Gap:** no tool ranks *model tiers* (2D → organoid → co-culture → in vivo)
against *your question + constraints* and hands you a sourcing lead. That's the build.

## 2. Critical considerations (the scoring dimensions)

1. **Protein presence (not mRNA)** — the real gate, drawn from a **tiered
   evidence hierarchy**, not HPA alone (HPA is human-*tissue* antibody evidence;
   it cannot tell you whether the *cell line/organoid you would culture* makes the
   protein). Tiers, highest value for model selection first:
   (1) **model-specific** DepMap/CCLE proteomics — does *this line* express it;
   (2) **tumor-quant** CPTAC/PDC — tumor-vs-normal abundance + phosphosites;
   (3) **localization+antibody** HPA — subcellular compartment + tissue IHC;
   (4) **MS-detectability** PRIDE/PaxDb — is it MS-visible at all, at what tier.
   `synthesize_protein_evidence()` fuses these into one `protein_present` score +
   `confidence` + provenance; direct (model/tumor) tiers dominate.
   **MS-absence guard:** low/zero MS detectability *lowers confidence but never
   drives presence to zero* for a membrane/low-abundance class — those are
   systematically under-sampled by shotgun MS. *Verified live: ZDHHC20 (UniProt
   Q5W0Z9) is in **0** PRIDE MS projects yet is a real, antibody-validated
   protein; a naive "not in PRIDE → reject" filter would kill exactly the
   tractable membrane enzymes this tool exists to rescue. HPA separately shows RNA
   "Detected in all" but PROTEIN "Detected in some" — discordant.* Against this,
   PRIDE holds **144 human PDAC MS projects** — a real evidence base for models.
2. **Proteomics modality routing** — Olink/SomaScan are affinity **plasma**
   panels: they only see secreted/extracellular proteins. An intracellular or
   membrane target (like ZDHHC20: vesicles + plasma *membrane*) is invisible to
   them by design — the tool routes such targets to MS evidence and *warns
   against* commissioning a plasma panel. (Note: "plasma membrane" ≠ blood
   plasma — a real trap the router guards against.)
3. **Isoform / splicing** — a model can express the gene but the wrong
   transcript. *Verified: ZDHHC20 has 16 protein-coding isoforms, 45–365 aa;*
   truncated forms may lack the catalytic DHHC domain. Flag isoform-specificity
   risk and tell the scientist to confirm the functional isoform.
4. mRNA expression — kept as a weak supporting signal only
5. Disease-mechanism relevance — right drivers/subtype/microenvironment
6. Model tier vs. question — screen / validate / mechanism / efficacy / tox
7. Assay compatibility & throughput
8. Genetic tractability — can you CRISPR the target here
9. Provenance & reliability — authentication, misidentification history
10. Availability / sourcing — catalog line vs. biobank organoid vs. CRO-built
11. Translational track record — has this model type predicted clinic before
12. Ethical / regulatory (NAM acceptance)

1–9 computed deterministically (`scoring.py`, `proteomics.py`, `isoforms.py`);
11–12 come from the evidence layer (Elicit + Amass) with citations.

### Science first, THEN technical suitability (two-stage gate)
The decision is ordered the way a scientist reasons: **does the biology hold in
this model** before **is it practical to run**.

**STAGE 1 — Science gate (must pass):** a target present in a *broken pathway*
is not a relevant model. But "broken" must mean a **mechanistically required**
partner is missing — not merely a co-expressed neighbour. This distinction is
the crux, and getting it wrong produces false rejections.

*Relations are DERIVED FROM LITERATURE, not asserted from co-expression.* A
STRING edge or a co-expression correlation tells you two genes move together; it
does not tell you one is required for the other's function. So for each partner
we retrieve the PubMed abstracts co-mentioning it with the target, and an LLM
classifier (with PMID provenance) assigns a `relation_type`:
`catalytic_cofactor` / `stabilizer_accessory` / `substrate` / `upstream_driver`
/ `paralog_related` / `no_direct_functional_link`. Only a partner the literature
says is **required for the target's function** (`gates_model_selection=True`) can
hard-reject a model. Substrates, upstream drivers and co-expressed neighbours are
**relevance/confidence modifiers**, never kill switches. The enzyme itself —
protein present + intact catalytic domain (isoform-resolved) — is always a gate.

- *Cautionary tale, verified against primary literature (this is why the design
  changed):* STRING's top ZDHHC20 partner is **GOLGA7/GCP16 (0.68)**, and it is
  tempting to call it a required cofactor and reject any model lacking it. **The
  literature refutes this.** GCP16/GOLGA7 stabilises the *DHHC9 subfamily*
  (DHHC9/14/18/5/8) via a conserved C-terminal cysteine motif that "is **not**
  present in distantly related DHHCs, such as DHHC3 and DHHC20" (Front Physiol
  2023, PMC10076531; JBC 2005, PMID 16000296). ZDHHC20 is a standalone positive
  control in palmitoylation assays; a direct "ZDHHC20 GOLGA7" PubMed search
  returns **zero** papers. GOLGA7's role, where it applies, is *structural* —
  preventing enzyme aggregation and governing trafficking (it controls NRAS
  Golgi→PM transit "but not its palmitoylation", PMID 38317235). So the tool now
  classifies GOLGA7 as `no_direct_functional_link` for ZDHHC20 and does **not**
  reject a GOLGA7-low model. For ZDHHC20 there is *no* known obligate partner —
  the gate correctly rests on the enzyme (protein + catalytic DHHC domain), with
  EGFR (substrate) and KRAS (context) as relevance modifiers.
- Reactome files ZDHHC20 only under COVID spike maturation, so context is built
  from STRING + literature-derived relations, not curated pathway membership.

**STAGE 1b — Mechanism → culture-context (the "right target, wrong model"
check):** expressing the target and having a coherent pathway is still not
enough — the target's **mechanism of action** imposes *culture-context
requirements*, and a model where the mechanism's readout can't be observed is the
wrong model however well it expresses the target. This is the axis most tools
miss: they check *presence*, not *observability*.

`mechanism.py` derives the MoA's context requirements **from literature** (same
pattern as the relation map: `build_moa_context` runs in the repl tool over
PubMed abstracts, an LLM converts mechanistic prose into culture conditions with
PMIDs, result cached to JSON). Each requirement is one of a fixed condition
taxonomy (`ligand_stimulation`, `immune_compartment`, `tumor_stroma`,
`three_d_architecture`, `hypoxia_metabolic`, `vascular_flow`), tagged with a
**necessity** (`required` / `enhancing` / `hypothesis`), the **questions** it
applies to, and — critically — whether it is **retrofittable** (addable to the
media/culture) or needs a different model class. The matcher then compares each
model's native + retrofittable capabilities against the requirements in play for
the scientist's question and returns:

- `context_fit` (0–1) — a Stage-1 science dimension (weight 0.16),
- a **hard context gate** (`moa_context_unmet`) when a `required`,
  non-retrofittable condition is missing — right target, wrong model,
- **concrete culture actions** — the retrofits a model needs, each with the
  assay it unlocks. This is the *contextual evidence for model selection* the
  scientist acts on, not just a score.

*Worked proof — the same target routes to different models by question:*
- **`target_validation`:** ZDHHC20 palmitoylates the EGFR C-tail to tune RTK
  signalling (PMID 27153536), so in unstimulated 2D culture the readout is muted.
  This condition is **retrofittable** → PANC-1 and MIA PaCa-2 **pass**, but every
  card now carries the action *"serum-starve + add EGF → read pEGFR/MAPK ±
  palmitoylation (ABE/acyl-RAC)."* The 2D line is usable **only with the
  stimulation protocol** — and the tool says so instead of passing it silently.
- **`immune_mechanism`:** an immune-evasion readout needs an immune compartment
  (and 3D architecture, PMID 38821916) that a 2D monoculture cannot provide and
  **cannot retrofit** → PANC-1 and MIA PaCa-2 are **hard-gated**
  (`moa_context_unmet`, ctx = 0.00, *"REJECTED — wrong model for this
  mechanism"*), while the T-cell co-culture and KPC GEMM pass natively. The
  immune requirement for ZDHHC20 is flagged `hypothesis`/needs-verification, so
  it informs and surfaces a "verify" note rather than gating without evidence.

**STAGE 2 — Technical suitability (only for models that pass Stage 1):** tier
fit vs. the question, CRISPR-tractability, provenance, prior use, throughput,
then availability & sourcing. Final score = 0.65·science + 0.35·technical, where
the science half now weights protein_present 0.24, pathway_coherence 0.20,
**context_fit 0.16**, disease_features 0.18, isoform_match 0.10, dependency 0.12.

Demo proof (corrected): **PANC-1** now **passes** (total 0.68) despite GOLGA7
being absent — the card labels GOLGA7 `no_direct_functional_link, context`, not a
kill switch. The model that *is* rejected is a **DHHC-truncated line** expressing
only an isoform without the catalytic DHHC domain — a real loss of enzyme
function — whose card reads *"CATALYTIC_DOMAIN absent — Technical suitability not
assessed; fix the biology first."* The gate now fires on mechanism, not on
guilt-by-association.

### The recommendation is a decision aid, not a leaderboard
`recommend.py` emits a per-model **card**: *Step 1 Science gate* (pathway
coherence + per-member co-expression), *Step 1b Mechanism context* (MoA
observability verdict, per-condition native/add-to-culture/missing state, and the
concrete culture actions to make the mechanism observable), *Step 2 Why this model* (strong
dimensions), *Watch-outs* (weak dimensions), *Context for your decision*
(mRNA/protein discordance, proteomics modality routing, isoform caveat,
protein-level disease signal), and *Source* (supplier/CRO + catalog link).
Every card shows **Science score → Technical score** so the scientist sees the
evidence and confidence behind the ordering, not just a rank.

## 3. Architecture (thin, 1-day)

```
target + disease + constraints
  ├─ STRUCTURED FACTS   Open Targets · DepMap/Cell Model Passports ·
  │                     Cellosaurus · HPA         -> deterministic scores
  ├─ EVIDENCE           Elicit (prior-use table) · Amass TrialCore/
  │                     RegulatoryCore/Patent/WebCore (track record + sourcing)
  └─ LLM JUDGE (rubric) -> ranked shortlist + cited rationale + in-vivo fallback
                        -> Streamlit cards
```

**Person A:** `retrieval.py` (done, live-verified) + Amass client.
**Person B:** `scoring.py` (done) + `judge.py` prompt + Streamlit UI.
Neither builds a literature scraper — Elicit + Amass erase that.

## Why ZDHHC20/PDAC is the perfect demo

Live-probed facts (reproducible):
- Open Targets **direct ZDHHC20–PDAC association = 0.0** — the DB underrates it,
  while KRAS tops PDAC at 0.51.
- ZDHHC20 is still **small-molecule tractable** (structure-with-ligand enzyme).
- **333** sourceable PDAC models in Cellosaurus, **7 flagged problematic.**

So the naive "association score" recommender fails this target — but ours finds
the model by leaning on functional data + literature (Elicit/Amass). **Showing
judges a tool that rescues an underrated-but-real target is the pitch.**

Demo output (from `demo_pdac_zdhhc20.py`) — the recommendation shifts with the question:
- **HTS screen** → KRAS-mutant 2D lines rise (MIA PaCa-2 / PANC-1)
- **Target validation** → patient-derived PDAC organoid wins
- **Immune mechanism** → KPC GEMM + organoid/T-cell co-culture top the list

## Scope discipline (protect the demo)

- One disease area (cancer = best API coverage). Non-cancer = stretch.
- Hand-curate ~15 CROs tagged by capability; let Amass WebCore augment.
- Cache 2–3 example queries so the live demo never depends on an API being up.
- Ship the "no adequate model → go in vivo" branch — cheap, credible, differentiating.

## Files
- `mm/retrieval.py` — live-verified clients (Open Targets, Cellosaurus, DepMap stub)
- `mm/proteomics.py` — **tiered protein-evidence synthesizer**
  (`synthesize_protein_evidence`: DepMap model-specific → CPTAC tumor-quant → HPA
  localization/antibody → PRIDE MS-detectability) with the **MS-absence guard**;
  live PRIDE client (`pride_ms_detectability`, via omics-archives) + HPA (live);
  Olink/SomaScan modality router; CPTAC/PDC + DepMap-proteomics wiring points
- `mm/isoforms.py` — Ensembl protein-coding isoform enumeration + splicing-risk flag (live)
- `mm/pathway.py` — STRING functional partners (live) + **literature-derived
  relation map** (`build_relation_map`: PubMed abstracts → LLM `relation_type` +
  PMIDs) + evidence-grounded science gate that hard-rejects only on a
  literature-required partner or a broken enzyme/catalytic domain
- `mm/mechanism.py` — **MoA → culture-context layer** (`build_moa_context`:
  PubMed abstracts → LLM condition requirements + PMIDs; `match_model_context`:
  model capabilities vs. requirements → `context_fit`, hard context gate, and
  concrete retrofit actions). Encodes the "right target, wrong model / wrong
  conditions" check and emits the culture steps (ligand, co-culture, hypoxia…)
  that make a mechanism observable
- `mm/scoring.py` — tier rubric + deterministic scoring (protein-weighted, isoform-aware,
  protein + **MoA-context** hard-gates, `context_fit` science dimension) + in-vivo verdict
- `mm/recommend.py` — per-model decision cards (why / watch-outs / context / sourcing)
- `mm/evidence.py` — Elicit + Amass query templates / playbook
- `demo_pdac_zdhhc20.py` — end-to-end runnable example, prints full cards

## Wiring points left for the team (all scaffolded, not stubbed silently)
- CPTAC PDC GraphQL (`proteomics.cptac_stub`) — real tumor-vs-normal protein quant;
  endpoint needs GET-encoded queries with exact field names from PDC docs.
- Elicit list-extraction + Amass core calls (`evidence.py`) — plug API keys.
- Auto-build candidate panel by joining Cellosaurus × DepMap KRAS-status × HPA
  protein (currently a hand-set panel in the demo).
