"""Unit tests for how the download seam maps HTTP error statuses."""

from email.message import Message
from urllib import error

import pytest

from opendata_bcb._internal.utils import http_downloader


STR_URL = "https://example.org/file.csv"


def _raise_status(int_code: int) -> None:
    """Patch target body: raise an ``HTTPError`` with the given status.

    Parameters
    ----------
    int_code : int
        The HTTP status to raise.

    Raises
    ------
    urllib.error.HTTPError
        Always.
    """
    raise error.HTTPError(STR_URL, int_code, "status", Message(), None)


def test_fetch_bytes_not_found_raises_file_not_found(monkeypatch: pytest.MonkeyPatch) -> None:
    """A 404 becomes ``FileNotFoundError`` so callers can tell 'no such file' apart."""
    monkeypatch.setattr(http_downloader._OPENER, "open", lambda *_a, **_k: _raise_status(404))
    with pytest.raises(FileNotFoundError, match="Not found"):
        http_downloader._fetch_bytes(STR_URL, int_timeout_s=1)


@pytest.mark.parametrize("int_code", [500, 503, 403])
def test_fetch_bytes_other_status_is_not_file_not_found(
    monkeypatch: pytest.MonkeyPatch, *, int_code: int
) -> None:
    """Any other error status takes the transfer-failure branch, never the 'missing file' one."""
    monkeypatch.setattr(http_downloader._OPENER, "open", lambda *_a, **_k: _raise_status(int_code))
    with pytest.raises(OSError, match="Failed to download"):
        http_downloader._fetch_bytes(STR_URL, int_timeout_s=1)
