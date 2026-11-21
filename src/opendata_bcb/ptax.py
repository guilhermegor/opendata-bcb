"""Read PTAX exchange rates from the BCB Olinda ``PTAX`` service.

The module owns everything the service's readers share: the service name, the date-parameter
format and the typing of the quote frame. Each public ``read_*`` function binds one resource
of the service to that shared path (the Olinda client for HTTP, paging, cache and provenance).
Rates are exact :class:`decimal.Decimal` built from the source text, never ``float``.
"""

from __future__ import annotations

from collections.abc import Callable
from datetime import date
from decimal import Decimal
from pathlib import Path
import tempfile

import pandas as pd

from opendata_bcb._internal.config.contracts import (
    PTAX_CURRENCIES,
    PTAX_QUOTES,
    PTAX_USD_BRL,
    FileContract,
)
from opendata_bcb._internal.olinda import fetch_frame
from opendata_bcb._internal.utils.daily_cache import DownloadFn
from opendata_bcb._internal.utils.http_downloader import download_file
from opendata_bcb._internal.utils.ptax_currencies_frame import normalise_ptax_currencies
from opendata_bcb._internal.utils.ptax_frame import normalise_ptax_quotes
from opendata_bcb._internal.utils.ptax_quotes_frame import normalise_ptax_period_quotes
from opendata_bcb._internal.utils.typing import type_checker


_STR_SERVICE = "PTAX"


@type_checker
def _olinda_date(dt_day: date) -> str:
    """Format a day the way Olinda's ``PTAX`` function imports expect it.

    Parameters
    ----------
    dt_day : datetime.date
        The day.

    Returns
    -------
    str
        ``MM-DD-YYYY``, month first.
    """
    return f"{dt_day:%m-%d-%Y}"


@type_checker
def _read_quotes(  # noqa: PLR0913, PLR0917 -- keyword-only reader inputs
    str_resource: str,
    *,
    cls_contract: FileContract,
    fn_normalise: Callable[[pd.DataFrame], pd.DataFrame],
    dict_params: dict[str, str | int | Decimal],
    dt_reference: date,
    path_cache_dir: Path | None,
    bool_use_cache: bool,
    fn_download: DownloadFn,
) -> pd.DataFrame:
    """Fetch one ``PTAX`` function import into a typed, provenance-stamped quote frame.

    Parameters
    ----------
    str_resource : str
        The function import, e.g. ``"CotacaoDolarPeriodo"``.
    cls_contract : FileContract
        The contract the payload must satisfy.
    fn_normalise : Callable
        The frame typing applied after the contract check.
    dict_params : dict
        Its parameters, already formatted for Olinda.
    dt_reference : datetime.date
        The data's reference day, keying the daily cache.
    path_cache_dir : pathlib.Path or None
        Cache directory; ``None`` falls back to a folder under the system temp directory.
    bool_use_cache : bool
        Whether cached pages may be served.
    fn_download : DownloadFn
        The download seam.

    Returns
    -------
    pd.DataFrame
        The typed quote frame.
    """
    return fn_normalise(
        fetch_frame(
            _STR_SERVICE,
            str_resource,
            cls_contract=cls_contract,
            path_cache_dir=path_cache_dir or Path(tempfile.gettempdir()) / "opendata-bcb-cache",
            dt_reference=dt_reference,
            dict_params=dict_params,
            bool_use_cache=bool_use_cache,
            fn_download=fn_download,
        )
    )


