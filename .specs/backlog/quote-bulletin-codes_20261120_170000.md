# Work ledger: quote-bulletin currency codes (#10)

## Done

- [x] `read_quote_bulletin_codes`, exported from `__all__`: `code` and `name` as strings, plus
      provenance columns; daily cache and `fn_download` injection as in `read_banks`.
- [x] Source is the form named in the issue; parsed with the stdlib `html.parser` (no new
      dependency, no lxml); page decoded as ISO-8859-1.
- [x] Missing or empty `<select name="ChkMoeda">` raises `ContractError`, never an empty frame.
- [x] `config/contracts/quote_bulletins.py`, `utils/quote_bulletins_frame.py`.
- [x] Trimmed real fixture (6 of 248 options, bytes preserved); 9 offline unit tests.
- [x] Docs sections appended (reference and examples).

## Open

- [ ] Issue scope mentions `Decimal` for rates and quotes: this frame has none; that belongs
      to #11 (bulletins per currency).
