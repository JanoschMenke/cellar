import importlib
import inspect
import pkgutil

import cellar.tools as tools_package
from cellar.tools.base import Tool

_SKIP_MODULES = {"base", "registry"}


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
