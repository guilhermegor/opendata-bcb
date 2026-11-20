"""Typing and renaming of the raw PTAX currency code frame (pure transform, no I/O)."""

from __future__ import annotations

import pandas as pd

from opendata_bcb._internal.utils.typing import type_checker


_DICT_RENAME = {
    "Código": "currency_code",
    "Nome": "name",
    "Simbolo": "symbol",
    "Código País": "country_code",
    "País": "country",
    "Tipo": "currency_type",
    "Data Exclusão PTAX": "exclusion_date",
}


@type_checker
def normalise_currency_codes(df_raw: pd.DataFrame) -> pd.DataFrame:
    """Rename to English snake_case, trim the fixed-width padding and type the columns.

    The source pads text fields with trailing spaces and leaves a few legacy rows with blank
    fields; blanks become NA. Codes stay strings (the currency code is 3 digits and keeps its
    leading zeros). An empty exclusion date means the currency is still active in PTAX, which
    ``is_active`` states explicitly. The date is parsed day-first with an explicit format.

    Parameters
    ----------
    df_raw : pd.DataFrame
        The contract-validated text frame with the source's column names.

    Returns
    -------
    pd.DataFrame
        The renamed, typed frame.
    """
    df_codes = df_raw.rename(columns=_DICT_RENAME)
    for str_col in _DICT_RENAME.values():
        ser_text = df_codes[str_col].str.strip()
        df_codes[str_col] = ser_text.where(ser_text != "", pd.NA)
    df_codes["currency_code"] = df_codes["currency_code"].str.zfill(3)
    df_codes["is_active"] = df_codes["exclusion_date"].isna()
    df_codes["exclusion_date"] = pd.to_datetime(
        df_codes["exclusion_date"], format="%d/%m/%Y"
    ).dt.date
    return df_codes
