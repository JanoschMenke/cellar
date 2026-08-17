import json

from cellar.schemas.tool_inputs import ProposeModelCandidateInput
from cellar.schemas.tool_names import TOOL_DESCRIPTIONS, ToolName
from cellar.tools.base import Tool, ToolResult

_ACCEPTED_URL_SCHEMES = ("http://", "https://")


def _clean_url(url: str) -> str:
    candidate = url.strip()
    return candidate if candidate.startswith(_ACCEPTED_URL_SCHEMES) else ""


class ProposeModelCandidateTool(Tool[ProposeModelCandidateInput]):
    name = ToolName.PROPOSE_MODEL_CANDIDATE
    description = TOOL_DESCRIPTIONS[ToolName.PROPOSE_MODEL_CANDIDATE]
    input_model = ProposeModelCandidateInput

    def run(self, arguments: ProposeModelCandidateInput) -> ToolResult:
        name = arguments.name.strip()
        if not name:
            return ToolResult(content="A model name is required.", is_error=True)
        sourcing_url = _clean_url(arguments.sourcing_url)
        supplier = arguments.supplier_or_cro.strip()
        payload: dict[str, object] = {
            "found": True,
            "name": name,
            "tier": str(arguments.tier),
            "basis": arguments.basis.strip(),
            "supplier_or_cro": supplier,
            "sourcing_url": sourcing_url,
            "sourced": bool(supplier and sourcing_url),
            "note": (
                f"{name} added to the candidate panel as a {arguments.tier} model. "
                "It will be scored by the same two-stage pipeline when you call "
                "build_recommendations."
            ),
        }
        if not sourcing_url:
            payload["sourcing_warning"] = (
                "No supplier URL was supplied, so this card will carry no sourcing. "
                "Run web_search for a supplier or CRO and propose it again to attach one."
            )
        return ToolResult(content=json.dumps(payload))
