"""Unit tests for the PTAX per-currency quote reader (fixture-backed, no network)."""

from datetime import date
from decimal import Decimal
import hashlib
from pathlib import Path

import pandas as pd
import pytest

from opendata_bcb._internal.config.contracts import ContractError
from opendata_bcb.ptax import read_ptax_quotes


PATH_FIXTURE = Path(__file__).parent.parent / "fixtures" / "ptax" / "cotacao_moeda_periodo.json"

DT_REFERENCE = date(2026, 11, 20)
DT_START = date(2026, 11, 3)
DT_END = date(2026, 11, 5)


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
    """Run the reader against the fake download, on a fixed day unless the test names one."""
    dict_kwargs = {
        "dt_start": DT_START,
        "dt_end": DT_END,
        "dt_reference": DT_REFERENCE,
        **kwargs,
    }
    return read_ptax_quotes("EUR", path_cache_dir=tmp_path, fn_download=cls_fake, **dict_kwargs)


def test_read_ptax_quotes_data_columns_come_first(tmp_path: Path) -> None:
    """The six quote columns lead the frame."""
    df_quotes = _read(tmp_path, cls_fake=_FakeDownload())
    assert df_quotes.columns.tolist()[:6] == [
        "buy_parity",
        "sell_parity",
        "buy_rate",
        "sell_rate",
        "quoted_at",
        "bulletin_type",
    ]


def test_read_ptax_quotes_rates_are_decimal(tmp_path: Path) -> None:
    """Rates are exact ``Decimal`` from the source text, not float."""
    df_quotes = _read(tmp_path, cls_fake=_FakeDownload())
    assert df_quotes["buy_rate"].iloc[0] == Decimal("6.13690")


def test_read_ptax_quotes_parities_are_decimal(tmp_path: Path) -> None:
    """Parities are ``Decimal`` too."""
    df_quotes = _read(tmp_path, cls_fake=_FakeDownload())
    assert isinstance(df_quotes["sell_parity"].iloc[0], Decimal)


def test_read_ptax_quotes_quoted_at_is_datetime(tmp_path: Path) -> None:
    """``quoted_at`` is parsed to ``datetime64``."""
    df_quotes = _read(tmp_path, cls_fake=_FakeDownload())
    assert pd.api.types.is_datetime64_any_dtype(df_quotes["quoted_at"])


def test_read_ptax_quotes_keeps_all_bulletin_types(tmp_path: Path) -> None:
    """``bulletin_type`` keeps the three bulletin kinds, none is filtered out."""
    df_quotes = _read(tmp_path, cls_fake=_FakeDownload())
    assert set(df_quotes["bulletin_type"]) == {"Abertura", "Intermediário", "Fechamento"}


def test_read_ptax_quotes_stamps_provenance(tmp_path: Path) -> None:
    """Provenance columns follow the data columns."""
    df_quotes = _read(tmp_path, cls_fake=_FakeDownload())
    assert {"url", "updated_at", "content_hash"} <= set(df_quotes.columns)


def test_read_ptax_quotes_requests_quoted_currency(tmp_path: Path) -> None:
    """The URL carries the single-quoted symbol."""
    cls_fake = _FakeDownload()
    _read(tmp_path, cls_fake=cls_fake)
    assert "@moeda=%27EUR%27" in cls_fake.list_urls[0]


def test_read_ptax_quotes_requests_month_first_dates(tmp_path: Path) -> None:
    """The period is sent as ``MM-DD-YYYY``."""
    cls_fake = _FakeDownload()
    _read(tmp_path, cls_fake=cls_fake)
    assert "@dataInicial=%2711-03-2026%27" in cls_fake.list_urls[0]


def test_read_ptax_quotes_requests_period_resource(tmp_path: Path) -> None:
    """The request targets ``CotacaoMoedaPeriodo`` of the ``PTAX`` service."""
    cls_fake = _FakeDownload()
    _read(tmp_path, cls_fake=cls_fake)
    assert "/servico/PTAX/versao/v1/odata/CotacaoMoedaPeriodo" in cls_fake.list_urls[0]


def test_read_ptax_quotes_second_read_hits_cache(tmp_path: Path) -> None:
    """A repeat read the same day downloads nothing."""
    cls_fake = _FakeDownload()
    _read(tmp_path, cls_fake=cls_fake)
    _read(tmp_path, cls_fake=cls_fake)
    assert len(cls_fake.list_urls) == 1


def test_read_ptax_quotes_next_reference_day_redownloads(tmp_path: Path) -> None:
    """A later reference day refetches even for the same period."""
    cls_fake = _FakeDownload()
    _read(tmp_path, cls_fake=cls_fake, dt_reference=date(2026, 11, 20))
    _read(tmp_path, cls_fake=cls_fake, dt_reference=date(2026, 11, 21))
    assert len(cls_fake.list_urls) == 2


def test_read_ptax_quotes_cache_bypass_redownloads(tmp_path: Path) -> None:
    """``bool_use_cache=False`` fetches again."""
    cls_fake = _FakeDownload()
    _read(tmp_path, cls_fake=cls_fake)
    _read(tmp_path, cls_fake=cls_fake, bool_use_cache=False)
    assert len(cls_fake.list_urls) == 2


def test_read_ptax_quotes_inverted_period_raises(tmp_path: Path) -> None:
    """A start after the end is rejected before any download."""
    with pytest.raises(ValueError, match="after"):
        _read(tmp_path, cls_fake=_FakeDownload(), dt_start=DT_END, dt_end=DT_START)


def test_read_ptax_quotes_empty_period_raises(tmp_path: Path) -> None:
    """An empty period is a contract error, not an empty frame."""
    with pytest.raises(ContractError):
        _read(tmp_path, cls_fake=_FakeDownload('{"value": []}'))


def test_read_ptax_quotes_row_count_matches_fixture(tmp_path: Path) -> None:
    """One row per quote in the real response (count taken from the bytes)."""
    int_expected = PATH_FIXTURE.read_bytes().count(b'"tipoBoletim"')
    assert len(_read(tmp_path, cls_fake=_FakeDownload())) == int_expected


def test_read_ptax_quotes_pins_content_hash_of_real_artifact(tmp_path: Path) -> None:
    """The stamped hash is that of the fixture bytes, nobody-authored."""
    str_sha = hashlib.sha256(PATH_FIXTURE.read_bytes()).hexdigest()
    assert _read(tmp_path, cls_fake=_FakeDownload())["content_hash"].iloc[0] == str_sha
