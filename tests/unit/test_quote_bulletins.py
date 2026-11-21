"""Unit tests for the quote-bulletin reader (real trimmed CSV fixture, no network)."""

from datetime import date
from decimal import Decimal
import hashlib
from pathlib import Path
import shutil
from unittest.mock import Mock

import pandas as pd
import pytest

from opendata_bcb._internal.utils.tabular_reader import ContractError
from opendata_bcb.quote_bulletins import read_quote_bulletins


PATH_FIXTURE = (
    Path(__file__).parent.parent
    / "fixtures"
    / "quote_bulletins"
    / "boletim_usd_20261110_20261119.csv"
)
DT_DAY = date(2026, 11, 20)
DT_START = date(2026, 11, 10)
DT_END = date(2026, 11, 19)


def _fake_download(*, str_url: str, path_dest: Path) -> Path:
    """Stand in for the HTTP seam by copying the real CSV.

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


def _download_malformed(*, str_url: str, path_dest: Path) -> Path:
    """Serve a CSV whose row has too few fields.

    Parameters
    ----------
    str_url : str
        Ignored.
    path_dest : pathlib.Path
        Where the cache layer wants the bytes.

    Returns
    -------
    pathlib.Path
        ``path_dest``, now holding a malformed row.
    """
    path_dest.write_text("10112026;220;A\n", encoding="ascii")
    return path_dest


@pytest.fixture
def df_bulletins(tmp_path: Path) -> pd.DataFrame:
    """Read the fixture through the public function.

    Parameters
    ----------
    tmp_path : pathlib.Path
        Per-test cache directory.

    Returns
    -------
    pd.DataFrame
        The parsed bulletins.
    """
    return read_quote_bulletins(
        "61",
        dt_start=DT_START,
        dt_end=DT_END,
        dt_reference=DT_DAY,
        path_cache_dir=tmp_path,
        fn_download=_fake_download,
    )


def test_read_bulletins_first_row_decimals_exact(df_bulletins: pd.DataFrame) -> None:
    """Comma decimals become exact Decimals built from the source text."""
    assert df_bulletins.loc[0, ["buy_rate", "sell_rate"]].tolist() == [
        Decimal("5.5834"),
        Decimal("5.5840"),
    ]


def test_read_bulletins_parses_ddmmyyyy_dates(df_bulletins: pd.DataFrame) -> None:
    """The ``ddmmyyyy`` day becomes a ``date``."""
    assert df_bulletins["date"].iloc[0] == date(2026, 11, 10)


def test_read_bulletins_row_count_matches_fixture_lines(df_bulletins: pd.DataFrame) -> None:
    """One row per CSV line (count taken from the bytes)."""
    assert len(df_bulletins) == PATH_FIXTURE.read_bytes().count(b"\n")


def test_read_bulletins_pins_content_hash_of_real_artifact(df_bulletins: pd.DataFrame) -> None:
    """The stamped hash is that of the fixture bytes, nobody-authored."""
    str_sha = hashlib.sha256(PATH_FIXTURE.read_bytes()).hexdigest()
    assert df_bulletins["content_hash"].iloc[0] == str_sha


def test_read_bulletins_url_carries_code_and_period(df_bulletins: pd.DataFrame) -> None:
    """The stamped URL names the currency code and the period."""
    assert (
        df_bulletins["url"].iloc[0].endswith("&ChkMoeda=61&DATAINI=10/11/2026&DATAFIM=19/11/2026")
    )


def test_read_bulletins_stamps_provenance_columns(df_bulletins: pd.DataFrame) -> None:
    """The fetch time, source key and content hash are present."""
    assert {"updated_at", "source_key", "content_hash"} <= set(df_bulletins.columns)


def _read_cached(path_cache: Path, *, fn_download: Mock, dt_reference: date) -> pd.DataFrame:
    """Read the fixture period on one reference day.

    Parameters
    ----------
    path_cache : pathlib.Path
        Cache directory.
    fn_download : unittest.mock.Mock
        The counting download seam.
    dt_reference : datetime.date
        The day keying the cache.

    Returns
    -------
    pd.DataFrame
        The parsed bulletins.
    """
    return read_quote_bulletins(
        "61",
        dt_start=DT_START,
        dt_end=DT_END,
        dt_reference=dt_reference,
        path_cache_dir=path_cache,
        fn_download=fn_download,
    )


def test_read_bulletins_second_call_hits_daily_cache(tmp_path: Path) -> None:
    """Two reads on one reference day download once."""
    fn_counting = Mock(side_effect=_fake_download)
    _read_cached(tmp_path, fn_download=fn_counting, dt_reference=DT_DAY)
    _read_cached(tmp_path, fn_download=fn_counting, dt_reference=DT_DAY)
    assert fn_counting.call_count == 1


def test_read_bulletins_next_day_misses_cache(tmp_path: Path) -> None:
    """A new reference day re-downloads, so a period ending today never goes stale."""
    fn_counting = Mock(side_effect=_fake_download)
    _read_cached(tmp_path, fn_download=fn_counting, dt_reference=DT_DAY)
    _read_cached(tmp_path, fn_download=fn_counting, dt_reference=date(2026, 11, 21))
    assert fn_counting.call_count == 2


def test_read_bulletins_malformed_row_raises(tmp_path: Path) -> None:
    """A row with the wrong field count fails loudly."""
    with pytest.raises(ContractError):
        read_quote_bulletins(
            "61",
            dt_start=DT_START,
            dt_end=DT_END,
            dt_reference=DT_DAY,
            path_cache_dir=tmp_path,
            fn_download=_download_malformed,
        )


def test_read_bulletins_inverted_period_raises(tmp_path: Path) -> None:
    """A start after the end is rejected before any download."""
    with pytest.raises(ValueError):  # noqa: PT011 -- message is this project's own
        read_quote_bulletins(
            "61",
            dt_start=DT_END,
            dt_end=DT_START,
            dt_reference=DT_DAY,
            path_cache_dir=tmp_path,
            fn_download=_fake_download,
        )
