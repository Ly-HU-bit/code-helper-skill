#!/usr/bin/env python3
"""
C++ Code Style Checker for CodeHelper.

Checks C++ source files against the project's language-agnostic style guide
(see ``spec/stylecheck.md``), adapted to C++ idioms:

  - camelCase variable / function naming (loop temps i,j,k,x,y are exempt)
  - PascalCase class / struct / enum / type naming
  - UPPER_SNAKE_CASE for macros (``#define``) and top-level ``const``
  - ``@param`` / ``@return`` doc comments (``///`` or ``/** */``) for
    non-trivial functions (>5 lines)
  - Consistent indentation (4 spaces or tabs, not mixed)
  - Spaces around operators / after commas / in for-loop heads
  - Functions >50 lines should be split
  - Header files need an include guard; no ``using namespace std;`` in headers
  - (strict only) no magic numbers

This module reuses ``lang_common.BaseStyleChecker`` so its CLI, reporting,
and violation shape are identical to the Java / Python checkers.

Usage:
    python checkstyle_cpp.py <file.cpp> [--strict]
    python checkstyle_cpp.py <directory/> [--strict]

Output:
    Prints style violations with file, line number, and suggestion.
    Exits with code 0 if no violations, 1 otherwise.
"""

import re
import sys
from pathlib import Path

from lang_common import (
    BaseStyleChecker,
    DEFAULT_LINE_LIMIT,
    LOOP_TEMPS,
    leading_indent,
    run_cli,
)

_HEADER_SUFFIXES = {".h", ".hpp", ".hxx", ".hh"}


