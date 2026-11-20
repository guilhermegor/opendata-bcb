"""Unit tests for the PTAX currency code reader (fixture-backed, no network)."""

from datetime import date
from pathlib import Path
import shutil
from unittest.mock import Mock

import pandas as pd
import pytest

from opendata_bcb._internal.utils.tabular_reader import ContractError
from opendata_bcb.ingestion.currency_codes import URL_CURRENCY_CODES, read_currency_codes


PATH_FIXTURE = Path(__file__).parent.parent / "fixtures" / "currency_codes" / "moedas_ptax.csv"
DT_DAY = date(2026, 11, 19)
DT_NO_FILE = date(2026, 11, 20)


def _fake_download(*, str_url: str, path_dest: Path) -> Path:
    """Stand in for the HTTP seam by copying the trimmed real artifact.

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


def _download_from_19th(  # complexity-ok: stand-in answering 404 for every other day
    *, str_url: str, path_dest: Path
) -> Path:
    """Serve the fixture only for the 19th, like the source answering 404 for the 20th.

    Parameters
    ----------
    str_url : str
        The requested URL.
    path_dest : pathlib.Path
        Where the cache layer wants the bytes.

    Returns
    -------
    pathlib.Path
        ``path_dest`` holding the fixture.

    Raises
    ------
    FileNotFoundError
        For any other day.
    """
    if "M20261119" not in str_url:
        raise FileNotFoundError("status 404")
    return _fake_download(str_url=str_url, path_dest=path_dest)


def _always_missing(*, str_url: str, path_dest: Path) -> Path:
    """Fail like a source with no file on any day.

    Parameters
    ----------
    str_url : str
        Ignored.
    path_dest : pathlib.Path
        Ignored.

    Returns
    -------
    pathlib.Path
        Never returned.

    Raises
    ------
    FileNotFoundError
        Always.
    """
    raise FileNotFoundError("status 404")


def _broken_download(*, str_url: str, path_dest: Path) -> Path:
    """Serve a CSV missing most of the contract columns.

    Parameters
    ----------
    str_url : str
        Ignored.
    path_dest : pathlib.Path
        Where the cache layer wants the bytes.

    Returns
    -------
    pathlib.Path
        ``path_dest``, now holding the truncated CSV.
    """
    path_dest.write_text("Nome;Tipo\nX;A\n", encoding="latin-1")
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
        The parsed table.
    """
    return read_currency_codes(
        dt_reference=DT_DAY, path_cache_dir=tmp_path, fn_download=_fake_download
    )


def test_read_currency_codes_codes_stay_strings(df_codes: pd.DataFrame) -> None:
    """Currency codes are 3-digit strings, leading zero kept."""
    assert df_codes["currency_code"].tolist() == ["005", "610", "978", "790", "986"]


def test_read_currency_codes_country_code_stays_string(df_codes: pd.DataFrame) -> None:
    """Country codes are strings."""
    assert df_codes["country_code"].tolist()[:4] == ["132", "230", "230", "1058"]


def test_read_currency_codes_trims_fixed_width_padding(df_codes: pd.DataFrame) -> None:
    """Symbols lose their trailing spaces."""
    assert df_codes["symbol"].iloc[0] == "AFN"


def test_read_currency_codes_country_names_trimmed(df_codes: pd.DataFrame) -> None:
    """Country names lose their padding."""
    assert df_codes["country"].iloc[3] == "BRASIL"


def test_read_currency_codes_empty_exclusion_means_active(df_codes: pd.DataFrame) -> None:
    """An empty exclusion date is still active; a filled one is not."""
    assert df_codes["is_active"].tolist() == [True, False, True, True, False]


def test_read_currency_codes_exclusion_date_parsed_day_first(df_codes: pd.DataFrame) -> None:
    """``02/01/2002`` is January 2nd."""
    assert df_codes["exclusion_date"].iloc[1] == date(2002, 1, 2)


def test_read_currency_codes_blank_fields_become_na(df_codes: pd.DataFrame) -> None:
    """The legacy row with blank type yields NA, not an empty string."""
    assert df_codes["currency_type"].isna().tolist()[-1]


def test_read_currency_codes_stamps_provenance_url(df_codes: pd.DataFrame) -> None:
    """Every row carries the dated source URL."""
    assert df_codes["url"].unique().tolist() == [URL_CURRENCY_CODES.format(dt=DT_DAY)]


def test_read_currency_codes_stamps_provenance_columns(df_codes: pd.DataFrame) -> None:
    """The fetch time, source key and content hash are present."""
    assert {"updated_at", "source_key", "content_hash"} <= set(df_codes.columns)


def test_read_currency_codes_falls_back_to_previous_business_day(tmp_path: Path) -> None:
    """A missing file for the 20th falls back to the 19th."""
    df_fallback = read_currency_codes(
        dt_reference=DT_NO_FILE, path_cache_dir=tmp_path, fn_download=_download_from_19th
    )
    assert df_fallback["url"].iloc[0].endswith("M20261119.csv")


def test_read_currency_codes_no_file_anywhere_raises(tmp_path: Path) -> None:
    """When every candidate day is missing the read fails loudly."""
    with pytest.raises(FileNotFoundError):
        read_currency_codes(
            dt_reference=DT_DAY, path_cache_dir=tmp_path, fn_download=_always_missing
        )


def _server_error(*, str_url: str, path_dest: Path) -> Path:
    """Fail like a source answering 503: a broken transfer, not a missing file.

    Parameters
    ----------
    str_url : str
        Ignored.
    path_dest : pathlib.Path
        Ignored.

    Returns
    -------
    pathlib.Path
        Never returned.

    Raises
    ------
    OSError
        Always.
    """
    raise OSError("status 503")


def test_read_currency_codes_server_error_does_not_fall_back(tmp_path: Path) -> None:
    """A 503 surfaces as a failure instead of silently serving an older day's file."""
    fn_failing = Mock(side_effect=_server_error)
    with pytest.raises(OSError, match="503"):
        read_currency_codes(dt_reference=DT_DAY, path_cache_dir=tmp_path, fn_download=fn_failing)


def test_read_currency_codes_second_call_hits_daily_cache(tmp_path: Path) -> None:
    """Two reads on one reference day download once."""
    fn_counting = Mock(side_effect=_fake_download)
    read_currency_codes(dt_reference=DT_DAY, path_cache_dir=tmp_path, fn_download=fn_counting)
    read_currency_codes(dt_reference=DT_DAY, path_cache_dir=tmp_path, fn_download=fn_counting)
    assert fn_counting.call_count == 1


def test_read_currency_codes_missing_column_raises(tmp_path: Path) -> None:
    """A source that dropped contract columns fails loudly."""
    with pytest.raises(ContractError):
        read_currency_codes(
            dt_reference=DT_DAY, path_cache_dir=tmp_path, fn_download=_broken_download
        )
