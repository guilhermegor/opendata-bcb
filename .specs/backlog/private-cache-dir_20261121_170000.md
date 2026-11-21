# Work ledger: per-user cache directory, refused when others can write it (#42)

## Why

Every reader defaulted its cache to a fixed path under the shared temp directory. Another
account could create it first and plant files under the predictable cache names, which a read
served as hits with a valid provenance stamp.

## Done

- [x] `daily_cache.resolve_cache_dir` is the one default: `$XDG_CACHE_HOME/opendata-bcb`, else
      `~/.cache/opendata-bcb`; the nine inline copies in the readers are gone.
- [x] `download_daily` creates the directory `0o700` and refuses one owned by another uid or
      writable by group/other.
- [x] A symlinked cache entry is a miss.
- [x] `tests/unit/test_daily_cache.py`; each refusal mutation-checked.
- [x] `docs/api/reference.md` documents the location.

Completed — kept as a record.
