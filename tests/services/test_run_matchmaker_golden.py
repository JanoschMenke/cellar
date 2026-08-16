from unittest.mock import patch

from cellar.schemas.derivation import HpaProteinEvidence, ProteinSynthesis
from cellar.schemas.matchmaker import (
    MatchmakerQuery,
    ModelTier,
    QuestionType,
    SeedModel,
)
from cellar.schemas.sources import OtDiseaseHit, OtTargetProfile
from cellar.services.derivation.matchmaker import run_matchmaker

_QUERY = MatchmakerQuery(
    target_symbol="ZDHHC20",
    disease="pancreatic cancer",
    question_type=QuestionType.TARGET_VALIDATION,
)

_PANEL: list[SeedModel] = [
    SeedModel(
        name="MIA PaCa-2 (KRAS G12C, 2D)",
        tier=ModelTier.TWO_D_LINE,
        source="ATCC CRL-1420",
        catalog_url="https://www.atcc.org/products/crl-1420",
        mrna_expressed=0.9,
        protein_present=0.7,
        isoform_match=0.7,
        disease_features_match=0.7,
        dependency_signal=0.5,
        genetic_tractable=0.95,
        provenance_ok=1.0,
        prior_use=0.5,
        coexpression={"GOLGA7": 0.6, "KRAS": 0.85},
        catalytic_domain_ok=True,
    ),
    SeedModel(
        name="Patient-derived PDAC organoid (HUB/Hubrecht)",
        tier=ModelTier.ORGANOID,
        source="HUB Organoids / HCMI",
        catalog_url="",
        mrna_expressed=0.85,
        protein_present=0.2,
        isoform_match=0.8,
        disease_features_match=0.9,
        dependency_signal=0.6,
        genetic_tractable=0.8,
        provenance_ok=1.0,
        prior_use=0.7,
        coexpression={"GOLGA7": 0.8, "KRAS": 0.9},
        catalytic_domain_ok=True,
    ),
]

_RELATIONS: dict[str, dict[str, object]] = {
    "GOLGA7": {
        "relation_type": "stabilizer_accessory",
        "gates_model_selection": True,
        "evidence_pmids": ["11111111"],
        "note": "co-chaperone for ZDHHC20 palmitoylation",
    },
    "KRAS": {
        "relation_type": "substrate",
        "gates_model_selection": False,
        "evidence_pmids": ["22222222"],
        "note": "palmitoylation-dependent membrane localization",
    },
}

_MOA_CONTEXT: dict[str, object] = {
    "target": "ZDHHC20",
    "disease": "pancreatic cancer",
    "pmids_scanned": ["33333333"],
    "requirements": [
        {
            "condition": "three_d_architecture",
            "necessity": "required",
            "retrofittable": False,
            "rationale": "PDAC stroma requires 3D architecture for KRAS-driven invasion",
            "readout_hint": "invasion assay",
            "evidence_pmids": ["33333333"],
            "needs_verification": False,
            "applies_to_questions": ["all"],
        },
        {
            "condition": "hypoxia_metabolic",
            "necessity": "enhancing",
            "retrofittable": True,
            "rationale": "tumor core hypoxia modulates palmitoylation flux",
            "readout_hint": "HIF1A stabilization",
            "evidence_pmids": [],
            "needs_verification": True,
            "applies_to_questions": ["all"],
        },
        {
            "condition": "immune_compartment",
            "necessity": "hypothesis",
            "retrofittable": False,
            "rationale": "possible immune modulation, unconfirmed",
            "readout_hint": "cytokine panel",
            "evidence_pmids": [],
            "needs_verification": True,
            "applies_to_questions": ["all"],
        },
    ],
}


