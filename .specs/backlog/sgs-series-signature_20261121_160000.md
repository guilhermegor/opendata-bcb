# Work ledger: align read_sgs_series with the other readers (#40)

## Why

The 1.x API guarantee freezes keyword names. `read_sgs_series` was the one reader with no
`dt_reference` and a required `path_cache_dir`, and it keyed its cache on each window's end
date, so a past window never picked up a BCB revision.

## Done

- [x] `dt_reference` and `path_cache_dir` are optional, with the same defaults as every reader.
- [x] Cache key carries the window end; the cache day is the reference day.
- [x] Tests: default dir, same-day hit, next-day refetch, other end date misses; mutation-checked.
- [x] `docs/api/reference.md` and `docs/examples.md` follow the new signature.

Completed — kept as a record.
