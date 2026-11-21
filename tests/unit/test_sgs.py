"""Unit tests for the SGS reader, fed by fixtures through the download seam."""

from datetime import date
from decimal import Decimal
import hashlib
from pathlib import Path

import pandas as pd
import pytest

from opendata_bcb import sgs


PATH_FIXTURES = Path(__file__).parent.parent / "fixtures" / "sgs"


class _FakeDownload:
    """Download seam that copies a fixture and records the requested URLs."""

    def __init__(self, path_fixture: Path) -> None:
        """Remember which fixture to serve."""
        self.path_fixture = path_fixture
        self.list_urls: list[str] = []

    def __call__(self, *, str_url: str, path_dest: Path) -> Path:
        """Write the fixture bytes to the destination."""
        self.list_urls.append(str_url)
        path_dest.write_bytes(self.path_fixture.read_bytes())
        return path_dest


@pytest.fixture
def cls_fake(tmp_path: Path) -> _FakeDownload:
    """Serve the series-1 fixture; ``tmp_path`` is unused here but keeps isolation explicit."""
    return _FakeDownload(PATH_FIXTURES / "serie_1_valores.json")


@pytest.fixture
def df_values(*, tmp_path: Path, cls_fake: _FakeDownload) -> pd.DataFrame:
    """Read the series-1 fixture over a 10-day range."""
    return sgs.read_sgs_series(
        1,
        dt_start=date(2026, 11, 1),
        dt_end=date(2026, 11, 10),
        path_cache_dir=tmp_path,
        fn_download=cls_fake,
    )


def test_read_sgs_series_value_is_exact_decimal(df_values: pd.DataFrame) -> None:
    """The first value keeps the source scale as a Decimal."""
    assert df_values["valor"].iloc[0] == Decimal("5.4935")


def test_read_sgs_series_date_is_parsed(df_values: pd.DataFrame) -> None:
    """``dd/mm/yyyy`` becomes a date."""
    assert df_values["data"].iloc[0] == date(2026, 11, 3)


def test_read_sgs_series_row_count(df_values: pd.DataFrame) -> None:
    """Every fixture row is returned."""
    assert len(df_values) == 6


def test_read_sgs_series_has_provenance(df_values: pd.DataFrame) -> None:
    """Provenance columns are stamped."""
    assert "content_hash" in df_values.columns


def test_read_sgs_series_formats_source_url(
    *, df_values: pd.DataFrame, cls_fake: _FakeDownload
) -> None:
    """The request carries code and dd/mm/yyyy bounds."""
    assert cls_fake.list_urls == [
        "https://api.bcb.gov.br/dados/serie/bcdata.sgs.1/dados"
        "?formato=json&dataInicial=01/11/2026&dataFinal=10/11/2026"
    ]


def test_read_sgs_series_splits_long_range(tmp_path: Path) -> None:
    """A 25-year range needs three windows, hence three requests."""
    cls_fake = _FakeDownload(PATH_FIXTURES / "serie_1_valores.json")
    sgs.read_sgs_series(
        1,
        dt_start=date(2000, 1, 1),
        dt_end=date(2025, 1, 1),
        path_cache_dir=tmp_path,
        fn_download=cls_fake,
    )
    assert len(cls_fake.list_urls) == 3


def test_split_windows_rejects_inverted_range() -> None:
    """Start after end is an error."""
    with pytest.raises(ValueError, match="after"):
        sgs._split_windows(date(2026, 1, 2), dt_end=date(2026, 1, 1))


def test_split_windows_are_contiguous() -> None:
    """The second window starts the day after the first ends."""
    list_windows = sgs._split_windows(date(2000, 1, 1), dt_end=date(2025, 1, 1))
    assert list_windows[1][0] - list_windows[0][1] == date(2000, 1, 2) - date(2000, 1, 1)


def test_read_sgs_series_stamps_sha256_of_fixture_bytes(df_values: pd.DataFrame) -> None:
    """A single-window read stamps the sha256 of the bytes it parsed."""
    _bytes_fixture = (PATH_FIXTURES / "serie_1_valores.json").read_bytes()
    assert df_values["content_hash"].iloc[0] == hashlib.sha256(_bytes_fixture).hexdigest()


def _read_series(
    *, cls_fake: _FakeDownload, path_cache_dir: Path | None, dt_reference: date, dt_end: date
) -> pd.DataFrame:
    """Read series 1 from 2026-11-01 with the given cache arguments."""
    return sgs.read_sgs_series(
        1,
        dt_start=date(2026, 11, 1),
        dt_end=dt_end,
        dt_reference=dt_reference,
        path_cache_dir=path_cache_dir,
        fn_download=cls_fake,
    )


def test_read_sgs_series_defaults_cache_dir_under_temp(
    *, tmp_path: Path, cls_fake: _FakeDownload, monkeypatch: pytest.MonkeyPatch
) -> None:
    """With no cache directory, the window lands under the system temp directory."""
    monkeypatch.setattr(sgs.tempfile, "gettempdir", lambda: str(tmp_path))
    _read_series(
        cls_fake=cls_fake,
        path_cache_dir=None,
        dt_reference=date(2026, 11, 20),
        dt_end=date(2026, 11, 10),
    )
    assert len(list((tmp_path / "opendata-bcb-cache").glob("sgs-1-*.json"))) == 1


def test_read_sgs_series_same_reference_day_hits_cache(
    *, tmp_path: Path, cls_fake: _FakeDownload
) -> None:
    """A second read on the same reference day downloads nothing."""
    _read_series(
        cls_fake=cls_fake,
        path_cache_dir=tmp_path,
        dt_reference=date(2026, 11, 20),
        dt_end=date(2026, 11, 10),
    )
    _read_series(
        cls_fake=cls_fake,
        path_cache_dir=tmp_path,
        dt_reference=date(2026, 11, 20),
        dt_end=date(2026, 11, 10),
    )
    assert len(cls_fake.list_urls) == 1


def test_read_sgs_series_later_reference_day_downloads_again(
    *, tmp_path: Path, cls_fake: _FakeDownload
) -> None:
    """A later reference day re-fetches the window, so a BCB revision is picked up."""
    _read_series(
        cls_fake=cls_fake,
        path_cache_dir=tmp_path,
        dt_reference=date(2026, 11, 20),
        dt_end=date(2026, 11, 10),
    )
    _read_series(
        cls_fake=cls_fake,
        path_cache_dir=tmp_path,
        dt_reference=date(2026, 11, 21),
        dt_end=date(2026, 11, 10),
    )
    assert len(cls_fake.list_urls) == 2


def test_read_sgs_series_other_end_date_misses_cache(
    *, tmp_path: Path, cls_fake: _FakeDownload
) -> None:
    """Same start and day but a different end is a different window, not a cache hit."""
    _read_series(
        cls_fake=cls_fake,
        path_cache_dir=tmp_path,
        dt_reference=date(2026, 11, 20),
        dt_end=date(2026, 11, 10),
    )
    _read_series(
        cls_fake=cls_fake,
        path_cache_dir=tmp_path,
        dt_reference=date(2026, 11, 20),
        dt_end=date(2026, 11, 12),
    )
    assert len(cls_fake.list_urls) == 2
