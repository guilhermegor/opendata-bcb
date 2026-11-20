# Work ledger: docs-drift prototype (#18)

## Done

- [x] `bin/check_docs_drift.py`: part 1 (symbol drift: `__all__` vs `docs/api/reference.md`, `poe <task>`
      citations vs `poe_tasks*.toml`, cited repo paths/links) and part 2 (`--diff <base> [--head <ref>]`
      against `.docs-coupling.yaml`). Advisory: not wired into pre-commit or CI.
- [x] `.docs-coupling.yaml` (5 starter rules), `tests/unit/test_check_docs_drift.py` (should-fail witnesses).
- [x] Measurements below.

## Open

- [ ] Owner decides what becomes a blocking gate (see Recommendation); the issue stays open.
- [ ] Carry the result to a BlueprintX issue.

## Method notes

- Escape implemented: a commit in `<base>..<head>` carrying `Docs: not needed because <reason>` (offline).
  Option, not built: a `docs:none` PR label read via REST in CI.
- Dunder names (`__version__`) are skipped in `__all__`. A name counts as documented when reference.md has a
  `:::` directive for it or the word inside a heading. Poe/path citations are read only from code spans and
  fenced blocks. Coupling rules are any-of: touching one listed doc satisfies the rule.
- The repo has only 3 merged PRs (#15, #17, #21) plus 2 bootstrap commits, not ~15; replayed all of them,
  plus open #19 and #20 and (by file list) open dependabot #2.
- `SECURITY.md` does not exist, so the network-code rule can only be satisfied via `docs/api/reference.md`.

## Part 1: symbol drift on origin/main (10 findings)

| # | Finding | Class | Why |
|---|---------|-------|-----|
| 1 | CONTRIBUTING.md cites `poe new_branch` | TRUE drift | no such task in `poe_tasks*.toml` or `bin/` |
| 2 | CONTRIBUTING.md cites `poe git_merge_to_main` | TRUE drift | same |
| 3 | docs/index.md "`poe vive`" | false positive | Portuguese prose ("o poe vive dentro do venv") in a code-block comment |
| 4 | CONTRIBUTING.md `docs/63-update-api-reference` | false positive | an example branch name |
| 5 | CONTRIBUTING.md link `../../issues` | false positive | GitHub-relative link, resolves on github.com only |
| 6-8 | README.md x2, docs/contributing.md `bin/corporate_ca.pem` | false positive (x3) | git-ignored, generated on demand, documented as optional |
| 9 | README.md `.venv/Scripts/poe.exe` | false positive | generated venv file |
| 10 | docs/api/reference.md `CODCOMPE/Tabela.pdf` | false positive | name of the legacy external source |

Total 10 findings: 2 true, 8 false. `__all__` check on main: 0 findings
(`main`, `read_banks` documented). Poe and symbol checks are precise on real drift; the path check is the noisy
one: 7 of 7 path findings are false positives, all fixable by skipping git-ignored/generated paths
(`git check-ignore`), `../../` links and a small ignore list.

## Part 2: coupling replay and symbol check at PR heads

| PR / commit | Source touched | Coupling fired? | Verdict |
|---|---|---|---|
| #21 bank registry (merged) | `__init__.py`, `ingestion/banks.py`, contracts | no (reference.md + examples.md touched) | true negative; no gap seen |
| #17 footers (merged) | README, docs/index, mkdocs.yml | no | true negative |
| #15 logo (merged) | README, assets | no | true negative |
| e18f7c7 versioning (bootstrap commit) | `pyproject.toml`, `poe_tasks.repo.toml` (removes `bump_version`, switches to dynamic versioning) | yes, 2 rules | likely true catch: the release mechanics changed with no docs touched (docs still cite removed offline poe tasks, see Part 1 #1-2) |
| #19 Olinda client (open) | `_internal/*`, drops example contract/port | no | true negative; no stale doc mention of `example_source`/`example_port` found |
| #20 SGS reader (open) | `__init__.py`, `ingestion/sgs.py`, reference.md | no (docs touched) | true negative for coupling |
| #2 dependabot actions bump (open) | 16 workflow files incl. `release-*.yaml` | would fire (rule `.github/workflows/release*`) | false positive; a bot commit cannot carry a `Docs:` line |

Part 1 re-run on PR heads: `origin/feat/3-olinda-client` clean; **`origin/feat/4-sgs-reader` reports
`read_sgs_series` and `read_sgs_metadata` undocumented, a false positive**: reference.md documents both in a
table row and in prose (`ingestion.sgs` section) rather than a heading or `:::` directive. This is the real
precision cost of the "heading or directive" definition of documented; widening it to "name in a backticked
table cell" fixes it at the price of a weaker oracle.

Misses: none seen on the 3 merged PRs; coupling has no way to see a README gap when `pyproject.toml` did not
change (e.g. #21 added a runtime download but README Install did not need a change).

## Recommendation (owner decides; trade-offs only)

- **Candidates to block:** the `poe <task>` existence check (2 true catches, 1 prose false positive removable by
  skipping fenced-block comments) and the `__all__`-in-reference.md check once "documented" is widened to
  table cells. Trade-off: block now and fix the one #20-shaped false positive first, or keep advisory until
  the reference.md layout is stable (it is still a template-era file).
- **Keep advisory:** the path-existence check (7/7 false positives until git-ignored and generated paths are
  excluded) and the whole coupling map (n=7 replays, one likely catch, one bot false positive; too small to
  justify a hard block).
- **Coupling map should start with:** `pyproject.toml` -> README install, `__init__.py` -> reference.md,
  `.github/workflows/release*` -> releasing doc. Drop the `poe_tasks*.toml` rule unless the poe-existence
  check covers it. `SECURITY.md` rule is dead until the file exists.
- **Escape:** the commit-message `Docs: not needed because <reason>` works offline and is auditable in
  history; the `docs:none` label is easier for bots and reviewers but needs a REST call in CI and leaves no
  trace in the commit. Bot authors (dependabot) need an exemption either way, as the ledger gate does.
