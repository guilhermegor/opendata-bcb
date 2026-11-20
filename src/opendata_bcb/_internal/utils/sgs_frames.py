"""Frame builders for the SGS reader: the pandas seam, so the public layer holds none.

The public ``ingestion.sgs`` module may only name pandas in annotations; every call that
builds or types a frame lives here.
"""

from __future__ import annotations

import pandas as pd

from opendata_bcb._internal.utils.dtypes import apply_dtypes


try:
    from opendata_bcb._internal.utils.typing import type_checker
except ModuleNotFoundError:  # pragma: no cover
    from opendata_bcb._internal.utils.typing import type_checker


@type_checker
def build_values_frame(list_records: list[dict[str, str]]) -> pd.DataFrame:
    """Type the raw SGS ``data``/``valor`` records.

    Parameters
    ----------
    list_records : list of dict of {str: str}
        Records as served: ``data`` is ``dd/mm/yyyy``, ``valor`` a ``.``-decimal string.

    Returns
    -------
    pd.DataFrame
        ``data`` as ``date`` and ``valor`` as exact ``Decimal``. The date format is explicit:
        letting pandas guess would read ``03/11/2026`` as 11 March.
    """
    df_raw = pd.DataFrame(list_records, columns=["data", "valor"])
    df_raw["data"] = pd.to_datetime(df_raw["data"], format="%d/%m/%Y")
    return apply_dtypes(
        df_raw.astype({"valor": "string"}),
        list_date_cols=["data"],
        list_decimal_cols=["valor"],
    )


@type_checker
def build_metadata_frame(dict_meta: dict[str, str]) -> pd.DataFrame:
    """Build the one-row, text-typed metadata frame.

    Parameters
    ----------
    dict_meta : dict of {str: str}
        Metadata fields keyed by column name.

    Returns
    -------
    pd.DataFrame
        One row, every column the nullable ``string`` dtype.
    """
    return apply_dtypes(pd.DataFrame([dict_meta]), dict_dtypes=dict.fromkeys(dict_meta, "str"))
