# PTAX currency codes (#9)

- [x] `read_currency_codes` reads the dated M<yyyymmdd>.csv (latin-1, `;`)
- [x] Codes stay strings; empty exclusion date means active (`is_active`)
- [x] Fallback to the previous business day on a missing file
- [x] Provenance columns and daily cache
- [x] Offline tests on a trimmed real fixture
- [x] Docs: reference and example (pt-BR)
- [ ] Rates/quotes as `Decimal`: not applicable to this table (belongs to #10)
- [x] README: readers listed in Funcionalidades (merge pass)
- [x] Fall back only on a 404; any other download failure raises (CodeRabbit review)
