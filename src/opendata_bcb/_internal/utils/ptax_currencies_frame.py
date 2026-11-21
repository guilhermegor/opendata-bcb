"""Renaming of the raw PTAX currency frame (pure transform, no I/O)."""

from __future__ import annotations

import pandas as pd

from opendata_bcb._internal.utils.typing import type_checker


_DICT_RENAME_CURRENCIES = {
    "simbolo": "symbol",
    "nomeFormatado": "name",
    "tipoMoeda": "currency_type",
}


@type_checker
def normalise_ptax_currencies(df_currencies: pd.DataFrame) -> pd.DataFrame:
    """Rename the currency columns to English snake_case.

    Parameters
    ----------
    df_currencies : pd.DataFrame
        The contract-checked, provenance-stamped frame with the source's column names.

    Returns
    -------
    pd.DataFrame
        The renamed frame.
    """
    return df_currencies.rename(columns=_DICT_RENAME_CURRENCIES)
