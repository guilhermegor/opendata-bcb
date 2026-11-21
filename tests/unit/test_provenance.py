"""Unit tests for the read-once artifact helper."""

import hashlib
from pathlib import Path

import pytest

from opendata_bcb._internal.utils.provenance import read_artifact


PATH_FIXTURE = Path(__file__).parent.parent / "fixtures" / "banks" / "participantes_str.csv"


def test_read_artifact_returns_the_exact_fixture_bytes() -> None:
    """The bytes are the file's, unmodified."""
    assert read_artifact(PATH_FIXTURE)[0] == PATH_FIXTURE.read_bytes()


def test_read_artifact_returns_sha256_of_those_bytes() -> None:
    """The digest is the sha256 hex of the returned bytes."""
    _bytes_read, _str_hash = read_artifact(PATH_FIXTURE)
    assert _str_hash == hashlib.sha256(_bytes_read).hexdigest()


def test_read_artifact_missing_file_raises(tmp_path: Path) -> None:
    """A missing file fails fast at the read boundary."""
    with pytest.raises(FileNotFoundError):
        read_artifact(tmp_path / "absent.csv")
