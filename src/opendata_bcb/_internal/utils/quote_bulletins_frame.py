"""Parsing of the quote-bulletin form into a typed frame (pure transform, no I/O)."""

from __future__ import annotations

from html.parser import HTMLParser

import pandas as pd

from opendata_bcb._internal.config.contracts import ContractError
from opendata_bcb._internal.utils.typing import type_checker


NAME_SELECT_CURRENCY = "ChkMoeda"


class _CurrencySelectParser(HTMLParser):
    """Collect the ``(value, label)`` pairs of the currency ``<select>`` and nothing else."""

    def __init__(self) -> None:
        super().__init__()
        self.bool_found_select = False
        self.list_options: list[tuple[str, str]] = []
        self._bool_inside = False
        self._str_value: str | None = None
        self._list_text: list[str] = []

    def handle_starttag(  # noqa: PLR0917 -- signature fixed by HTMLParser
        self, tag: str, attrs: list[tuple[str, str | None]]
    ) -> None:
        """Dispatch the two opening tags that matter.

        Parameters
        ----------
        tag : str
            The tag name, lower-cased by the parser.
        attrs : list of tuple
            The tag's attributes.
        """
        fn_open = {"select": self._open_select, "option": self._open_option}.get(tag)
        if fn_open:
            fn_open(dict(attrs))

    def handle_endtag(self, tag: str) -> None:
        """Dispatch the two closing tags that matter.

        Parameters
        ----------
        tag : str
            The tag name, lower-cased by the parser.
        """
        fn_close = {"select": self._close_select, "option": self._close_option}.get(tag)
        if fn_close:
            fn_close()

    def handle_data(self, data: str) -> None:
        """Accumulate the label of the option being read.

        Parameters
        ----------
        data : str
            A text chunk (character references already resolved).
        """
        if self._str_value is not None:
            self._list_text.append(data)

    def _open_select(self, dict_attrs: dict[str, str | None]) -> None:
        """Enter the currency select (any other select is ignored)."""
        self._bool_inside = dict_attrs.get("name") == NAME_SELECT_CURRENCY
        self.bool_found_select = self.bool_found_select or self._bool_inside

    def _open_option(self, dict_attrs: dict[str, str | None]) -> None:
        """Start an option, only while inside the currency select."""
        if not self._bool_inside:
            return
        self._str_value = dict_attrs.get("value")
        self._list_text = []

    def _close_option(self) -> None:
        """Emit the option being read."""
        if self._str_value is not None:
            self.list_options.append((self._str_value.strip(), "".join(self._list_text).strip()))
        self._str_value = None

    def _close_select(self) -> None:
        """Leave the select."""
        self._bool_inside = False


@type_checker
def parse_currency_options(str_html: str) -> list[tuple[str, str]]:
    """Extract the ``(code, name)`` options of the currency select.

    Parameters
    ----------
    str_html : str
        The decoded form page.

    Returns
    -------
    list of tuple of str
        One ``(code, name)`` pair per option, in page order.

    Raises
    ------
    ContractError
        When the select is absent or holds no option — a markup change, never an empty result.
    """
    cls_parser = _CurrencySelectParser()
    cls_parser.feed(str_html)
    cls_parser.close()
    if not cls_parser.list_options:
        raise ContractError(
            [f"select name={NAME_SELECT_CURRENCY!r} missing or empty in the bulletin form"]
        )
    return cls_parser.list_options


@type_checker
def build_currency_frame(list_options: list[tuple[str, str]]) -> pd.DataFrame:
    """Turn the option pairs into the ``code``/``name`` text frame.

    Parameters
    ----------
    list_options : list of tuple of str
        The pairs from :func:`parse_currency_options`.

    Returns
    -------
    pd.DataFrame
        Columns ``code`` and ``name``, both strings; one row per option.
    """
    return pd.DataFrame(list_options, columns=["code", "name"], dtype="string")
