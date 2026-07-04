# Perturbation & Controls layer — design note

**Audience:** teammate implementing the experimental-design side of Model Matchmaker.
**Status:** design proposal, not yet built. Read `PROPOSAL.md` first for the two-stage gate,
the tiered-evidence pattern, and the `mm/` module boundaries — this layer reuses all three.

---

## 1. Why this exists (the gap it fills)

Today the tool answers **"which model?"** — protein present, pathway coherent, mechanism
observable, technically sourceable. It does **not** answer **"how do you perturb the target in
that model, and what do you control for?"**

That is a distinct axis. The clearest case: a gene knockout that shows **no phenotype on its
own** because a redundant family member buffers it — you only see the effect when you knock out
**both**. Redundancy like this does **not** change which model is correct; it changes the
**perturbation strategy and the control set**. So it must not touch model selection scores. It
is a new output, produced *after* search + collation, consuming the same evidence bundle.

Current handling is inadequate: in `pathway.py` a paralog is classified `paralog_related` and
treated as a *relevance/confidence modifier, never a kill switch*. That is right for model
selection but wrong for design — for design, "there is a redundant paralog" is a **first-class
requirement on the experiment**, not a soft modifier.

---

## 2. Where it plugs in

```
retrieval + collation  ──►  (frozen EvidenceBundle)  ──►  Design stage  ──►  Critic  ──►  card
   (existing mm/*)                                        (NEW mm/perturbation.py)
```

- **Reuse, don't re-fetch.** The design stage consumes the *frozen* evidence bundle the
  collation stage already produced (relations, DepMap signals, isoform calls, mechanism
  context). It must not open new API calls — that keeps it unit-testable against a fixed bundle.
- **New module:** `mm/perturbation.py`.
- **Extends:** `pathway.py` (add a redundancy signal to the relation map), `recommend.py`
  (a new "Perturbation & controls" section on the card).
- **Does not touch:** `scoring.py` model-selection scores. Redundancy is never a model gate.

---

## 3. Determining the context (detection)

Fuse three tiers into a redundancy verdict, exactly like `synthesize_protein_evidence()` fuses
protein evidence — direct/functional signals dominate, sequence similarity is only a candidate
flag, and everything carries provenance + a confidence.

1. **Sequence / family (candidate signal only).** Paralog or same-family member with an
   overlapping functional domain (Ensembl paralogs; shared catalytic domain). Necessary, not
   sufficient — sequence similarity alone never asserts functional redundancy.
2. **Functional genomics — DepMap (strongest signal, already in the stack).**
   - Target expressed but **not** a dependency in relevant lines → possible buffering.
   - **Paralog co-dependency / mutual exclusivity** → classic paralog synthetic lethality.
   - Compensatory upregulation of the paralog on target loss.
3. **Literature.** Explicit "functional redundancy with X" / "double knockout required"
   statements, retrieved and LLM-classified with PMIDs — same pattern as `build_relation_map`.

**Output:** a `redundancy` call — `none | partial | full`, whether a **single** perturbation is
sufficient or a **co-perturbation is required**, tagged with `necessity`
(`required | enhancing | hypothesis`) and provenance.

> **Honesty rule (important):** a redundancy inferred from sequence + a weak DepMap hint but not
> confirmed in the literature is `hypothesis`, not `required`. A `hypothesis`-tier redundancy
> **must never** silently force a double knockout. It surfaces a **single-KO control arm that
> would prove the buffering** instead. This mirrors how `mechanism.py` treats unverified culture
> requirements.

---

## 4. Schemas (match the existing typed-schema style)

Put these in `schemas/` (pydantic `BaseModel`, `StrEnum` for fixed choices — no bare dicts).

```python
class RedundancyLevel(StrEnum):
    NONE = "none"
    PARTIAL = "partial"
    FULL = "full"

class Necessity(StrEnum):          # reuse the one mechanism.py already uses
    REQUIRED = "required"
    ENHANCING = "enhancing"
    HYPOTHESIS = "hypothesis"

class PerturbationStrategy(StrEnum):
    SINGLE_KO = "single_ko"
    DOUBLE_KO = "double_ko"
    DEGRON = "degron"
    DOMINANT_NEGATIVE = "dominant_negative"
    INHIBITOR = "inhibitor"

class ControlKind(StrEnum):
    NEGATIVE = "negative"           # non-targeting / scramble
    POSITIVE = "positive"           # condition known to give the phenotype
    SPECIFICITY = "specificity"     # rescue / add-back, orthogonal perturbation
    REDUNDANCY_ARM = "redundancy_arm"   # single-KO arm to demonstrate buffering
    ISOFORM = "isoform"             # isoform-specific reagent + confirmation
    KNOCKDOWN_CONFIRMATION = "kd_confirmation"  # confirm loss at protein level

class RedundancyVerdict(BaseModel):
    level: RedundancyLevel
    co_perturb: list[str]           # redundant family members to hit together
    necessity: Necessity
    rationale: str
    provenance: list[str]           # PMIDs / DepMap refs
    confidence: float

class ControlSpec(BaseModel):
    kind: ControlKind
    description: str
    reads_out: str                  # what this control demonstrates
    triggered_by: str               # the risk flag that generated it

class PerturbationRequirement(BaseModel):
    strategy: PerturbationStrategy
    co_perturb: list[str]
    necessity: Necessity
    rationale: str
    provenance: list[str]
    implied_controls: list[ControlSpec]
```

