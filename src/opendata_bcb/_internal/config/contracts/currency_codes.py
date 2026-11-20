"""Data contract for the BCB PTAX currency code table (the dated ``M<yyyymmdd>.csv``).

Subset contract: the keys the reader depends on must be present; a column the source adds
later flows through untouched rather than failing the read.
"""

from __future__ import annotations

from opendata_bcb._internal.utils.tabular_reader import (
    FileContract,  # noqa: TID251 -- contracts are constructed here
)


CONTRACT_CURRENCY_CODES = FileContract(
    "BCB PTAX currency codes",
    "bcb_currency_codes",
    (
        "Código",
        "Nome",
        "Simbolo",
        "Código País",
        "País",
        "Tipo",
        "Data Exclusão PTAX",
    ),
    (),
)
