# Work ledger: flatten `ingestion/` (#27)

## Done

- [x] `banks`, `currency_codes`, `sgs`, `quote_bulletins` moved to `src/opendata_bcb/`;
      `ingestion/` deleted. Root imports (`from opendata_bcb import read_*`) unchanged.
- [x] Module constants made private (`_URL_BANKS`, `_URL_CURRENCY_CODES`,
      `_INT_MAX_FALLBACK_DAYS`, `_URL_QUOTE_BULLETIN_FORM`, `_ENCODING_QUOTE_BULLETIN_FORM`):
      at the package root `check-all-exports` would force them into `__all__`, and the
      docs-drift gate would then require documenting them. Owner chose private over public.
- [x] Open issue surfaces (#5–#8, #10, #11) rewritten to flat paths.

## Open

- [ ] Every new reader must land at `src/opendata_bcb/<x>.py` and keep its constants private.
