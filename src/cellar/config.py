import os
from enum import StrEnum

from pydantic import BaseModel

OPEN_TARGETS_URL = "https://api.platform.opentargets.org/api/v4/graphql"
CELLOSAURUS_URL = "https://api.cellosaurus.org"
HPA_URL_TEMPLATE = "https://www.proteinatlas.org/{ensembl_id}.json"
PRIDE_UNIPROT_URL = "https://rest.uniprot.org/uniprotkb/search"
PUBMED_EUTILS_URL = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils"
ENSEMBL_URL = "https://rest.ensembl.org"
EUROPE_PMC_SEARCH_URL = "https://www.ebi.ac.uk/europepmc/webservices/rest/search"
CELL_MODEL_PASSPORTS_URL = "https://api.cellmodelpassports.sanger.ac.uk"
STRING_URL = "https://string-db.org/api/json"

HTTP_USER_AGENT = "cellar-matchmaker/1.0 (+https://github.com/JanoschMenke/cellar)"
EUROPE_PMC_MAX_RESULTS = 100
CMP_DEFAULT_PAGE_SIZE = 100
CMP_DEFAULT_MAX_PAGES = 25
CMP_ACCEPT_HEADER = "application/vnd.api+json"


class ModelProvider(StrEnum):
    DIRECT_API = "direct_api"
    BEDROCK = "bedrock"


_DEFAULT_MODEL_BY_PROVIDER: dict[ModelProvider, str] = {
    ModelProvider.DIRECT_API: "claude-sonnet-4-6",
    ModelProvider.BEDROCK: "eu.anthropic.claude-sonnet-4-6",
}


class Settings(BaseModel):
    provider: ModelProvider = ModelProvider.DIRECT_API
    model_name: str = "claude-sonnet-4-6"
    aws_region: str = "eu-west-2"
    max_output_tokens: int = 8192
    max_agent_steps: int = 20
    verifier_max_tool_rounds: int = 4
    verifier_max_tokens: int = 3000
    workspace_dir: str = ".cellar"


def load_settings() -> Settings:
    provider = ModelProvider(os.environ.get("CELLAR_PROVIDER", ModelProvider.DIRECT_API))
    model_name = os.environ.get("CELLAR_MODEL_NAME", _DEFAULT_MODEL_BY_PROVIDER[provider])
    return Settings(
        provider=provider,
        model_name=model_name,
        aws_region=os.environ.get("AWS_REGION", "eu-west-2"),
        workspace_dir=os.environ.get("CELLAR_WORKSPACE_DIR", ".cellar"),
    )
