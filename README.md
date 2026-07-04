# cellar

An agentic scientist system: autonomous agents that propose hypotheses, plan and run
experiments, gather evidence from tools, critique results, and report findings.

This project uses **[uv](https://docs.astral.sh/uv/)** to manage Python, dependencies, and the
virtual environment. If you have never used uv, read the short guide below.

## What is uv?

uv is a fast, all-in-one Python package and project manager (a drop-in replacement for `pip`,
`pip-tools`, `virtualenv`, and `pyenv`). For this repo it does three things:

- installs and pins the correct **Python version** (3.13),
- resolves and locks **dependencies** into `uv.lock` for reproducible installs,
- manages the project's **virtual environment** in `.venv/` automatically.

You generally never activate the virtualenv or run `pip` by hand — you prefix commands with
`uv run`, and uv makes sure the environment is correct first.

## Installing uv

**macOS / Linux:**

```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
```

**macOS (Homebrew):**

```bash
brew install uv
```

**Windows (PowerShell):**

```powershell
powershell -ExecutionPolicy ByPass -c "irm https://astral.sh/uv/install.ps1 | iex"
```

Verify the install:

```bash
uv --version
```

To update uv later: `uv self update`.

## Getting started

Clone the repo, then from the project root:

```bash
uv sync
```

`uv sync` reads `pyproject.toml` and `uv.lock`, installs the pinned Python 3.13 if needed,
creates `.venv/`, and installs all dependencies (plus this project as an editable package).
That single command is all you need to get a working environment.

Run code with `uv run`:

```bash
uv run python -c "import cellar; print(cellar.load_settings())"
```

## Everyday commands

| Task                              | Command                          |
| --------------------------------- | -------------------------------- |
| Install / update the environment  | `uv sync`                        |
| Run a script or module            | `uv run python -m cellar...`     |
| Run any command in the venv       | `uv run <command>`               |
| Add a dependency                  | `uv add <package>`               |
| Add a dev-only dependency         | `uv add --dev <package>`         |
| Remove a dependency               | `uv remove <package>`            |
| Show the dependency tree          | `uv tree`                        |
| Upgrade the lockfile              | `uv lock --upgrade`              |

### Adding dependencies

Always add libraries through uv so `pyproject.toml` and `uv.lock` stay in sync:

```bash
uv add pydantic
```

Do **not** hand-edit the `dependencies` list in `pyproject.toml` or call `pip install` — uv
manages both the manifest and the lockfile together, and manual edits break reproducibility.

## Project layout

The package lives under `src/cellar/`. See [CLAUDE.md](./CLAUDE.md) for the module boundaries,
coding conventions, and the deterministic-core / agent-at-the-edges design philosophy.
