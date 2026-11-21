"""Unit tests for the SGS metadata reader, pinned to a real WebService capture."""

from datetime import date
import hashlib
from pathlib import Path

import pandas as pd
import pytest

from opendata_bcb import sgs


PATH_FIXTURE = Path(__file__).parent.parent / "fixtures" / "sgs" / "serie_433_ultimo_valor.xml"
DT_REFERENCE = date(2026, 11, 20)


class _FakeDownload:
    """Download seam that copies the fixture and records the requested URLs."""

    def __init__(self) -> None:
        """Start with no requests."""
        self.list_urls: list[str] = []

    def __call__(self, *, str_url: str, path_dest: Path) -> Path:
        """Write the fixture bytes to the destination."""
        self.list_urls.append(str_url)
        path_dest.write_bytes(PATH_FIXTURE.read_bytes())
        return path_dest


def _download_return_without_declaration(*, str_url: str, path_dest: Path) -> Path:
    """Write an envelope whose return text has no XML declaration and no series."""
    path_dest.write_bytes(b"<e><getUltimoValorXMLReturn>&lt;x/&gt;</getUltimoValorXMLReturn></e>")
    return path_dest


def _download_garbage(*, str_url: str, path_dest: Path) -> Path:
    """Write a body that is not an SGS response."""
    path_dest.write_bytes(b"<a><b/></a>")
    return path_dest


@pytest.fixture
def cls_fake() -> _FakeDownload:
    """Build a fresh fake seam."""
    return _FakeDownload()


@pytest.fixture
def df_meta(*, tmp_path: Path, cls_fake: _FakeDownload) -> pd.DataFrame:
    """Read series 433 through the fake seam."""
    return sgs.read_sgs_metadata(
        433, path_cache_dir=tmp_path, dt_reference=DT_REFERENCE, fn_download=cls_fake
    )


def test_metadata_name_is_decoded(df_meta: pd.DataFrame) -> None:
    """Accents survive the double decode."""
    assert df_meta["name"].iloc[0] == "Índice nacional de preços ao consumidor-amplo (IPCA)"


def test_metadata_periodicity(df_meta: pd.DataFrame) -> None:
    """The source letter code is kept."""
    assert df_meta["periodicity"].iloc[0] == "M"


def test_metadata_unit(df_meta: pd.DataFrame) -> None:
    """The unit is read as served."""
    assert df_meta["unit"].iloc[0] == "Var. % mensal"


def test_metadata_code_is_int(df_meta: pd.DataFrame) -> None:
    """The code is typed as an integer."""
    assert df_meta["code"].iloc[0] == 433


def test_metadata_content_hash_is_fixture_sha256(df_meta: pd.DataFrame) -> None:
    """The hash is that of the captured bytes, not of anything the parser produced."""
    assert df_meta["content_hash"].iloc[0] == hashlib.sha256(PATH_FIXTURE.read_bytes()).hexdigest()


def test_metadata_name_comes_from_fixture_bytes(df_meta: pd.DataFrame) -> None:
    """The unaccented tail of the name is literally present in the captured bytes."""
    assert b"consumidor-amplo (IPCA)" in PATH_FIXTURE.read_bytes()


def test_metadata_requests_code_url(*, df_meta: pd.DataFrame, cls_fake: _FakeDownload) -> None:
    """The request names the method and the code."""
    assert cls_fake.list_urls == [
        "https://www3.bcb.gov.br/wssgs/services/FachadaWSSGS?method=getUltimoValorXML&in0=433"
    ]


def test_metadata_second_read_hits_cache(*, tmp_path: Path, cls_fake: _FakeDownload) -> None:
    """A same-day second read does not download again."""
    sgs.read_sgs_metadata(
        433, path_cache_dir=tmp_path, dt_reference=DT_REFERENCE, fn_download=cls_fake
    )
    sgs.read_sgs_metadata(
        433, path_cache_dir=tmp_path, dt_reference=DT_REFERENCE, fn_download=cls_fake
    )
    assert len(cls_fake.list_urls) == 1


def test_metadata_rejects_response_without_series(tmp_path: Path) -> None:
    """A SOAP body without a return element is an error."""
    with pytest.raises(ValueError, match="no series"):
        sgs.read_sgs_metadata(
            1, path_cache_dir=tmp_path, dt_reference=DT_REFERENCE, fn_download=_download_garbage
        )


def test_metadata_return_without_declaration_raises_value_error(tmp_path: Path) -> None:
    """A return text lacking the ``?>`` declaration is still a ValueError, not an IndexError."""
    with pytest.raises(ValueError, match="no series"):
        sgs.read_sgs_metadata(
            1,
            path_cache_dir=tmp_path,
            dt_reference=DT_REFERENCE,
            fn_download=_download_return_without_declaration,
        )
