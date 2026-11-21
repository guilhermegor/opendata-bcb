"""Focus survey: annual market expectations per indicator, from BCB Olinda.

Reads the ``ExpectativasMercadoAnuais`` entity of the ``Expectativas`` service. Statistics
(mean, median, standard deviation, minimum, maximum) are exact :class:`decimal.Decimal`
values built from the source text, never floats; the respondent count is an int.
"""

from __future__ import annotations

from datetime import date
from pathlib import Path
import tempfile

import pandas as pd

from opendata_bcb._internal.config.contracts import CONTRACT_FOCUS_ANNUAL
from opendata_bcb._internal.olinda import fetch_frame
from opendata_bcb._internal.utils.focus_frame import type_focus_annual
from opendata_bcb._internal.utils.http_downloader import DownloadFn, download_file
from opendata_bcb._internal.utils.typing import type_checker


_STR_SERVICE = "Expectativas"
_STR_RESOURCE = "ExpectativasMercadoAnuais"


@type_checker
def _build_filter(str_indicator: str, *, dt_start: date, dt_end: date) -> str:
    """Build the ``$filter`` for one indicator over a ``Data`` range.

    Parameters
    ----------
    str_indicator : str
        Focus indicator name, e.g. ``"IPCA"``.
    dt_start : datetime.date
        First survey day, inclusive.
    dt_end : datetime.date
        Last survey day, inclusive.

    Returns
    -------
    str
        The OData filter; ``Data`` is a text field, so ISO dates compare correctly.

    Raises
    ------
    ValueError
        If ``dt_start`` is after ``dt_end``.
    """
    if dt_start > dt_end:
        raise ValueError(f"dt_start {dt_start} is after dt_end {dt_end}")
    str_name = str_indicator.replace("'", "''")
    return (
        f"Indicador eq '{str_name}' and Data ge '{dt_start:%Y-%m-%d}' "
        f"and Data le '{dt_end:%Y-%m-%d}'"
    )


@type_checker
def read_focus_annual_expectations(
    str_indicator: str,
    *,
    dt_start: date,
    dt_end: date,
    dt_reference: date | None = None,
    path_cache_dir: Path | None = None,
    bool_use_cache: bool = True,
    fn_download: DownloadFn = download_file,
) -> pd.DataFrame:
    """Read the Focus annual expectations of one indicator over a survey-date range.

    Parameters
    ----------
    str_indicator : str
        Focus indicator name as the service spells it, e.g. ``"IPCA"`` or ``"Selic"``.
    dt_start : datetime.date
        First survey day (``Data``), inclusive.
    dt_end : datetime.date
        Last survey day (``Data``), inclusive.
    dt_reference : datetime.date, optional
        The day keying the daily cache; defaults to today.
    path_cache_dir : pathlib.Path, optional
        Directory for the daily cache; defaults to a folder under the system temp directory.
    bool_use_cache : bool, optional
        ``False`` re-downloads even when today's pages are cached, by default ``True``.
    fn_download : DownloadFn, optional
        The download seam, injected so tests never touch the network.

    Returns
    -------
    pd.DataFrame
        One row per survey day and reference year: ``Indicador``, ``IndicadorDetalhe``,
        ``Data`` (date), ``DataReferencia`` (str), ``Media``, ``Mediana``, ``DesvioPadrao``,
        ``Minimo``, ``Maximo`` (all ``Decimal``), ``numeroRespondentes`` (int),
        ``baseCalculo``, then the provenance columns.

    Raises
    ------
    ValueError
        If ``dt_start`` is after ``dt_end``.
    """
    df_rows = fetch_frame(
        _STR_SERVICE,
        _STR_RESOURCE,
        cls_contract=CONTRACT_FOCUS_ANNUAL,
        path_cache_dir=path_cache_dir or Path(tempfile.gettempdir()) / "opendata-bcb-cache",
        dt_reference=dt_reference or date.today(),
        str_filter=_build_filter(str_indicator, dt_start=dt_start, dt_end=dt_end),
        bool_use_cache=bool_use_cache,
        fn_download=fn_download,
    )
    return type_focus_annual(df_rows)
