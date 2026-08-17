"""Generate compact reports and patches for quick workflows."""

from __future__ import annotations

import shutil
import subprocess
import sys
from pathlib import Path

from .profiles import Profile


ROOT = Path(__file__).resolve().parent.parent


def render_report(manifest: dict, profile: Profile, verification: dict) -> str:
    """Render a concise report for quick and standard modes."""
    stats = manifest["stats"]
    check_lines = []
    for check in verification["checks"]:
        marker = "✓" if check["status"] == "passed" else "!"
        check_lines.append(
            f"- {marker} {check['name']}: {check['status']} "
            f"({check['duration_seconds']}s)"
        )
    check_lines.extend(f"- ↷ {item}" for item in verification["skipped"])
    if not check_lines:
        check_lines.append("- No automated checks were applicable.")

    return "\n".join([
        "# CodeHelper Report",
        "",
        f"- Profile: `{profile.name}`",
        f"- Status: `{verification['status']}`",
        f"- Preset: `{manifest['preset'] or 'none'}`",
        f"- Scope: {stats['source_files']} source files / "
        f"{stats['source_lines']} source lines / "
        f"{stats['test_files']} test files",
        f"- Verification time: {verification['duration_seconds']}s",
        "",
        "## Automated verification",
        "",
        *check_lines,
        "",
        "## Review summary",
        "",
        "<!-- The CodeHelper agent replaces this line with the concise debug, "
        "style, test, and optimization summary relevant to the selected "
        "profile. -->",
        "",
        "## Changes",
        "",
        "See `changes.patch` for the canonical line-by-line diff.",
        "",
    ])


def write_report(output_dir: Path, manifest: dict, profile: Profile,
                 verification: dict) -> Path:
    """Write a compact report or copy deep-mode report templates."""
    output_dir.mkdir(parents=True, exist_ok=True)
    if profile.split_reports:
        template_dir = ROOT / "output" / "_template" / "doc"
        destination_dir = output_dir / "doc"
        destination_dir.mkdir(parents=True, exist_ok=True)
        for template in sorted(template_dir.glob("*.txt")):
            shutil.copy2(template, destination_dir / template.name)
        return destination_dir / "00_summary.txt"
    destination = output_dir / "report.md"
    destination.write_text(render_report(manifest, profile, verification),
                           encoding="utf-8")
    return destination


def generate_patch(original_dir: Path, modified_dir: Path,
                   output_dir: Path) -> dict:
    """Generate changes.patch with the existing diff utility."""
    destination = output_dir / "changes.patch"
    command = [
        sys.executable,
        str(ROOT / "src" / "generate_diff.py"),
        str(original_dir),
        str(modified_dir),
        "--output",
        str(destination),
    ]
    result = subprocess.run(
        command, cwd=str(ROOT), capture_output=True, text=True
    )
    # Exit 1 means differences were found, which is success here.
    status = "written" if result.returncode in (0, 1) else "failed"
    return {
        "status": status,
        "exit_code": result.returncode,
        "path": str(destination),
        "output": (result.stdout + result.stderr).strip(),
    }
