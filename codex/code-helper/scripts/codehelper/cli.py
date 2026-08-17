"""Single command entry point for bounded CodeHelper workflows."""

from __future__ import annotations

import argparse
import json
import re
import shutil
import sys
from pathlib import Path

from .manifest import build_manifest
from .profiles import PROFILES, get_profile
from .report import generate_patch, write_report
from .verify import verify_project


def _write_json(data: dict, destination: str | None) -> None:
    rendered = json.dumps(data, ensure_ascii=False, indent=2) + "\n"
    if destination:
        path = Path(destination)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(rendered, encoding="utf-8")
    else:
        print(rendered, end="")


def _with_policy(
    manifest: dict, profile_name: str, deadline: int | None
) -> dict:
    profile = get_profile(profile_name)
    result = dict(manifest)
    result["policy"] = profile.to_dict()
    if deadline is not None:
        result["policy"]["deadline_seconds"] = deadline
    result["agent_handoff"] = {
        "read_only_paths": [manifest["project_dir"]],
        "single_pass_analysis": profile.name != "deep",
        "generate_tests": profile.generate_tests,
        "analyze_optimization": profile.analyze_optimization,
        "generate_visual_debugger": profile.generate_visual_debugger,
        "split_reports": profile.split_reports,
        "max_fix_retries": profile.max_fix_retries,
    }
    return result


def _add_profile_options(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--profile", choices=PROFILES,
                        help="Override requirements profile (default: quick)")
    parser.add_argument("--deadline", type=int,
                        help="Override total deadline in seconds")


def build_parser() -> argparse.ArgumentParser:
    """Create the public command-line parser."""
    parser = argparse.ArgumentParser(
        prog="python -m codehelper",
        description="Fast, bounded orchestration for CodeHelper",
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    scan = subparsers.add_parser(
        "scan", help="Create the shared source manifest"
    )
    scan.add_argument("project_dir")
    scan.add_argument("-o", "--output")
    _add_profile_options(scan)

    prepare = subparsers.add_parser(
        "prepare", help="Create a clean runnable workspace and its manifest"
    )
    prepare.add_argument("project_dir")
    prepare.add_argument("code_dir")
    prepare.add_argument("-o", "--output", help="Manifest path")
    _add_profile_options(prepare)

    verify = subparsers.add_parser(
        "verify", help="Run style and existing tests concurrently"
    )
    verify.add_argument("project_dir")
    verify.add_argument("-o", "--output")
    _add_profile_options(verify)

    finalize = subparsers.add_parser(
        "finalize",
        help="Verify code and create report.md + changes.patch",
    )
    finalize.add_argument("original_dir")
    finalize.add_argument("modified_dir")
    finalize.add_argument("output_dir")
    _add_profile_options(finalize)
    return parser


def _resolve_profile(requested: str | None, manifest: dict) -> str:
    if requested:
        return requested
    match = re.search(
        r"^\s*profile\s*:\s*(quick|standard|deep)\s*$",
        manifest.get("requirements", ""),
        flags=re.IGNORECASE | re.MULTILINE,
    )
    return match.group(1).lower() if match else "quick"


def _prepare_workspace(args, manifest: dict, result: dict) -> None:
    source_root = Path(args.project_dir).resolve()
    code_dir = Path(args.code_dir).resolve()
    if code_dir == source_root or source_root in code_dir.parents:
        raise ValueError("code_dir must be outside the input project")
    if code_dir.exists() and any(code_dir.iterdir()):
        raise ValueError(
            f"Refusing to overwrite non-empty directory: {code_dir}"
        )
    code_dir.mkdir(parents=True, exist_ok=True)
    for entry in manifest["files"]:
        source = source_root / entry["path"]
        destination = code_dir / entry["path"]
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source, destination)
    result["prepared_code_dir"] = str(code_dir)
    default_manifest = code_dir.parent / "manifest.json"
    _write_json(result, args.output or str(default_manifest))
    print(f"Prepared {len(manifest['files'])} files in {code_dir}")


def _handle_scan(args) -> None:
    manifest = build_manifest(Path(args.project_dir))
    profile_name = _resolve_profile(args.profile, manifest)
    result = _with_policy(manifest, profile_name, args.deadline)
    if args.command == "prepare":
        _prepare_workspace(args, manifest, result)
    else:
        _write_json(result, args.output)


def _handle_verify(args) -> None:
    project_dir = Path(args.project_dir)
    manifest = build_manifest(project_dir)
    profile = get_profile(_resolve_profile(args.profile, manifest))
    result = verify_project(project_dir, manifest, profile, args.deadline)
    _write_json(result, args.output)
    if result["status"] != "passed":
        raise SystemExit(1)


def _handle_finalize(args) -> None:
    original_dir = Path(args.original_dir)
    modified_dir = Path(args.modified_dir)
    output_dir = Path(args.output_dir)
    original_manifest = build_manifest(original_dir)
    manifest = build_manifest(modified_dir)
    if not manifest["requirements"]:
        manifest["requirements"] = original_manifest["requirements"]
        manifest["requirements_files"] = original_manifest[
            "requirements_files"
        ]
    if not manifest["preset"]:
        manifest["preset"] = original_manifest["preset"]
    profile_name = _resolve_profile(args.profile, original_manifest)
    profile = get_profile(profile_name)
    verification = verify_project(
        modified_dir, manifest, profile, args.deadline
    )
    report = write_report(output_dir, manifest, profile, verification)
    patch = generate_patch(original_dir, modified_dir, output_dir)
    result = {
        "status": verification["status"],
        "report": str(report),
        "patch": patch,
        "verification": verification,
    }
    _write_json(result, str(output_dir / "verification.json"))
    print(json.dumps(result, ensure_ascii=False, indent=2))
    if patch["status"] == "failed":
        raise SystemExit(2)
    if verification["status"] != "passed":
        raise SystemExit(1)


def main(argv: list[str] | None = None) -> None:
    """Run the requested CodeHelper orchestration command."""
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    args = build_parser().parse_args(argv)
    try:
        if args.command in {"scan", "prepare"}:
            _handle_scan(args)
        elif args.command == "verify":
            _handle_verify(args)
        else:
            _handle_finalize(args)
    except (ValueError, OSError) as exc:
        print(f"Error: {exc}", file=sys.stderr)
        raise SystemExit(2) from exc
