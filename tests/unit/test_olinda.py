"""Unit tests for the shared Olinda OData client.

Grounded in real responses saved under ``tests/fixtures/olinda/``. The download seam is
replaced by a stand-in that serves fixture bytes and records the URLs, so nothing touches the
network.
"""

import contextlib
from datetime import date
from decimal import Decimal
import hashlib
from pathlib import Path

import pandas as pd
import pytest

from opendata_bcb._internal.config.contracts import PTAX_USD_BRL, ContractError, FileContract
from opendata_bcb._internal.olinda import (
    OlindaError,
    build_url,
    fetch_frame,
    parse_page,
    parse_payload,
)


_FIXTURES = Path(__file__).parent.parent / "fixtures" / "olinda"
_PARAMS = {"dataInicial": "11-03-2026", "dataFinalCotacao": "11-04-2026"}


def _fixture_text(str_name: str) -> str:
    """Read one fixture file."""
    return (_FIXTURES / str_name).read_text(encoding="utf-8")


class _FakeDownload:
    """Download stand-in serving queued bodies and recording each requested URL."""

    def __init__(self, list_bodies: list[str]) -> None:
        """Queue the bodies to serve, one per call."""
        self.list_bodies = list(list_bodies)
        self.list_urls: list[str] = []

    def __call__(self, *, str_url: str, path_dest: Path) -> Path:
        """Write the next body to ``path_dest``."""
        self.list_urls.append(str_url)
        path_dest.write_bytes(self.list_bodies.pop(0).encode("utf-8"))
        return path_dest


def _fetch(cls_fake: _FakeDownload, *, path_cache: Path, **kwargs: object) -> pd.DataFrame:
    """Run ``fetch_frame`` for PTAX against the fake download."""
    return fetch_frame(
        "PTAX",
        "CotacaoDolarPeriodo",
        cls_contract=PTAX_USD_BRL,
        path_cache_dir=path_cache,
        dt_reference=date(2026, 11, 4),
        dict_params=_PARAMS,
        fn_download=cls_fake,
        **kwargs,
    )


def test_build_url_function_import_matches_real_request() -> None:
    """The URL equals the one the real fixture was downloaded with."""
    str_url = build_url(
        "PTAX",
        "CotacaoDolarPeriodo",
        dict_params=_PARAMS,
        str_select="cotacaoCompra,cotacaoVenda,dataHoraCotacao",
        int_top=100,
    )
    assert str_url == (
        "https://olinda.bcb.gov.br/olinda/servico/PTAX/versao/v1/odata/"
        "CotacaoDolarPeriodo(dataInicial=@dataInicial,dataFinalCotacao=@dataFinalCotacao)"
        "?@dataInicial=%2711-03-2026%27&@dataFinalCotacao=%2711-04-2026%27"
        "&$select=cotacaoCompra,cotacaoVenda,dataHoraCotacao&$top=100&$format=json"
    )


def test_build_url_entity_set_with_filter_and_paging() -> None:
    """An entity set has no parentheses; filter is encoded, paging options included."""
    str_url = build_url(
        "Expectativas",
        "ExpectativasMercadoAnuais",
        str_filter="Indicador eq 'IPCA'",
        int_top=10,
        int_skip=20,
    )
    assert str_url.endswith(
        "/ExpectativasMercadoAnuais?$filter=Indicador%20eq%20%27IPCA%27&$top=10&$skip=20&$format=json"
    )


def test_parse_payload_keeps_exact_decimals() -> None:
    """Rates are Decimal built from the source text, trailing zero preserved."""
    list_rows = parse_payload(_fixture_text("ptax_usd_brl.json"))
    assert repr(list_rows[0]["cotacaoCompra"]) == "Decimal('5.49290')"


def test_parse_payload_rejects_real_error_body() -> None:
    """The real 400 body (comment-wrapped codigo/mensagem) raises, never returns empty."""
    with pytest.raises(OlindaError, match="Olinda returned an error"):
        parse_payload(_fixture_text("error_unknown_resource.txt"))


def test_parse_payload_rejects_odata_error_envelope() -> None:
    """The OData-spec error envelope raises too."""
    with pytest.raises(OlindaError):
        parse_payload('{"odata.error": {"code": "1"}}')


@pytest.mark.parametrize("str_body", ["<html>", "[]", '{"other": 1}'])
def test_parse_payload_rejects_malformed_bodies(str_body: str) -> None:
    """Non-JSON, non-object and value-less payloads are loud failures."""
    with pytest.raises(OlindaError):
        parse_payload(str_body)


@pytest.fixture
def df_rates(tmp_path: Path) -> pd.DataFrame:
    """Fetch the real PTAX fixture through the client.

    Parameters
    ----------
    tmp_path : pathlib.Path
        Disposable cache directory.

    Returns
    -------
    pd.DataFrame
        The stamped frame.
    """
    return _fetch(_FakeDownload([_fixture_text("ptax_usd_brl.json")]), path_cache=tmp_path)


def test_fetch_frame_columns_are_source_then_provenance(df_rates: pd.DataFrame) -> None:
    """Source columns come first, provenance columns after."""
    assert list(df_rates.columns) == [
        *PTAX_USD_BRL.tuple_required,
        *FileContract.PROVENANCE_COLUMNS,
    ]


def test_fetch_frame_cells_are_exact_decimals(df_rates: pd.DataFrame) -> None:
    """Rate cells are Decimal built from the source text."""
    assert df_rates["cotacaoVenda"].tolist() == [Decimal("5.49350"), Decimal("5.47780")]


def test_fetch_frame_stamps_source_key(df_rates: pd.DataFrame) -> None:
    """Every row carries the contract's source key."""
    assert df_rates["source_key"].unique().tolist() == ["bcb_olinda_ptax_usd_brl"]


