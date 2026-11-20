"""Data contract for the BCB STR participants list (the bank registry CSV).

Subset contract: the keys the reader depends on must be present; a column the source adds
later flows through untouched rather than failing the read.
"""

from __future__ import annotations

from opendata_bcb._internal.utils.tabular_reader import (
    FileContract,  # noqa: TID251 -- contracts are constructed here
)


CONTRACT_BANKS = FileContract(
    "BCB STR participants",
    "bcb_banks",
    (
        "ISPB",
        "Nome_Reduzido",
        "Número_Código",
        "Participa_da_Compe",
        "Acesso_Principal",
        "Nome_Extenso",
        "Início_da_Operação",
    ),
    (),
)
