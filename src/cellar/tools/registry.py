import importlib
import inspect
import pkgutil
from typing import Any

import cellar.tools as tools_package
from cellar.config import ModelProvider, Settings
from cellar.tools.base import Tool

_SKIP_MODULES = {"base", "registry"}

_WEB_SEARCH_TOOL: dict[str, object] = {
    "type": "web_search_20250305",
    "name": "web_search",
    "max_uses": 5,
}


def _import_tool_modules() -> None:
    for module in pkgutil.iter_modules(tools_package.__path__):
        if module.name not in _SKIP_MODULES:
            importlib.import_module(f"{tools_package.__name__}.{module.name}")


def _concrete_tool_classes() -> list[type[Tool[Any]]]:
    discovered: set[type[Tool[Any]]] = set()
    pending = list(Tool.__subclasses__())
    while pending:
        cls = pending.pop()
        if cls in discovered:
            continue
        discovered.add(cls)  # type: ignore[type-abstract]
        pending.extend(cls.__subclasses__())
    return [
        cls
        for cls in discovered
        if not inspect.isabstract(cls) and getattr(cls, "name", None) and cls.include_in_agent
    ]


def build_matchmaker_tools() -> list[Tool[Any]]:
    _import_tool_modules()
    classes = sorted(_concrete_tool_classes(), key=lambda cls: cls.name)
    return [cls() for cls in classes]


def build_server_tools(settings: Settings) -> list[dict[str, object]]:
    if settings.provider is ModelProvider.BEDROCK:
        return []
    return [_WEB_SEARCH_TOOL]
