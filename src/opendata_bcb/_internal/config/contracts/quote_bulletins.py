"""Data contract for the quote-bulletin currency codes (the form's ``<select>`` options).

The source is an HTML form, not a table: the contract names the two columns the parser
yields from the options (``value`` attribute and label).
"""

from __future__ import annotations

from opendata_bcb._internal.utils.tabular_reader import (
    FileContract,  # noqa: TID251 -- contracts are constructed here
)


CONTRACT_QUOTE_BULLETIN_CODES = FileContract(
    "BCB quote-bulletin currency codes",
    "bcb_quote_bulletin_codes",
    ("code", "name"),
    (),
)


CONTRACT_QUOTE_BULLETINS = FileContract(
    "BCB quote bulletins (closing quotes of one currency over a period)",
    "bcb_quote_bulletins",
    (
        "date",
        "currency_code",
        "bulletin_type",
        "currency_symbol",
        "buy_rate",
        "sell_rate",
        "buy_parity",
        "sell_parity",
    ),
    (),
)
