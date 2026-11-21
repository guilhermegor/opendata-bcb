"""Read Banco Central do Brasil SGS time series.

The SGS JSON endpoint caps a request window (10 years for daily series), so a long range is
split into windows and concatenated. ``valor`` arrives as a ``.``-decimal string and is parsed
to an exact :class:`decimal.Decimal`, never a float.
"""

from __future__ import annotations

from datetime import date, timedelta
import json
from pathlib import Path
from typing import TYPE_CHECKING

import pandas as pd

from opendata_bcb._internal.utils.daily_cache import download_daily, resolve_cache_dir
from opendata_bcb._internal.utils.http_downloader import DownloadFn, download_file
from opendata_bcb._internal.utils.provenance import (
    read_artifact,
    resolve_package_version,
    stamp_provenance,
)
from opendata_bcb._internal.utils.sgs_frames import build_metadata_frame, build_values_frame
from opendata_bcb._internal.utils.tabular_reader import (
    FileContract,  # noqa: TID251 -- contracts are constructed here
)


if TYPE_CHECKING:
    from typing import TypeVar

    _F = TypeVar("_F")

    def type_checker(fn: _F) -> _F:
        """Type-only stub — see src/utils/CLAUDE.md."""
else:
    try:
        from opendata_bcb._internal.utils.typing import type_checker
    except ModuleNotFoundError:
        from opendata_bcb._internal.utils.typing import type_checker


_URL_VALUES = (
    "https://api.bcb.gov.br/dados/serie/bcdata.sgs.{code}/dados"
    "?formato=json&dataInicial={start}&dataFinal={end}"
)
_URL_METADATA = (
    "https://www3.bcb.gov.br/wssgs/services/FachadaWSSGS?method=getUltimoValorXML&in0={code}"
)
_CONTRACT_METADATA = FileContract(
    "SGS metadata", "sgs_metadata", ("code", "name", "periodicity", "unit"), ()
)
_DAYS_PER_WINDOW = 3650
_CONTRACT_VALUES = FileContract("SGS values", "sgs_values", ("data", "valor"), ())


@type_checker
def _require_ordered(dt_start: date, *, dt_end: date) -> None:
    """Reject a range whose start is after its end.

    Parameters
    ----------
    dt_start : datetime.date
        First day requested.
    dt_end : datetime.date
        Last day requested.

    Returns
    -------
    None

    Raises
    ------
    ValueError
        If ``dt_start`` is after ``dt_end``.
    """
    if dt_start > dt_end:
        raise ValueError(f"dt_start {dt_start} is after dt_end {dt_end}")


@type_checker
def _split_windows(dt_start: date, *, dt_end: date) -> list[tuple[date, date]]:
    """Split ``[dt_start, dt_end]`` into consecutive windows the SGS API accepts.

    Parameters
    ----------
    dt_start : datetime.date
        First day requested.
    dt_end : datetime.date
        Last day requested (inclusive).

    Returns
    -------
    list of tuple of datetime.date
        Non-overlapping ``(start, end)`` windows of at most 10 years.
    """
    _require_ordered(dt_start, dt_end=dt_end)
    return [
        (
            dt_start + timedelta(days=int_offset),
            min(dt_start + timedelta(days=int_offset + _DAYS_PER_WINDOW - 1), dt_end),
        )
        for int_offset in range(0, (dt_end - dt_start).days + 1, _DAYS_PER_WINDOW)
    ]


