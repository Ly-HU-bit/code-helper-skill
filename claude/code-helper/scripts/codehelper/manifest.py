"""Scan once and share the resulting manifest across stages."""

from __future__ import annotations

import hashlib
import re
from dataclasses import asdict, dataclass
from pathlib import Path


SOURCE_EXTENSIONS = {
    ".java", ".py", ".js", ".ts", ".tsx", ".jsx",
    ".c", ".cpp", ".cc", ".cxx", ".h", ".hpp",
    ".cs", ".go", ".rs", ".rb", ".kt", ".scala",
}
RESOURCE_EXTENSIONS = {
    ".json", ".yaml", ".yml", ".toml", ".ini", ".cfg", ".csv", ".txt",
    ".xml",
}
BINARY_RESOURCE_EXTENSIONS = {
    ".png", ".jpg", ".jpeg", ".gif", ".npy", ".npz",
}
PROJECT_FILE_NAMES = {
    "pom.xml", "build.gradle", "build.gradle.kts", "settings.gradle",
    "settings.gradle.kts", "gradlew", "gradlew.bat", "pyproject.toml",
    "setup.cfg", "pytest.ini", "tox.ini", "cmakelists.txt", "makefile",
    "package.json", "tsconfig.json",
}
TEST_PATTERNS = (
    re.compile(r"(^|/)tests?/", re.IGNORECASE),
    re.compile(r"(^|/)test_[^/]+\.py$", re.IGNORECASE),
    re.compile(r"(^|/)[^/]+_test\.py$", re.IGNORECASE),
    re.compile(r"(^|/)[^/]*test[^/]*\.java$", re.IGNORECASE),
    re.compile(r"(^|/)[^/]*test[^/]*\.(?:cpp|cc|cxx)$", re.IGNORECASE),
)
IGNORED_DIRS = {
    ".git", ".idea", ".vscode", "__pycache__", ".pytest_cache",
    ".mypy_cache", ".tox", ".venv", "venv", "node_modules", "out",
    "build", "dist", "target", ".gradle",
}
REQUIREMENT_NAMES = {
    "requirements.md", "requirements.txt", "requirement.md", "requirement.txt",
    "审阅要求.txt", "审阅要求.md", "要求.txt", "要求.md",
}
LANGUAGE_BY_EXTENSION = {
    ".java": "java",
    ".py": "python",
    ".c": "cpp",
    ".cpp": "cpp",
    ".cc": "cpp",
    ".cxx": "cpp",
    ".h": "cpp",
    ".hpp": "cpp",
    ".js": "javascript",
    ".jsx": "javascript",
    ".ts": "typescript",
    ".tsx": "typescript",
}


@dataclass(frozen=True)
class FileEntry:
    """One relevant file in a prepared submission."""

    path: str
    language: str
    kind: str
    lines: int
    bytes: int
    sha256: str


def _is_ignored(relative: Path) -> bool:
    return any(part.lower() in IGNORED_DIRS for part in relative.parts[:-1])


def _is_test(relative_posix: str) -> bool:
    return any(pattern.search(relative_posix) for pattern in TEST_PATTERNS)


def _read_text(path: Path) -> str:
    raw = path.read_bytes()
    for encoding in ("utf-8-sig", "gb18030"):
        try:
            return raw.decode(encoding)
        except UnicodeDecodeError:
            continue
    return raw.decode("utf-8", errors="replace")


def _detect_preset(languages: set[str], requirements: str) -> str | None:
    match = re.search(r"^\s*preset\s*:\s*([\w-]+)\s*$", requirements,
                      flags=re.IGNORECASE | re.MULTILINE)
    if match:
        return match.group(1)
    if languages == {"python"}:
        return "pep8_python"
    if "java" in languages:
        return "ucb61b_java"
    return None


def _collect_entries(
    root: Path,
) -> tuple[list[FileEntry], list[str], list[str]]:
    entries: list[FileEntry] = []
    requirement_parts: list[str] = []
    requirement_files: list[str] = []
    for path in sorted(p for p in root.rglob("*") if p.is_file()):
        relative = path.relative_to(root)
        if _is_ignored(relative):
            continue
        relative_posix = relative.as_posix()
        if path.name.lower() in REQUIREMENT_NAMES:
            requirement_files.append(relative_posix)
            requirement_parts.append(_read_text(path))
            continue
        suffix = path.suffix.lower()
        lower_name = path.name.lower()
        is_supported = (
            suffix in SOURCE_EXTENSIONS
            or suffix in RESOURCE_EXTENSIONS
            or suffix in BINARY_RESOURCE_EXTENSIONS
            or lower_name in PROJECT_FILE_NAMES
        )
        if not is_supported:
            continue
        raw = path.read_bytes()
        content = (
            "" if suffix in BINARY_RESOURCE_EXTENSIONS else _read_text(path)
        )
        if suffix in SOURCE_EXTENSIONS:
            language = LANGUAGE_BY_EXTENSION.get(suffix, suffix.lstrip("."))
            kind = "test" if _is_test(relative_posix) else "source"
        else:
            language = (
                "config" if lower_name in PROJECT_FILE_NAMES else "resource"
            )
            kind = language
        entries.append(
            FileEntry(
                path=relative_posix,
                language=language,
                kind=kind,
                lines=len(content.splitlines()),
                bytes=len(raw),
                sha256=hashlib.sha256(raw).hexdigest(),
            )
        )
    return entries, requirement_files, requirement_parts


def build_manifest(project_dir: Path) -> dict:
    """Return a manifest without reading build or cache artifacts."""
    root = project_dir.resolve()
    if not root.is_dir():
        raise ValueError(f"Project directory does not exist: {project_dir}")
    entries, requirement_files, requirement_parts = _collect_entries(root)

    languages = {
        entry.language for entry in entries
        if entry.kind in {"source", "test"}
    }
    requirements = "\n".join(requirement_parts).strip()
    source_entries = [entry for entry in entries if entry.kind == "source"]
    test_entries = [entry for entry in entries if entry.kind == "test"]
    fingerprint_data = "\n".join(
        f"{entry.path}:{entry.sha256}" for entry in entries
    ).encode("utf-8")

    return {
        "version": 1,
        "project_dir": str(root),
        "fingerprint": hashlib.sha256(fingerprint_data).hexdigest(),
        "preset": _detect_preset(languages, requirements),
        "languages": sorted(languages),
        "requirements_files": requirement_files,
        "requirements": requirements,
        "stats": {
            "source_files": len(source_entries),
            "test_files": len(test_entries),
            "source_lines": sum(entry.lines for entry in source_entries),
            "test_lines": sum(entry.lines for entry in test_entries),
        },
        "files": [asdict(entry) for entry in entries],
    }
