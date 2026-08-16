# cellar: Model Matchmaker

cellar is a small agentic tool that helps you pick a sensible in-vitro (or in-vivo) biological
model for testing a **target** in a **disease**: a 2D cell line, an organoid, a co-culture, or
an honest "just go in vivo". It leans on a science-first two-stage gate, literature-grounded
evidence, and CRO/supplier sourcing. A thin Claude agent decides which deterministic tools to
call and narrates the result, but the ranked models, their scores, and their provenance all come
from plain code rather than from the model's own prose.

<img width="583" height="787" alt="image" src="https://github.com/user-attachments/assets/713127a8-7920-45bc-9e6e-687d0288a753" />


It started life as a hackathon project, so treat it as a useful prototype rather than a polished
product (see the honest notes below).


## Good to know

A few honest caveats before you rely on anything it tells you:

- **This began as a hackathon build.** It is lightly tested and rough around some edges. It
  works and we think it is genuinely useful, but it has not been hardened for production.
- **Do not fully trust the LLM.** The scores, ranks, and evidence records come from deterministic
  code, but a language model still drives the workflow and writes the narration, so it can be
  wrong or misleading. Treat the output as a helpful starting point, and check the cited
  evidence and sources yourself before making a real decision.
- **You bring your own Claude API key** (see below). As with any secret, be careful where you
  paste it: only enter it into tools you actually trust, and keep it out of shared machines,
  screenshots, and chat logs.

We aim to guide the model to push back on unreasonable requests:

<img width="689" height="384" alt="cellar recommendation cards" src="https://github.com/user-attachments/assets/05bbe5d5-d29f-4850-a7af-298f486b2f25" />

## Quickstart

Requires **[uv](https://docs.astral.sh/uv/)** (it installs and pins Python 3.13, resolves
dependencies, and manages the virtualenv, so you never call `pip` directly) and your own
Anthropic (Claude) API key.

```bash
uv sync                              # installs Python 3.13, deps, and this package
cp .env.example .env                 # then set ANTHROPIC_API_KEY=sk-ant-... in .env
uv run cellar-web                    # starts the web app
```

The server prints the URL it is listening on (default `http://127.0.0.1:1312`, or the next free
port if 1312 is busy). Open that URL in your browser.

If you start the app without a key set, it will prompt you to paste one in the browser and save
it to your local `.env`. However you provide the key, remember it is a secret: only paste it into
places you trust.

## Architecture

cellar keeps the LLM out of the data path: a thin agent decides *which* deterministic tool to
call next and turns the result into narration, but every score, rank, and evidence record comes
from typed, testable code. `services/` own external I/O (Open Targets, Cellosaurus, Cell Model
Passports, Europe PMC, HPA, STRING, PRIDE, and so on) and return pydantic schemas; `tools/` wrap
those services (plus deterministic scoring and recommendation logic) as agent-callable
capabilities; `schemas/` defines the shared data vocabulary everything else passes around.

| Path | Contents |
| --- | --- |
| `src/cellar/agents/` | The agent loop: `StreamingAgent` (main matchmaker loop, streams events to the UI) and `VerifierAgent` (a bounded, lookup-only follow-up pass that checks each recommendation after it is produced). |
| `src/cellar/schemas/` | Pydantic models and `StrEnum`s, e.g. `matchmaker.py` (query, model tiers, question types), `recommendation.py` (recommendation report), `evidence.py` (evidence records), `events.py` (streaming event kinds). |
| `src/cellar/services/` | External-data clients and LLM-derivation logic, one module per source: `open_targets.py`, `cellosaurus.py`, `cell_model_passports.py`, `dependency.py`, `proteomics.py`, `hpa.py`, `isoforms.py`, `pathway.py`, `mechanism.py`, `literature.py` (Europe PMC), `pubmed.py`, `pride.py`, `live_lookups.py` (Open Targets + Cellosaurus disease-search helpers), plus `llm.py` (Claude client), `evidence_store.py` (per-run provenance), `aggregate.py`, `derivation.py`, `matchmaker.py`, `recommendation.py`, `panels.py`. |
| `src/cellar/tools/` | Agent-callable, deterministic capabilities that wrap the services above: `scoring.py` (two-stage science/technical scoring), `recommend.py` / `recommend_models.py` / `build_recommendations.py` (decision cards), `annotate.py`, plus one tool module per data source (`open_targets.py`, `cellosaurus.py`, `cell_models.py`, `dependency.py`, `hpa.py`, `literature.py`, `lookups.py`, `text.py`). New sources are auto-discovered via `registry.py`, so no central registration is needed. |
| `src/cellar/prompts/` | System prompts for the matchmaker agent and the verifier agent. |
| `src/cellar/web/` | The FastAPI app (`server.py`) and the static/design-system frontend that renders the agent's typed output as tables, cards, and plots. |
| `src/cellar/data/` | Cached evidence used by the ZDHHC20 worked example (relations and a PRIDE probe). |
| `src/cellar/config.py` | Settings loading (`Settings`, `load_settings`). |

## Configuration

All configuration is environment variables, loaded via `.env` (see `.env.example`) and read in
`src/cellar/config.py`.

| Variable | Default | Purpose |
| --- | --- | --- |
| `ANTHROPIC_API_KEY` | required | Your Anthropic API key, `sk-ant-...`. |
| `CELLAR_PROVIDER` | `direct_api` | `direct_api` or `bedrock`. |
| `CELLAR_MODEL_NAME` | `claude-sonnet-4-6` (per provider) | Model override. |
| `AWS_REGION` | `eu-west-2` | Only used when `CELLAR_PROVIDER=bedrock`. |
| `CELLAR_WORKSPACE_DIR` | `.cellar` | Local workspace/scratch directory. |
| `CELLAR_HOST` | `127.0.0.1` | Host the web server binds to (see `web/server.py`). |
| `CELLAR_PORT` | `1312` | Preferred port; the server tries the next free ones if it is busy. |

## Development

See [CONTRIBUTING.md](./CONTRIBUTING.md) for setup, the quality gates, and coding standards.

## License

Apache-2.0. See [LICENSE](./LICENSE).
