#!/usr/bin/env python3
"""Portable entry point for the bundled CodeHelper package."""

from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parent))

from codehelper.cli import main  # noqa: E402


if __name__ == "__main__":
    main()
