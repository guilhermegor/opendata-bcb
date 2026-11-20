"""Shared client for the BCB Olinda OData host (``olinda.bcb.gov.br``).

Four readers (PTAX, currencies, currencies time series, Focus) call the same host, so the URL
building, paging, payload parsing, caching and provenance stamping live here once. A reader
supplies the service, the resource, its parameters and its contract; it gets back a typed,
contract-checked, provenance-stamped frame.

Numbers are parsed with :class:`~decimal.Decimal` straight from the source text
(``5.49290`` stays ``Decimal("5.49290")``), never through ``float``.

The Olinda quirks this module absorbs: a function import takes ``(name=@name)`` with the value
in the query string as ``@name='value'``; an error comes back as HTTP 400 whose body is a
``/* ... */``-wrapped JSON with ``codigo``/``mensagem`` (the OData spec's ``error`` envelope is
rejected too); and a page shorter than ``$top`` marks the last page.
"""

from __future__ import annotations

from datetime import date
from decimal import Decimal
import hashlib
import json
from pathlib import Path
import re
from urllib.parse import quote

import pandas as pd

from opendata_bcb._internal.config.contracts import (
    ContractError,
    FileContract,  # noqa: TID251 -- type annotation only
    find_contract_problems,
)
from opendata_bcb._internal.utils.daily_cache import download_daily
from opendata_bcb._internal.utils.http_downloader import DownloadFn, download_file
from opendata_bcb._internal.utils.provenance import (
    hash_artifact,
    resolve_package_version,
    stamp_provenance,
)
from opendata_bcb._internal.utils.records_frame import frame_from_records
from opendata_bcb._internal.utils.typing import type_checker


_BASE_URL = "https://olinda.bcb.gov.br/olinda/servico"
_DEFAULT_PAGE_SIZE = 1000
_MAX_PAGES = 10_000
_RE_BLOCK_COMMENT = re.compile(r"^\s*/\*(.*)\*/\s*$", re.DOTALL)
_ERROR_KEYS = ("odata.error", "error", "codigo")


class OlindaError(Exception):
    """Raised when Olinda answers with an error payload or a malformed body."""


@type_checker
def build_url(  # noqa: PLR0913, PLR0917 -- one keyword per OData system option
    str_service: str,
    str_resource: str,
    *,
    dict_params: dict[str, str | int | Decimal] | None = None,
    str_filter: str | None = None,
    str_select: str | None = None,
    int_top: int | None = None,
    int_skip: int | None = None,
    str_version: str = "v1",
) -> str:
    """Build an Olinda OData URL (always ``$format=json``).

    Parameters
    ----------
    str_service : str
        Olinda service, e.g. ``"PTAX"``.
    str_resource : str
        Entity set or function import, e.g. ``"CotacaoDolarPeriodo"``.
    dict_params : dict, optional
        Function-import parameters. Strings are quoted (``'11-03-2026'``), numbers are not.
    str_filter : str, optional
        OData ``$filter`` expression.
    str_select : str, optional
        Comma-separated ``$select`` fields.
    int_top : int, optional
        ``$top`` page size.
    int_skip : int, optional
        ``$skip`` offset.
    str_version : str, optional
        Service version, by default ``"v1"``.

    Returns
    -------
    str
        The fully encoded URL.
    """
    dict_params = dict_params or {}
    str_path = f"{_BASE_URL}/{str_service}/versao/{str_version}/odata/{str_resource}"
    list_query = []
    if dict_params:
        str_args = ",".join(f"{str_name}=@{str_name}" for str_name in dict_params)
        str_path = f"{str_path}({str_args})"
        list_query = [
            f"@{str_name}={_encode_param(value)}" for str_name, value in dict_params.items()
        ]
    dict_options = {
        "$filter": str_filter,
        "$select": str_select,
        "$top": int_top,
        "$skip": int_skip,
    }
    list_query += [
        f"{str_key}={quote(str(v), safe=',')}"
        for str_key, v in dict_options.items()
        if v is not None
    ]
    list_query.append("$format=json")
    return f"{str_path}?{'&'.join(list_query)}"


@type_checker
def _encode_param(value: str | int | Decimal) -> str:
    """Encode one function-import argument: strings single-quoted, numbers bare.

    Parameters
    ----------
    value : str or int or Decimal
        The argument value.

    Returns
    -------
    str
        The URL-encoded literal.
    """
    if isinstance(value, str):
        return f"%27{quote(value, safe='')}%27"
    return quote(str(value), safe="")


