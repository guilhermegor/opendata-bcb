"""Data contract of the PTAX currency list served by the Olinda ``Moedas`` resource.

Pinned against a real response (``tests/fixtures/ptax/moedas.json``): a subset contract, the
three fields the reader renames are required, anything the service adds flows through.
"""

from __future__ import annotations

from opendata_bcb._internal.utils.tabular_reader import (
    FileContract,  # noqa: TID251 -- contracts are constructed here
)


PTAX_CURRENCIES = FileContract(
    "PTAX currencies",
    "bcb_olinda_ptax_currencies",
    ("simbolo", "nomeFormatado", "tipoMoeda"),
    (),
)
