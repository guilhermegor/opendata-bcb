"""Typing and renaming of the raw PTAX per-currency quote frame (pure transform, no I/O)."""

from __future__ import annotations

import pandas as pd

from opendata_bcb._internal.utils.typing import type_checker


_DICT_RENAME_QUOTES = {
    "paridadeCompra": "buy_parity",
    "paridadeVenda": "sell_parity",
    "cotacaoCompra": "buy_rate",
    "cotacaoVenda": "sell_rate",
    "dataHoraCotacao": "quoted_at",
    "tipoBoletim": "bulletin_type",
}


@type_checker
def normalise_ptax_period_quotes(df_quotes: pd.DataFrame) -> pd.DataFrame:
    """Rename the quote columns to English snake_case and parse the quotation timestamp.

    The parities and rates are already exact ``Decimal`` (the Olinda client parses them from
    the source text) and stay untouched; ``tipoBoletim`` is kept as ``bulletin_type``.

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
