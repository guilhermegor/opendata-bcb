"""Data contracts for the project's input sources (config layer).

A contract is **declarative configuration** of a source's expected shape — which columns it
must carry — *not* data access. Convention: **one file per source** under this package, each
defining a single ``FileContract`` instance; this aggregator re-exports them (plus the
machinery from ``utils.tabular_reader``) so callers import from one place:
``from opendata_bcb._internal.config.contracts import PTAX_USD_BRL, find_contract_problems``.
"""

from __future__ import annotations

from opendata_bcb._internal.config.contracts.banks import CONTRACT_BANKS
from opendata_bcb._internal.config.contracts.currency_codes import CONTRACT_CURRENCY_CODES
from opendata_bcb._internal.config.contracts.focus import CONTRACT_FOCUS_ANNUAL
from opendata_bcb._internal.config.contracts.ptax_currencies import PTAX_CURRENCIES
from opendata_bcb._internal.config.contracts.ptax_usd_brl import PTAX_USD_BRL
from opendata_bcb._internal.config.contracts.quote_bulletins import (
    CONTRACT_QUOTE_BULLETIN_CODES,
    CONTRACT_QUOTE_BULLETINS,
)
from opendata_bcb._internal.utils.tabular_reader import (
    ContractError,
    FileContract,  # noqa: TID251 -- contracts are constructed here
    find_contract_problems,
    find_file_problems,
)


__all__ = [
    "CONTRACT_BANKS",
    "CONTRACT_CURRENCY_CODES",
    "CONTRACT_FOCUS_ANNUAL",
    "CONTRACT_QUOTE_BULLETIN_CODES",
    "CONTRACT_QUOTE_BULLETINS",
    "ContractError",
    "FileContract",
    "find_contract_problems",
    "find_file_problems",
    "PTAX_CURRENCIES",
    "PTAX_USD_BRL",
]
