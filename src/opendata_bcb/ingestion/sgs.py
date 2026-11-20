"""Read Banco Central do Brasil SGS time series and their metadata.

The SGS JSON endpoint caps a request window (10 years for daily series), so a long range is
split into windows and concatenated. ``valor`` arrives as a ``.``-decimal string and is parsed
to an exact :class:`decimal.Decimal`, never a float.
"""

from __future__ import annotations

from datetime import date, timedelta
from html.parser import HTMLParser
import json
from pathlib import Path
from typing import TYPE_CHECKING

import pandas as pd

from opendata_bcb._internal.utils.daily_cache import download_daily
from opendata_bcb._internal.utils.http_downloader import DownloadFn, download_file
from opendata_bcb._internal.utils.provenance import (
    hash_artifact,
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
    "https://www3.bcb.gov.br/sgspub/consultarmetadados/consultarMetadadosSeries.do"
    "?method=consultarMetadadosSeriesInternet&hdOidSerieSelecionada={code}"
)
_DAYS_PER_WINDOW = 3650
_CELLS_MIN = 4
_CONTRACT_VALUES = FileContract("SGS values", "sgs_values", ("data", "valor"), ())
_CONTRACT_METADATA = FileContract("SGS metadata", "sgs_metadata", (), ())
_METADATA_CELLS = (
    ("Full name", "full_name", 1),
    ("Full name", "short_name", 3),
    ("Periodicity", "periodicity", 3),
    ("Unit", "unit", 3),
    ("Start date", "start_date", 1),
)


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
    path_cache_dir: Path,
    fn_download: DownloadFn = download_file,
    bool_use_cache: bool = True,
) -> pd.DataFrame:
    """Read one SGS series for a date range.

    Parameters
    ----------
    int_code : int
        SGS series code, e.g. ``1`` for the USD sell rate.
    dt_start : datetime.date
        First day requested.
    dt_end : datetime.date
        Last day requested (inclusive); ranges over 10 years are fetched in windows.
    path_cache_dir : pathlib.Path
        Directory of the daily on-disk cache.
    fn_download : DownloadFn, optional
        Download seam, injected by tests.
    bool_use_cache : bool, optional
        Whether to read a same-day cached window, by default ``True``.

    Returns
    -------
    pd.DataFrame
        Columns ``data`` (``date``) and ``valor`` (``Decimal``), plus provenance columns.
    """
    list_records: list[dict[str, str]] = []
    list_hashes: list[str] = []
    for dt_win_start, dt_win_end in _split_windows(dt_start, dt_end=dt_end):
        str_url = _URL_VALUES.format(
            code=int_code, start=f"{dt_win_start:%d/%m/%Y}", end=f"{dt_win_end:%d/%m/%Y}"
        )
        path_raw = download_daily(
            str_url,
            path_cache_dir=path_cache_dir,
            str_key=f"sgs-{int_code}-{dt_win_start:%Y%m%d}",
            dt_reference=dt_win_end,
            str_suffix=".json",
            bool_use_cache=bool_use_cache,
            fn_download=fn_download,
        )
        list_hashes.append(hash_artifact(path_raw))
        list_records.extend(json.loads(path_raw.read_text(encoding="utf-8")))
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


class _TableRows(HTMLParser):
    """Collect the text of every ``td`` cell, row by row."""

    def __init__(self) -> None:
        """Start with no rows."""
        super().__init__()
        self.list_rows: list[list[str]] = []
        self._bool_in_cell = False
        self._dict_openers = {"tr": self._open_row, "td": self._open_cell}

    def _open_row(self) -> None:
        """Start a new row."""
        self.list_rows.append([])

    def _open_cell(self) -> None:
        """Start a new cell in the current row, ignoring a cell outside any row."""
        if not self.list_rows:
            return
        self.list_rows[-1].append("")
        self._bool_in_cell = True

    def handle_starttag(  # noqa: PLR0917 -- overrides the HTMLParser signature
        self, tag: str, attrs: list[tuple[str, str | None]]
    ) -> None:
        """Dispatch a row or cell opening."""
        self._dict_openers.get(tag, bool)()

    def handle_endtag(self, tag: str) -> None:
        """Close a cell."""
        self._bool_in_cell = self._bool_in_cell and tag != "td"

    def handle_data(self, data: str) -> None:
        """Append text to the open cell."""
        if self._bool_in_cell:
            self.list_rows[-1][-1] += data.strip()


@type_checker
def _index_rows_by_label(list_rows: list[list[str]]) -> dict[str, tuple[str, ...]]:
    """Index table rows (padded to four cells) by their first and third cell text.

    Parameters
    ----------
    list_rows : list of list of str
        Cell texts per row.

    Returns
    -------
    dict of {str: tuple of str}
        Each label cell maps to its whole row.
    """
    return {
        str_label: list_padded
        for list_padded in ((*list_cells, "", "", "", "")[:_CELLS_MIN] for list_cells in list_rows)
        for str_label in (list_padded[0], list_padded[2])
    }


@type_checker
def parse_sgs_metadata(str_html: str) -> dict[str, str]:
    """Extract the basic series metadata from the SGS metadata page HTML.

    Parameters
    ----------
    str_html : str
        HTML of the page's basic-data table.

    Returns
    -------
    dict of {str: str}
        Keys ``full_name``, ``short_name``, ``periodicity``, ``unit``, ``start_date``;
        a field absent from the page is an empty string.
    """
    cls_parser = _TableRows()
    cls_parser.feed(str_html)
    dict_by_label = _index_rows_by_label(cls_parser.list_rows)
    return {
        str_column: dict_by_label.get(str_label, ("", "", "", ""))[int_cell]
        for str_label, str_column, int_cell in _METADATA_CELLS
    }


@type_checker
def read_sgs_metadata(
    int_code: int,
    *,
    dt_reference: date,
    path_cache_dir: Path,
    fn_download: DownloadFn = download_file,
    bool_use_cache: bool = True,
) -> pd.DataFrame:
    """Read the metadata of one SGS series.

    Parameters
    ----------
    int_code : int
        SGS series code.
    dt_reference : datetime.date
        Reference day keying the daily cache.
    path_cache_dir : pathlib.Path
        Directory of the daily on-disk cache.
    fn_download : DownloadFn, optional
        Download seam, injected by tests.
    bool_use_cache : bool, optional
        Whether to read a same-day cached page, by default ``True``.

    Returns
    -------
    pd.DataFrame
        One row with ``full_name``, ``short_name``, ``periodicity``, ``unit`` and
        ``start_date`` (text), plus provenance columns.
    """
    str_url = _URL_METADATA.format(code=int_code)
    path_raw = download_daily(
        str_url,
        path_cache_dir=path_cache_dir,
        str_key=f"sgs-meta-{int_code}",
        dt_reference=dt_reference,
        str_suffix=".html",
        bool_use_cache=bool_use_cache,
        fn_download=fn_download,
    )
    dict_meta = parse_sgs_metadata(path_raw.read_text(encoding="utf-8", errors="replace"))
    df_meta = build_metadata_frame(dict_meta)
    return stamp_provenance(
        df_meta,
        str_url=str_url,
        cls_contract=_CONTRACT_METADATA,
        str_content_hash=hash_artifact(path_raw),
        str_package_version=resolve_package_version("opendata-bcb"),
    )
