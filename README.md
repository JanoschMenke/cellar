# cellar — Model Matchmaker

Picks the right in vitro biological model (2D line, organoid, co-culture, or
"go in vivo") for testing a **target** in a **disease**, with a science-first
two-stage gate, literature-grounded evidence, and CRO/supplier sourcing.

Worked example: **ZDHHC20 in PDAC**.

## Run the demo
```bash
uv run python examples/pdac_zdhhc20.py
```

## Layout

The Model Matchmaker follows the repo's `src/cellar/` layout (see [CLAUDE.md](./CLAUDE.md)):
external-data and LLM-derivation modules live under `services/`, deterministic capabilities
under `tools/`, the shared data vocabulary under `schemas/`, and cached evidence under `data/`.

- `services/retrieval.py`  — live clients (Open Targets, Cellosaurus disease search)
- `services/cellosaurus.py` — Cellosaurus client: cell-line identity, provenance/reliability (problematic-line flags), supplier catalogue numbers, and cross-refs (CVCL → SIDM/DepMap/ATCC)
- `services/cell_model_passports.py` — Sanger Cell Model Passports (DepMap) JSON:API client: model/gene lookup, per-model datasets, matchmaker fact sheets
- `services/dependency.py` — CRISPR gene-dependency ("is my target essential here") from the Sanger/Broad integrated Cancer Dependency Map (Project Score `crispr_ko` gene-effect); DepMap-equivalent, queried live via the CMP API
- `services/proteomics.py` — tiered protein-evidence synthesizer + MS-absence guard; live PRIDE + HPA
- `services/hpa.py` — Human Protein Atlas client: subcellular localization, tissue/cell-type expression, mRNA-vs-protein discordance, antibody reliability, and cancer prognostic significance (TCGA + validation cohorts)
- `services/isoforms.py`   — Ensembl protein-coding isoform enumeration + splicing-risk flag
- `services/pathway.py`    — STRING partners + literature-derived relation map + science gate
- `services/mechanism.py`  — MoA -> culture-context layer ("right target, wrong model" check)
- `services/evidence.py`   — Elicit + Amass query templates
- `tools/scoring.py`       — two-stage (science 0.65 / technical 0.35) deterministic scoring
- `tools/recommend.py`     — per-model decision cards (why / watch-outs / context / sourcing)
- `schemas/matchmaker.py`  — `ModelCandidate` + `ModelTier` / `QuestionType` enums
- `data/`                  — cached evidence (ZDHHC20 relations, PRIDE probe)
- `examples/pdac_zdhhc20.py` — end-to-end runnable example

See `PROPOSAL.md` for the full design rationale.

---

## Environment (uv)

This project uses **[uv](https://docs.astral.sh/uv/)** to manage Python, dependencies, and the
virtual environment. If you have never used uv, read the short guide below.

### What is uv?

uv is a fast, all-in-one Python package and project manager (a drop-in replacement for `pip`,
`pip-tools`, `virtualenv`, and `pyenv`). For this repo it does three things:

- installs and pins the correct **Python version** (3.13),
- resolves and locks **dependencies** into `uv.lock` for reproducible installs,
- manages the project's **virtual environment** in `.venv/` automatically.

You generally never activate the virtualenv or run `pip` by hand — you prefix commands with
`uv run`, and uv makes sure the environment is correct first.

### Installing uv

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

### Getting started

Clone the repo, then from the project root:

```bash
uv sync
```

`uv sync` reads `pyproject.toml` and `uv.lock`, installs the pinned Python 3.13 if needed,
creates `.venv/`, and installs all dependencies (plus this project as an editable package).
That single command is all you need to get a working environment.

### Everyday commands

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

Always add libraries through uv so `pyproject.toml` and `uv.lock` stay in sync. Do **not**
hand-edit the `dependencies` list in `pyproject.toml` or call `pip install`.

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

The agent also carries **Cell Model Passports tools** backed by `services/cell_model_passports.py`.
Ask it something like *"Is MIA PaCa-2 in Cell Model Passports, and does it carry a KRAS
mutation?"* and it calls `find_cell_model` / `cell_model_gene_mutations`, then answers from the
live Sanger data (SIDM id, available datasets, KRAS G12C, …). A `gene_dependency` tool — *"Is
KRAS a CRISPR dependency in MIA PaCa-2?"* — returns the gene-effect score from the Sanger/Broad
Cancer Dependency Map, and a `cell_line_provenance` tool adds Cellosaurus identity/reliability
checks — *"Is the KB cell line problematic?"* returns its CVCL accession, the contamination flag,
supplier catalogue numbers, and cross-refs to SIDM/DepMap; and a `protein_atlas_profile` tool —
*"Does ZDHHC20 have mRNA-vs-protein discordance, and is it prognostic in pancreatic cancer?"* —
returns the Human Protein Atlas localization, expression, antibody reliability and cancer
prognostic evidence. Adding a data source is drop-in: create a `tools/<source>.py` with a `Tool`
subclass and it is **auto-discovered** by
`tools/registry.py` — no central registration. Set `include_in_agent = False` on a tool to keep
it out of the agent (e.g. the `count_characters` smoke-test tool).

Environment overrides: `CELLAR_PROVIDER` (`direct_api` | `bedrock`), `CELLAR_MODEL_NAME`,
`AWS_REGION`.

## Project layout notes

The original uv scaffold package lives under `src/cellar/`. See [CLAUDE.md](./CLAUDE.md) for the
module boundaries, coding conventions, and the deterministic-core / agent-at-the-edges design
philosophy.
