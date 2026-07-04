import importlib
import inspect
import pkgutil

import cellar.tools as tools_package
from cellar.config import ModelProvider, Settings
from cellar.tools.base import Tool

_SKIP_MODULES = {"base", "registry"}

# Anthropic's server-executed web search — resolved and billed by Anthropic itself,
# never dispatched through our Tool.run() loop. Used for commercial/CRO sourcing
# leads on model types Cellosaurus doesn't catalog (organoids, co-cultures,
# GEMM/PDX). Not supported on Amazon Bedrock (see the Claude API server-tools
# availability table), so it is only added for the direct Anthropic API.
_WEB_SEARCH_TOOL: dict[str, object] = {
    "type": "web_search_20260209",
    "name": "web_search",
    "max_uses": 5,
}


def _import_tool_modules() -> None:
    for module in pkgutil.iter_modules(tools_package.__path__):
        if module.name not in _SKIP_MODULES:
            importlib.import_module(f"{tools_package.__name__}.{module.name}")


def _concrete_tool_classes() -> list[type[Tool]]:
    discovered: set[type[Tool]] = set()
    pending = list(Tool.__subclasses__())
    while pending:
        cls = pending.pop()
        if cls in discovered:
            continue
        discovered.add(cls)
        pending.extend(cls.__subclasses__())
    return [
        cls
        for cls in discovered
        if not inspect.isabstract(cls) and getattr(cls, "name", None) and cls.include_in_agent
    ]


def build_matchmaker_tools() -> list[Tool]:
    """Discover every agent-facing Tool subclass under cellar.tools and instantiate
    it. A new data source only has to add a tools/<source>.py with a Tool subclass —
    no central registration, so source PRs never collide on this file. A tool opts
    out of the agent by setting include_in_agent = False (e.g. smoke-test tools)."""
    _import_tool_modules()
    classes = sorted(_concrete_tool_classes(), key=lambda cls: cls.name)
    return [cls() for cls in classes]


def build_server_tools(settings: Settings) -> list[dict[str, object]]:
    """Server-executed tool specs (raw API dicts, not Tool subclasses) — Anthropic
    resolves these itself and the result arrives already filled in on the same
    response, so the agent loop must not try to dispatch them through
    Tool.run(). Gated by provider since not every server tool is available on
    every provider."""
    if settings.provider is ModelProvider.BEDROCK:
        return []
    return [_WEB_SEARCH_TOOL]
