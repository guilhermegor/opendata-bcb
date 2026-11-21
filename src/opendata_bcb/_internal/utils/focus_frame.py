"""Typing of the raw Focus annual expectations frame (pure transform, no I/O)."""

from __future__ import annotations

import pandas as pd

from opendata_bcb._internal.utils.dtypes import apply_dtypes
from opendata_bcb._internal.utils.typing import type_checker


_LIST_STATISTICS = ["Media", "Mediana", "DesvioPadrao", "Minimo", "Maximo"]


@type_checker
def type_focus_annual(df_raw: pd.DataFrame) -> pd.DataFrame:
    """Type the statistics as exact ``Decimal``, the respondent count as int, ``Data`` as date.

    The Olinda client already parses numbers into ``Decimal`` from the source text; they are
    routed through ``string`` here so a value the service serves as a bare integer (``4``)
    also lands as an exact ``Decimal`` and never as a float.

    Parameters
    ----------
    df_raw : pd.DataFrame
        The contract-checked, provenance-stamped rows as served.

    Returns
    -------
    pd.DataFrame
        The typed frame; ``DataReferencia`` stays text (a year, or a ``1/2027``-style period).
    """
    df_text = df_raw.astype(dict.fromkeys(_LIST_STATISTICS, "string"))
    return apply_dtypes(
        df_text,
        dict_dtypes={"numeroRespondentes": "int64"},
        list_date_cols=["Data"],
        list_decimal_cols=_LIST_STATISTICS,
    )
