"""Unit tests for the PTAX currency-list reader (fixture-backed, no network)."""

from datetime import date
import hashlib
from pathlib import Path

import pandas as pd
import pytest

from opendata_bcb._internal.config.contracts import ContractError
from opendata_bcb.ptax import read_ptax_currencies


PATH_FIXTURE = Path(__file__).parent.parent / "fixtures" / "ptax" / "moedas.json"
LIST_PROVENANCE = ["url", "updated_at", "source_key", "package_version", "ingestion_run_id"]

DT_REFERENCE = date(2026, 11, 20)


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
    dict_kwargs = {"dt_reference": DT_REFERENCE, **kwargs}
    return read_ptax_currencies(path_cache_dir=tmp_path, fn_download=cls_fake, **dict_kwargs)


def test_read_ptax_currencies_data_columns_come_first(tmp_path: Path) -> None:
    """The three currency columns lead the frame."""
    df_currencies = _read(tmp_path, cls_fake=_FakeDownload())
    assert df_currencies.columns.tolist()[:3] == ["symbol", "name", "currency_type"]


def test_read_ptax_currencies_keeps_accented_names(tmp_path: Path) -> None:
    """Names keep the source's Portuguese spelling."""
    df_currencies = _read(tmp_path, cls_fake=_FakeDownload())
    assert df_currencies["name"].iloc[0] == "Dólar australiano"


def test_read_ptax_currencies_stamps_provenance(tmp_path: Path) -> None:
    """Provenance columns follow the data columns."""
    df_currencies = _read(tmp_path, cls_fake=_FakeDownload())
    assert set(LIST_PROVENANCE) <= set(df_currencies.columns)


def test_read_ptax_currencies_requests_moedas_resource(tmp_path: Path) -> None:
    """The request targets the ``Moedas`` resource of the ``PTAX`` service."""
    cls_fake = _FakeDownload()
    _read(tmp_path, cls_fake=cls_fake)
    assert "/servico/PTAX/versao/v1/odata/Moedas" in cls_fake.list_urls[0]


def test_read_ptax_currencies_second_read_hits_cache(tmp_path: Path) -> None:
    """A repeat read the same day downloads nothing."""
    cls_fake = _FakeDownload()
    _read(tmp_path, cls_fake=cls_fake)
    _read(tmp_path, cls_fake=cls_fake)
    assert len(cls_fake.list_urls) == 1


def test_read_ptax_currencies_cache_bypass_redownloads(tmp_path: Path) -> None:
    """``bool_use_cache=False`` fetches again."""
    cls_fake = _FakeDownload()
    _read(tmp_path, cls_fake=cls_fake)
    _read(tmp_path, cls_fake=cls_fake, bool_use_cache=False)
    assert len(cls_fake.list_urls) == 2


def test_read_ptax_currencies_next_day_redownloads(tmp_path: Path) -> None:
    """A read on a later reference day is fetched again."""
    cls_fake = _FakeDownload()
    _read(tmp_path, cls_fake=cls_fake, dt_reference=date(2026, 11, 20))
    _read(tmp_path, cls_fake=cls_fake, dt_reference=date(2026, 11, 21))
    assert len(cls_fake.list_urls) == 2


def test_read_ptax_currencies_empty_list_raises(tmp_path: Path) -> None:
    """An empty list is a contract error, not an empty frame."""
    with pytest.raises(ContractError):
        _read(tmp_path, cls_fake=_FakeDownload('{"value": []}'))


def test_read_ptax_currencies_row_count_matches_fixture(tmp_path: Path) -> None:
    """One row per currency in the real response (count taken from the bytes)."""
    int_expected = PATH_FIXTURE.read_bytes().count(b'"simbolo"')
    assert len(_read(tmp_path, cls_fake=_FakeDownload())) == int_expected


def test_read_ptax_currencies_pins_content_hash_of_real_artifact(tmp_path: Path) -> None:
    """The stamped hash is that of the fixture bytes, nobody-authored."""
    str_sha = hashlib.sha256(PATH_FIXTURE.read_bytes()).hexdigest()
    assert _read(tmp_path, cls_fake=_FakeDownload())["content_hash"].iloc[0] == str_sha