class CppStyleChecker(BaseStyleChecker):
    """Checks a single C++ file for style violations."""

    # ── regexes ─────────────────────────────────────────────────────────

    # Function / method definition: a return type, optional scope (Foo::),
    # a name, then "(...)" followed by { ; or = (definition/declaration).
    _FUNC_RE = re.compile(
        r'(?P<ret>(?:[A-Za-z_][\w\s*&:,<>]*?))\s+'
        r'(?P<scope>(?:[A-Za-z_]\w*::)*)'
        r'(?P<name>[A-Za-z_]\w*)\s*\((?P<params>[^()]*)\)'
        r'(?:\s*const)?'
        r'\s*(?:=\s*0|final|override|noexcept(?:\([^)]*\))?)?'
        r'\s*[{;=]'
    )

    _SNAKE_RE = re.compile(r'\b[a-z][a-z0-9]*_[a-z0-9_]*\b')
    _TYPE_RE = re.compile(
        r'\b(?:class|struct|enum|union|typedef)\b\s+(?:class\s+)?([A-Za-z_]\w*)'
    )
    _DEFINE_RE = re.compile(r'#define\s+([A-Za-z_]\w*)')
    _CONST_RE = re.compile(
        r'\bconst\s+(?:[A-Za-z_]\w*\s*[\*&]?\s+)+([A-Za-z_]\w*)\s*='
    )

    # Statements that can legally precede a "name(args)" without being a
    # definition — used to avoid false positives in the doc/length checks.
    _STATEMENT_KW = {
        "return", "throw", "if", "for", "while", "switch", "catch",
        "delete", "using", "case", "sizeof", "static_assert", "assert",
        "co_return", "co_yield", "goto",
    }

    _SKIP_DOC_NAMES = {"main"}

    # ── entry point ──────────────────────────────────────────────────────

    def check_file(self, filepath: Path) -> list[dict]:
        self.violations = []
        try:
            content = filepath.read_text(encoding="utf-8")
        except Exception as e:
            return [{"file": str(filepath), "line": 0,
                     "msg": f"Cannot read file: {e}"}]

        lines = content.split("\n")
        is_header = filepath.suffix.lower() in _HEADER_SUFFIXES

        self._check_naming(lines, filepath)
        self._check_spacing(lines, filepath)
        self._check_indentation(lines, filepath)
        self._check_documentation(lines, filepath)
        self._check_function_length(content, filepath)
        if is_header:
            self._check_header_guards(content, filepath)
        if self.strict:
            self._check_magic_numbers(lines, filepath)
        return self.violations

    # ── naming ───────────────────────────────────────────────────────────

    def _check_naming(self, lines, filepath):
        for i, line in enumerate(lines, 1):
            stripped = line.strip()
            if not stripped or stripped.startswith("//") or stripped.startswith("/*"):
                continue

            # Macros and top-level consts should be UPPER_SNAKE_CASE. These may
            # be preprocessor lines, so they are checked before the skip below.
            for m in self._DEFINE_RE.finditer(line):
                name = m.group(1)
                if not _is_upper_snake(name):
                    self._add(filepath, i,
                              f"Macro '{name}' should use UPPER_SNAKE_CASE")
            for m in self._CONST_RE.finditer(line):
                name = m.group(1)
                if not _is_upper_snake(name):
                    self._add(filepath, i,
                              f"Constant '{name}' should use UPPER_SNAKE_CASE")

            if stripped.startswith("#"):  # remaining preprocessor lines
                continue

            # snake_case identifiers used as variables.
            for match in self._SNAKE_RE.findall(line):
                if match.lower() in LOOP_TEMPS:
                    continue
                if match.isupper():          # UPPER_SNAKE constants are OK
                    continue
                if match.startswith("_"):     # _prefix private members OK
                    continue
                self._add(filepath, i,
                          f"Variable '{match}' uses snake_case; use camelCase instead")

            # Type declarations should be PascalCase.
            for m in self._TYPE_RE.finditer(line):
                name = m.group(1)
                if name in ("class", "struct", "enum", "union", "typedef"):
                    continue
                if name[0].islower() or "_" in name:
                    self._add(filepath, i,
                              f"Type '{name}' should use PascalCase")

    # ── spacing ─────────────────────────────────────────────────────────

    def _check_spacing(self, lines, filepath):
        for i, line in enumerate(lines, 1):
            stripped = line.strip()
            if stripped.startswith("//") or stripped.startswith("/*") or stripped.startswith("*"):
                continue
            if stripped.startswith("#"):
                continue

            # for(int i=0;i<n;i++) → missing spaces
            for_match = re.search(r'for\s*\([^;]*;[^;]*;[^)]*\)', line)
            if for_match:
                for_part = for_match.group()
                if re.search(r'[^\s];[^\s]', for_part):
                    self._add(filepath, i,
                              "Missing space after ';' in for-loop declaration")

            # if(condition) → missing space before '('
            if re.search(r'\b(if|for|while|switch|catch)\s*\(', line):
                if re.search(r'\b(if|for|while|switch|catch)\(', line):
                    self._add(filepath, i,
                              "Missing space before '(' after keyword")

            # Comparison operators == and != need surrounding spaces.
            for m in re.finditer(r'[^\s=!<>(]==[^\s=]|[^\s=!<>(]!=[^\s=]', line):
                seg = line[m.start():m.end()]
                if not seg.startswith("//"):
                    self._add(filepath, i,
                              "Missing spaces around comparison operator (==/!=)")

            # Assignment operator = needs surrounding spaces (single '=').
            for m in re.finditer(r'[^\s=!<>(]=[^=\s]', line):
                seg = line[m.start():m.end()]
                if not seg.startswith("//"):
                    self._add(filepath, i,
                              "Missing spaces around assignment operator (=)")

            # Comma should be followed by a space: foo(a,b) → foo(a, b)
            if re.search(r',[^\s)]', line):
                self._add(filepath, i, "Missing space after ','")

    # ── indentation ─────────────────────────────────────────────────────

    def _check_indentation(self, lines, filepath):
        uses_tabs = False
        uses_spaces = False
        for i, line in enumerate(lines, 1):
            if not line.strip():
                continue
            if line[0] == "\t":
                uses_tabs = True
            elif line[0] in " \x0c":
                uses_spaces = True

            stripped = line.strip()
            if stripped.startswith("//") or stripped.startswith("/*") or stripped.startswith("*"):
                continue
            if stripped.startswith("#"):
                continue

            indent = leading_indent(line)
            if indent > 0 and indent % 4 != 0:
                self._add(filepath, i,
                          f"Indentation is {indent} columns (should be multiple of 4)")

        if uses_tabs and uses_spaces:
            self._add(filepath, 1,
                      "Mixed tabs and spaces for indentation; pick one style")

    # ── documentation ───────────────────────────────────────────────────

    def _check_documentation(self, lines, filepath):
        doc_buffer: list[str] = []
        in_block = False

        for i, line in enumerate(lines, 1):
            s = line.strip()

            if s.startswith("///"):
                doc_buffer.append(s.lstrip("/").strip())
                continue

            if s.startswith("/*") or in_block:
                if in_block:
                    content = s
                    if "*/" in s:
                        content = s[:s.index("*/")]
                        in_block = False
                    doc_buffer.append(content.strip().strip("*").strip())
                else:
                    rest = s[s.index("/*") + 2:]
                    if "*/" in rest:
                        doc_buffer.append(rest[:rest.index("*/")].strip().strip("*").strip())
                    else:
                        in_block = True
                        doc_buffer.append(rest.strip().strip("*").strip())
                continue

            m = self._FUNC_RE.search(line)
            if m and not self._is_skipped_def(m, s):
                doc_text = "\n".join(doc_buffer).lower()
                has_param = "@param" in doc_text
                has_return = "@return" in doc_text
                # A function with no parameters (or `void`) doesn't need @param.
                params = m.group("params").strip()
                needs_param = bool(params) and params != "void"
                if (needs_param and not has_param) or not has_return:
                    name = m.group("name")
                    self._add(filepath, i,
                              f"Function '{name}' missing @param / @return documentation")
                doc_buffer = []
            else:
                doc_buffer = []

    def _is_skipped_def(self, m, stripped: str) -> bool:
        name = m.group("name")
        if name in self._SKIP_DOC_NAMES:
            return True
        if name.startswith("get") or name.startswith("set"):
            return True
        if name.startswith("operator"):
            return True
        # Trivial single-line definitions (e.g. `int value() const { return 0; }`)
        # don't need a doc comment — the spec only requires docs for >5-line
        # functions.
        if "{" in stripped and "}" in stripped:
            return True
        if any(stripped.startswith(kw + " ") or stripped == kw
               for kw in self._STATEMENT_KW):
            return True
        return False

    # ── function length ─────────────────────────────────────────────────

    def _check_function_length(self, content, filepath):
        lines = content.split("\n")
        brace_depth = 0
        func_start = None
        func_name = "?"

        for i, line in enumerate(lines, 1):
            m = self._FUNC_RE.search(line)
            if m and not self._is_skipped_def(m, line.strip()):
                if brace_depth == 0 or brace_depth == 1:
                    func_start = i
                    func_name = m.group("name")

            brace_depth += line.count("{") - line.count("}")
            if brace_depth == 0 and func_start is not None:
                length = i - func_start
                if length > 50:
                    self._add(filepath, func_start,
                              f"Function '{func_name}' is {length} lines long; "
                              "consider extracting helper functions")
                func_start = None

    # ── header guards ───────────────────────────────────────────────────

    def _check_header_guards(self, content, filepath):
        if "#pragma once" in content:
            return
        has_ifndef = "#ifndef" in content
        has_define = "#define" in content
        has_endif = "#endif" in content
        if has_ifndef and has_define and has_endif:
            return
        self._add(filepath, 1,
                  "Header missing include guard (#pragma once or #ifndef/#define/#endif)")

        # 'using namespace std;' pollutes every translation unit that includes
        # the header.
        for i, line in enumerate(content.split("\n"), 1):
            if re.search(r'using\s+namespace\s+std\s*;', line):
                self._add(filepath, i,
                          "Avoid 'using namespace std;' in header files")

    # ── magic numbers (strict only) ─────────────────────────────────────

    def _check_magic_numbers(self, lines, filepath):
        for i, line in enumerate(lines, 1):
            stripped = line.strip()
            if not stripped or stripped.startswith("//") or stripped.startswith("/*"):
                continue
            if stripped.startswith("#"):
                continue
            for m in re.finditer(r'\b(\d{1,3})\b', line):
                value = int(m.group(1))
                if value in (0, 1, 2):
                    continue
                # Skip digits that are part of a wider token (e.g. 0x..).
                if m.group(0) != m.group(1):
                    continue
                self._add(filepath, i,
                          f"Magic number {value}; extract to a named constant")


def _is_upper_snake(name: str) -> bool:
    """True if ``name`` is valid UPPER_SNAKE_CASE (e.g. MAX_SIZE or MAX)."""
    return name.isupper() and name.replace("_", "").isalpha()


def main():
    run_cli(CppStyleChecker, ["cpp", "cc", "cxx", "c++", "h", "hpp", "hxx", "hh"],
            "C++ Style Checker for CodeHelper", "C++")


if __name__ == "__main__":
    main()
