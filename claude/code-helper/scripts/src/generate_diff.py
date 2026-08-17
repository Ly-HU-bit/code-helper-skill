#!/usr/bin/env python3
"""
Unified Diff Generator for CodeHelper.

Generates a .patch file comparing original code (in input/) against
modified code (in output/), so users can apply changes directly:

    patch -p1 < output/<project>/changes.patch
    git apply output/<project>/changes.patch

Scope (default):
  Only recognized *source-code* files are diffed. This keeps the patch
  clean when the agent compares whole project roots: report text
  (doc/00~04.txt), the previously generated changes.patch, README, and
  other non-source artifacts are skipped automatically.

  - Default allow-list: .java .py .js .ts .tsx .jsx .c .cpp .cc .cxx
    .h .hpp .cs .go .rs .rb .kt .scala .m .swift .php .r .sh .sql
    .scm .lisp .lua .pl
  - Pass --all to include every file regardless of extension.
  - Pass --ext to supply a custom allow-list (e.g. --ext java,py).

Supports:
  - Single-file diff (input/X.java vs output/X.java)
  - Multi-file diff (entire project directory)
  - Context lines control (default: 3)
  - Summary statistics

Usage:
    python generate_diff.py input/<project>/src output/<project>/code
    python generate_diff.py input/<project> output/<project> --output changes.patch
    python generate_diff.py input/<project> output/<project> --context 5
    python generate_diff.py input/<project> output/<project> --all
    python generate_diff.py input/<project> output/<project> --ext java,py,ts

Output:
    Writes unified diff to stdout or specified file.
    Exits with code 0 if no differences, 1 if differences found.
"""

import argparse
import difflib
import os
import sys
from pathlib import Path


# Extensions treated as "source code" for the default diff scope. Comparing a
# whole project root would otherwise drag in report text (doc/00~04.txt), the
# previously generated changes.patch, README, etc.
SOURCE_EXTENSIONS = {
    ".java", ".py", ".js", ".ts", ".tsx", ".jsx",
    ".c", ".cpp", ".cc", ".cxx", ".h", ".hpp",
    ".cs", ".go", ".rs", ".rb", ".kt", ".scala", ".m", ".swift",
    ".php", ".r", ".sh", ".sql", ".scm", ".lisp", ".lua", ".pl",
}


def _ext_allowed(filepath: Path, allow: set[str] | None) -> bool:
    """True if ``filepath``'s suffix is in the allow-list.

    ``allow is None`` means "accept every file" (used by ``--all``).
    """
    if allow is None:
        return True
    return filepath.suffix.lower() in allow


def collect_files(
    input_dir: Path,
    output_dir: Path,
    source_only: bool = True,
    extensions: set[str] | None = None,
) -> list[tuple[str, Path | None, Path | None, str]]:
    """Match files between input and output directories.

    Returns a list of ``(key, input_path, output_path, status)`` where ``key``
    is the path used for the patch header (``a/<key>`` / ``b/<key>``):

      - status ``matched`` : file present in both (content may differ)
      - status ``new``     : file only in output (added by CodeHelper)
      - status ``ambiguous``: basename collides with multiple input files

    Matching strategy:
      1. Exact relative-path match (``input_dir`` vs ``output_dir``).
      2. Otherwise fall back to a *unique* basename match, so that
         ``src/Foo.java`` in the input maps to ``code/Foo.java`` in the
         output. The patch key is then the original (input) path, which keeps
         ``git apply`` / ``patch -p1`` aligned with the student's source tree.

    Filtering:
      By default only source-code files (``SOURCE_EXTENSIONS``) are considered.
      Pass ``source_only=False`` to include every file, or ``extensions`` to
      supply a custom allow-list (which replaces ``SOURCE_EXTENSIONS``).
    """
    allow: set[str] | None = None
    if source_only:
        allow = extensions if extensions is not None else SOURCE_EXTENSIONS

    # Index input files by relative path and by basename.
    input_by_rel: dict[str, Path] = {}
    input_by_base: dict[str, list[str]] = {}
    if input_dir.is_dir():
        for f in input_dir.rglob("*"):
            if f.is_file() and not _is_binary(f) and _ext_allowed(f, allow):
                rel = str(f.relative_to(input_dir)).replace(os.sep, "/")
                input_by_rel[rel] = f
                input_by_base.setdefault(f.name, []).append(rel)

    # Index output files by relative path.
    output_by_rel: dict[str, Path] = {}
    if output_dir.is_dir():
        for f in output_dir.rglob("*"):
            if f.is_file() and not _is_binary(f) and _ext_allowed(f, allow):
                output_by_rel[str(f.relative_to(output_dir)).replace(os.sep, "/")] = f

    pairs: list[tuple[str, Path | None, Path | None, str]] = []
    for rel, out in output_by_rel.items():
        if rel in input_by_rel:
            pairs.append((rel, input_by_rel[rel], out, "matched"))
            continue
        base = Path(rel).name
        candidates = input_by_base.get(base, [])
        if len(candidates) == 1:
            # Unique basename match → align patch path with original tree.
            pairs.append((candidates[0], input_by_rel[candidates[0]], out, "matched"))
        else:
            pairs.append((rel, None, out, "new" if not candidates else "ambiguous"))

    return pairs


