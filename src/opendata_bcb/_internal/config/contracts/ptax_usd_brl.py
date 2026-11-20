"""Data contract of the PTAX USD/BRL quotes served by the BCB Olinda ``CotacaoDolarPeriodo``.

The contract was pinned against a real response (``tests/fixtures/olinda/ptax_usd_brl.json``):
a subset contract — the three selected fields are required, anything else flows through.
"""

from __future__ import annotations

from opendata_bcb._internal.utils.tabular_reader import (
    FileContract,  # noqa: TID251 -- contracts are constructed here
)


PTAX_USD_BRL = FileContract(
    "PTAX USD/BRL",
    "bcb_olinda_ptax_usd_brl",
    ("cotacaoCompra", "cotacaoVenda", "dataHoraCotacao"),
    (),
)
