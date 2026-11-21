"""Data contract of the Focus annual market expectations served by the Olinda ``Expectativas``.

Pinned against a real response (``tests/fixtures/focus/expectativas_mercado_anuais_ipca.json``):
a subset contract — the fields the reader types are required, anything the service adds flows
through.
"""

from __future__ import annotations

from opendata_bcb._internal.utils.tabular_reader import (
    FileContract,  # noqa: TID251 -- contracts are constructed here
)


CONTRACT_FOCUS_ANNUAL = FileContract(
    "Focus annual expectations",
    "bcb_olinda_focus_annual",
    (
        "Indicador",
        "Data",
        "DataReferencia",
        "Media",
        "Mediana",
        "DesvioPadrao",
        "Minimo",
        "Maximo",
        "numeroRespondentes",
    ),
    (),
)
