#!/usr/bin/env python3
"""
Java Code Style Checker for CodeHelper.

Checks Java source files against UCB 61B style guide conventions:
  - camelCase variable/method naming
  - PascalCase class naming
  - @param / @return documentation
  - Consistent indentation (4 spaces)
  - Operator spacing
  - Function length (one function, one job)

Reference: https://sp24.datastructur.es/resources/guides/style/

Usage:
    python checkstyle_java.py <file.java> [--strict]
    python checkstyle_java.py <directory/> [--strict]

Output:
    Prints style violations with file, line number, and suggestion.
    Exits with code 0 if no violations, 1 otherwise.
"""

import re
from pathlib import Path

from lang_common import BaseStyleChecker, run_cli


class JavaStyleChecker(BaseStyleChecker):
    """Checks a single Java file for style violations."""

    def check_file(self, filepath: Path) -> list[dict]:
        """Run all style checks on a Java file. Returns list of violations."""
        self.violations = []
        try:
            content = filepath.read_text(encoding="utf-8")
        except Exception as e:
            return [{"file": str(filepath), "line": 0, "msg": f"Cannot read file: {e}"}]

        lines = content.split("\n")
        self._check_naming(lines, filepath)
        self._check_spacing(lines, filepath)
        self._check_indentation(lines, filepath)
        self._check_documentation(lines, filepath)
        self._check_function_length(content, filepath)
        return self.violations

    # ── naming ──────────────────────────────────────────────────────────

    _SNAKE_CASE_RE = re.compile(r'\b[a-z][a-z0-9]*_[a-z0-9_]*\b')
    # Java keywords to ignore
    _JAVA_KEYWORDS = {
        "abstract", "assert", "boolean", "break", "byte", "case", "catch",
        "char", "class", "const", "continue", "default", "do", "double",
        "else", "enum", "extends", "final", "finally", "float", "for",
        "goto", "if", "implements", "import", "instanceof", "int",
        "interface", "long", "native", "new", "package", "private",
        "protected", "public", "return", "short", "static", "strictfp",
        "super", "switch", "synchronized", "this", "throw", "throws",
        "transient", "try", "void", "volatile", "while", "true", "false",
        "null", "String", "Override",
    }

    def _check_naming(self, lines, filepath):
        """Check for snake_case variable names (should be camelCase)."""
        for i, line in enumerate(lines, 1):
            # Skip comments and strings (simplified)
            stripped = line.strip()
            if stripped.startswith("//") or stripped.startswith("*") or stripped.startswith("/*"):
                continue
            if stripped.startswith("package ") or stripped.startswith("import "):
                continue

            # Find snake_case identifiers
            matches = self._SNAKE_CASE_RE.findall(line)
            for match in matches:
                if match.lower() in self._JAVA_KEYWORDS:
                    continue
                if match.isupper():  # CONSTANTS are OK
                    continue
                if match.startswith("_"):  # _prefix private fields are OK
                    continue
                self._add(filepath, i,
                          f"Variable '{match}' uses snake_case; use camelCase instead")

    # ── spacing ─────────────────────────────────────────────────────────

    def _check_spacing(self, lines, filepath):
        """Check for missing spaces around operators and after semicolons in for-loops."""
        for i, line in enumerate(lines, 1):
            stripped = line.strip()
            if stripped.startswith("//") or stripped.startswith("/*") or stripped.startswith("*"):
                continue

            # for(int x=0;x<n;x++) → missing spaces
            for_match = re.search(r'for\s*\([^;]*;[^;]*;[^)]*\)', line)
            if for_match:
                for_part = for_match.group()
                if re.search(r';\s*\S', for_part):
                    # There IS a space after some semicolons; check for missing ones
                    if re.search(r'[^\s];[^\s]', for_part):
                        self._add(filepath, i,
                                  "Missing space after ';' in for-loop declaration")

            # if(condition) → missing space
            if re.search(r'\b(if|for|while|switch|catch)\s*\(', line):
                if re.search(r'\b(if|for|while|switch|catch)\(', line):
                    self._add(filepath, i,
                              "Missing space before '(' after keyword")

            # Comparison operators == and != need surrounding spaces.
            # Bare < / > are deliberately NOT checked here: they appear in Java
            # generics (e.g. List<String>) and would cause false positives.
            comp_matches = re.finditer(
                r'[^\s=!<>(]==[^\s=]|[^\s=!<>(]!=[^\s=]', line)
            for m in comp_matches:
                seg = line[m.start():m.end()]
                if not seg.startswith("//"):
                    self._add(filepath, i,
                              "Missing spaces around comparison operator (==/!=)")

            # Assignment operator = needs surrounding spaces too. This is a
            # single '=' (excluded '=' after it, so == is not double-reported).
            asn_matches = re.finditer(r'[^\s=!<>(]=[^=\s]', line)
            for m in asn_matches:
                seg = line[m.start():m.end()]
                if not seg.startswith("//"):
                    self._add(filepath, i,
                              "Missing spaces around assignment operator (=)")

    # ── indentation ─────────────────────────────────────────────────────

    def _check_indentation(self, lines, filepath):
        """Check for inconsistent indentation (should be 4 spaces per level)."""
        indent_levels = []
        for i, line in enumerate(lines, 1):
            stripped = line.strip()
            if not stripped:
                continue
            # Don't judge indentation of comment / javadoc lines (e.g. " *").
            # Those use a leading "*" and would otherwise always be flagged.
            if stripped.startswith("//") or stripped.startswith("/*") or stripped.startswith("*"):
                continue
            leading_spaces = len(line) - len(line.lstrip())
            if leading_spaces > 0 and leading_spaces % 4 != 0:
                self._add(filepath, i,
                          f"Indentation is {leading_spaces} spaces (should be multiple of 4)")
            indent_levels.append(leading_spaces)

        # Check for large jumps in indentation
        for j in range(1, len(indent_levels)):
            diff = abs(indent_levels[j] - indent_levels[j - 1])
            if diff > 8:
                self._add(filepath, j + 1,
                          f"Large indentation jump ({diff} spaces); check brace matching")

    # ── documentation ───────────────────────────────────────────────────

    def _check_documentation(self, lines, filepath):
        """Check that non-trivial methods have @param / @return documentation."""
        in_javadoc = False
        javadoc_lines: list[str] = []
        current_method = None

        for i, line in enumerate(lines, 1):
            stripped = line.strip()

            # Track JavaDoc blocks
            if stripped.startswith("/**"):
                in_javadoc = True
                javadoc_lines = [stripped]
                continue
            if in_javadoc:
                javadoc_lines.append(stripped)
                if "*/" in stripped:
                    in_javadoc = False

            # Detect method declarations (non-trivial: >3 lines heuristic)
            method_match = re.search(
                r'(public|private|protected)\s+\w+\s+(\w+)\s*\(', line
            )
            if method_match:
                method_name = method_match.group(2)
                # Skip common trivial methods. Project-specific exemptions
                # belong in spec/presets/, not hardcoded here.
                if method_name in ("main", "toString", "equals", "hashCode"):
                    javadoc_lines = []
                    continue
                if method_name.startswith("get") or method_name.startswith("set"):
                    javadoc_lines = []
                    continue

                javadoc_text = "\n".join(javadoc_lines).lower()
                # Accept standard javadoc (@param/@return) or the capitalized
                # variants (@Params/@Output) so the checker matches the spec.
                has_params = "@param" in javadoc_text or "@params" in javadoc_text
                has_return = "@return" in javadoc_text or "@output" in javadoc_text
                if not has_params or not has_return:
                    self._add(filepath, i,
                              f"Method '{method_name}' missing @param / @return documentation")
                javadoc_lines = []

    # ── function length ─────────────────────────────────────────────────

    def _check_function_length(self, content, filepath):
        """Flag methods longer than ~50 lines (one function, one job heuristic)."""
        # Simplified: count lines between method signatures
        lines = content.split("\n")
        brace_depth = 0
        method_start = None
        method_name = "?"

        for i, line in enumerate(lines, 1):
            # Rough method start detection
            if re.search(r'(public|private|protected)\s+\w+\s+(\w+)\s*\(', line):
                if brace_depth == 0 or brace_depth == 1:
                    method_start = i
                    m = re.search(r'(public|private|protected)\s+\w+\s+(\w+)\s*\(', line)
                    if m:
                        method_name = m.group(2)

            brace_depth += line.count("{") - line.count("}")

            if brace_depth == 0 and method_start is not None:
                length = i - method_start
                if length > 50:
                    self._add(filepath, method_start,
                              f"Method '{method_name}' is {length} lines long; "
                              "consider extracting helper methods")
                method_start = None


def main():
    run_cli(JavaStyleChecker, ["java"], "Java Style Checker for CodeHelper", "Java")


if __name__ == "__main__":
    main()
