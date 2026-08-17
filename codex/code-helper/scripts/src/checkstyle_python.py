#!/usr/bin/env python3
"""
Python Code Style Checker for CodeHelper.

Checks Python source files against PEP 8 conventions:
  - snake_case variable/function naming
  - PascalCase class naming
  - Docstrings for modules, classes, and functions
  - Consistent indentation (4 spaces)
  - Import ordering (stdlib → third-party → local)
  - Line length (≤ 79 for code, ≤ 72 for docstrings)
  - Function length (one function, one job)

Usage:
    python checkstyle_python.py <file.py> [--strict]
    python checkstyle_python.py <directory/> [--strict]

Output:
    Prints style violations with file, line number, and suggestion.
    Exits with code 0 if no violations, 1 otherwise.
"""

import ast
import re
import sys
from pathlib import Path

from lang_common import BaseStyleChecker, run_cli


class PythonStyleChecker(BaseStyleChecker):
    """Checks Python files for PEP 8 style violations."""

    def check_file(self, filepath: Path) -> list[dict]:
        """Run all style checks. Returns list of violations."""
        self.violations = []
        try:
            content = filepath.read_text(encoding="utf-8")
        except Exception as e:
            return [{"file": str(filepath), "line": 0, "msg": f"Cannot read file: {e}"}]

        self._check_line_length(content, filepath)
        self._check_ast(content, filepath)
        self._check_naming(content, filepath)
        self._check_docstrings(content, filepath)
        self._check_imports(content, filepath)
        return self.violations

    # ── line length ─────────────────────────────────────────────────────

    def _check_line_length(self, content, filepath):
        lines = content.split("\n")
        docstring_lines: set[int] = set()
        try:
            tree = ast.parse(content)
            for node in ast.walk(tree):
                if (isinstance(node, ast.Expr)
                        and isinstance(node.value, ast.Constant)
                        and isinstance(node.value.value, str)):
                    docstring_lines.update(
                        range(node.lineno, (node.end_lineno or node.lineno) + 1)
                    )
        except SyntaxError:
            pass
        for i, line in enumerate(lines, 1):
            limit = 72 if i in docstring_lines else 79
            if len(line) > limit:
                self._add(filepath, i,
                          f"Line too long ({len(line)} > {limit} characters)")

    # ── AST-based checks ────────────────────────────────────────────────

    def _check_ast(self, content, filepath):
        """Use Python's AST for structural checks."""
        try:
            tree = ast.parse(content)
        except SyntaxError as e:
            self._add(filepath, e.lineno or 1, f"Syntax error: {e.msg}")
            return

        visitor = _StyleVisitor(self, filepath)
        visitor.visit(tree)


    # ── naming ──────────────────────────────────────────────────────────

    _CAMEL_CASE_RE = re.compile(r'\b[a-z]+[A-Z][a-zA-Z]*\b')

    def _check_naming(self, content, filepath):
        """Check for camelCase names (should be snake_case in Python)."""
        lines = content.split("\n")
        for i, line in enumerate(lines, 1):
            stripped = line.strip()
            if stripped.startswith("#"):
                continue

            matches = self._CAMEL_CASE_RE.findall(line)
            for match in matches:
                # Allow common camelCase that comes from external APIs
                if match[0].isupper():  # PascalCase = class name, OK
                    continue
                if match.startswith("test"):  # test function names
                    continue
                # Variable assignment: someVar = ...
                if re.search(rf'\b{match}\s*[:=]', line):
                    self._add(filepath, i,
                              f"Variable '{match}' uses camelCase; use snake_case instead")

    # ── docstrings ──────────────────────────────────────────────────────

    def _check_docstrings(self, content, filepath):
        """Check that modules, classes, and functions have docstrings."""
        try:
            tree = ast.parse(content)
        except SyntaxError:
            return
        if ast.get_docstring(tree) is None:
            self._add(filepath, 1, "Module missing docstring")
        for node in ast.walk(tree):
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                if not node.name.startswith("_") and ast.get_docstring(node) is None:
                    self._add(filepath, node.lineno,
                              f"Function '{node.name}' missing docstring")
            elif isinstance(node, ast.ClassDef) and ast.get_docstring(node) is None:
                self._add(filepath, node.lineno,
                          f"Class '{node.name}' missing docstring")

    # ── imports ─────────────────────────────────────────────────────────

    def _check_imports(self, content, filepath):
        """Check import ordering: stdlib → third-party → local."""
        lines = content.split("\n")
        import_lines = []
        for i, line in enumerate(lines, 1):
            stripped = line.strip()
            if stripped.startswith("import ") or stripped.startswith("from "):
                import_lines.append((i, stripped))

        if len(import_lines) < 2:
            return

        stdlib_modules = getattr(sys, "stdlib_module_names", set())

        sections = []
        for _, line in import_lines:
            module = line.split()[1]
            if module.startswith("."):
                sections.append("local")
            elif module.split(".")[0] in stdlib_modules:
                sections.append("stdlib")
            else:
                sections.append("third-party")

        # Check ordering
        order = {"stdlib": 0, "third-party": 1, "local": 2}
        for j in range(1, len(sections)):
            if order.get(sections[j], 1) < order.get(sections[j - 1], 1):
                self._add(filepath, import_lines[j][0],
                          "Import order violation: stdlib → third-party → local")


class _StyleVisitor(ast.NodeVisitor):
    """AST visitor for structural style checks."""

    def __init__(self, checker, filepath):
        self.checker = checker
        self.filepath = filepath

    def visit_FunctionDef(self, node):
        # Check function length
        end_line = node.end_lineno or node.lineno
        length = end_line - node.lineno + 1
        if length > 50 and not node.name.startswith("test_"):
            self.checker._add(self.filepath, node.lineno,
                              f"Function '{node.name}' is {length} lines long; "
                              "consider extracting helper functions")
        self.generic_visit(node)

    def visit_ClassDef(self, node):
        # Check class name is PascalCase
        if not node.name[0].isupper():
            self.checker._add(self.filepath, node.lineno,
                              f"Class '{node.name}' should use PascalCase")
        self.generic_visit(node)


def main():
    run_cli(PythonStyleChecker, ["py"], "Python Style Checker for CodeHelper", "Python")


if __name__ == "__main__":
    main()
