"""Build a DataFrame from parsed JSON records (the one place a reader's rows become a frame)."""

from __future__ import annotations

import pandas as pd

from opendata_bcb._internal.utils.typing import type_checker


@type_checker
def frame_from_records(list_records: list[dict[str, object]]) -> pd.DataFrame:
    """Return a frame with one row per record and one column per key.

    Cells keep the Python objects the parser produced (e.g. exact ``Decimal`` values); no
    dtype inference runs over them.

    Parameters
    ----------
    list_records : list of dict
        Parsed rows; may be empty.

    Returns
    -------
    pd.DataFrame
        The frame (no columns when ``list_records`` is empty).
    """
    return pd.DataFrame(list_records, dtype=object)
