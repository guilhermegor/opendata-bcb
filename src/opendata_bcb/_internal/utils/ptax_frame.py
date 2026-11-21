"""Typing and renaming of the raw PTAX quote frame (pure transform, no I/O)."""

from __future__ import annotations

import pandas as pd

from opendata_bcb._internal.utils.typing import type_checker


_DICT_RENAME_QUOTES = {
    "cotacaoCompra": "buy_rate",
    "cotacaoVenda": "sell_rate",
    "dataHoraCotacao": "quoted_at",
}


@type_checker
def normalise_ptax_quotes(df_quotes: pd.DataFrame) -> pd.DataFrame:
    """Rename the quote columns to English snake_case and parse the quotation timestamp.

    The rates are already exact ``Decimal`` (the Olinda client parses them from the source
    text) and stay untouched; ``dataHoraCotacao`` keeps its time of day.

    Parameters
    ----------
    df_quotes : pd.DataFrame
        The contract-checked, provenance-stamped frame with the source's column names.

    Returns
    -------
    pd.DataFrame
        The renamed frame with ``quoted_at`` as ``datetime64``.
    """
    df_typed = df_quotes.rename(columns=_DICT_RENAME_QUOTES)
    df_typed["quoted_at"] = pd.to_datetime(df_typed["quoted_at"], format="ISO8601")
    return df_typed