---

## 5. Controls are DERIVED from flagged risks — not invented

A control is a response to a specific risk the evidence layer already raised. So control
generation is mostly a **deterministic mapping** over the evidence bundle's flags. The LLM is
only for the judgment calls (is the redundancy real, which paralog, which perturbation
modality) — never for emitting "include a non-targeting control."

| Flag already produced upstream        | Control(s) it implies                                              |
| -------------------------------------- | ----------------------------------------------------------------- |
| Redundancy → `double_ko` required      | single-KO arm (expected **no** phenotype = the proof), paralog-KO arm, double-KO arm |
| Off-target / specificity risk          | rescue / add-back of the target, or an orthogonal perturbation (2nd sgRNA, degron, inhibitor) |
| Isoform risk (`isoforms.py`)           | isoform-specific reagent + confirm the functional isoform         |
| Protein-presence uncertainty           | confirm loss at the **protein** level (WB), not just editing      |
| Mechanism-observability (`mechanism.py`) | the stimulation / context condition run as a control arm         |
| Always                                 | non-targeting / scramble negative + a positive control condition  |

Implement this table as a pure function: `flagged_risks -> list[ControlSpec]`. It is fully
deterministic and unit-testable.

---

## 6. Agent / stage decomposition (the "should it be a separate agent" question)

**Yes — a separate *stage* after search + collation. But keep most of it deterministic; use the
LLM only at the edges.**

Inside `mm/perturbation.py`:

1. **Deterministic control generator** — the §5 table. Pure function over the evidence bundle.
2. **LLM judgment (narrow)** — proposes/justifies only the non-obvious calls: is the redundancy
   real, *which* paralog to co-perturb, `double_ko` vs `degron` vs `inhibitor`. Every claim
   carries provenance. Same prompt discipline as the relation classifier.
3. **Critic pass** — validates the plan against the bundle:
   - every `required` requirement has a matching control,
   - no control asserts a redundancy the evidence rated only `hypothesis`,
   - the single-KO arm is present whenever redundancy is `hypothesis`.
   This is the existing Critic role; reuse it.

**Why a separate stage:**
- Different job — collation *gathers* evidence; design *reasons over frozen evidence to produce
  a plan*. Different prompt, different rubric.
- Clean interface — the design stage consumes only the bundle, so you can unit-test it against a
  fixed fixture without re-running retrieval.
- Prevents gap-filling hallucination — if collation didn't find a redundancy signal, the design
  stage should **say so and propose the arm that tests it**, not invent one.

**Why not make it a big LLM agent:** the standard controls are rule-derived; wrapping them in an
LLM only adds non-determinism. Keep the LLM surface as small as possible.

---

## 7. Card output (`recommend.py`)

Add a **Perturbation & controls** section to each model card, after Mechanism context:

- **Perturbation strategy** — single vs. double KO (or degron/inhibitor) + one-line rationale + PMIDs.
- **Controls** — the derived set, each with *what it demonstrates* and *which risk triggered it*.
- **Verify notes** — any `hypothesis`-tier requirement, phrased as "run this arm to confirm,"
  never as a hard instruction.

Keep it a **decision aid, not a protocol**: enough for the scientist to see the reasoning and
the arms to run, with provenance — not a full SOP.

---

## 8. Open decisions (please pick before building)

1. **Can redundancy ever be a hard requirement?** Recommendation: **no** — start it
   `hypothesis`-tagged and non-gating; propose the single-KO arm that would prove it. Revisit
   once the literature signal is strong enough to trust.
2. **Scope of perturbation modalities** for v1 — I'd ship `single_ko / double_ko` + a
   specificity control (rescue or 2nd reagent), and leave degron/dominant-negative/inhibitor as
   enum values wired but not yet reasoned about.
3. **Where the redundancy signal lives** — extend the `pathway.py` relation map with a
   `redundancy` field, or a standalone `redundancy` block in the bundle? I lean standalone, so
   model-selection scoring can keep ignoring it cleanly.

---

## 9. Suggested split of work

- **You:** `mm/perturbation.py` — the deterministic control generator (§5), the schemas (§4),
  and the card section (§7). All unit-testable against a fixed evidence-bundle fixture.
- **Me / other:** the DepMap redundancy signal + literature redundancy classifier feeding the
  bundle (§3), and the Critic checks (§6.3).

Start with a hand-built evidence-bundle fixture that includes a redundancy case, wire §5 → §7
end to end deterministically, then layer the LLM judgment and Critic on top.
