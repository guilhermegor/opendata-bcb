"""Quote bulletins: the currency codes the BCB bulletin form accepts.

The Central Bank's quote-bulletin form (``consultaBoletim.do``) lists the currencies it can
report in a ``<select>``; its option values are the codes the bulletin query takes. The
bulletins themselves (per currency) build on :data:`_URL_QUOTE_BULLETIN_FORM` and the codes
read here.
"""

from __future__ import annotations

from datetime import date
from pathlib import Path
import tempfile

import pandas as pd

from opendata_bcb._internal.config.contracts import CONTRACT_QUOTE_BULLETIN_CODES
from opendata_bcb._internal.utils.daily_cache import DownloadFn, download_daily
from opendata_bcb._internal.utils.http_downloader import download_file
from opendata_bcb._internal.utils.provenance import (
    hash_artifact,
    resolve_package_version,
    stamp_provenance,
)
from opendata_bcb._internal.utils.quote_bulletins_frame import (
    build_currency_frame,
    parse_currency_options,
)
from opendata_bcb._internal.utils.typing import type_checker


_URL_QUOTE_BULLETIN_FORM = (
    "https://ptax.bcb.gov.br/ptax_internet/consultaBoletim.do"
    "?method=exibeFormularioConsultaBoletim"
)
_ENCODING_QUOTE_BULLETIN_FORM = "iso-8859-1"


@type_checker
def read_quote_bulletin_codes(
    *,
    dt_reference: date | None = None,
    path_cache_dir: Path | None = None,
    bool_use_cache: bool = True,
    fn_download: DownloadFn = download_file,
) -> pd.DataFrame:
    """Read the currency codes the quote-bulletin form accepts.

    Parameters
    ----------
    dt_reference : datetime.date, optional
        The reference day keying the daily cache; defaults to today.
    path_cache_dir : pathlib.Path, optional
        Directory for the daily cache; defaults to a folder under the system temp directory.
    bool_use_cache : bool, optional
        ``False`` re-downloads even when today's page is cached, by default ``True``.
    fn_download : DownloadFn, optional
        The download seam, injected so tests never touch the network.

    Returns
    -------
    pd.DataFrame
        One row per currency: ``code`` (string, the form's option value) and ``name`` (the
        source's label), then the provenance columns.

    Raises
    ------
    ContractError
        When the form has no currency select, or an empty one (markup change).
    """
    dt_day = dt_reference or date.today()
    path_dir = path_cache_dir or Path(tempfile.gettempdir()) / "opendata-bcb-cache"
    path_html = download_daily(
        _URL_QUOTE_BULLETIN_FORM,
        path_cache_dir=path_dir,
        str_key="bcb-quote-bulletin-form",
        dt_reference=dt_day,
        str_suffix=".html",
        bool_use_cache=bool_use_cache,
        fn_download=fn_download,
    )
    str_html = path_html.read_text(encoding=_ENCODING_QUOTE_BULLETIN_FORM)
    df_codes = build_currency_frame(parse_currency_options(str_html))
    return stamp_provenance(
        df_codes,
        str_url=_URL_QUOTE_BULLETIN_FORM,
        cls_contract=CONTRACT_QUOTE_BULLETIN_CODES,
        str_content_hash=hash_artifact(path_html),
        str_package_version=resolve_package_version("opendata-bcb"),
    )