def _run_golden_matchmaker() -> str:
    with (
        patch(
            "cellar.services.derivation.matchmaker.open_targets.ot_resolve_target",
            return_value="ENSG00000180776",
        ),
        patch(
            "cellar.services.derivation.matchmaker.open_targets.ot_resolve_disease",
            return_value=OtDiseaseHit(id="EFO_0002618", name="pancreatic cancer"),
        ),
        patch(
            "cellar.services.derivation.matchmaker.open_targets.ot_target_profile",
            return_value=OtTargetProfile(symbol="ZDHHC20", tractability=[], top_diseases=[]),
        ),
        patch(
            "cellar.services.derivation.matchmaker.open_targets.ot_assoc_score",
            return_value=0.42,
        ),
        patch(
            "cellar.services.derivation.matchmaker.isoforms.protein_coding_isoforms",
            return_value=[],
        ),
        patch(
            "cellar.services.derivation.matchmaker.isoforms.isoform_risk_summary",
            return_value=None,
        ),
        patch(
            "cellar.services.derivation.matchmaker.proteomics.hpa_protein_evidence",
            return_value=HpaProteinEvidence(
                subcellular=[],
                protein_class=None,
                rna_tissue_distribution=None,
                protein_tissue_distribution=None,
                mrna_protein_discordant=False,
                protein_cell_type_intensity=None,
                disease_protein_prognostic={},
            ),
        ),
        patch(
            "cellar.services.derivation.matchmaker.proteomics.synthesize_protein_evidence",
            return_value=ProteinSynthesis(
                protein_present=0.7,
                confidence=0.8,
                ms_absence_guard_applied=False,
            ),
        ),
        patch(
            "cellar.services.derivation.matchmaker.proteomics.cptac_tumor_quant",
            return_value=None,
        ),
        patch(
            "cellar.services.derivation.matchmaker.proteomics.depmap_proteomics",
            return_value=None,
        ),
        patch(
            "cellar.services.derivation.matchmaker.cellosaurus.cello_models",
            return_value=[],
        ),
        patch(
            "cellar.services.derivation.matchmaker.string_db.string_partners",
            return_value=[],
        ),
        patch(
            "cellar.services.derivation.matchmaker.derivation.relations_for",
            return_value=_RELATIONS,
        ),
        patch(
            "cellar.services.derivation.matchmaker.derivation.moa_context_for",
            return_value=_MOA_CONTEXT,
        ),
        patch(
            "cellar.services.derivation.matchmaker.derivation.pride_for",
            return_value=None,
        ),
    ):
        report = run_matchmaker(_QUERY, panel=_PANEL)
    return report.model_dump_json(
        exclude={"cards": {"__all__": {"rendered_markdown", "dimensions"}}}
    )


