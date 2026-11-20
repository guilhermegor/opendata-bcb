"""Typing and renaming of the raw STR participants frame (pure transform, no I/O)."""

from __future__ import annotations

import pandas as pd

from opendata_bcb._internal.utils.typing import type_checker


_DICT_RENAME = {
    "ISPB": "ispb",
    "Nome_Reduzido": "short_name",
    "Número_Código": "compe_code",
    "Participa_da_Compe": "participates_in_compe",
    "Acesso_Principal": "main_access",
    "Nome_Extenso": "full_name",
    "Início_da_Operação": "operation_start",
}


@type_checker
def normalise_banks(df_raw: pd.DataFrame) -> pd.DataFrame:
    """Rename to English snake_case and type the codes, flag and date.

    The COMPE code is zero-padded to 3 digits (the source drops leading zeros on some rows
    and writes ``n/a`` where none applies, which becomes NA). The date is parsed day-first
    with an explicit format: a bare ``to_datetime`` would read ``04/05/2002`` month-first.

    Parameters
    ----------
    df_raw : pd.DataFrame
        The contract-validated text frame with the source's column names.

    Returns
    -------
    pd.DataFrame
        The renamed, typed frame.
    """
    df_banks = df_raw.rename(columns=_DICT_RENAME)
    ser_code = df_banks["compe_code"].str.strip()
    df_banks["compe_code"] = ser_code.where(ser_code.str.isdigit(), pd.NA).str.zfill(3)
    df_banks["participates_in_compe"] = df_banks["participates_in_compe"].str.strip() == "Sim"
    df_banks["operation_start"] = pd.to_datetime(
        df_banks["operation_start"], format="%d/%m/%Y"
    ).dt.date
    return df_banks
