# Contributing to cellar

## Prerequisites

- **[uv](https://docs.astral.sh/uv/)** — manages the Python version, dependencies, and the
  virtualenv for this project. Never call `pip` directly.
- **Python 3.13** — `uv sync` installs the pinned version automatically if it isn't already
  available; you don't need to install it yourself first.

## Setup

```bash
uv sync
```

This reads `pyproject.toml` and `uv.lock`, installs Python 3.13 if needed, creates `.venv/`,
and installs all dependencies plus `cellar` itself as an editable package.

Add dependencies with `uv add <package>` (`uv add --dev <package>` for dev-only tools). Do not
hand-edit the `dependencies` list in `pyproject.toml` — let `uv` manage it and `uv.lock`
together. Run everything through `uv run ...` rather than activating the virtualenv by hand.

## Quality gates

Run these before opening a PR — all four should be clean:

```bash
uv run ruff check src tests      # lint
uv run ruff format src tests     # format
uv run mypy src                  # type-check
uv run pytest                    # tests
```

## Coding standards

The highlights:

- **Types everywhere.** Annotate every function parameter, return value, and non-trivial local.
  Avoid `Any` where a precise type is available.
- **Modern native generics.** `list[str]`, `dict[str, float]`, `str | None` — not `List`, `Dict`,
  `Optional`, `Union` from `typing`.
- **Schemas over dicts.** Model structured data as pydantic `BaseModel`s (or a `@dataclass` for
  a lightweight, validation-free value object) rather than passing bare dictionaries around.
- **`StrEnum` for fixed choices.** No magic strings for statuses, roles, kinds, or modes.
- **No comments, no docstrings.** Express intent through naming, small functions, and types
  instead. If code needs a comment to be understood, restructure it.
- **Small, single-purpose functions and expressive names.**

## Project layout — where new code goes

```
src/cellar/
├── agents/     # the agent loop(s) — orchestration only, no business logic
├── schemas/    # pydantic models and StrEnums — the shared data vocabulary
├── services/   # stateful integrations: external APIs, the LLM client, persistence
├── tools/      # deterministic, agent-callable capabilities that wrap services
├── prompts/    # system prompts for the agents
├── web/        # the FastAPI app and frontend
└── config.py   # settings loading
```

- A new external data source gets a `services/<source>.py` client that returns typed schemas,
  plus a `tools/<source>.py` `Tool` subclass exposing it to the agent. Tools are auto-discovered
  by `tools/registry.py` — no central registration needed; set `include_in_agent = False` on a
  `Tool` to keep it out of the agent (e.g. a smoke-test tool).
- Anything with I/O, network calls, or long-lived state belongs in `services/`, not `tools/` or
  `agents/`.
- New data structures crossing a module boundary should be pydantic models in `schemas/`, not
  loose dicts.
- Keep the agent layer thin: it should only decide which tool to call and interpret the result,
  never do arithmetic, parsing, or data wrangling that a function could do deterministically.

## Commits and PRs

- Keep commits focused; write commit messages that explain *why*, not just *what* changed.
- Run the four quality gates above before pushing — a PR with failing lint, formatting, types,
  or tests should not be opened.
- Prefer small, reviewable PRs over large ones. Describe what changed and why in the PR
  description.
