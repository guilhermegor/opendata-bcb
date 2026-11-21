"""Unit tests that keep the documented Python snippets honest.

The snippets in the README and the usage pages call the live BCB services, so they are not
executed here. They are parsed instead: every import must resolve, every reader they name
must be in ``__all__``, and every keyword argument they pass must exist in that reader's
signature. A renamed reader or argument fails this file before it reaches a user.
"""

import ast
import importlib
import inspect
from pathlib import Path
import re

import pytest

import opendata_bcb


PATH_ROOT = Path(__file__).resolve().parents[2]
LIST_DOCS = ["README.md", "docs/examples.md", "docs/usage.md"]
RE_PYTHON_BLOCK = re.compile(r"```python\n(.*?)```", re.DOTALL)


def _snippets() -> dict[str, ast.Module]:  # complexity-ok: collects blocks across the doc files
    """Return every documented Python snippet, parsed, keyed by file and position."""
    dict_found: dict[str, ast.Module] = {}
    for str_doc in LIST_DOCS:
        str_text = (PATH_ROOT / str_doc).read_text(encoding="utf-8")
        for int_pos, str_code in enumerate(RE_PYTHON_BLOCK.findall(str_text), start=1):
            dict_found[f"{str_doc}#{int_pos}"] = ast.parse(str_code)
    return dict_found


DICT_SNIPPETS = _snippets()


def _reader_calls(str_id: str) -> list[ast.Call]:  # complexity-ok: filters an AST walk
    """Return the calls in a snippet that target a name starting with ``read_``."""
    return [
        cls_node
        for cls_node in ast.walk(DICT_SNIPPETS[str_id])
        if isinstance(cls_node, ast.Call)
        and isinstance(cls_node.func, ast.Name)
        and cls_node.func.id.startswith("read_")
    ]


def _missing_imports(str_id: str) -> list[str]:  # complexity-ok: walks the snippet imports
    """Return the ``module.name`` imports of a snippet that do not resolve."""
    list_missing: list[str] = []
    for cls_node in ast.walk(DICT_SNIPPETS[str_id]):
        if not isinstance(cls_node, ast.ImportFrom) or cls_node.module is None:
            continue
        cls_module = importlib.import_module(cls_node.module)
        list_missing += [
            f"{cls_node.module}.{cls_alias.name}"
            for cls_alias in cls_node.names
            if not hasattr(cls_module, cls_alias.name)
        ]
    return list_missing


def _unknown_keywords(str_id: str) -> list[str]:  # complexity-ok: checks each call keyword
    """Return the ``reader(keyword=)`` pairs whose keyword is not a parameter."""
    list_unknown: list[str] = []
    for cls_call in _reader_calls(str_id):
        set_params = set(inspect.signature(getattr(opendata_bcb, cls_call.func.id)).parameters)
        list_unknown += [
            f"{cls_call.func.id}({cls_kw.arg}=)"
            for cls_kw in cls_call.keywords
            if cls_kw.arg not in set_params
        ]
    return list_unknown


def test_documented_snippets_exist() -> None:
    """The docs carry snippets, so the parametrised checks below are never vacuous."""
    assert len(DICT_SNIPPETS) >= 10


@pytest.mark.parametrize("str_id", list(DICT_SNIPPETS))
def test_snippet_imports_resolve(str_id: str) -> None:
    """Every ``from X import Y`` in a snippet resolves to a real attribute."""
    assert _missing_imports(str_id) == []


@pytest.mark.parametrize("str_id", list(DICT_SNIPPETS))
def test_snippet_reader_names_are_public(str_id: str) -> None:
    """Every reader a snippet calls is exported in ``__all__``."""
    set_called = {cls_call.func.id for cls_call in _reader_calls(str_id)}
    assert set_called <= set(opendata_bcb.__all__)


@pytest.mark.parametrize("str_id", list(DICT_SNIPPETS))
def test_snippet_keyword_arguments_exist(str_id: str) -> None:
    """Every keyword a snippet passes to a reader is a parameter of that reader."""
    assert _unknown_keywords(str_id) == []


def test_readme_guarantee_names_every_public_reader() -> None:
    """The README's 1.x guarantee names each exported reader, so none is left unpromised."""
    str_readme = (PATH_ROOT / "README.md").read_text(encoding="utf-8")
    str_section = str_readme.split("### Garantia de API da série 1.x", maxsplit=1)[1]
    str_section = str_section.split("<!-- slug:", maxsplit=1)[0]
    set_readers = {str_name for str_name in opendata_bcb.__all__ if str_name.startswith("read_")}
    set_named = set(re.findall(r"`(read_\w+)`", str_section))
    assert set_readers == set_named
