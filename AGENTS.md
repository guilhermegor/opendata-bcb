# AGENTS.md

Guidance for agents working in this repository.

## Engineering principles

Read `PRINCIPLES.md` for the single-responsibility and function-design rules this project follows.

## Shared conventions

The boundary rules, data-handling guardrails, runtime type-checking notes, naming and
file-naming conventions, tooling summary and the project-memory rule are shared by every
BlueprintX skeleton and live in `.claude/CLAUDE.md` (single source:
`templates/common/CLAUDE.md`). Read that file before editing code: only Claude Code
loads it on its own, other agents must be told to. This file keeps only what is
specific to this skeleton.

⚠️ The shared boundary rule 1 (the seam knows the vendor) has one tier-specific twist here:
a caller imports the seam **package-qualified** —
`from opendata_bcb._internal.utils.http_downloader import download_file` — never a bare
`from utils…`, which resolves only by accident of `sys.path` and breaks once the wheel is
installed.

## What this is

`opendata-bcb` is a PyPI library that reads open data published by the Banco Central do Brasil.
Its public API is the ten `read_*` functions and `__version__`; everything under
`opendata_bcb._internal` is private.

## Layout

```
src/opendata_bcb/
    __init__.py            # the public API surface (control it with __all__)
    <reader>.py            # one public module per source (banks.py, sgs.py, ptax.py, ...)
    _internal/             # PRIVATE — ships in the wheel, but not a public API
        utils/             # vendored helpers (dtypes, tabular_reader, retry/, http_downloader,
                           #   text, br_identifiers, typing/)
        config/            # ALL private structural declarations (one config/CLAUDE.md maps them)
            contracts/     # FileContract declarations (one per input source)
            # schemas/     # (opt-in) Pydantic models mirroring an external standard, or the
                           #   library's own product — the ONLY home of pydantic models
                           #   (check-layer-imports allows pydantic only in config and utils);
                           #   never re-exported: check-all-exports bans `_internal` names in __all__
tests/
    unit/  integration/  performance/
```

**Public vs private.** Consumers import `opendata_bcb`. Everything under
`opendata_bcb._internal` is vendored support code: it ships inside the wheel (so imports
resolve after `pip install`), but the leading underscore marks it off-limits — keep it out
of the public `__all__`. The internal imports are package-qualified
(`from opendata_bcb._internal.utils.dtypes import …`).

**Consumer-built schema models stay in `_internal/config/schemas/`.** When the models are the
library's product (consumers construct them), the file location is still an implementation
detail: re-export each class from the package `__all__` and let consumers write
`from opendata_bcb import X`, never the `_internal` path. Do not move them to a public
`schemas/` package. Accepted cost: the class's `__module__` (tracebacks, mkdocstrings paths,
pickles) shows the `_internal` path, so moving the file later is a pickle-compatibility change.

## Architecture

- **One public class per module/file.** The public class is named after the file
  (`user_service.py` → `UserService`). When helpers share no state and need no lifecycle,
  prefer **module-level functions** over a utility class. A private/shared base class gets
  its **own** `_`-prefixed file (`_base_reader.py`) — never share a module with a public
  class.
- **Separate I/O from logic**: pure functions in the core, side effects at the edges.
- Reach for a class only when there is **state + lifecycle**, **interface conformance**, or
  **dependency injection** — otherwise a module of functions is the right shape.
- **No redundant package-name subfolder.** When the package's whole purpose is one domain
  (e.g. `calendars`), do **not** nest a subfolder that repeats the package name
  (`src/opendata_bcb/opendata_bcb/`) — the package name already conveys the scope. Keep
  public modules **flat** at `src/opendata_bcb/` (`src/opendata_bcb/banks.py`), and put
  non-exported abstract bases / internals under `_internal/`.
- **On migration, reuse the target's own implementation.** When lifting code in from another
  repo, if this project already has an equivalent module (its own `_internal` typing engine, a
  helper), rewrite the imports to **this** project's version and discard the source's duplicate —
  never vendor a second copy (DRY).

## Conventions (inherited from `templates/python-common/`)

