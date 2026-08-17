#!/usr/bin/env python3
"""
Shared, reusable primitives for CodeHelper language checkers.

Every style checker in this project (Java, Python, C++) follows the same
shape: collect ``{"file", "line", "msg"}`` violations, discover targets from
a file or directory, render a report, and exit 0/1. This module implements
that duplicated ~80% once, so each language checker only implements the
language-specific rules.

Public API
---------
- ``make_violation(file, line, msg)`` -> dict   (the canonical violation shape)
- ``BaseStyleChecker``                         (subclass + implement ``check_file``)
- ``discover_targets(target, extensions)``     (file/dir -> list[Path] | None)
- ``render_report(violations, language)``      (prints + returns exit code)
- ``run_cli(checker_cls, extensions, description, language)``
- ``leading_indent(line)`` / ``strip_line_comment(line, marker)``  (line helpers)

The violation record is kept dict-shaped (``{"file", "line", "msg"}``) on
purpose: the existing per-language test suites assert against ``v["msg"]``,
so changing it to a dataclass would break them.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

# Maximum line length used by the default style guide (Java/C++ ≤ 100).
# Python checkers use their own 79/72 limit; this is the shared default.
DEFAULT_LINE_LIMIT = 100

# Identifiers that may legitimately be short, even in a "meaningful names" rule.
LOOP_TEMPS = {"i", "j", "k", "x", "y", "n", "m", "t", "e", "it", "idx", "len"}

IGNORED_DIRS = {
    ".git", ".idea", ".vscode", "__pycache__", ".pytest_cache",
    ".mypy_cache", ".tox", ".venv", "venv", "node_modules", "out",
    "build", "dist", "target", ".gradle",
}


def make_violation(file: str, line: int, msg: str) -> dict:
    """Build a violation record. Dict-shaped for backward compatibility."""
    return {"file": file, "line": line, "msg": msg}


class BaseStyleChecker:
    """Common state + helpers for language-specific style checkers.

    Subclasses implement ``check_file(self, filepath: Path) -> list[dict]``
    and register findings via ``self._add(filepath, line, msg)``. The base
    class owns ``strict`` and ``violations`` so every checker behaves the same.
    """

    def __init__(self, strict: bool = False):
        self.strict = strict
        self.violations: list[dict] = []

    def _add(self, filepath, lineno, msg) -> None:
        self.violations.append(make_violation(str(filepath), lineno, msg))

    def check_file(self, filepath: Path) -> list[dict]:
        """Run all checks on one file. Subclasses must override."""
        raise NotImplementedError


def discover_targets(target: Path, extensions: list[str]) -> list[Path] | None:
    """Resolve a CLI ``target`` into a sorted list of source files.

    ``extensions`` is a list like ``["java"]`` / ``["cpp", "cc", "hpp"]``
    (with or without leading dots). Returns ``None`` when ``target`` is
    neither an existing file nor an existing directory.
    """
    exts = {"." + e.lstrip(".") for e in extensions}
    if target.is_file():
        return [target]
    if target.is_dir():
        files: list[Path] = []
        for ext in exts:
            files.extend(
                path for path in target.rglob(f"*{ext}")
                if not any(part.lower() in IGNORED_DIRS
                           for part in path.relative_to(target).parts[:-1])
            )
        return sorted(files)
    return None


def render_report(violations: list[dict], language: str) -> int:
    """Print the style report and return the process exit code.

    Returns 0 when there are no violations, 1 otherwise — consistent across
    all language checkers so the orchestrator can rely on the exit code.
    """
    if not violations:
        print("[OK] No style violations found.")
        return 0
    print(f"Found {len(violations)} {language} style violation(s):\n")
    for v in sorted(violations, key=lambda x: (x["file"], x["line"])):
        print(f"  {v['file']}:{v['line']} - {v['msg']}")
    return 1


def run_cli(
    checker_cls,
    extensions: list[str],
    description: str,
    language: str,
) -> None:
    """Build a uniform CLI for a checker and run it.

    Wires argparse (``target`` + ``--strict``), target discovery, the checker,
    and report rendering so each language module needs almost no boilerplate::

        if __name__ == "__main__":
            run_cli(JavaStyleChecker, ["java"], "Java Style Checker", "Java")
    """
    parser = argparse.ArgumentParser(description=description)
    parser.add_argument("target", help=f"{language} file or directory to check")
    parser.add_argument("--strict", action="store_true",
                        help="Report all issues (even minor ones)")
    args = parser.parse_args()

    target = Path(args.target)
    files = discover_targets(target, extensions)
    if files is None:
        print(f"Error: {target} is not a valid file or directory", file=sys.stderr)
        sys.exit(2)

    checker = checker_cls(strict=args.strict)
    all_violations: list[dict] = []
    for f in files:
        all_violations.extend(checker.check_file(f))

    sys.exit(render_report(all_violations, language))


# ── line-level helpers (reused across checkers) ───────────────────────────

def leading_indent(line: str) -> int:
    """Number of leading whitespace columns (tabs expanded to 4 spaces)."""
    expanded = line.expandtabs(4)
    return len(expanded) - len(expanded.lstrip())


def strip_line_comment(line: str, marker: str) -> str:
    """Remove a trailing ``//``- or ``#``-style comment (best-effort).

    String literals are tracked so a ``#`` / ``//`` inside a quoted string is
    not treated as a comment. This is intentionally simple: it will not handle
    every edge case (e.g. a ``#`` inside a triple-quoted Python string), which
    is acceptable for a lightweight style checker.
    """
    out: list[str] = []
    in_str = False
    quote = ""
    i = 0
    n = len(line)
    mlen = len(marker)
    while i < n:
        ch = line[i]
        if in_str:
            out.append(ch)
            if ch == quote and (i == 0 or line[i - 1] != "\\"):
                in_str = False
            i += 1
            continue
        if ch in ("'", '"'):
            in_str = True
            quote = ch
            out.append(ch)
            i += 1
            continue
        if line[i:i + mlen] == marker:
            break
        out.append(ch)
        i += 1
    return "".join(out)
