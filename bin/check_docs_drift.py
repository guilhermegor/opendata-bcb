"""Prototype docs-drift guard: do README/docs still MATCH the code, not just have the right shape.

ADVISORY ONLY (prototype for opendata-bcb#18): nothing wires this into pre-commit or CI. Two parts,
by oracle strength:

1. **Symbol drift** (strong, mechanical, default mode). Reports
   - a name in the package ``__all__`` (dunders skipped) that ``docs/api/reference.md`` neither
     opens with a ``:::`` mkdocstrings directive nor carries in a heading;
   - a ``poe <task>`` cited in a code span / fenced block of README.md, CONTRIBUTING.md or
     ``docs/**/*.md`` that is not defined in the poe task files;
   - a repo-relative path cited in a code span or a local markdown link that does not exist.
2. **Coupling map** (medium, ``--diff <base>``). ``.docs-coupling.yaml`` maps source globs to the
   docs that must be reviewed when they change; a diff touching a glob but none of its docs is
   reported, unless a commit in ``<base>..<head>`` has a ``Docs: not needed because <why>`` line.

Exit code 1 when anything is reported, so the caller decides whether that blocks.
"""

import argparse
import ast
import fnmatch
import pathlib
import re
import subprocess
import sys
import tomllib

import yaml


PATH_ROOT = pathlib.Path(__file__).resolve().parent.parent
PATH_INIT = pathlib.Path("src/opendata_bcb/__init__.py")
PATH_REFERENCE = pathlib.Path("docs/api/reference.md")
PATH_COUPLING = pathlib.Path(".docs-coupling.yaml")
LIST_DOC_GLOBS = ["README.md", "CONTRIBUTING.md", "SECURITY.md", "docs/**/*.md"]
RE_FENCE = re.compile(r"```.*?```", re.DOTALL)
RE_SPAN = re.compile(r"`([^`\n]+)`")
RE_LINK = re.compile(r"\]\(([^)\s]+)\)")
RE_POE = re.compile(r"\bpoe\s+([a-z_][\w-]*)")
RE_HEADING = re.compile(r"^#+ .*$", re.MULTILINE)
RE_DIRECTIVE = re.compile(r"^:::\s*(\S+)", re.MULTILINE)
RE_PATHLIKE = re.compile(r"^[\w./-]+$")
RE_ESCAPE = re.compile(r"^Docs: not needed because \S.*$", re.MULTILINE)
LIST_TOP_DIRS = ("bin/", "docs/", "src/", "tests/", ".github/", ".specs/")


def list_all_names(path_root: pathlib.Path) -> list:
    """Return the non-dunder names of the package ``__all__``.

    Parameters
    ----------
    path_root : pathlib.Path
        Repository root.

    Returns
    -------
    list
        Public names, in declaration order.
    """
    cls_tree = ast.parse((path_root / PATH_INIT).read_text(encoding="utf-8"))
    for cls_node in cls_tree.body:
        if isinstance(cls_node, ast.Assign) and cls_node.targets[0].id == "__all__":
            return [
                str_n for str_n in ast.literal_eval(cls_node.value) if not str_n.startswith("__")
            ]
    return []


def find_undocumented_names(path_root: pathlib.Path) -> list:
    """Return ``__all__`` names that reference.md documents nowhere.

    A name counts as documented when it is the last dotted part of a ``:::`` directive or a whole
    word inside a heading line.

    Parameters
    ----------
    path_root : pathlib.Path
        Repository root.

    Returns
    -------
    list
        One finding string per undocumented name.
    """
    str_text = (path_root / PATH_REFERENCE).read_text(encoding="utf-8")
    set_documented = {str_d.split(".")[-1] for str_d in RE_DIRECTIVE.findall(str_text)}
    str_headings = "\n".join(RE_HEADING.findall(str_text))
    return [
        f"symbol: `{str_n}` is in __all__ but not documented in {PATH_REFERENCE}"
        for str_n in list_all_names(path_root)
        if str_n not in set_documented and not re.search(rf"\b{re.escape(str_n)}\b", str_headings)
    ]


def list_doc_files(path_root: pathlib.Path) -> list:
    """Return the doc files the guard reads (those that exist)."""
    set_files = set()
    for str_glob in LIST_DOC_GLOBS:
        set_files.update(path_root.glob(str_glob))
    return sorted(set_files)


def list_code_snippets(str_text: str) -> list:
    """Return the fenced blocks and inline code spans of a markdown text."""
    return RE_FENCE.findall(str_text) + RE_SPAN.findall(RE_FENCE.sub("", str_text))


def list_poe_tasks(path_root: pathlib.Path) -> set:
    """Return every poe task name defined across ``poe_tasks*.toml``."""
    set_tasks = set()
    for path_toml in path_root.glob("poe_tasks*.toml"):
        dict_toml = tomllib.loads(path_toml.read_text(encoding="utf-8"))
        set_tasks.update(dict_toml.get("tool", {}).get("poe", {}).get("tasks", {}))
    return set_tasks


