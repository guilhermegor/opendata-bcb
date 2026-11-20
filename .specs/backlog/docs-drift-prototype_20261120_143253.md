# Work ledger: docs-drift prototype (#18)

## Done

- [x] `bin/check_docs_drift.py`: part 1 (symbol drift: `__all__` vs `docs/api/reference.md`, `poe <task>`
      citations vs `poe_tasks*.toml`, cited repo paths/links) and part 2 (`--diff <base> [--head <ref>]`
      against `.docs-coupling.yaml`). Advisory: not wired into pre-commit or CI.
- [x] `.docs-coupling.yaml` (5 starter rules), `tests/unit/test_check_docs_drift.py` (should-fail witnesses).
- [x] Measurements below (taken on the prototype as first built, kept as the record).
- [x] Owner decisions applied (see Decisions): two checks blocking in pre-commit and CI, two advisory in
      CI, the true drift fixed (CONTRIBUTING.md offline clause dropped), new should-fail witnesses.

## Open

- [ ] Carry the result to a BlueprintX issue.

## Method notes

- Escape implemented: a commit in `<base>..<head>` carrying `Docs: not needed because <reason>` (offline).
  Option, not built: a `docs:none` PR label read via REST in CI.
- Dunder names (`__version__`) are skipped in `__all__`. A name counts as documented when reference.md has a
  `:::` directive for it or the word inside a heading. Poe/path citations are read only from code spans and
  fenced blocks. Coupling rules are any-of: touching one listed doc satisfies the rule.
- The repo has only 3 merged PRs (#15, #17, #21) plus 2 bootstrap commits, not ~15; replayed all of them,
  plus open #19 and #20 and (by file list) open dependabot #2.
- Correction: `SECURITY.md` exists (the first draft of this ledger said it did not; a filtered `ls` listed
  nothing). It is a vulnerability-reporting policy with no mention of outbound requests.

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

## Decisions (owner, applied in this branch)

- **Blocking** (default mode of `bin/check_docs_drift.py`; pre-commit hook `check-docs-drift` and the
  `Run Docs-Drift Enforcement` step in `tests.yml`):
  1. `poe <task>` existence. Only commands in fenced blocks and inline code spans are read, shell `#`
     comments are dropped, prose is never read. Removes the `poe vive` false positive.
  2. `__all__` documented. A name counts when it appears anywhere in `docs/api/reference.md` as a whole
     word (heading, `:::`, table row, prose). Re-checked on `origin/feat/4-sgs-reader`: the #20 false
     positive is gone (only the CONTRIBUTING.md findings below remain there, same as on main).
- **Advisory** (CI only, always exit 0, findings printed):
  3. Cited paths exist (`--advisory`): git-ignored paths, `.venv/` and `../` links are skipped. On the
     branch it still reports `docs/63-update-api-reference` (an example branch name) and
     `CODCOMPE/Tabela.pdf` (the legacy source name): 2 false positives, down from 7.
  4. Coupling map (`--diff origin/<base> --author <login>`, PR events only). Trimmed to
     pyproject.toml -> README.md, `__init__.py` -> reference.md, `.github/workflows/release*` ->
     docs/releasing-1-0-0.md, `http_downloader.py` and `olinda.py` -> SECURITY.md. Escape: a
     `Docs: not needed because <reason>` line in any commit of the range; `dependabot[bot]` and
     `github-actions[bot]` authors are exempt.
- **True drift fixed:** CONTRIBUTING.md no longer cites `poe new_branch` / `poe git_merge_to_main`, which
  exist only in BlueprintX's offline mode; this project is online. Blocking check is green on the branch.

## Re-replay with the final design

| Case | Blocking checks | Coupling (final map) |
|---|---|---|
| #21, #17, #15 | clean | no fire |
| e18f7c7 | n/a | fires: pyproject.toml without README.md (likely true catch, as before) |
| #19 Olinda client | clean | fires: `olinda.py` changed, `SECURITY.md` untouched. SECURITY.md has no network section, so this is a review prompt rather than a missing sentence: defensible but noisy |
| #20 SGS reader | clean (false positive fixed) | no fire |
| #2 dependabot | n/a | exempt by author (the former false positive) |

## Remaining trade-offs

- The coupling map is still n=7 replays; one likely catch, one debatable hit. It stays advisory until a few
  more PRs have been measured.
- `docs/api/reference.md` accepting any whole-word mention is a weaker oracle than a heading or directive: a
  passing mention in prose satisfies it. Chosen by the owner over the heading-only form that failed on #20.
- Escape via commit line is auditable but invisible to a reviewer reading only the PR page; a `docs:none`
  label (REST read in CI) remains an option.
