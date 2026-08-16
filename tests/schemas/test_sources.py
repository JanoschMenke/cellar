from cellar.schemas.sources import (
    CellModelHit,
    CommercialListing,
    Isoform,
    IsoformRiskSummary,
    ModelFacts,
    OtDiseaseHit,
    OtTargetProfile,
    OtTractabilityRow,
    Provenance,
    ShortestIsoform,
    StringPartner,
    UniprotHit,
)


def test_ot_disease_hit_round_trips() -> None:
    d: dict[str, object] = {"id": "EFO_0000305", "name": "breast carcinoma"}
    assert OtDiseaseHit(**d).model_dump() == d


def test_ot_tractability_row_round_trips() -> None:
    d: dict[str, object] = {"modality": "SM", "label": "Approved Drug", "value": True}
    assert OtTractabilityRow(**d).model_dump() == d


def test_ot_target_profile_round_trips() -> None:
    d: dict[str, object] = {
        "symbol": "ZDHHC20",
        "tractability": [
            {"modality": "SM", "label": "Approved Drug", "value": True},
            {"modality": "AB", "label": "Predicted Tractable", "value": False},
        ],
        "top_diseases": [("pancreatic carcinoma", 0.812), ("breast carcinoma", 0.451)],
    }
    assert OtTargetProfile(**d).model_dump() == d


def test_uniprot_hit_round_trips() -> None:
    d: dict[str, object] = {"accession": "Q9NPJ3", "protein_existence_level": 1}
    assert UniprotHit(**d).model_dump() == d


def test_uniprot_hit_round_trips_with_null_existence_level() -> None:
    d: dict[str, object] = {"accession": "Q9NPJ3", "protein_existence_level": None}
    assert UniprotHit(**d).model_dump() == d


def test_uniprot_hit_round_trips_with_null_accession() -> None:
    d: dict[str, object] = {"accession": None, "protein_existence_level": None}
    assert UniprotHit(**d).model_dump() == d


def test_cell_model_hit_round_trips() -> None:
    d: dict[str, object] = {
        "id": "CVCL_0480",
        "name": "PANC-1",
        "category": "Cancer cell line",
        "problematic": False,
    }
    assert CellModelHit(**d).model_dump() == d


def test_cell_model_hit_round_trips_with_null_id() -> None:
    d: dict[str, object] = {
        "id": None,
        "name": None,
        "category": None,
        "problematic": False,
    }
    assert CellModelHit(**d).model_dump() == d


def test_string_partner_round_trips() -> None:
    d: dict[str, object] = {"partner": "DHHC20", "score": 0.912}
    assert StringPartner(**d).model_dump() == d


def test_isoform_round_trips() -> None:
    d: dict[str, object] = {
        "transcript_id": "ENST00000373069",
        "name": "ZDHHC20-201",
        "aa_length": 322,
        "is_canonical": True,
    }
    assert Isoform(**d).model_dump() == d


def test_isoform_round_trips_with_null_aa_length() -> None:
    d: dict[str, object] = {
        "transcript_id": "ENST00000999999",
        "name": None,
        "aa_length": None,
        "is_canonical": False,
    }
    assert Isoform(**d).model_dump() == d


def test_shortest_isoform_round_trips() -> None:
    d: dict[str, object] = {
        "name": "ZDHHC20-202",
        "transcript_id": "ENST00000373070",
        "aa_length": 200,
        "pct_of_canonical": 62,
    }
    assert ShortestIsoform(**d).model_dump() == d


def test_isoform_risk_summary_round_trips_with_shortest_isoform() -> None:
    d: dict[str, object] = {
        "canonical": "ZDHHC20-201",
        "canonical_aa": 322,
        "n_protein_coding": 3,
        "n_alternative": 2,
        "aa_span": (200, 322),
        "shortest_isoform": {
            "name": "ZDHHC20-202",
            "transcript_id": "ENST00000373070",
            "aa_length": 200,
            "pct_of_canonical": 62,
        },
        "isoform_specificity_risk": "low",
        "message": "Ensembl annotates 3 protein-coding isoforms (200-322 aa).",
    }
    assert IsoformRiskSummary(**d).model_dump() == d


def test_isoform_risk_summary_round_trips_without_shortest_isoform() -> None:
    d: dict[str, object] = {
        "canonical": "ZDHHC20-201",
        "canonical_aa": 322,
        "n_protein_coding": 1,
        "n_alternative": 0,
        "aa_span": (322, 322),
        "shortest_isoform": None,
        "isoform_specificity_risk": "high",
        "message": "A substantial isoform is below the functional length.",
    }
    assert IsoformRiskSummary(**d).model_dump() == d


def test_isoform_risk_summary_round_trips_with_empty_span() -> None:
    d: dict[str, object] = {
        "canonical": None,
        "canonical_aa": None,
        "n_protein_coding": 0,
        "n_alternative": 0,
        "aa_span": (None, None),
        "shortest_isoform": None,
        "isoform_specificity_risk": "low",
        "message": "No protein-coding isoforms found.",
    }
    assert IsoformRiskSummary(**d).model_dump() == d


def test_commercial_listing_round_trips() -> None:
    d: dict[str, object] = {"accession": "ATCC-CRL-1469", "url": "https://www.atcc.org/CRL-1469"}
    assert CommercialListing(**d).model_dump() == d


def test_provenance_round_trips() -> None:
    d: dict[str, object] = {
        "found": True,
        "accession": "CVCL_0480",
        "names": ["PANC-1"],
        "category": "Cancer cell line",
        "species": ["Homo sapiens"],
        "problematic": False,
        "problems": [],
        "cautions": ["Some populations may be contaminated"],
        "provenance_ok": 1.0,
        "commercial_listings": {
            "ATCC": {"accession": "CRL-1469", "url": "https://www.atcc.org/CRL-1469"},
        },
        "cross_ids": {"cell_model_passport": "SIDM00003", "depmap": "ACH-000042"},
        "cellosaurus_url": "https://www.cellosaurus.org/CVCL_0480",
    }
    assert Provenance(**d).model_dump() == d


def test_provenance_round_trips_when_problematic_and_no_accession() -> None:
    d: dict[str, object] = {
        "found": True,
        "accession": None,
        "names": [],
        "category": None,
        "species": [],
        "problematic": True,
        "problems": ["Contaminated"],
        "cautions": [],
        "provenance_ok": 0.0,
        "commercial_listings": {},
        "cross_ids": {},
        "cellosaurus_url": None,
    }
    assert Provenance(**d).model_dump() == d


def test_model_facts_round_trips() -> None:
    d: dict[str, object] = {
        "sidm_id": "SIDM00003",
        "names": ["PANC-1"],
        "model_type": "Cell Line",
        "growth_properties": "Adherent",
        "ploidy": 2.0,
        "mutations_per_mb": 3.4,
        "crispr_ko_available": True,
        "datasets_available": ["mutations", "cnv", "expression"],
        "catalog_url": "https://cellmodelpassports.sanger.ac.uk/passports/SIDM00003",
    }
    assert ModelFacts(**d).model_dump() == d


def test_model_facts_round_trips_with_nulls() -> None:
    d: dict[str, object] = {
        "sidm_id": "SIDM00004",
        "names": None,
        "model_type": None,
        "growth_properties": None,
        "ploidy": None,
        "mutations_per_mb": None,
        "crispr_ko_available": False,
        "datasets_available": [],
        "catalog_url": "https://cellmodelpassports.sanger.ac.uk/passports/SIDM00004",
    }
    assert ModelFacts(**d).model_dump() == d
