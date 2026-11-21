"""Bank registry: the STR participants list, keyed by ISPB and COMPE code.

The Central Bank publishes the participants of its reserve-transfer system (STR) as a
structured CSV, refreshed daily. It carries both the ISPB (8 digits) and the COMPE code
(3 digits), so it replaces the legacy ``CODCOMPE/Tabela.pdf`` — a PDF frozen at 2009 with no
ISPB — and no PDF parser is needed.
"""

from __future__ import annotations

from datetime import date
from pathlib import Path

import pandas as pd

from opendata_bcb._internal.config.contracts import CONTRACT_BANKS
from opendata_bcb._internal.utils.banks_frame import normalise_banks
from opendata_bcb._internal.utils.daily_cache import DownloadFn, download_daily, resolve_cache_dir
from opendata_bcb._internal.utils.http_downloader import download_file
from opendata_bcb._internal.utils.provenance import (
    read_artifact,
    resolve_package_version,
    stamp_provenance,
)
from opendata_bcb._internal.utils.tabular_reader import read_table
from opendata_bcb._internal.utils.typing import type_checker


_URL_BANKS = "https://www.bcb.gov.br/content/estabilidadefinanceira/str1/ParticipantesSTR.csv"


@type_checker
def read_banks(
    *,
    dt_reference: date | None = None,
    path_cache_dir: Path | None = None,
    bool_use_cache: bool = True,
    fn_download: DownloadFn = download_file,
) -> pd.DataFrame:
    """Read the bank registry (STR participants) with COMPE and ISPB codes.

    The frame lists the participants of the STR, the BCB reserve-transfer system, direct or
    indirect, as published in ``ParticipantesSTR.csv``
    (https://www.bcb.gov.br/content/estabilidadefinanceira/str1/ParticipantesSTR.csv),
    which the BCB refreshes daily. It is not every bank in Brazil: institutions that take
    part only in PIX are not included.

    Parameters
    ----------
    dt_reference : datetime.date, optional
        The reference day keying the daily cache; defaults to today. The source is refreshed
        daily, so one day is one download.
    path_cache_dir : pathlib.Path, optional
        Directory for the daily cache; defaults to a folder under the system temp directory.
    bool_use_cache : bool, optional
        ``False`` re-downloads even when today's file is cached, by default ``True``.
    fn_download : DownloadFn, optional
        The download seam, injected so tests never touch the network.

    Returns
    -------
    pd.DataFrame
        One row per participant: ``ispb`` (8-digit string), ``short_name``, ``compe_code``
        (3-digit string, NA for participants without one), ``participates_in_compe`` (bool),
        ``main_access``, ``full_name``, ``operation_start`` (date), then the provenance
        columns.
    """
    dt_day = dt_reference or date.today()
    path_dir = resolve_cache_dir(path_cache_dir)
    path_csv = download_daily(
        _URL_BANKS,
        path_cache_dir=path_dir,
        str_key="bcb-banks",
        dt_reference=dt_day,
        str_suffix=".csv",
        bool_use_cache=bool_use_cache,
        fn_download=fn_download,
    )
    bytes_csv, str_hash = read_artifact(path_csv)
    df_raw = read_table(
        path_csv,
        str_sheet="",
        dict_dtypes=dict.fromkeys(CONTRACT_BANKS.tuple_required, "str"),
        cls_contract=CONTRACT_BANKS,
        str_csv_sep=",",
        bytes_content=bytes_csv,
    )
    df_banks = normalise_banks(df_raw)
    return stamp_provenance(
        df_banks,
        str_url=_URL_BANKS,
        cls_contract=CONTRACT_BANKS,
        str_content_hash=str_hash,
        str_package_version=resolve_package_version("opendata-bcb"),
    )