@type_checker
def parse_payload(str_body: str) -> list[dict[str, object]]:
    """Parse an Olinda response body into its ``value`` rows.

    Parameters
    ----------
    str_body : str
        The raw response text.

    Returns
    -------
    list of dict
        The rows; decimals are exact :class:`~decimal.Decimal` built from the source text.
        An empty ``value`` array yields ``[]`` (a legitimately empty page).

    Raises
    ------
    OlindaError
        If the body is not JSON, carries an error envelope, or has no ``value`` array —
        never an empty result in disguise.
    """
    re_match = _RE_BLOCK_COMMENT.match(str_body)
    str_json = re_match.group(1) if re_match else str_body
    try:
        payload = json.loads(str_json, parse_float=Decimal)
    except json.JSONDecodeError as cls_err:
        raise OlindaError(f"Olinda body is not JSON: {str_body[:200]!r}") from cls_err
    if not isinstance(payload, dict):
        raise OlindaError(f"Olinda payload is not an object: {str_body[:200]!r}")
    if any(str_key in payload for str_key in _ERROR_KEYS):
        raise OlindaError(f"Olinda returned an error: {payload}")
    list_rows = payload.get("value")
    if not isinstance(list_rows, list):
        raise OlindaError(f"Olinda payload has no 'value' array: {str_body[:200]!r}")
    return list_rows


@type_checker
def fetch_frame(  # noqa: PLR0913, PLR0917 -- keyword-only reader inputs
    str_service: str,
    str_resource: str,
    *,
    cls_contract: FileContract,
    path_cache_dir: Path,
    dt_reference: date,
    dict_params: dict[str, str | int | Decimal] | None = None,
    str_filter: str | None = None,
    str_select: str | None = None,
    int_page_size: int = _DEFAULT_PAGE_SIZE,
    bool_use_cache: bool = True,
    fn_download: DownloadFn = download_file,
) -> pd.DataFrame:
    """Fetch every page of a resource into one contract-checked, stamped frame.

    Pages are requested with ``$top``/``$skip`` until one comes back shorter than the page
    size, each cached per reference day (``dt_reference`` is the data's date, not the wall
    clock; only for data stable across that day).

    Parameters
    ----------
    str_service : str
        Olinda service, e.g. ``"PTAX"``.
    str_resource : str
        Entity set or function import.
    cls_contract : FileContract
        The contract the frame must satisfy; also supplies the provenance ``source_key``.
    path_cache_dir : pathlib.Path
        Directory for the daily cache.
    dt_reference : datetime.date
        The data's reference date, keying the cache.
    dict_params : dict, optional
        Function-import parameters.
    str_filter : str, optional
        OData ``$filter``.
    str_select : str, optional
        Comma-separated ``$select`` fields.
    int_page_size : int, optional
        ``$top`` per request, by default 1000.
    bool_use_cache : bool, optional
        ``False`` re-downloads (and refreshes the cache), by default ``True``.
    fn_download : DownloadFn, optional
        Download seam, injected by tests so nothing touches the network.

    Returns
    -------
    pd.DataFrame
        Rows plus the provenance columns; ``url`` is the first page's URL and
        ``content_hash`` digests all pages' bytes.

    Raises
    ------
    OlindaError
        On an error payload, a malformed body, or a runaway page loop.
    ContractError
        If the rows do not satisfy ``cls_contract`` (including an empty result).
    """
    list_rows: list[dict[str, object]] = []
    cls_digest = hashlib.sha256()
    str_first_url = ""
    for int_page in range(_MAX_PAGES):
        str_url = build_url(
            str_service,
            str_resource,
            dict_params=dict_params,
            str_filter=str_filter,
            str_select=str_select,
            int_top=int_page_size,
            int_skip=int_page * int_page_size,
        )
        str_first_url = str_first_url or str_url
        path_page = download_daily(
            str_url,
            path_cache_dir=path_cache_dir,
            str_key=f"olinda-{hashlib.sha256(str_url.encode()).hexdigest()[:16]}",
            dt_reference=dt_reference,
            str_suffix=".json",
            bool_use_cache=bool_use_cache,
            fn_download=fn_download,
        )
        cls_digest.update(hash_artifact(path_page).encode())
        list_page = parse_payload(path_page.read_text(encoding="utf-8"))
        list_rows += list_page
        if len(list_page) < int_page_size:
            break
    else:
        raise OlindaError(f"Olinda paging did not terminate after {_MAX_PAGES} pages")
    df_rows = frame_from_records(list_rows)
    list_fatal = find_contract_problems(df_rows, cls_contract=cls_contract).list_fatal
    if list_fatal:
        raise ContractError(list_fatal)
    return stamp_provenance(
        df_rows,
        str_url=str_first_url,
        cls_contract=cls_contract,
        str_content_hash=cls_digest.hexdigest(),
        str_package_version=resolve_package_version("opendata-bcb"),
    )
