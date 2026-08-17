"""Bounded, parallel verification for CodeHelper outputs."""

from __future__ import annotations

import os
import subprocess
import sys
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

from .profiles import Profile


ROOT = Path(__file__).resolve().parent.parent
STYLE_SCRIPTS = {
    "java": ROOT / "src" / "checkstyle_java.py",
    "python": ROOT / "src" / "checkstyle_python.py",
    "cpp": ROOT / "src" / "checkstyle_cpp.py",
}


def _run_command(name: str, command: list[str], timeout: float) -> dict:
    started = time.monotonic()
    environment = os.environ.copy()
    environment["PYTHONIOENCODING"] = "utf-8"
    try:
        result = subprocess.run(
            command,
            cwd=str(ROOT),
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            env=environment,
            timeout=max(1.0, timeout),
        )
        return {
            "name": name,
            "status": "passed" if result.returncode == 0 else "failed",
            "exit_code": result.returncode,
            "duration_seconds": round(time.monotonic() - started, 3),
            "output": (result.stdout + result.stderr).strip(),
        }
    except subprocess.TimeoutExpired as exc:
        output = "".join(part for part in (exc.stdout, exc.stderr) if part)
        return {
            "name": name,
            "status": "timed_out",
            "exit_code": 2,
            "duration_seconds": round(time.monotonic() - started, 3),
            "output": output.strip() or f"Timed out after {timeout:.0f}s",
        }
    except OSError as exc:
        return {
            "name": name,
            "status": "unavailable",
            "exit_code": 2,
            "duration_seconds": round(time.monotonic() - started, 3),
            "output": str(exc),
        }


def _build_jobs(
    project_dir: Path, manifest: dict, profile: Profile, deadline: int
) -> list[tuple[str, list[str], int]]:
    jobs: list[tuple[str, list[str], int]] = []
    for language in manifest["languages"]:
        script = STYLE_SCRIPTS.get(language)
        if script:
            command = [sys.executable, str(script), str(project_dir)]
            if profile.strict_style:
                command.append("--strict")
            jobs.append((f"style:{language}", command, min(30, deadline)))

    if manifest["stats"]["test_files"]:
        jobs.append((
            "tests",
            [
                sys.executable,
                str(ROOT / "src" / "run_tests.py"),
                str(project_dir),
                "--timeout",
                str(profile.test_timeout_seconds),
            ],
            min(profile.test_timeout_seconds + 5, deadline),
        ))
    return jobs


def _run_jobs(jobs: list[tuple[str, list[str], int]]) -> list[dict]:
    results: list[dict] = []
    if jobs:
        with ThreadPoolExecutor(max_workers=min(4, len(jobs))) as executor:
            futures = {
                executor.submit(_run_command, name, command, timeout): name
                for name, command, timeout in jobs
            }
            for future in as_completed(futures):
                results.append(future.result())
    results.sort(key=lambda item: item["name"])
    return results


def verify_project(
    project_dir: Path,
    manifest: dict,
    profile: Profile,
    deadline_seconds: int | None = None,
) -> dict:
    """Run style and existing tests concurrently within a deadline."""
    started = time.monotonic()
    deadline = deadline_seconds or profile.deadline_seconds
    jobs = _build_jobs(project_dir, manifest, profile, deadline)
    results = _run_jobs(jobs)
    elapsed = round(time.monotonic() - started, 3)
    failed = [r for r in results if r["status"] != "passed"]
    return {
        "version": 1,
        "profile": profile.name,
        "deadline_seconds": deadline,
        "duration_seconds": elapsed,
        "deadline_exhausted": elapsed >= deadline,
        "status": "passed" if not failed else "needs_attention",
        "checks": results,
        "skipped": ["tests: no existing test files"]
        if not manifest["stats"]["test_files"] else [],
    }