def find_missing_poe_tasks(path_root: pathlib.Path) -> list:
    """Return findings for ``poe <task>`` citations whose task is undefined."""
    set_tasks = list_poe_tasks(path_root)
    list_findings = []
    for path_doc in list_doc_files(path_root):
        str_text = path_doc.read_text(encoding="utf-8")
        set_cited = {m for str_s in list_code_snippets(str_text) for m in RE_POE.findall(str_s)}
        list_findings += [
            f"poe: {path_doc.relative_to(path_root)} cites `poe {str_t}`, not in poe_tasks*.toml"
            for str_t in sorted(set_cited - set_tasks)
        ]
    return list_findings


def is_checkable_path(str_candidate: str) -> bool:
    """Return whether a code-span string looks like a concrete repo path."""
    if not RE_PATHLIKE.match(str_candidate) or "/" not in str_candidate:
        return False
    return str_candidate.startswith(LIST_TOP_DIRS) or "." in str_candidate.rsplit("/", 1)[-1]


def find_missing_paths(path_root: pathlib.Path) -> list:
    """Return findings for cited repo paths and local links that do not exist.

    Backticked paths resolve from the repo root; markdown links resolve from the citing file.
    """
    list_findings = []
    for path_doc in list_doc_files(path_root):
        str_text = path_doc.read_text(encoding="utf-8")
        str_rel = path_doc.relative_to(path_root)
        list_cited = [
            (path_root / str_s.rstrip("/"), str_s)
            for str_s in RE_SPAN.findall(RE_FENCE.sub("", str_text))
            if is_checkable_path(str_s)
        ]
        for str_link in RE_LINK.findall(str_text):
            str_target = str_link.split("#")[0]
            if str_target and "://" not in str_target and not str_target.startswith("mailto:"):
                list_cited.append((path_doc.parent / str_target, str_link))
        list_findings += [
            f"path: {str_rel} cites `{str_s}`, which does not exist"
            for path_c, str_s in list_cited
            if not path_c.exists()
        ]
    return list_findings


def find_symbol_drift(path_root: pathlib.Path) -> list:
    """Return every part-1 finding."""
    return (
        find_undocumented_names(path_root)
        + find_missing_poe_tasks(path_root)
        + find_missing_paths(path_root)
    )


def load_coupling(path_root: pathlib.Path) -> list:
    """Return the coupling rules: dicts with ``src`` (globs) and ``docs`` (files)."""
    path_file = path_root / PATH_COUPLING
    return (
        yaml.safe_load(path_file.read_text(encoding="utf-8"))["rules"]
        if path_file.exists()
        else []
    )


def find_coupling_gaps(list_changed: list, *, list_rules: list, str_messages: str) -> list:
    """Return findings for changed source globs whose docs were not touched.

    Parameters
    ----------
    list_changed : list
        Repo-relative changed paths.
    list_rules : list
        Rules from ``.docs-coupling.yaml``.
    str_messages : str
        Commit messages of the range; a ``Docs: not needed because <reason>`` line escapes all.

    Returns
    -------
    list
        One finding per violated rule; empty when escaped.
    """
    if RE_ESCAPE.search(str_messages):
        return []
    list_findings = []
    for dict_rule in list_rules:
        list_hits = [
            str_c
            for str_c in list_changed
            if any(fnmatch.fnmatch(str_c, g) for g in dict_rule["src"])
        ]
        if list_hits and not set(dict_rule["docs"]) & set(list_changed):
            list_findings.append(
                f"coupling: {', '.join(list_hits[:3])} changed but none of "
                f"{', '.join(dict_rule['docs'])} did"
            )
    return list_findings


def run_git(list_args: list) -> str:
    """Run git at the repo root and return stdout."""
    return subprocess.run(  # noqa: S603
        ["git", *list_args],  # noqa: S607
        cwd=PATH_ROOT,
        capture_output=True,
        text=True,
        check=True,
        encoding="utf-8",
    ).stdout


def main() -> int:
    """Run the guard; ``--diff <base>`` adds the coupling map."""
    cls_parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    cls_parser.add_argument("--diff", metavar="BASE", help="also check the coupling map vs BASE")
    cls_parser.add_argument("--head", default="HEAD", help="head ref for --diff (default HEAD)")
    cls_args = cls_parser.parse_args()
    list_findings = [] if cls_args.diff else find_symbol_drift(PATH_ROOT)
    if cls_args.diff:
        list_changed = run_git(["diff", "--name-only", cls_args.diff, cls_args.head]).split()
        str_messages = run_git(["log", "--format=%B", f"{cls_args.diff}..{cls_args.head}"])
        list_findings = find_coupling_gaps(
            list_changed, list_rules=load_coupling(PATH_ROOT), str_messages=str_messages
        )
    print("\n".join(list_findings) or "docs-drift: no findings")
    return 1 if list_findings else 0


if __name__ == "__main__":
    sys.exit(main())
