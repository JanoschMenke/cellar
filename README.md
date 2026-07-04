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

## Running the console agent

`cellar` ships a minimal console agent (a thin tool-use loop) for smoke-testing the model
connection. It supports two providers.

**Direct Anthropic API (default).** Needs an `sk-ant-...` key. If `ANTHROPIC_API_KEY` is set it
is used automatically; otherwise the agent prompts you to paste one at startup.

```bash
export ANTHROPIC_API_KEY=sk-ant-...   # optional — you'll be prompted if unset
uv run cellar
```

**Amazon Bedrock (opt-in).** No Anthropic key — authenticates with AWS credentials. Requires an
AWS profile with Bedrock invoke access.

```bash
aws sso login --profile dev-run
AWS_PROFILE=dev-run CELLAR_PROVIDER=bedrock uv run cellar
```

On the very first run with the direct API and no key set, the agent prompts you to paste an
`sk-ant-...` key, then saves it to `.env` (gitignored) so you are not asked again.

### Quick walkthrough

Once it starts you get an interactive prompt. Type a normal message for plain chat, or ask
something that needs a tool to see the tool-calling loop in action:

```text
cellar console agent — provider direct_api, model claude-opus-4-8
Type a message, or 'exit' to quit.

you > what is a cell line?
cellar > A cell line is a population of cells grown in culture that ...

you > how many characters are in "hello world"?
cellar > The text "hello world" contains 11 characters (including the space).

you > exit
```

The second question is the interesting one: the agent decides to call the `count_characters`
tool, the loop runs the tool locally, feeds the result back, and Claude answers with it — the
same deterministic-tool pattern the whole project is built on. Type `exit` (or Ctrl-D) to quit.

Environment overrides: `CELLAR_PROVIDER` (`direct_api` | `bedrock`), `CELLAR_MODEL_NAME`,
`AWS_REGION`.

## Project layout

The package lives under `src/cellar/`. See [CLAUDE.md](./CLAUDE.md) for the module boundaries,
coding conventions, and the deterministic-core / agent-at-the-edges design philosophy.
