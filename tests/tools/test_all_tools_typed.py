from cellar.schemas.tool_names import ToolName
from cellar.tools.registry import build_matchmaker_tools


def _all_tool_classes():
    seen, pending = (
        set(),
        list(__import__("cellar.tools.base", fromlist=["Tool"]).Tool.__subclasses__()),
    )
    while pending:
        cls = pending.pop()
        if cls in seen:
            continue
        seen.add(cls)
        pending.extend(cls.__subclasses__())
    return [
        c for c in seen if getattr(c, "name", None) and c.__module__.startswith("cellar.tools.")
    ]


def test_every_tool_declares_an_input_model() -> None:
    for cls in _all_tool_classes():
        assert cls.input_model is not None, cls.__name__


def test_every_tool_name_is_a_toolname_member() -> None:
    for cls in _all_tool_classes():
        assert cls.name in set(ToolName), cls.__name__


def test_agent_tools_still_discovered() -> None:
    names = {t.name for t in build_matchmaker_tools()}
    assert ToolName.LITERATURE_SEARCH in names