_GOLDEN_REPORT_JSON = (
    '{"query":{"target_symbol":"ZDHHC20","disease":"pancreatic cancer","question_type":'
    '"target_validation","constraints":[]},"verdict":"No in-vitro model scores >0.45 '
    '(best=0.35); recommend GEMM/PDX in vivo.","in_vivo_recommended":true,"facts":'
    '{"target_id":"ENSG00000180776","disease_id":"EFO_0002618","small_molecule_tractable":'
    'false,"ot_direct_association":0.42,"n_sourceable_models":0,"n_problematic_models":0,'
    '"isoform_n_protein_coding":0,"isoform_aa_span":"","isoform_specificity_risk":"",'
    '"mrna_protein_discordant":false,"protein_present":0.7,"protein_confidence":"0.8",'
    '"ms_absence_guard_applied":false,"pride_n_projects":0,"protein_evidence_note":"",'
    '"string_top_partners":[]},"relations":[{"gene":"GOLGA7","relation_type":'
    '"stabilizer_accessory","gates_model_selection":true,"evidence_pmids":["11111111"]},'
    '{"gene":"KRAS","relation_type":"substrate","gates_model_selection":false,'
    '"evidence_pmids":["22222222"]}],"cards":[{"rank":1,"model_name":"MIA PaCa-2 (KRAS G12C, '
    '2D)","tier":"2d_line","tier_label":"2D cell line","question":"target_validation",'
    '"recommended":false,"gate":"moa_context_unmet","verdict_label":"Rejected — wrong model '
    'for this mechanism","confidence":"weak","headline":"Rejected — wrong model for this '
    'mechanism — fix the biology before assessing suitability.","scores":{"overall":0.35,'
    '"science":0.612,"technical":0.809,"context":0.267},"reasons":[{"key":"protein_present",'
    '"label":"The protein itself is detected in this model, not just its mRNA.","value":0.7,'
    '"strength":"strong","source":"Human Protein Atlas","source_url":'
    '"https://www.proteinatlas.org/ENSG00000180776"},{"key":"pathway_coherence","label":'
    '"Its pathway partners are co-expressed, so the target\'s signalling context is intact.",'
    '"value":0.725,"strength":"strong","source":"PubMed","source_url":'
    '"https://pubmed.ncbi.nlm.nih.gov/11111111/"},{"key":"isoform_match","label":"Expresses '
    'the functional isoform with the catalytic domain intact.","value":0.7,"strength":'
    '"strong","source":"Ensembl","source_url":'
    '"https://www.ensembl.org/Homo_sapiens/Gene/Summary?g=ENSG00000180776"},{"key":'
    '"disease_features_match","label":"Carries the disease\'s driver alterations — the right '
    'genetic background.","value":0.7,"strength":"strong","source":"Cell Model Passports / '
    'COSMIC","source_url":null}],"watch_outs":[{"key":"context_fit","label":"This model '
    'can\'t show the mechanism\'s readout without added culture conditions.","value":0.267,'
    '"strength":"weak","source":"PubMed","source_url":'
    '"https://pubmed.ncbi.nlm.nih.gov/33333333/"},{"key":"dependency_signal","label":"Weak '
    'or absent dependency in screens — knockout effects may be hard to detect.","value":0.5,'
    '"strength":"moderate","source":"DepMap","source_url":'
    '"https://depmap.org/portal/gene/ZDHHC20"}],"context_notes":[],"science_gate":{"verdict":'
    '"Science gate PASS: enzyme intact and substrate/context co-expressed.","coherence":'
    '0.725,"partners":[{"gene":"GOLGA7","relation_type":"stabilizer_accessory",'
    '"gates_model_selection":true,"status":"present","evidence_pmids":["11111111"]},'
    '{"gene":"KRAS","relation_type":"substrate","gates_model_selection":false,"status":'
    '"present","evidence_pmids":["22222222"]}]},"mechanism":{"verdict":"MECHANISM NOT '
    "OBSERVABLE HERE: required context three_d_architecture cannot be provided by a "
    "'2d_line' model and is not retrofittable — right target, wrong model for this "
    'question.","context_fit":0.267,"context_required_unmet":true,"conditions":[{'
    '"condition":"three_d_architecture","necessity":"required","state":"unmet",'
    '"retrofittable":false,"rationale":"PDAC stroma requires 3D architecture for '
    'KRAS-driven invasion","readout_hint":"invasion assay","evidence_pmids":["33333333"]},'
    '{"condition":"hypoxia_metabolic","necessity":"enhancing","state":"retrofit",'
    '"retrofittable":true,"rationale":"tumor core hypoxia modulates palmitoylation flux",'
    '"readout_hint":"HIF1A stabilization","evidence_pmids":[]},{"condition":'
    '"immune_compartment","necessity":"hypothesis","state":"unmet","retrofittable":false,'
    '"rationale":"possible immune modulation, unconfirmed","readout_hint":"cytokine panel",'
    '"evidence_pmids":[]}],"actions":[{"condition":"hypoxia_metabolic","action":"culture in '
    'hypoxia chamber / defined low-nutrient media","cost":"low","necessity":"enhancing",'
    '"readout_hint":"HIF1A stabilization"}],"verify":["hypoxia_metabolic: tumor core '
    'hypoxia modulates palmitoylation flux","immune_compartment: possible immune '
    'modulation, unconfirmed"]},"sourcing":{"supplier_or_cro":"ATCC CRL-1420","catalog_url":'
    '"https://www.atcc.org/products/crl-1420","purchasable":false}},{"rank":2,"model_name":'
    '"Patient-derived PDAC organoid (HUB/Hubrecht)","tier":"organoid","tier_label":'
    '"Organoid","question":"target_validation","recommended":false,"gate":'
    '"science_gate_failed","verdict_label":"Rejected — science gate","confidence":"weak",'
    '"headline":"Rejected — science gate — fix the biology before assessing suitability.",'
    '"scores":{"overall":0.35,"science":0.681,"technical":0.868,"context":0.933},"reasons":'
    '[{"key":"pathway_coherence","label":"Its pathway partners are co-expressed, so the '
    'target\'s signalling context is intact.","value":0.85,"strength":"strong","source":'
    '"PubMed","source_url":"https://pubmed.ncbi.nlm.nih.gov/11111111/"},{"key":'
    '"context_fit","label":"The mechanism you want to study can actually be read out in '
    'this model.","value":0.933,"strength":"strong","source":"PubMed","source_url":'
    '"https://pubmed.ncbi.nlm.nih.gov/33333333/"},{"key":"isoform_match","label":'
    '"Expresses the functional isoform with the catalytic domain intact.","value":0.8,'
    '"strength":"strong","source":"Ensembl","source_url":'
    '"https://www.ensembl.org/Homo_sapiens/Gene/Summary?g=ENSG00000180776"},{"key":'
    '"disease_features_match","label":"Carries the disease\'s driver alterations — the '
    'right genetic background.","value":0.9,"strength":"strong","source":"Cell Model '
    'Passports / COSMIC","source_url":null},{"key":"dependency_signal","label":"Cells '
    'depend on this target in loss-of-function screens, so effects should be detectable.",'
    '"value":0.6,"strength":"moderate","source":"DepMap","source_url":'
    '"https://depmap.org/portal/gene/ZDHHC20"}],"watch_outs":[{"key":"protein_present",'
    '"label":"Little or no protein detected here — mRNA presence alone won\'t validate the '
    'target.","value":0.2,"strength":"weak","source":"Human Protein Atlas","source_url":'
    '"https://www.proteinatlas.org/ENSG00000180776"}],"context_notes":[],"science_gate":{'
    '"verdict":"SCIENCE GATE FAIL: TARGET_PROTEIN absent/broken — target present but '
    'non-functional or context missing in this model.","coherence":0.85,"partners":[{'
    '"gene":"GOLGA7","relation_type":"stabilizer_accessory","gates_model_selection":true,'
    '"status":"present","evidence_pmids":["11111111"]},{"gene":"KRAS","relation_type":'
    '"substrate","gates_model_selection":false,"status":"present","evidence_pmids":'
    '["22222222"]}]},"mechanism":{"verdict":"Mechanism observable; optional augmentations '
    'available to strengthen the readout.","context_fit":0.933,"context_required_unmet":'
    'false,"conditions":[{"condition":"three_d_architecture","necessity":"required",'
    '"state":"native","retrofittable":false,"rationale":"PDAC stroma requires 3D '
    'architecture for KRAS-driven invasion","readout_hint":"invasion assay",'
    '"evidence_pmids":["33333333"]},{"condition":"hypoxia_metabolic","necessity":'
    '"enhancing","state":"retrofit","retrofittable":true,"rationale":"tumor core hypoxia '
    'modulates palmitoylation flux","readout_hint":"HIF1A stabilization","evidence_pmids":'
    '[]},{"condition":"immune_compartment","necessity":"hypothesis","state":"retrofit",'
    '"retrofittable":false,"rationale":"possible immune modulation, unconfirmed",'
    '"readout_hint":"cytokine panel","evidence_pmids":[]}],"actions":[{"condition":'
    '"hypoxia_metabolic","action":"hypoxic incubation / metabolic media","cost":"low",'
    '"necessity":"enhancing","readout_hint":"HIF1A stabilization"},{"condition":'
    '"immune_compartment","action":"convert to organoid + immune co-culture","cost":"high",'
    '"necessity":"hypothesis","readout_hint":"cytokine panel"}],"verify":['
    '"hypoxia_metabolic: tumor core hypoxia modulates palmitoylation flux",'
    '"immune_compartment: possible immune modulation, unconfirmed"]},"sourcing":{'
    '"supplier_or_cro":"HUB Organoids / HCMI","catalog_url":"","purchasable":false}}]}'
)


def test_run_matchmaker_golden_report_json_is_byte_identical() -> None:
    actual = _run_golden_matchmaker()
    assert actual == _GOLDEN_REPORT_JSON
