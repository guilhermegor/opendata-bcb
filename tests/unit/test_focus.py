"""Unit tests for the Focus annual expectations reader, fed by a real trimmed response."""

from datetime import date
from decimal import Decimal
from pathlib import Path

import pandas as pd
import pytest

from opendata_bcb import read_focus_annual_expectations


PATH_FIXTURE = (
    Path(__file__).parent.parent / "fixtures" / "focus" / "expectativas_mercado_anuais_ipca.json"
)


class _FakeDownload:
    """Download seam that serves the fixture and records the requested URLs."""

    def __init__(self) -> None:
        """Start with no requests recorded."""
        self.list_urls: list[str] = []

    def __call__(self, *, str_url: str, path_dest: Path) -> Path:
        """Write the fixture bytes to the destination."""
        self.list_urls.append(str_url)
        path_dest.write_bytes(PATH_FIXTURE.read_bytes())
        return path_dest


@pytest.fixture
def cls_fake() -> _FakeDownload:
    """Provide a fresh download seam."""
    return _FakeDownload()


@pytest.fixture
def df_focus(*, tmp_path: Path, cls_fake: _FakeDownload) -> pd.DataFrame:
    """Read the IPCA fixture (6 rows, fewer than the page size, so one page)."""
    return read_focus_annual_expectations(
        "IPCA",
        dt_start=date(2026, 11, 9),
        dt_end=date(2026, 11, 13),
        path_cache_dir=tmp_path,
        fn_download=cls_fake,
    )


def test_read_focus_mean_is_exact_decimal(df_focus: pd.DataFrame) -> None:
    """The mean keeps the source scale as a Decimal."""
    assert df_focus["Media"].iloc[0] == Decimal("5.2163")


def test_read_focus_median_keeps_trailing_zeros(df_focus: pd.DataFrame) -> None:
    """A source ``4.0000`` keeps its four-digit scale."""
    assert str(df_focus["Mediana"].iloc[2]) == "4.0000"


def test_read_focus_std_is_decimal(df_focus: pd.DataFrame) -> None:
    """The standard deviation is a Decimal, never a float."""
    assert isinstance(df_focus["DesvioPadrao"].iloc[0], Decimal)


def test_read_focus_respondents_is_int(df_focus: pd.DataFrame) -> None:
    """The respondent count is an integer."""
    assert df_focus["numeroRespondentes"].iloc[0] == 146


def test_read_focus_date_is_parsed(df_focus: pd.DataFrame) -> None:
    """``Data`` becomes a date."""
    assert df_focus["Data"].iloc[0] == date(2026, 11, 9)


def test_read_focus_row_count(df_focus: pd.DataFrame) -> None:
    """Every fixture row is returned."""
    assert len(df_focus) == 6


def test_read_focus_has_provenance(df_focus: pd.DataFrame) -> None:
    """Provenance columns are stamped."""
    assert "content_hash" in df_focus.columns


def test_read_focus_filters_indicator_and_range(
    *, df_focus: pd.DataFrame, cls_fake: _FakeDownload
) -> None:
    """The request filters by indicator and the Data range."""
    assert (
        "Indicador%20eq%20%27IPCA%27%20and%20Data%20ge%20%272026-11-09%27"
        "%20and%20Data%20le%20%272026-11-13%27"
    ) in cls_fake.list_urls[0]


def test_read_focus_rejects_inverted_range(tmp_path: Path) -> None:
    """A start after the end is refused before any request."""
    with pytest.raises(ValueError, match="after"):
        read_focus_annual_expectations(
            "IPCA", dt_start=date(2026, 11, 13), dt_end=date(2026, 11, 9), path_cache_dir=tmp_path
        )
