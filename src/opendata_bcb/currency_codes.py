"""PTAX currency code table: code, symbol, name, country, type and exclusion date.

The Central Bank publishes the table inside the dated closing file ``M<yyyymmdd>.csv`` — a
``;``-separated Latin-1 CSV. A day without a file answers 404, so the reader falls back to the
previous business day.
"""

from __future__ import annotations

from datetime import date
from pathlib import Path

import pandas as pd

from opendata_bcb._internal.config.contracts import CONTRACT_CURRENCY_CODES
from opendata_bcb._internal.utils.currency_codes_frame import normalise_currency_codes
from opendata_bcb._internal.utils.daily_cache import DownloadFn, download_daily, resolve_cache_dir
from opendata_bcb._internal.utils.dates import add_working_days
from opendata_bcb._internal.utils.http_downloader import download_file
from opendata_bcb._internal.utils.provenance import (
    read_artifact,
    resolve_package_version,
    stamp_provenance,
)
from opendata_bcb._internal.utils.tabular_reader import read_table
from opendata_bcb._internal.utils.typing import type_checker


_URL_CURRENCY_CODES = "https://www4.bcb.gov.br/Download/fechamento/M{dt:%Y%m%d}.csv"
_INT_MAX_FALLBACK_DAYS = 5


@type_checker
def _try_download(
    dt_day: date, *, path_dir: Path, bool_use_cache: bool, fn_download: DownloadFn
) -> tuple[Path, str] | None:
    """Fetch one day's file, or ``None`` when the source has none for that day.

    Parameters
    ----------
    dt_day : datetime.date
        The file's day.
    path_dir : pathlib.Path
        Daily cache directory.
    bool_use_cache : bool
        Whether a cached file may be served.
    fn_download : DownloadFn
        The download seam.

    Returns
    -------
    tuple of (pathlib.Path, str) or None
        The cached file and the URL it came from, or ``None`` when the source answers 404.

    Raises
    ------
    OSError
        On any other download failure (5xx, timeout, write error), which must not be mistaken
        for a missing day and silently fall back to an older file.
    """
    str_url = _URL_CURRENCY_CODES.format(dt=dt_day)
    try:
        path_csv = download_daily(
            str_url,
            path_cache_dir=path_dir,
            str_key="bcb-currency-codes",
            dt_reference=dt_day,
            str_suffix=".csv",
            bool_use_cache=bool_use_cache,
            fn_download=fn_download,
        )
    except FileNotFoundError:
        return None
    return path_csv, str_url


@type_checker
def _candidate_days(dt_day: date) -> list[date]:
    """List the reference day and the business days before it, newest first.

    Parameters
    ----------
    dt_day : datetime.date
        The reference day.

    Returns
    -------
    list of datetime.date
        ``dt_day`` followed by ``_INT_MAX_FALLBACK_DAYS`` earlier business days.
    """
    list_days = [dt_day]
    for _ in range(_INT_MAX_FALLBACK_DAYS):
        list_days.append(add_working_days(list_days[-1], int_days=-1))
    return list_days


@type_checker
def _locate_file(
    dt_day: date, *, path_dir: Path, bool_use_cache: bool, fn_download: DownloadFn
) -> tuple[Path, str]:
    """Return the first candidate day's file the source actually has.

    Parameters
    ----------
    dt_day : datetime.date
        The reference day.
    path_dir : pathlib.Path
        Daily cache directory.
    bool_use_cache : bool
        Whether a cached file may be served.
    fn_download : DownloadFn
        The download seam.

    Returns
    -------
    tuple of (pathlib.Path, str)
        The cached file and the URL it came from.

    Raises
    ------
    FileNotFoundError
        When no candidate day has a file.
    """
    tuple_found = next(
        filter(
            None,
            (
                _try_download(
                    dt_try,
                    path_dir=path_dir,
                    bool_use_cache=bool_use_cache,
                    fn_download=fn_download,
                )
                for dt_try in _candidate_days(dt_day)
            ),
        ),
        None,
    )
    if tuple_found is None:
        raise FileNotFoundError(f"no PTAX currency code file from {dt_day} backwards")
    return tuple_found


@type_checker
def read_currency_codes(
    *,
    dt_reference: date | None = None,
    path_cache_dir: Path | None = None,
    bool_use_cache: bool = True,
    fn_download: DownloadFn = download_file,
) -> pd.DataFrame:
    """Read the PTAX currency code table.

    Parameters
    ----------
    dt_reference : datetime.date, optional
        The file day, defaulting to today. When the source has no file for it, the previous
        business day is tried, up to ``_INT_MAX_FALLBACK_DAYS`` times.
    path_cache_dir : pathlib.Path, optional
        Directory for the daily cache; defaults to a folder under the system temp directory.
    bool_use_cache : bool, optional
        ``False`` re-downloads even when the day's file is cached, by default ``True``.
    fn_download : DownloadFn, optional
        The download seam, injected so tests never touch the network.

    Returns
    -------
    pd.DataFrame
        One row per currency/country pair: ``currency_code`` (3-digit string), ``name``,
        ``symbol``, ``country_code`` (string), ``country``, ``currency_type`` (``A`` or
        ``B``), ``exclusion_date`` (date, NA while active), ``is_active`` (bool), then the
        provenance columns.

    Raises
    ------
    FileNotFoundError
        When no file exists for the reference day nor the fallback business days.
    """
    path_dir = resolve_cache_dir(path_cache_dir)
    path_csv, str_url = _locate_file(
        dt_reference or date.today(),
        path_dir=path_dir,
        bool_use_cache=bool_use_cache,
        fn_download=fn_download,
    )
    bytes_csv, str_hash = read_artifact(path_csv)
    df_raw = read_table(
        path_csv,
        str_sheet="",
        dict_dtypes=dict.fromkeys(CONTRACT_CURRENCY_CODES.tuple_required, "str"),
        cls_contract=CONTRACT_CURRENCY_CODES,
        str_encoding="latin-1",
        bytes_content=bytes_csv,
    )
    return stamp_provenance(
        normalise_currency_codes(df_raw),
        str_url=str_url,
        cls_contract=CONTRACT_CURRENCY_CODES,
        str_content_hash=str_hash,
        str_package_version=resolve_package_version("opendata-bcb"),
    )
