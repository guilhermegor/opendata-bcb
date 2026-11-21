"""Frame builders for the SGS reader: the pandas seam, so the public layer holds none.

The public ``sgs`` module may only name pandas in annotations; every call that
builds or types a frame lives here.
"""

from __future__ import annotations

from xml.etree.ElementTree import Element  # noqa: S405 -- annotation only; parsing uses defusedxml

from defusedxml.ElementTree import fromstring as parse_xml_safely
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
def _find_serie(bytes_response: bytes) -> Element:
    """Return the ``SERIE`` element nested inside the SOAP return text.

    Parameters
    ----------
    bytes_response : bytes
        The SOAP response exactly as served.

    Returns
    -------
    xml.etree.ElementTree.Element
        The ``SERIE`` element.

    Raises
    ------
    ValueError
        If the response carries no series (unknown code or a SOAP fault).
    """
    cls_envelope = parse_xml_safely(bytes_response)
    str_inner = next(
        (el.text for el in cls_envelope.iter() if el.tag.endswith("Return") and el.text), None
    )
    cls_serie = (
        None if str_inner is None else parse_xml_safely(str_inner.split("?>", 1)[1]).find("SERIE")
    )
    if cls_serie is None:
        raise ValueError("SGS response carries no series metadata")
    return cls_serie


@type_checker
def build_metadata_frame(bytes_response: bytes) -> pd.DataFrame:
    """Parse a ``getUltimoValorXML`` SOAP response into a one-row metadata frame.

    The envelope's return element carries the real document as escaped text (with its own
    ISO-8859-1 declaration, already decoded by the outer parse), so it is parsed a second time.

    Parameters
    ----------
    bytes_response : bytes
        The SOAP response exactly as served.

    Returns
    -------
    pd.DataFrame
        One row: ``code`` (int), ``name``, ``periodicity`` (source letter code) and ``unit``.

    Raises
    ------
    ValueError
        If the response carries no series (unknown code or a SOAP fault).
    """
    cls_serie = _find_serie(bytes_response)
    return apply_dtypes(
        pd.DataFrame(
            [
                {
                    "code": cls_serie.findtext("CODIGO"),
                    "name": cls_serie.findtext("NOME"),
                    "periodicity": cls_serie.findtext("PERIODICIDADE"),
                    "unit": cls_serie.findtext("UNIDADE"),
                }
            ]
        ),
        dict_dtypes={"code": "int64", "name": "str", "periodicity": "str", "unit": "str"},
    )