def test_fetch_frame_pages_until_short_page(tmp_path: Path) -> None:
    """A full page triggers the next ``$skip``; a short page stops the loop."""
    str_body = _fixture_text("ptax_usd_brl.json")
    str_short = '{"value": [{"cotacaoCompra": 1.5, "cotacaoVenda": 1.6, "dataHoraCotacao": "x"}]}'
    cls_fake = _FakeDownload([str_body, str_short])
    df_paged = _fetch(cls_fake, path_cache=tmp_path, int_page_size=2)
    assert (len(df_paged), ["$skip=2" in str_url for str_url in cls_fake.list_urls]) == (
        3,
        [False, True],
    )


def test_fetch_frame_serves_second_call_from_cache(tmp_path: Path) -> None:
    """The daily cache means the second read downloads nothing."""
    cls_fake = _FakeDownload([_fixture_text("ptax_usd_brl.json")])
    _fetch(cls_fake, path_cache=tmp_path)
    _fetch(cls_fake, path_cache=tmp_path)
    assert len(cls_fake.list_urls) == 1


def test_fetch_frame_empty_result_violates_contract(tmp_path: Path) -> None:
    """An empty ``value`` array is a contract error, not a silent empty frame."""
    cls_fake = _FakeDownload(['{"value": []}'])
    with pytest.raises(ContractError):
        _fetch(cls_fake, path_cache=tmp_path)


def test_build_url_doubles_apostrophes_in_string_params() -> None:
    """An embedded apostrophe cannot terminate the OData literal."""
    assert "%27O%27%27Neil%27" in build_url("S", "R", dict_params={"name": "O'Neil"})


@pytest.mark.parametrize("str_body", ['{"value": [null]}', '{"value": [{"a": 1}, 3]}'])
def test_parse_payload_rejects_non_object_rows(str_body: str) -> None:
    """Every element is checked, not a sample."""
    with pytest.raises(OlindaError, match="array of objects"):
        parse_payload(str_body)


def test_parse_payload_empty_value_is_valid() -> None:
    """An empty page is legitimate for the pager."""
    assert parse_payload('{"value": []}') == []


def test_parse_page_returns_next_link() -> None:
    """The opaque next link is surfaced when present."""
    str_link = "https://olinda.bcb.gov.br/olinda/servico/X/versao/v1/odata/R?$skip=2"
    assert parse_page('{"value": [], "@odata.nextLink": "' + str_link + '"}')[1] == str_link


def test_parse_page_rejects_foreign_next_link() -> None:
    """A link off the Olinda host is refused."""
    with pytest.raises(OlindaError, match="next link"):
        parse_page('{"value": [], "@odata.nextLink": "http://evil.example/x"}')


def test_fetch_frame_follows_next_link_on_short_page(tmp_path: Path) -> None:
    """A link on a short page is followed; the last page has none."""
    str_link = "https://olinda.bcb.gov.br/olinda/servico/PTAX/versao/v1/odata/R?$skiptoken=1"
    str_row = '{"cotacaoCompra": 1.5, "cotacaoVenda": 1.6, "dataHoraCotacao": "x"}'
    cls_fake = _FakeDownload(
        [
            '{"value": [' + str_row + '], "@odata.nextLink": "' + str_link + '"}',
            '{"value": [' + str_row + "]}",
        ]
    )
    df_linked = _fetch(cls_fake, path_cache=tmp_path, int_page_size=5)
    assert (len(df_linked), cls_fake.list_urls[1]) == (2, str_link)


@pytest.mark.parametrize("int_size", [0, -1])
def test_fetch_frame_rejects_non_positive_page_size(  # noqa: PLR0917 -- pytest fixture + param
    tmp_path: Path, int_size: int
) -> None:
    """No request is made with a page size that cannot advance."""
    cls_fake = _FakeDownload([])
    with pytest.raises(OlindaError, match="must be positive"):
        _fetch(cls_fake, path_cache=tmp_path, int_page_size=int_size)


def test_fetch_frame_malformed_page_raises(tmp_path: Path) -> None:
    """A malformed page is a loud failure."""
    with pytest.raises(OlindaError, match="not JSON"):
        _fetch(_FakeDownload(["not json"]), path_cache=tmp_path)


def test_fetch_frame_malformed_page_is_not_cached(tmp_path: Path) -> None:
    """A rejected page is not published, so the retry downloads it again."""
    cls_fake = _FakeDownload(["not json", _fixture_text("ptax_usd_brl.json")])
    with contextlib.suppress(OlindaError):
        _fetch(cls_fake, path_cache=tmp_path)
    _fetch(cls_fake, path_cache=tmp_path)
    assert len(cls_fake.list_urls) == 2


def test_fetch_frame_hash_covers_the_parsed_bytes(tmp_path: Path) -> None:
    """The content hash is the sha256 of the page bytes that were parsed."""
    str_body = _fixture_text("ptax_usd_brl.json")
    df_hashed = _fetch(_FakeDownload([str_body]), path_cache=tmp_path)
    assert df_hashed["content_hash"].iloc[0] == hashlib.sha256(str_body.encode()).hexdigest()


def test_fetch_frame_rejects_source_field_named_like_provenance(tmp_path: Path) -> None:
    """A source ``url`` field is refused rather than overwritten."""
    str_row = '{"cotacaoCompra": 1, "cotacaoVenda": 1, "dataHoraCotacao": "x", "url": "u"}'
    with pytest.raises(OlindaError, match="collide"):
        _fetch(_FakeDownload(['{"value": [' + str_row + "]}"]), path_cache=tmp_path)