@type_checker
def read_ptax_usd_brl(
    *,
    dt_start: date,
    dt_end: date,
    dt_reference: date | None = None,
    path_cache_dir: Path | None = None,
    bool_use_cache: bool = True,
    fn_download: DownloadFn = download_file,
) -> pd.DataFrame:
    """Read the PTAX USD/BRL buy and sell rates over a period.

    Parameters
    ----------
    dt_start : datetime.date
        First day requested.
    dt_end : datetime.date
        Last day requested (inclusive).
    dt_reference : datetime.date, optional
        The day keying the daily cache; defaults to today. Not ``dt_end``: a period ending
        today would then be served from cache, still missing its later quotes, forever.
    path_cache_dir : pathlib.Path, optional
        Directory for the daily cache; defaults to a folder under the system temp directory.
    bool_use_cache : bool, optional
        ``False`` re-downloads even when today's pages are cached, by default ``True``.
    fn_download : DownloadFn, optional
        The download seam, injected so tests never touch the network.

    Returns
    -------
    pd.DataFrame
        ``buy_rate`` and ``sell_rate`` (``Decimal``), ``quoted_at`` (``datetime64``, with the
        time of day), then the provenance columns. One row per day: the service returns
        the closing quote only, with no bulletin-type field.

    Raises
    ------
    ValueError
        If ``dt_start`` is after ``dt_end``.
    ContractError
        If the period holds no quotes or the payload lacks a required field.
    """
    if dt_start > dt_end:
        raise ValueError(f"dt_start {dt_start} is after dt_end {dt_end}")
    return _read_quotes(
        "CotacaoDolarPeriodo",
        cls_contract=PTAX_USD_BRL,
        fn_normalise=normalise_ptax_quotes,
        dict_params={
            "dataInicial": _olinda_date(dt_start),
            "dataFinalCotacao": _olinda_date(dt_end),
        },
        dt_reference=dt_reference or date.today(),
        path_cache_dir=path_cache_dir,
        bool_use_cache=bool_use_cache,
        fn_download=fn_download,
    )


@type_checker
def read_ptax_currencies(
    *,
    dt_reference: date | None = None,
    path_cache_dir: Path | None = None,
    bool_use_cache: bool = True,
    fn_download: DownloadFn = download_file,
) -> pd.DataFrame:
    """Read the list of currencies the PTAX service quotes.

    Parameters
    ----------
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
        ``symbol`` (currency code), ``name`` (Portuguese display name) and ``currency_type``
        (``"A"`` or ``"B"``, the PTAX parity convention), then the provenance columns.

    Raises
    ------
    ContractError
        If the list is empty or the payload lacks a required field.
    """
    return normalise_ptax_currencies(
        fetch_frame(
            _STR_SERVICE,
            "Moedas",
            cls_contract=PTAX_CURRENCIES,
            path_cache_dir=path_cache_dir or Path(tempfile.gettempdir()) / "opendata-bcb-cache",
            dt_reference=dt_reference or date.today(),
            bool_use_cache=bool_use_cache,
            fn_download=fn_download,
        )
    )


@type_checker
def read_ptax_quotes(  # noqa: PLR0913 -- keyword-only reader inputs
    str_currency: str,
    *,
    dt_start: date,
    dt_end: date,
    dt_reference: date | None = None,
    path_cache_dir: Path | None = None,
    bool_use_cache: bool = True,
    fn_download: DownloadFn = download_file,
) -> pd.DataFrame:
    """Read the PTAX quotes of one currency over a period, intraday bulletins included.

    Parameters
    ----------
    str_currency : str
        Currency symbol as listed by :func:`read_ptax_currencies`, e.g. ``"EUR"``.
    dt_start : datetime.date
        First day requested.
    dt_end : datetime.date
        Last day requested (inclusive).
    dt_reference : datetime.date, optional
        The day keying the daily cache; defaults to today. Not ``dt_end``: a period ending
        today would then be served from cache, still missing its later quotes, forever.
    path_cache_dir : pathlib.Path, optional
        Directory for the daily cache; defaults to a folder under the system temp directory.
    bool_use_cache : bool, optional
        ``False`` re-downloads even when today's pages are cached, by default ``True``.
    fn_download : DownloadFn, optional
        The download seam, injected so tests never touch the network.

    Returns
    -------
    pd.DataFrame
        ``buy_parity``, ``sell_parity``, ``buy_rate``, ``sell_rate`` (``Decimal``),
        ``quoted_at`` (``datetime64``, with the time of day) and ``bulletin_type``
        (``Abertura``, ``Intermediário`` or ``Fechamento``; a column, never a filter),
        then the provenance columns.

    Raises
    ------
    ValueError
        If ``dt_start`` is after ``dt_end``.
    ContractError
        If the period holds no quotes or the payload lacks a required field.
    """
    if dt_start > dt_end:
        raise ValueError(f"dt_start {dt_start} is after dt_end {dt_end}")
    return _read_quotes(
        "CotacaoMoedaPeriodo",
        cls_contract=PTAX_QUOTES,
        fn_normalise=normalise_ptax_period_quotes,
        dict_params={
            "moeda": str_currency,
            "dataInicial": _olinda_date(dt_start),
            "dataFinalCotacao": _olinda_date(dt_end),
        },
        dt_reference=dt_reference or date.today(),
        path_cache_dir=path_cache_dir,
        bool_use_cache=bool_use_cache,
        fn_download=fn_download,
    )
