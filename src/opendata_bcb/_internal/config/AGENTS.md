# AGENTS.md — `_internal/config/`

`config/` is the home of **every private structural declaration** — the shapes and
interfaces the library conforms to. It holds the sub-packages below, all under `_internal/`
(they ship inside the wheel but are **not part of the public API** — consumers import the
library's core, never `_internal`):

| Sub-package | Declares | Ships |
|-------------|----------|-------|
| `contracts/` | `FileContract` — the columns an input file must carry | always (drop if the library never reads tabular inputs) |
| `schemas/` | direction-neutral Pydantic models, one per external standard | **opt-in** — only when the models are the library's product |

The organising split is **declaration vs machinery**: `config/` answers "*what shape /
interface must this conform to?*"; `_internal/utils/` answers "*how is it done?*" (the engines:
`tabular_reader`, `dtypes`, `typing/`).

⚠️ `schemas/` is an **opt-in tier** — a single-purpose library should not carry it unless its
product is the models themselves. A behavioural `ports/` ABC would also live here, but this
library has none (an interface with one implementation is over-abstraction).

## The `contracts/` sub-package

A `FileContract` declares the shape an input file (or SQL result) must have: which columns
must be present (`tuple_required`) and which must hold at least one valid CNPJ
(`tuple_cnpj_cols`). It is a **declaration**, not a validator — the validation engine lives
in `_internal/utils/tabular_reader.py` (`read_table` / `read_query` raise `ContractError`
on a violation before types are applied).

- **One contract per file** (`cadastro.py`, `orders.py`, …): a module docstring plus a
  single `FileContract` constant. New input → new file.
- `contracts/__init__.py` re-exports every contract **and** the machinery
  (`FileContract`, `find_file_problems` from `_internal.utils.tabular_reader`), so callers
  use one import: `from <pkg>._internal.config.contracts import PTAX_USD_BRL`.
- A contract that constrains nothing is still explicit: `FileContract(name, key, (), ())`.
- **`contracts/` is the ONLY place a `FileContract` is constructed** — statically enforced
  by ruff (`TID251`). Loaders import the instances; they never build one inline.

`PTAX_USD_BRL` (`ptax_usd_brl.py`) is the first real contract — copy it per new source.

## `schemas/` vs `contracts/` — the boundary people get wrong

If you add `schemas/` (opt-in), keep the distinction sharp: a **schema** is a Pydantic model
that mirrors an external **standard** (e.g. the submission XML your library emits) — **schema ↔
structured document**. A **`FileContract`** describes a flat **tabular dump** an ingestion
reader consumes (an open-data CSV of the *same* standard) — **`FileContract` ↔ flat table**. So a
reader that consumes a *different artifact* of a standard your schema already models declares its
**own `FileContract`**; it does **not** reuse the schema. Same domain, two artifacts, two
declarations — both living here under `config/`.

## Consumer-built models still live in `schemas/`

When consumers **construct** the models (the library's product is the schema), they stay in
`_internal/config/schemas/`; do not promote them to a public `schemas/` package. Re-export each
class from the package's top-level `__all__`: consumers only ever write
`from <pkg> import X`, so the file location is an implementation detail. Accepted cost: the
class's `__module__` (tracebacks, mkdocstrings paths, pickles) shows the `_internal` path, so
moving the file later is a pickle-compatibility change.