@type_checker
def read_sgs_series(
    int_code: int,
    *,
    dt_start: date,
    dt_end: date,
    dt_reference: date | None = None,
    path_cache_dir: Path | None = None,
    bool_use_cache: bool = True,
    fn_download: DownloadFn = download_file,
) -> pd.DataFrame:
    """Read one SGS series for a date range.

    Each window is cached per reference day, so a BCB revision of past values is picked up
    once ``dt_reference`` changes: the next day under the default (today). A caller pinning
    the same ``dt_reference`` keeps getting the cached copy.

    Parameters
    ----------
    int_code : int
        SGS series code, e.g. ``1`` for the USD sell rate.
    dt_start : datetime.date
        First day requested.
    dt_end : datetime.date
        Last day requested (inclusive); ranges over 10 years are fetched in windows.
    dt_reference : datetime.date, optional
        Cache key day, defaulting to today.
    path_cache_dir : pathlib.Path, optional
        Directory of the daily cache; defaults to a folder under the system temp directory.
    bool_use_cache : bool, optional
        ``False`` re-downloads even when the day's file is cached, by default ``True``.
    fn_download : DownloadFn, optional
        Download seam, injected by tests.

    Returns
    -------
    pd.DataFrame
        Columns ``data`` (``date``) and ``valor`` (``Decimal``), plus provenance columns.
    """
    list_records: list[dict[str, str]] = []
    list_hashes: list[str] = []
    path_dir = resolve_cache_dir(path_cache_dir)
    dt_day = dt_reference or date.today()
    for dt_win_start, dt_win_end in _split_windows(dt_start, dt_end=dt_end):
        str_url = _URL_VALUES.format(
            code=int_code, start=f"{dt_win_start:%d/%m/%Y}", end=f"{dt_win_end:%d/%m/%Y}"
        )
        path_raw = download_daily(
            str_url,
            path_cache_dir=path_dir,
            str_key=f"sgs-{int_code}-{dt_win_start:%Y%m%d}-{dt_win_end:%Y%m%d}",
            dt_reference=dt_day,
            str_suffix=".json",
            bool_use_cache=bool_use_cache,
            fn_download=fn_download,
        )
        bytes_raw, str_hash = read_artifact(path_raw)
        list_hashes.append(str_hash)
        list_records.extend(json.loads(bytes_raw.decode("utf-8")))
    df_typed = build_values_frame(list_records)
    return stamp_provenance(
        df_typed,
        str_url=_URL_VALUES.format(
            code=int_code, start=f"{dt_start:%d/%m/%Y}", end=f"{dt_end:%d/%m/%Y}"
        ),
        cls_contract=_CONTRACT_VALUES,
        str_content_hash=";".join(list_hashes),
        str_package_version=resolve_package_version("opendata-bcb"),
    )


@type_checker
def read_sgs_metadata(
    int_code: int,
    *,
    dt_reference: date | None = None,
    path_cache_dir: Path | None = None,
    bool_use_cache: bool = True,
    fn_download: DownloadFn = download_file,
) -> pd.DataFrame:
    """Read the descriptive metadata of one SGS series.

    The source is the SGS WebService (``getUltimoValorXML``), which carries the series name,
    periodicity and unit. It does not expose the series start date. The metadata is stable
    within a day, so it is cached per reference day.

    Parameters
    ----------
    int_code : int
        SGS series code, e.g. ``433`` for the IPCA.
    dt_reference : datetime.date, optional
        Cache key day, defaulting to today.
    path_cache_dir : pathlib.Path, optional
        Directory of the daily cache; defaults to a folder under the system temp directory.
    bool_use_cache : bool, optional
        ``False`` re-downloads even when the day's file is cached, by default ``True``.
    fn_download : DownloadFn, optional
        Download seam, injected by tests.

    Returns
    -------
    pd.DataFrame
        One row: ``code`` (int), ``name``, ``periodicity`` (source letter, e.g. ``M``) and
        ``unit``, plus provenance columns.
    """
    str_url = _URL_METADATA.format(code=int_code)
    path_raw = download_daily(
        str_url,
        path_cache_dir=resolve_cache_dir(path_cache_dir),
        str_key=f"sgs-metadata-{int_code}",
        dt_reference=dt_reference or date.today(),
        str_suffix=".xml",
        bool_use_cache=bool_use_cache,
        fn_download=fn_download,
    )
    bytes_raw, str_hash = read_artifact(path_raw)
    return stamp_provenance(
        build_metadata_frame(bytes_raw),
        str_url=str_url,
        cls_contract=_CONTRACT_METADATA,
        str_content_hash=str_hash,
        str_package_version=resolve_package_version("opendata-bcb"),
    )