- **Ruff**: linter + formatter. Line-length 99, 4-space indent, double quotes, NumPy docstrings.
- **Pre-commit**: ruff, pydocstyle, codespell, commitizen, gitlint, unit + integration
  tests, coverage badge.
- **Tests**: `pytest` — `poe unit_tests`. Write
  pytest-style functions with fixtures, not `unittest.TestCase`.
- **Explicit column typing & Brazilian identifiers** — if the library touches pandas, type
  every DataFrame on load via `apply_dtypes` (`_internal.utils.dtypes`, never pandas'
  inference), route reads through `_internal.utils.tabular_reader`, and use
  `_internal.utils.br_identifiers` for CNPJ/CPF (alphanumeric-aware for the 2026 CNPJ).
- **No `.env`** — a distributable library has no runtime env to seed, so none is shipped.
- **Logging via dependency injection** — never hard-import a logging backend in a helper;
  inject a logger (stdlib default), as `_internal/utils/retry/log_emitter.py`'s `LogEmitter`
  shows; see `_internal/utils/CLAUDE.md`.
- **Every imported package is a direct dependency.** If a module `import`s a package, declare
  it in `pyproject.toml` — even when it is already installed transitively via another dep. A
  transitive presence is an accident of another package's tree and breaks silently the day that
  package drops or version-caps it. Run `poetry add <pkg>` for anything you import.

  **This is now enforced, not advised**: `bin/lint_deps.sh` runs `deptry` over `src/` in
  `poe lint`, the `lint-deps` pre-commit hook and CI. Its first run found the rule already
  broken in the tiers that ship it, which is the argument for the gate — the DDD tiers imported
  pandas in five `utils/` modules while declaring it nowhere, reaching them only through a
  business-day calendar that happens to depend on it. Two things worth knowing before working
  around it:

  - **A guarded import is still an import.** `try: import numpy / except ModuleNotFoundError:`
    degrades gracefully at runtime and changes nothing about the declaration — that pattern is
    why `numpy` went undeclared for as long as it did.
  - **Configuration lives in `pyproject.toml`'s `[tool.deptry]` block, never in a shared
    `deptry.toml`.** deptry takes its dependency list from the same file it takes its settings
    from, so `--config <other>` silently re-points it at a manifest that declares nothing.

## Releasing to PyPI

Two workflows ship under `.github/workflows/` (present only when a GitHub remote is set up):

- `release-test-pypi.yaml` — publish to **Test PyPI** first (`workflow_dispatch`).
- `release-pypi.yaml` — publish to **PyPI**, cut a GitHub release, then deploy the **versioned
  docs** with `mike deploy --update-aliases <X.Y> latest` (skipped for prereleases, so a suffixed
  version never moves `latest`).

Both validate the `version` input before anything else runs: `X.Y.Z`, optionally followed by a
PEP 440 pre/post/dev suffix (`1.2.3`, `1.2.3rc1`, `1.2.3-rc.1`, `1.2.3.post1`). A rejected value
means retyping it, not deleting a pushed tag.

**Docs are versioned via [mike](https://github.com/jimporter/mike)** and served from the
`gh-pages` branch — `docs.yml` is a strict *build check only* and never deploys. Pages must be
set to "Deploy from a branch → gh-pages" via `poe enable_pages`, which waits until the first
release creates that branch. See `docs/contributing.md`.

Both gate on the version being greater than what is already published, build with Poetry,
and publish through **OIDC trusted publishing** (`pypa/gh-action-pypi-publish`) — no token
secrets are needed. Register a **pending publisher** once per index (pypi.org and test.pypi.org):

- PyPI: workflow `release-pypi.yaml`, environment `release-pypi`.
- Test PyPI: workflow `release-test-pypi.yaml`, environment `release-test-pypi`.

The first `release-pypi.yaml` run creates the `gh-pages` branch, but `GITHUB_TOKEN` cannot set
the Pages source (it needs admin rights). The `deploy_docs` job prints the remedy in its job
summary: run `poe enable_pages` once afterwards.

## Extending the library

- Keep `src/opendata_bcb/` as the importable package root; grow the public API there.
- Add sub-packages as the project grows — keep one public module per source.
- Mirror the test folder hierarchy to match the package structure.
