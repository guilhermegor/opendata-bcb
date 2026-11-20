"""Unit tests for the bank registry reader (fixture-backed, no network)."""

from datetime import date
from pathlib import Path
import shutil
from unittest.mock import Mock

import pandas as pd
import pytest

from opendata_bcb._internal.utils.tabular_reader import ContractError
from opendata_bcb.ingestion.banks import URL_BANKS, read_banks


PATH_FIXTURE = Path(__file__).parent.parent / "fixtures" / "banks" / "participantes_str.csv"
DT_DAY = date(2026, 11, 20)


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
    path_dest.write_text("ISPB,Nome_Reduzido\n00000000,X\n", encoding="utf-8")
    return path_dest


@pytest.fixture
def df_banks(tmp_path: Path) -> pd.DataFrame:
    """Read the fixture through the public function.

    Parameters
    ----------
    tmp_path : pathlib.Path
        Per-test cache directory.

    Returns
    -------
    pd.DataFrame
        The parsed registry.
    """
    return read_banks(dt_reference=DT_DAY, path_cache_dir=tmp_path, fn_download=_fake_download)


def test_read_banks_ispb_keeps_leading_zeros(df_banks: pd.DataFrame) -> None:
    """The ISPB stays an 8-digit string, never an integer."""
    assert df_banks["ispb"].tolist()[:2] == ["00000000", "00000208"]


def test_read_banks_compe_code_is_three_digit_string(df_banks: pd.DataFrame) -> None:
    """COMPE codes are zero-padded to 3 digits (the source writes ``0`` for B3)."""
    assert df_banks["compe_code"].dropna().tolist() == ["001", "070", "000"]


def test_read_banks_compe_not_applicable_becomes_na(df_banks: pd.DataFrame) -> None:
    """``n/a`` in the source becomes a missing value, not a string."""
    assert df_banks["compe_code"].isna().sum() == 2


def test_read_banks_compe_flag_is_boolean(df_banks: pd.DataFrame) -> None:
    """``Sim``/``Não`` become real booleans."""
    assert df_banks["participates_in_compe"].tolist() == [True, True, False, False, False]


def test_read_banks_operation_start_parsed_day_first(df_banks: pd.DataFrame) -> None:
    """``22/04/2002`` is April 22nd, not an invalid month."""
    assert df_banks["operation_start"].iloc[0] == date(2002, 4, 22)


def test_read_banks_names_keep_accents(df_banks: pd.DataFrame) -> None:
    """UTF-8 with BOM decodes cleanly."""
    assert "Balcão B3" in df_banks["short_name"].tolist()


def test_read_banks_stamps_provenance_url(df_banks: pd.DataFrame) -> None:
    """Every row carries the source URL."""
    assert df_banks["url"].unique().tolist() == [URL_BANKS]


def test_read_banks_stamps_provenance_columns(df_banks: pd.DataFrame) -> None:
    """The fetch time, source key and content hash are present."""
    assert {"updated_at", "source_key", "content_hash"} <= set(df_banks.columns)


def test_read_banks_second_call_hits_daily_cache(tmp_path: Path) -> None:
    """Two reads on one reference day download once."""
    fn_counting = Mock(side_effect=_fake_download)
    read_banks(dt_reference=DT_DAY, path_cache_dir=tmp_path, fn_download=fn_counting)
    read_banks(dt_reference=DT_DAY, path_cache_dir=tmp_path, fn_download=fn_counting)
    assert fn_counting.call_count == 1


def test_read_banks_missing_column_raises(tmp_path: Path) -> None:
    """A source that dropped contract columns fails loudly."""
    with pytest.raises(ContractError):
        read_banks(dt_reference=DT_DAY, path_cache_dir=tmp_path, fn_download=_broken_download)
