"""Unit tests for the docs-drift prototype guard (bin/check_docs_drift.py)."""

import importlib.util
import pathlib

import pytest


PATH_SCRIPT = pathlib.Path(__file__).resolve().parents[2] / "bin" / "check_docs_drift.py"
_cls_spec = importlib.util.spec_from_file_location("check_docs_drift", PATH_SCRIPT)
if _cls_spec is None or _cls_spec.loader is None:
    raise ImportError(f"cannot load gate from {PATH_SCRIPT}")
cls_drift = importlib.util.module_from_spec(_cls_spec)
_cls_spec.loader.exec_module(cls_drift)

LIST_RULES = [{"src": ["pyproject.toml"], "docs": ["README.md"]}]
STR_ESCAPE = "feat: x\n\nDocs: not needed because dev-only bump\n"


def make_repo(path_root: pathlib.Path, *, str_reference: str = "", str_readme: str = "") -> None:
    """Build a minimal repo with ``__all__ = [read_banks]``, one poe task and one real file.

    Parameters
    ----------
    path_root : pathlib.Path
        Empty directory to populate.
    str_reference : str
        Content of ``docs/api/reference.md``.
    str_readme : str
        Content of ``README.md``.
    """
    (path_root / "src/opendata_bcb").mkdir(parents=True)
    (path_root / "src/opendata_bcb/__init__.py").write_text(
        '__all__ = ["__version__", "read_banks"]\n', encoding="utf-8"
    )
    (path_root / "docs/api").mkdir(parents=True)
    (path_root / "docs/api/reference.md").write_text(str_reference, encoding="utf-8")
    (path_root / "poe_tasks.toml").write_text(
        "[tool.poe.tasks.lint]\ncmd = 'x'\n", encoding="utf-8"
    )
    (path_root / "bin").mkdir()
    (path_root / "bin/real.sh").write_text("", encoding="utf-8")
    (path_root / "README.md").write_text(str_readme, encoding="utf-8")


def test_undocumented_name_is_reported(tmp_path: pathlib.Path) -> None:
    """An ``__all__`` name absent from reference.md is a finding (should-fail witness)."""
    make_repo(tmp_path, str_reference="# Reference\n")
    assert cls_drift.find_undocumented_names(tmp_path) == [
        "symbol: `read_banks` is in __all__ but not documented in docs/api/reference.md"
    ]


@pytest.mark.parametrize(
    "str_reference", ["### `read_banks(*, x=1) -> int`\n", "::: opendata_bcb.read_banks\n"]
)
def test_documented_name_passes(tmp_path: pathlib.Path, *, str_reference: str) -> None:
    """A heading or a ``:::`` directive documents the name."""
    make_repo(tmp_path, str_reference=str_reference)
    assert cls_drift.find_undocumented_names(tmp_path) == []


def test_unknown_poe_task_is_reported(tmp_path: pathlib.Path) -> None:
    """A cited poe task missing from poe_tasks*.toml is a finding (should-fail witness)."""
    make_repo(tmp_path, str_readme="run `poetry run poe nope`")
    assert len(cls_drift.find_missing_poe_tasks(tmp_path)) == 1


def test_known_poe_task_passes(tmp_path: pathlib.Path) -> None:
    """A cited poe task that exists passes."""
    make_repo(tmp_path, str_readme="run `poetry run poe lint`")
    assert cls_drift.find_missing_poe_tasks(tmp_path) == []


def test_missing_cited_path_is_reported(tmp_path: pathlib.Path) -> None:
    """A backticked path that does not exist is a finding (should-fail witness)."""
    make_repo(tmp_path, str_readme="see `bin/gone.sh`")
    assert len(cls_drift.find_missing_paths(tmp_path)) == 1


def test_existing_cited_path_passes(tmp_path: pathlib.Path) -> None:
    """An existing backticked path and an existing local link both pass."""
    make_repo(tmp_path, str_readme="see `bin/real.sh` and [r](bin/real.sh)")
    assert cls_drift.find_missing_paths(tmp_path) == []


def test_coupling_source_without_docs_is_reported() -> None:
    """A changed source glob with no doc touched is a finding (should-fail witness)."""
    list_found = cls_drift.find_coupling_gaps(
        ["pyproject.toml"], list_rules=LIST_RULES, str_messages=""
    )
    assert len(list_found) == 1


def test_coupling_source_with_docs_passes() -> None:
    """Touching one coupled doc satisfies the rule."""
    list_found = cls_drift.find_coupling_gaps(
        ["pyproject.toml", "README.md"], list_rules=LIST_RULES, str_messages=""
    )
    assert list_found == []


def test_coupling_escape_line_passes() -> None:
    """A ``Docs: not needed because <reason>`` commit line escapes the rule."""
    list_found = cls_drift.find_coupling_gaps(
        ["pyproject.toml"], list_rules=LIST_RULES, str_messages=STR_ESCAPE
    )
    assert list_found == []


def test_coupling_escape_without_reason_still_reported() -> None:
    """An escape line with no reason does not count."""
    list_found = cls_drift.find_coupling_gaps(
        ["pyproject.toml"], list_rules=LIST_RULES, str_messages="Docs: not needed because "
    )
    assert len(list_found) == 1
