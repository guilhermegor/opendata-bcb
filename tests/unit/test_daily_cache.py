"""Unit tests for the daily cache's directory and entry safety checks."""

from datetime import date
import os
from pathlib import Path

import pytest

from opendata_bcb._internal.utils import daily_cache


_DT_DAY = date(2026, 11, 21)
_POSIX_ONLY = pytest.mark.skipif(
    not hasattr(os, "getuid"), reason="owner and mode checks exist only where uids do"
)


def _fake_download(*, str_url: str, path_dest: Path) -> Path:
    """Write fixed bytes, standing in for the network."""
    path_dest.write_bytes(b"fresh")
    return path_dest


def _download(path_cache_dir: Path) -> Path:
    """Fetch one artifact through the cache."""
    return daily_cache.download_daily(
        "https://example.invalid/x.csv",
        path_cache_dir=path_cache_dir,
        str_key="example",
        dt_reference=_DT_DAY,
        str_suffix=".csv",
        fn_download=_fake_download,
    )


def test_resolve_cache_dir_keeps_caller_choice(tmp_path: Path) -> None:
    """An explicit directory is returned unchanged."""
    assert daily_cache.resolve_cache_dir(tmp_path) == tmp_path


def test_resolve_cache_dir_uses_xdg_cache_home(
    *, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """With XDG_CACHE_HOME set, the default lives under it."""
    monkeypatch.setenv("XDG_CACHE_HOME", str(tmp_path))
    assert daily_cache.resolve_cache_dir(None) == tmp_path / "opendata-bcb"


def test_resolve_cache_dir_falls_back_to_home_cache(
    *, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Without XDG_CACHE_HOME, the default is ~/.cache/opendata-bcb."""
    monkeypatch.delenv("XDG_CACHE_HOME", raising=False)
    monkeypatch.setattr(daily_cache.Path, "home", lambda: tmp_path)
    assert daily_cache.resolve_cache_dir(None) == tmp_path / ".cache" / "opendata-bcb"


@_POSIX_ONLY
def test_download_daily_creates_private_dir(tmp_path: Path) -> None:
    """A missing cache directory is created readable by the owner only."""
    path_dir = tmp_path / "cache"
    _download(path_dir)
    assert path_dir.stat().st_mode & 0o777 == 0o700


@_POSIX_ONLY
def test_download_daily_refuses_group_writable_dir(tmp_path: Path) -> None:
    """A directory others can write into is refused, not read."""
    path_dir = tmp_path / "shared"
    path_dir.mkdir()
    path_dir.chmod(0o777)
    with pytest.raises(PermissionError, match="writable by group or other"):
        _download(path_dir)


@_POSIX_ONLY
def test_download_daily_refuses_foreign_owned_dir(
    *, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A directory owned by another uid is refused."""
    monkeypatch.setattr(daily_cache.os, "getuid", lambda: tmp_path.stat().st_uid + 1)
    with pytest.raises(PermissionError, match="belongs to uid"):
        _download(tmp_path)


def test_download_daily_ignores_symlinked_entry(tmp_path: Path) -> None:
    """A symlink under the cache name is a miss: the real download replaces it."""
    path_target = tmp_path / "planted.csv"
    path_target.write_bytes(b"planted")
    path_dir = tmp_path / "cache"
    path_dir.mkdir(mode=0o700)
    path_entry = daily_cache.daily_cache_path(
        path_dir, str_key="example", dt_reference=_DT_DAY, str_suffix=".csv"
    )
    path_entry.symlink_to(path_target)
    assert _download(path_dir).read_bytes() == b"fresh"
