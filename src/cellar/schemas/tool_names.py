from enum import StrEnum


class ToolName(StrEnum):
    LITERATURE_SEARCH = "literature_search"
    BUILD_RECOMMENDATIONS = "build_recommendations"
    ANNOTATE_RECOMMENDATIONS = "annotate_recommendations"
    TARGET_DISEASE_EVIDENCE = "target_disease_evidence"
    PROTEIN_ATLAS_PROFILE = "protein_atlas_profile"
    PROTEIN_EVIDENCE = "protein_evidence"
    PATHWAY_RELATIONS = "pathway_relations"
    ISOFORM_RISK = "isoform_risk"
    GENE_DEPENDENCY = "gene_dependency"
    FIND_CELL_MODEL = "find_cell_model"
    CELL_MODEL_GENE_MUTATIONS = "cell_model_gene_mutations"
    CELL_LINE_PROVENANCE = "cell_line_provenance"
    PROPOSE_MODEL_CANDIDATE = "propose_model_candidate"
    RECOMMEND_MODELS = "recommend_models"
    COUNT_CHARACTERS = "count_characters"


VERIFIER_EXCLUDED_TOOLS: frozenset[ToolName] = frozenset(
    {
        ToolName.BUILD_RECOMMENDATIONS,
        ToolName.RECOMMEND_MODELS,
        ToolName.ANNOTATE_RECOMMENDATIONS,
        ToolName.PROPOSE_MODEL_CANDIDATE,
    }
)


