"""Unit tests for the PTAX USD/BRL reader (fixture-backed, no network)."""

from datetime import date
from decimal import Decimal
from pathlib import Path

import pandas as pd
import pytest

from opendata_bcb._internal.config.contracts import ContractError
from opendata_bcb.ptax import read_ptax_usd_brl


PATH_FIXTURE = Path(__file__).parent.parent / "fixtures" / "ptax" / "cotacao_dolar_periodo.json"
DT_START = date(2026, 11, 3)
DT_END = date(2026, 11, 5)
LIST_PROVENANCE = ["url", "updated_at", "source_key", "package_version", "ingestion_run_id"]


class _FakeDownload:
    """Download stand-in serving the real fixture and recording each requested URL."""

    def __init__(self, str_body: str | None = None) -> None:
        """Remember the body to serve, the fixture by default."""
        self.str_body = str_body or PATH_FIXTURE.read_text(encoding="utf-8")
        self.list_urls: list[str] = []

    def __call__(self, *, str_url: str, path_dest: Path) -> Path:
        """Write the body to ``path_dest``."""
        self.list_urls.append(str_url)
        path_dest.write_bytes(self.str_body.encode("utf-8"))
        return path_dest


def _read(tmp_path: Path, *, cls_fake: _FakeDownload, **kwargs: object) -> pd.DataFrame:
    """Run the reader against the fake download."""
    return read_ptax_usd_brl(
        dt_start=DT_START, dt_end=DT_END, path_cache_dir=tmp_path, fn_download=cls_fake, **kwargs
    )


def test_read_ptax_usd_brl_rates_are_exact_decimals(tmp_path: Path) -> None:
    """Rates keep the source's text, trailing zero included."""
    df_ptax = _read(tmp_path, cls_fake=_FakeDownload())
    assert df_ptax["buy_rate"].tolist() == [
        Decimal("5.49290"),
        Decimal("5.47720"),
        Decimal("5.46150"),
    ]


def test_read_ptax_usd_brl_rates_are_not_floats(tmp_path: Path) -> None:
    """No cell went through ``float``."""
    df_ptax = _read(tmp_path, cls_fake=_FakeDownload())
    assert {type(v) for v in df_ptax["sell_rate"]} == {Decimal}


def test_read_ptax_usd_brl_keeps_time_of_day(tmp_path: Path) -> None:
    """``quoted_at`` carries the bulletin's time, microseconds included."""
    df_ptax = _read(tmp_path, cls_fake=_FakeDownload())
    assert df_ptax["quoted_at"].iloc[0] == pd.Timestamp("2026-11-03 13:06:31.943412")


def test_read_ptax_usd_brl_data_columns_come_first(tmp_path: Path) -> None:
    """The three quote columns lead the frame."""
    df_ptax = _read(tmp_path, cls_fake=_FakeDownload())
    assert df_ptax.columns.tolist()[:3] == ["buy_rate", "sell_rate", "quoted_at"]


def test_read_ptax_usd_brl_stamps_provenance(tmp_path: Path) -> None:
    """Provenance columns follow the data columns."""
    df_ptax = _read(tmp_path, cls_fake=_FakeDownload())
    assert set(LIST_PROVENANCE) <= set(df_ptax.columns)


def test_read_ptax_usd_brl_requests_month_first_dates(tmp_path: Path) -> None:
    """Olinda wants ``MM-DD-YYYY`` in the function-import parameters."""
    cls_fake = _FakeDownload()
    _read(tmp_path, cls_fake=cls_fake)
    assert "@dataInicial=%2711-03-2026%27" in cls_fake.list_urls[0]


def test_read_ptax_usd_brl_second_read_hits_cache(tmp_path: Path) -> None:
    """A repeat read the same day downloads nothing."""
    cls_fake = _FakeDownload()
    _read(tmp_path, cls_fake=cls_fake)
    _read(tmp_path, cls_fake=cls_fake)
    assert len(cls_fake.list_urls) == 1


def test_read_ptax_usd_brl_cache_bypass_redownloads(tmp_path: Path) -> None:
    """``bool_use_cache=False`` fetches again."""
    cls_fake = _FakeDownload()
    _read(tmp_path, cls_fake=cls_fake)
    _read(tmp_path, cls_fake=cls_fake, bool_use_cache=False)
    assert len(cls_fake.list_urls) == 2


def test_read_ptax_usd_brl_empty_period_raises(tmp_path: Path) -> None:
    """A period without quotes is a contract error, not an empty frame."""
    with pytest.raises(ContractError):
        _read(tmp_path, cls_fake=_FakeDownload('{"value": []}'))


def test_read_ptax_usd_brl_reversed_range_raises(tmp_path: Path) -> None:
    """A start after the end is rejected before any download."""
    with pytest.raises(ValueError, match="is after"):
        read_ptax_usd_brl(dt_start=DT_END, dt_end=DT_START, path_cache_dir=tmp_path)
