# cellar

An agentic scientist system: autonomous agents that propose hypotheses, plan and run
experiments, gather evidence from tools, critique results, and report findings.

## Environment & tooling

- Python 3.13, managed with **uv**. Never call `pip` directly.
- Add dependencies with `uv add <package>` (and `uv add --dev <package>` for dev-only tools).
  Do not hand-edit the `dependencies` list in `pyproject.toml` — let `uv` manage it and the
  lockfile together.
- Run code with `uv run python -m cellar...` or `uv run <script>`; the project is installed
  as an editable `src` package, so `import cellar` works everywhere.
- Sync the environment with `uv sync` after pulling changes.

## Design philosophy: deterministic core, agent at the edges

Push as much logic as possible into plain, deterministic code. The LLM agent is expensive,
non-reproducible, and hard to test — so it should do the least work that only it can do.

- **Prefer tools over prompting.** When the system needs to *do* something — search, query,
  compute, transform, validate, persist — write a deterministic **tool** for it under
  `tools/` rather than asking the agent to produce the result in free text. Tools take typed
  inputs and return typed schemas.
- **Use the agent only to reason and to schedule.** The agent's job is judgment: forming
  hypotheses, deciding *which* tool to call next, interpreting results, and sequencing steps.
  It should not be doing arithmetic, parsing, data wrangling, or anything a function can do
  reliably.
- **No hidden logic in prompts.** If behavior can be expressed as code, it belongs in code,
  not baked into a prompt. Prompts describe intent and available tools; they are not a place
  to smuggle business rules.
- **Deterministic wherever feasible.** Given the same inputs, non-agent code paths should
  produce the same outputs. Isolate the non-determinism (LLM calls) behind `services/` so the
  rest of the system stays reproducible and unit-testable.

## Project layout

The package lives under `src/cellar/` (src layout). Keep the boundaries below crisp — logic
belongs in exactly one of these places:

```
src/cellar/
├── agents/     # agent definitions and orchestration (planner, researcher, critic, ...)
├── schemas/    # pydantic models, dataclasses, and StrEnums — the shared data vocabulary
├── services/   # stateful integrations: LLM clients, external APIs, persistence
├── tools/      # discrete capabilities agents can invoke (literature search, code exec, ...)
├── utils/      # small, pure, stateless helpers with no domain state
├── prompts/    # prompt templates and prompt-construction helpers
└── config.py   # settings loading
```

Rules of thumb:

- `schemas/` holds data, never behavior with side effects. Everything crossing a module
  boundary should be a typed schema from here, not a loose `dict`.
- `services/` owns anything with I/O, network calls, or long-lived state.
- `tools/` are the things an agent decides to call; keep each tool focused and independently
  testable, returning a schema.
- `utils/` is for pure functions only. If a helper needs config, a client, or state, it is a
  service, not a util.

## Coding style

These are firm defaults. Match them unless there is a concrete reason not to.

**Types everywhere.** Annotate every function parameter, return value, and non-trivial local.
Prefer precise types over `Any`. Code should be readable as a set of typed contracts.

**Use modern native generics.** Write `list[str]`, `dict[str, float]`, `tuple[int, ...]`,
`str | None`. Do **not** import from `typing` for these (`List`, `Dict`, `Optional`, `Union`
are banned). Reach into `typing`/`collections.abc` only for things without a native form
(`Protocol`, `Callable`, `Iterable`, `TypeVar`, etc.).

**Schemas over dicts.** Model structured data as **pydantic `BaseModel`** by default;
use a `@dataclass` when you need a lightweight, dependency-free value object with no
validation. Do not pass around bare dictionaries as informal records.

**Enums, specifically StrEnum.** Represent any fixed set of string-like choices as a
`StrEnum` (Python 3.11+). Prefer `StrEnum` over string literals and over plain `Enum` so the
values stay JSON- and log-friendly. No magic strings for statuses, roles, kinds, or modes.

**Expressive names.** Variables, functions, and classes should read as plain descriptions.
`candidate_hypotheses`, not `ch`; `refine_experiment_plan`, not `proc`. The name should make
the value's role obvious without a comment.

**No comments, no docstrings.** Do not write inline comments or docstrings. Express intent
through good names, small functions, and types instead. If code needs a comment to be
understood, restructure it until it doesn't. (Linters may flag missing docstrings — that
warning is intentionally ignored for this project.)

**Small, single-purpose functions.** Prefer composing several well-named functions over one
long one. A function should do one thing its name describes.

**Prefer immutability and explicitness.** Favor returning new values over mutating arguments;
make dependencies explicit parameters rather than reaching for globals.
