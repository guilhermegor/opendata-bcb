# Work ledger: read_banks covers STR participants only (#24)

## Why

`read_banks` reads `ParticipantesSTR.csv`: the participants of the STR (direct or indirect),
refreshed daily. The docs read as "every bank in Brazil"; PIX-only institutions are absent.

## Done

- [x] `read_banks` docstring states the STR coverage, the source URL and the daily refresh.
- [x] `docs/api/reference.md` and `docs/examples.md` carry the same note in pt-BR.
- [x] stpstone parity break noted: ISPB now available, 2009 `CODCOMPE/Tabela.pdf` dropped.
- [x] README wording aligned.

Completed — kept as a record.
