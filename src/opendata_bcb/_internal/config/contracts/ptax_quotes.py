"""Data contract of the PTAX per-currency quotes served by the BCB Olinda ``CotacaoMoedaPeriodo``.

The contract was pinned against a real response
(``tests/fixtures/ptax/cotacao_moeda_periodo.json``): a subset contract — the six selected
fields are required, anything else flows through.
"""

from __future__ import annotations

from opendata_bcb._internal.utils.tabular_reader import (
    FileContract,  # noqa: TID251 -- contracts are constructed here
)


PTAX_QUOTES = FileContract(
    "PTAX quotes",
    "bcb_olinda_ptax_quotes",
    (
        "paridadeCompra",
        "paridadeVenda",
        "cotacaoCompra",
        "cotacaoVenda",
        "dataHoraCotacao",
        "tipoBoletim",
    ),
    (),
)
