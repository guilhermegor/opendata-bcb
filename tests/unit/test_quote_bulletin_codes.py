"""Unit tests for the quote-bulletin currency codes reader (fixture-backed, no network)."""

from datetime import date
import hashlib
from pathlib import Path
import shutil
from unittest.mock import Mock

import pandas as pd
import pytest

from opendata_bcb._internal.utils.tabular_reader import ContractError
from opendata_bcb.ingestion.quote_bulletins import (
    URL_QUOTE_BULLETIN_FORM,
    read_quote_bulletin_codes,
)


PATH_FIXTURE = (
    Path(__file__).parent.parent / "fixtures" / "quote_bulletins" / "consulta_boletim_form.html"
)
DT_DAY = date(2026, 11, 20)


def _fake_download(*, str_url: str, path_dest: Path) -> Path:
    """Stand in for the HTTP seam by copying the trimmed real page.

    Parameters
    ----------
    str_url : str
        Ignored; the fixture is served whatever the URL.
    path_dest : pathlib.Path
        Where the cache layer wants the bytes.

    Returns
    -------
    pathlib.Path
        ``path_dest``, now holding the fixture.
    """
    shutil.copy(PATH_FIXTURE, path_dest)
    return path_dest


def _download_without_select(*, str_url: str, path_dest: Path) -> Path:
    """Serve a page whose currency select is gone.

    Parameters
    ----------
    str_url : str
        Ignored.
    path_dest : pathlib.Path
        Where the cache layer wants the bytes.

    Returns
    -------
    pathlib.Path
        ``path_dest``, now holding markup without the select.
    """
    path_dest.write_text("<html><body><p>manutencao</p></body></html>", encoding="utf-8")
    return path_dest


def _download_empty_select(*, str_url: str, path_dest: Path) -> Path:
    """Serve a page whose currency select has no option.

    Parameters
    ----------
    str_url : str
        Ignored.
    path_dest : pathlib.Path
        Where the cache layer wants the bytes.

    Returns
    -------
    pathlib.Path
        ``path_dest``, now holding an empty select.
    """
    path_dest.write_text('<select name="ChkMoeda"></select>', encoding="utf-8")
    return path_dest


@pytest.fixture
def df_codes(tmp_path: Path) -> pd.DataFrame:
    """Read the fixture through the public function.

    Parameters
    ----------
    tmp_path : pathlib.Path
        Per-test cache directory.

    Returns
    -------
    pd.DataFrame
        The parsed currency codes.
    """
    return read_quote_bulletin_codes(
        dt_reference=DT_DAY, path_cache_dir=tmp_path, fn_download=_fake_download
    )


def test_read_codes_keeps_page_order_pairs(df_codes: pd.DataFrame) -> None:
    """Each option's value and label pair up, in page order."""
    assert df_codes[["code", "name"]].to_numpy().tolist()[:3] == [
        ["1", "AFEGANE AFEGANIST"],
        ["2331", "ARIARY MADAGASCAR"],
        ["4", "AUSTRAL"],
    ]


def test_read_codes_decodes_latin1_accents(df_codes: pd.DataFrame) -> None:
    """The ISO-8859-1 page decodes ``SÃO TOMÉ`` correctly."""
    assert "DOBRA SÃO TOMÉ E PRÍNCIPE" in df_codes["name"].tolist()


def test_read_codes_row_count_matches_fixture_options(df_codes: pd.DataFrame) -> None:
    """One row per option in the trimmed page (count taken from the bytes)."""
    int_expected = PATH_FIXTURE.read_bytes().count(b"<option ")
    assert len(df_codes) == int_expected


def test_read_codes_pins_content_hash_of_real_artifact(df_codes: pd.DataFrame) -> None:
    """The stamped hash is that of the fixture bytes, nobody-authored."""
    str_sha = hashlib.sha256(PATH_FIXTURE.read_bytes()).hexdigest()
    assert df_codes["content_hash"].iloc[0] == str_sha


def test_read_codes_stamps_provenance_url(df_codes: pd.DataFrame) -> None:
    """Every row carries the source URL."""
    assert df_codes["url"].unique().tolist() == [URL_QUOTE_BULLETIN_FORM]


def test_read_codes_stamps_provenance_columns(df_codes: pd.DataFrame) -> None:
    """The fetch time, source key and content hash are present."""
    assert {"updated_at", "source_key", "content_hash"} <= set(df_codes.columns)


def test_read_codes_second_call_hits_daily_cache(tmp_path: Path) -> None:
    """Two reads on one reference day download once."""
    fn_counting = Mock(side_effect=_fake_download)
    read_quote_bulletin_codes(
        dt_reference=DT_DAY, path_cache_dir=tmp_path, fn_download=fn_counting
    )
    read_quote_bulletin_codes(
        dt_reference=DT_DAY, path_cache_dir=tmp_path, fn_download=fn_counting
    )
    assert fn_counting.call_count == 1


def test_read_codes_missing_select_raises(tmp_path: Path) -> None:
    """A page without the currency select fails loudly."""
    with pytest.raises(ContractError):
        read_quote_bulletin_codes(
            dt_reference=DT_DAY, path_cache_dir=tmp_path, fn_download=_download_without_select
        )


def test_read_codes_empty_select_raises(tmp_path: Path) -> None:
    """A select with no option fails loudly rather than returning an empty frame."""
    with pytest.raises(ContractError):
        read_quote_bulletin_codes(
            dt_reference=DT_DAY, path_cache_dir=tmp_path, fn_download=_download_empty_select
        )