TOOL_DESCRIPTIONS: dict[ToolName, str] = {
    ToolName.LITERATURE_SEARCH: (
        "Search the biomedical literature (Europe PMC: peer-reviewed papers plus "
        "bioRxiv/medRxiv preprints) for a research question. Returns citable papers "
        "(title, authors, year, abstract, DOI/PMID, venue, citation count, preprint flag). "
        "Use this when structured databases (Open Targets, STRING) show weak or absent "
        "evidence for a target-disease link but the primary literature may still be rich, "
        "when you need citations to support a claim, or when checking prior use of a model "
        "system for a target/disease."
    ),
    ToolName.BUILD_RECOMMENDATIONS: (
        "Aggregate ALL evidence gathered so far this conversation into the ranked "
        "recommendation cards. Call this LAST, only after using the source tools to "
        "gather evidence for the target and disease (target_disease_evidence, "
        "protein_evidence/protein_atlas_profile, isoform_risk, pathway_relations, "
        "literature_search) and for the specific candidate cell models you want ranked "
        "(find_cell_model, cell_line_provenance, gene_dependency, cell_model_gene_mutations). "
        "It fuses that evidence deterministically and returns the ranked models with "
        "scores, hard-gate status, reasons, watch-outs, and sourcing. It ranks only the "
        "cell models you actually investigated this conversation; if you have not looked "
        "up any specific models it returns no cards and says so."
    ),
    ToolName.ANNOTATE_RECOMMENDATIONS: (
        "Attach a one-sentence rationale to each ranked model, AFTER calling "
        "build_recommendations. Pass a list of {model, why}: 'model' is the exact model "
        "name shown on the recommendation cards, and 'why' is a single plain-language "
        "sentence giving the comparative, mechanistic argument for why that model wins or "
        "falls short — the kind of reasoning you put in your prose. Cite each factual "
        "claim inline with a Markdown link, exactly as you would in the chat. The 'why' "
        "renders as the 'Why this model' line on the matching card. This does not change "
        "the ranking; it only annotates the deterministic cards with your reasoning."
    ),
    ToolName.TARGET_DISEASE_EVIDENCE: (
        "Query Open Targets for the database 'outside view' on a target. Give a target "
        "gene symbol; optionally give a disease. WITH a disease, returns the overall "
        "target-disease association score, its per-evidence-type breakdown (genetic, "
        "known drug, literature, rna_expression, …) and the target's tractability — a "
        "low score together with small-molecule tractability flags a target the "
        "databases UNDERRATE (worth rescuing via functional data). WITHOUT a disease, "
        "returns tractability plus the target's top associated diseases. Use this to "
        "judge whether the naive association evidence supports the target."
    ),
    ToolName.PROTEIN_ATLAS_PROFILE: (
        "Look up a target's protein-level profile in the Human Protein Atlas (HPA): "
        "subcellular localization, protein class, tissue/cell-type expression "
        "distribution, antibody reliability, and cancer prognostic significance. "
        "Flags mRNA-vs-protein DISCORDANCE (RNA broadly detected but protein "
        "narrowly detected) — a warning against trusting RNA-seq alone as a "
        "presence proxy. Give a target gene symbol; optionally a disease name to "
        "filter the cancer prognostic results to that tumour type (TCGA + "
        "validation cohorts, with p-values). Use this to check whether a target's "
        "protein is actually detected (not just its mRNA) and where."
    ),
    ToolName.PROTEIN_EVIDENCE: (
        "Synthesize tiered protein-presence evidence for a target (HPA localization/"
        "antibody + PRIDE MS detectability, with the MS-absence guard) and route "
        "proteomics modality (MS vs plasma affinity panels). Use to answer 'is the "
        "protein actually present / detectable', not just mRNA."
    ),
    ToolName.PATHWAY_RELATIONS: (
        "Return STRING functional partners plus the literature-derived relation map "
        "(partner -> relation_type + PMIDs + whether it gates model selection). Use to "
        "explain why a partner does or does not hard-reject a model."
    ),
    ToolName.ISOFORM_RISK: (
        "Enumerate a target's protein-coding isoforms and flag splicing / isoform-"
        "specificity risk (e.g. truncated forms that may lack the catalytic domain). "
        "Use when the scientist asks whether a model expresses the functional isoform."
    ),
    ToolName.GENE_DEPENDENCY: (
        "Check whether a target gene is a CRISPR knockout dependency ('is my target "
        "essential here') using the Sanger Cancer Dependency Map / Project Score — the "
        "queryable CRISPR-dependency database equivalent to DepMap. Give a gene symbol; "
        "optionally give a specific cell model (name or SIDM id). With a model, returns "
        "that model's gene-effect score (negative = knockout is lethal = a dependency). "
        "Without a model, returns an across-model summary: in how many screened models "
        "the gene is a dependency and how strong. Use this to judge whether a model is "
        "worth choosing because the target is actually essential in it."
    ),
    ToolName.FIND_CELL_MODEL: (
        "Look up a cancer cell line or organoid in the Wellcome Sanger Cell Model "
        "Passports (the curated hub behind the Sanger Cancer Dependency Map) by name. "
        "Returns its Sanger model id (SIDM), model type, growth properties, which "
        "genomic datasets are available (mutations, expression, proteomics, CRISPR KO, "
        "etc.) and a passport URL. Use it to check whether a named model exists and "
        "what data backs it before recommending it. Tolerates punctuation differences "
        "in the name (e.g. 'MIA PaCa-2' resolves to 'MIA-PaCa-2')."
    ),
    ToolName.CELL_MODEL_GENE_MUTATIONS: (
        "Get the mutations called in a specific gene for a specific cancer cell model "
        "in Cell Model Passports. Accepts a model name or Sanger SIDM id plus a gene "
        "symbol (e.g. KRAS, TP53). Returns matching mutation records: protein change, "
        "effect, driver status and variant allele fraction. An empty list means no "
        "call for that gene in that model, which is itself informative (the model may "
        "lack mutation data, or be wild-type for that gene)."
    ),
    ToolName.CELL_LINE_PROVENANCE: (
        "Look up a cell line in Cellosaurus for identity, provenance/reliability and "
        "commercial sourcing. Given a cell line name, returns its stable CVCL accession "
        "and synonyms, whether it is a PROBLEMATIC line (misidentified / contaminated / "
        "wrong species) with the reason, direct commercial supplier purchase URLs "
        "(ATCC / ECACC / DSMZ / and ~15 more regional biobanks — a real, clickable "
        "product page, not just a catalogue number), and cross-reference IDs into "
        "other databases (Cell Model Passports SIDM, DepMap ACH). Use this to check a "
        "model is authentic before recommending it, to get a real purchase link for a "
        "standard catalog cell line, or to resolve a name to the SIDM id needed by the "
        "Cell Model Passports and dependency tools. For organoids, co-cultures, GEMM/PDX "
        "or other CRO-built models NOT in a commercial cell-line catalog, this tool "
        "returns found=false — use web_search instead to find current supplier/CRO "
        "sourcing information for those."
    ),
    ToolName.PROPOSE_MODEL_CANDIDATE: (
        "Add a non-catalogue model to the candidate panel so it gets ranked alongside the "
        "cell lines. Cell lines enter the panel through find_cell_model / "
        "cell_line_provenance / gene_dependency, but organoids, co-cultures and GEMM/PDX "
        "in-vivo models are not in those databases, so without this tool they can never be "
        "ranked and build_recommendations can only compare 2D lines. Use it whenever the "
        "biology needs a context a 2D monolayer cannot provide (3D crypt/lumen "
        "architecture, tumour-stroma, an immune compartment, vascular flow or systemic "
        "PK), or whenever the cell lines you looked up are all being rejected for the same "
        "contextual reason. Give the model class you actually want compared, for example "
        "'patient-derived intestinal organoid' or 'tumour organoid + autologous T-cell "
        "co-culture'. FIRST run web_search to find a real supplier or CRO offering it, then "
        "pass that supplier and its URL here so the card carries citable sourcing — "
        "cell_line_provenance does not cover these model types. The candidate is scored by "
        "the same deterministic two-stage pipeline as every other model; you supply the "
        "candidate and its sourcing, not its scores. Call this BEFORE build_recommendations."
    ),
    ToolName.RECOMMEND_MODELS: (
        "Rank in-vitro / in-vivo biological models for testing a target in a disease, "
        "given the scientist's question. Runs the deterministic two-stage science-then-"
        "technical pipeline and returns ranked models with scores, hard-gate status, "
        "reasons, watch-outs, and sourcing. Call this for any 'which model should I use "
        "for <target> in <disease>' request."
    ),
    ToolName.COUNT_CHARACTERS: (
        "Count the number of characters in a piece of text. "
        "Use this whenever the user asks how long a string or piece of text is."
    ),
}