def _is_binary(filepath: Path) -> bool:
    """Heuristic: check if file looks binary."""
    try:
        with open(filepath, "rb") as f:
            chunk = f.read(1024)
        return b"\x00" in chunk
    except Exception:
        return True


def generate_diff(
    input_dir: Path,
    output_dir: Path,
    context_lines: int = 3,
    source_only: bool = True,
    extensions: set[str] | None = None,
) -> str:
    """Generate a unified diff for all changed / new files.

    The patch header uses ``a/<key>`` / ``b/<key>`` (git-style), so it applies
    cleanly with ``git apply changes.patch`` or ``patch -p1 < changes.patch``
    from the original source tree.

    ``source_only`` / ``extensions`` mirror :func:`collect_files` — by default
    only source-code files enter the patch.
    """
    pairs = collect_files(input_dir, output_dir, source_only, extensions)
    all_diffs: list[str] = []
    stats = {"added": 0, "removed": 0, "changed": 0, "unchanged": 0, "new_file": 0}

    for key, inp, out, status in pairs:
        try:
            out_lines = out.read_text(encoding="utf-8").splitlines(True)
        except Exception:
            continue

        if inp is None:
            # New file added by CodeHelper.
            stats["new_file"] += 1
            diff = difflib.unified_diff(
                [], out_lines,
                fromfile=f"a/{key}",
                tofile=f"b/{key}",
                n=context_lines,
            )
            diff_text = "".join(diff)
            for line in diff_text.splitlines():
                if line.startswith("+") and not line.startswith("+++"):
                    stats["added"] += 1
            all_diffs.append(diff_text)
            continue

        try:
            inp_lines = inp.read_text(encoding="utf-8").splitlines(True)
        except Exception:
            continue

        if inp_lines == out_lines:
            stats["unchanged"] += 1
            continue

        stats["changed"] += 1
        diff = difflib.unified_diff(
            inp_lines, out_lines,
            fromfile=f"a/{key}",
            tofile=f"b/{key}",
            n=context_lines,
        )
        diff_text = "".join(diff)

        for line in diff_text.splitlines():
            if line.startswith("+") and not line.startswith("+++"):
                stats["added"] += 1
            elif line.startswith("-") and not line.startswith("---"):
                stats["removed"] += 1

        all_diffs.append(diff_text)

    # Build final output
    header = [
        "=" * 70,
        f"CodeHelper Diff Report",
        f"  Input:  {input_dir}",
        f"  Output: {output_dir}",
        f"  Files changed:  {stats['changed']}",
        f"  Files new:      {stats['new_file']}",
        f"  Files unchanged:{stats['unchanged']}",
        f"  Lines added:    {stats['added']}",
        f"  Lines removed:  {stats['removed']}",
        "=" * 70,
        "",
    ]

    return "\n".join(header) + "\n".join(all_diffs)


def main():
    parser = argparse.ArgumentParser(
        description="Generate unified diff for CodeHelper projects"
    )
    parser.add_argument("input_dir", help="Original code directory (input/<project>/)")
    parser.add_argument("output_dir", help="Modified code directory (output/<project>/)")
    parser.add_argument("-o", "--output", help="Write diff to file (default: stdout)")
    parser.add_argument("-c", "--context", type=int, default=3,
                        help="Number of context lines (default: 3)")
    parser.add_argument("--all", action="store_true",
                        help="Include ALL files, not just recognized source code "
                             "(disables the default source-extension filter)")
    parser.add_argument("--ext", default=None,
                        help="Comma-separated extension allow-list, e.g. 'java,py' "
                             "or '.java,.py'. Overrides the default set.")
    args = parser.parse_args()

    input_dir = Path(args.input_dir)
    output_dir = Path(args.output_dir)

    if not input_dir.exists():
        print(f"Error: input directory not found: {input_dir}", file=sys.stderr)
        sys.exit(2)

    if not output_dir.exists():
        print(f"Error: output directory not found: {output_dir}", file=sys.stderr)
        sys.exit(2)

    # Resolve the extension allow-list.
    exts: set[str] | None = None
    if args.ext:
        exts = {e if e.startswith(".") else "." + e
                for e in args.ext.split(",") if e}

    diff_text = generate_diff(
        input_dir, output_dir, args.context,
        source_only=not args.all, extensions=exts,
    )

    if args.output:
        Path(args.output).write_text(diff_text, encoding="utf-8")
        print(f"Diff written to: {args.output}")
    else:
        print(diff_text)

    # Exit 0 if no meaningful differences (only header)
    if "Files changed:  0" in diff_text and "Files new:      0" in diff_text:
        sys.exit(0)
    sys.exit(1)


if __name__ == "__main__":
    main()
