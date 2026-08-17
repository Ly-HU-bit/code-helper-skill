#!/usr/bin/env python3
"""
Auto Test Runner for CodeHelper.

Detects the test framework in a project directory and runs all tests.
Supports:
  - Java / JUnit 5 (via Maven or Gradle)
  - Java / plain javac (IntelliJ layout: *.iml + src/, no build file) — auto-detected
  - Python / pytest
  - Python / unittest
  - C++ / g++ (plain compile + run; GoogleTest / Catch2 binaries run all tests)
  - C++ / CMake (CMakeLists.txt)
  - C++ / Make (Makefile)

Usage:
    python run_tests.py <project_directory>
    python run_tests.py <project_directory> --framework junit
    python run_tests.py <project_directory> --framework javac
    python run_tests.py <project_directory> --framework gpp
    python run_tests.py <project_directory> --framework cmake
    python run_tests.py <project_directory> --framework make
    python run_tests.py <project_directory> --verbose

Output:
    Prints pass/fail summary for each test.
    Exits with code 0 if all tests pass, 1 if any fail.
"""

import argparse
import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path


IGNORED_DIRS = {
    ".git", ".idea", ".vscode", "__pycache__", ".pytest_cache",
    ".mypy_cache", ".tox", ".venv", "venv", "node_modules", "out",
    "build", "dist", "target", ".gradle",
}


def find_files(project_dir: Path, pattern: str) -> list[Path]:
    """Find project files while excluding build, dependency, and cache trees."""
    return [
        path for path in project_dir.rglob(pattern)
        if not any(part.lower() in IGNORED_DIRS
                   for part in path.relative_to(project_dir).parts[:-1])
    ]


def detect_framework(project_dir: Path) -> str | None:
    """Auto-detect the test framework used in the project."""
    # Java / JUnit detection
    pom_xml = project_dir / "pom.xml"
    build_gradle = project_dir / "build.gradle"
    if pom_xml.exists() or build_gradle.exists():
        return "junit"

    # C++ / CMake
    if (project_dir / "CMakeLists.txt").exists():
        return "cmake"

    # C++ / Make
    if (project_dir / "Makefile").exists():
        return "make"

    # Check for Java test files (IntelliJ / plain javac layout: no Maven/Gradle)
    java_tests = find_files(project_dir, "*Test*.java")
    if java_tests:
        return "javac"

    # Check for C++ sources (g++ plain compile + run)
    cpp_sources = (find_files(project_dir, "*.cpp")
                   + find_files(project_dir, "*.cc")
                   + find_files(project_dir, "*.cxx")
                   + find_files(project_dir, "*.c++"))
    if cpp_sources:
        return "gpp"

    # Python / pytest detection
    pyproject = project_dir / "pyproject.toml"
    setup_cfg = project_dir / "setup.cfg"
    pytest_ini = project_dir / "pytest.ini"
    if pyproject.exists() or setup_cfg.exists() or pytest_ini.exists():
        return "pytest"

    # Check for Python test files
    py_tests = (find_files(project_dir, "test_*.py")
                + find_files(project_dir, "*_test.py"))
    if py_tests:
        # Try pytest first, fall back to unittest
        try:
            subprocess.run(["pytest", "--version"], capture_output=True, timeout=5)
            return "pytest"
        except (FileNotFoundError, subprocess.TimeoutExpired):
            return "unittest"

    return None


def run_junit(project_dir: Path, verbose: bool,
              timeout: int = 300) -> tuple[int, str]:
    """Run JUnit tests. Returns (exit_code, output)."""
    pom_xml = project_dir / "pom.xml"

    if pom_xml.exists():
        cmd = ["mvn", "test", "-B"]
        if not verbose:
            cmd.append("-q")
    else:
        # Gradle
        cmd = ["./gradlew", "test"]
        if not verbose:
            cmd.append("--quiet")

    try:
        result = subprocess.run(
            cmd,
            cwd=str(project_dir),
            capture_output=True,
            text=True,
            timeout=timeout,
        )
        return result.returncode, result.stdout + result.stderr
    except FileNotFoundError:
        return 2, "Error: Maven (mvn) or Gradle (gradlew) not found."
    except subprocess.TimeoutExpired:
        return 2, f"Error: Test execution timed out ({timeout}s)."


def run_pytest(project_dir: Path, verbose: bool,
               timeout: int = 120) -> tuple[int, str]:
    """Run pytest. Returns (exit_code, output)."""
    cmd = ["pytest"]
    if verbose:
        cmd.append("-v")
    else:
        cmd.append("-q")

    try:
        result = subprocess.run(
            cmd,
            cwd=str(project_dir),
            capture_output=True,
            text=True,
            timeout=timeout,
        )
        return result.returncode, result.stdout + result.stderr
    except FileNotFoundError:
        return 2, "Error: pytest not installed. Run: pip install pytest"
    except subprocess.TimeoutExpired:
        return 2, f"Error: Test execution timed out ({timeout}s)."


def run_javac(project_dir: Path, verbose: bool,
              timeout: int = 300) -> tuple[int, str]:
    """Compile a plain javac / IntelliJ project and (optionally) run its tests.

    Falls back to this when no Maven/Gradle build file is present. Compiles
    every ``.java`` under the project with ``javac`` into a temp dir, then runs
    the tests if a JUnit Platform Console launcher jar is available.
    """
    javac = shutil.which("javac") or shutil.which("javac.exe")
    java = shutil.which("java") or shutil.which("java.exe")
    if not javac or not java:
        return 2, ("Error: JDK not found on PATH. Install a JDK (17+) and "
                   "ensure `javac`/`java` are available, or switch to a "
                   "Maven/Gradle project.")

    java_files = [str(p) for p in find_files(project_dir, "*.java")]
    if not java_files:
        return 2, "Error: no .java source files found to compile."

    build_dir = Path(tempfile.mkdtemp(prefix="codehelper_build_"))
    try:
        compile_cmd = [javac, "-d", str(build_dir)] + java_files
        proc = subprocess.run(compile_cmd, capture_output=True, text=True,
                              timeout=timeout)
        if proc.returncode != 0:
            return 1, "Compilation failed:\n" + proc.stdout + proc.stderr

        # Run tests only if a JUnit Platform Console launcher is available.
        standalone = os.environ.get("JUNIT_STANDALONE")
        if standalone and Path(standalone).is_file():
            run_cmd = [java, "-jar", standalone, "--scan-classpath",
                       "--classpath", str(build_dir)]
            if verbose:
                run_cmd.append("--details=tree")
            r = subprocess.run(run_cmd, capture_output=True, text=True,
                               timeout=timeout)
            return r.returncode, r.stdout + r.stderr

        return (2, "Compiled successfully, but no JUnit launcher was found to "
                   "run the tests automatically.\nSet the JUNIT_STANDALONE "
                   "environment variable to a junit-platform-console-standalone"
                   ".jar, or run the tests inside your IDE.")
    except subprocess.TimeoutExpired:
        return 2, f"Error: compile/test execution timed out ({timeout}s)."
    finally:
        shutil.rmtree(build_dir, ignore_errors=True)


def run_unittest(project_dir: Path, verbose: bool,
                 timeout: int = 120) -> tuple[int, str]:
    """Run Python unittest. Returns (exit_code, output)."""
    cmd = [sys.executable, "-m", "unittest", "discover", "-s", str(project_dir)]
    if verbose:
        cmd.append("-v")

    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=timeout,
        )
        return result.returncode, result.stdout + result.stderr
    except subprocess.TimeoutExpired:
        return 2, f"Error: Test execution timed out ({timeout}s)."


def run_cpp(project_dir: Path, verbose: bool,
            timeout: int = 300) -> tuple[int, str]:
    """Compile C++ sources with g++/clang++ and run the resulting binary.

    GoogleTest / Catch2 test binaries run all their tests when executed; the
    binary's exit code (non-zero on failure) is reported back. A plain ``main``
    returning 0 is treated as "all tests passed".
    """
    compiler = (shutil.which("g++") or shutil.which("g++.exe")
                 or shutil.which("clang++") or shutil.which("clang++.exe"))
    if not compiler:
        return 2, ("Error: no C++ compiler found on PATH. Install g++ (MinGW/"
                   "GCC) or clang++ and ensure it is available.")

    sources = ([str(p) for p in find_files(project_dir, "*.cpp")]
               + [str(p) for p in find_files(project_dir, "*.cc")]
               + [str(p) for p in find_files(project_dir, "*.cxx")]
               + [str(p) for p in find_files(project_dir, "*.c++")])
    if not sources:
        return 2, "Error: no C++ source files (*.cpp/*.cc/*.cxx) found."

    build_dir = Path(tempfile.mkdtemp(prefix="codehelper_cpp_"))
    exe = build_dir / ("a.exe" if os.name == "nt" else "a.out")
    compile_cmd = [compiler, "-std=c++17", "-Wall", "-o", str(exe)] + sources
    try:
        proc = subprocess.run(compile_cmd, capture_output=True, text=True,
                              timeout=timeout)
        if proc.returncode != 0:
            return 1, "Compilation failed:\n" + proc.stdout + proc.stderr

        run = subprocess.run([str(exe)], capture_output=True, text=True,
                             timeout=timeout)
        out = run.stdout + run.stderr
    except subprocess.TimeoutExpired:
        return 2, f"Error: compile/test execution timed out ({timeout}s)."
    finally:
        shutil.rmtree(build_dir, ignore_errors=True)

    # Surface a hint when a known test framework is detected.
    framework = ""
    haystack = " ".join(sources)
    if "TEST_F(" in haystack or "TEST(" in haystack:
        framework = " (GoogleTest)"
    elif "TEST_CASE(" in haystack:
        framework = " (Catch2)"
    return run.returncode, out + (f"\n[detected{framework}]\n" if framework else "")


def run_make(project_dir: Path, verbose: bool,
             timeout: int = 300) -> tuple[int, str]:
    """Build and test a project with Make."""
    make = shutil.which("make") or shutil.which("make.exe")
    if not make:
        return 2, "Error: make not found on PATH."
    cmd = [make] + (["--quiet"] if not verbose else [])
    try:
        result = subprocess.run(cmd, cwd=str(project_dir),
                                capture_output=True, text=True, timeout=timeout)
        return result.returncode, result.stdout + result.stderr
    except subprocess.TimeoutExpired:
        return 2, f"Error: build timed out ({timeout}s)."


def run_cmake(project_dir: Path, verbose: bool,
              timeout: int = 300) -> tuple[int, str]:
    """Configure and build a CMake project, then run the test binary."""
    cmake = shutil.which("cmake") or shutil.which("cmake.exe")
    if not cmake:
        return 2, "Error: cmake not found on PATH."
    build_dir = Path(tempfile.mkdtemp(prefix="codehelper_cmake_"))
    try:
        cfg = subprocess.run([cmake, "-S", str(project_dir), "-B", str(build_dir)],
                             capture_output=True, text=True, timeout=timeout)
        if cfg.returncode != 0:
            return 1, "CMake configure failed:\n" + cfg.stdout + cfg.stderr
        cmd = [cmake, "--build", str(build_dir)]
        if verbose:
            cmd.append("--verbose")
        result = subprocess.run(cmd, capture_output=True, text=True,
                                timeout=timeout)
        return result.returncode, result.stdout + result.stderr
    except subprocess.TimeoutExpired:
        return 2, f"Error: build timed out ({timeout}s)."
    finally:
        shutil.rmtree(build_dir, ignore_errors=True)


def main():
    parser = argparse.ArgumentParser(description="Auto Test Runner for CodeHelper")
    parser.add_argument("project_dir", help="Project directory containing tests")
    parser.add_argument("--framework",
                        choices=["junit", "javac", "pytest", "unittest",
                                 "gpp", "make", "cmake"],
                        help="Force a specific test framework")
    parser.add_argument("--verbose", "-v", action="store_true",
                        help="Verbose test output")
    parser.add_argument("--timeout", type=int, default=300,
                        help="Hard timeout for compile/test execution in seconds")
    args = parser.parse_args()

    if args.timeout <= 0:
        parser.error("--timeout must be a positive integer")

    project_dir = Path(args.project_dir)
    if not project_dir.is_dir():
        print(f"Error: {project_dir} is not a valid directory", file=sys.stderr)
        sys.exit(2)

    # Detect or use specified framework
    framework = args.framework or detect_framework(project_dir)
    if framework is None:
        print("Error: Could not detect test framework. "
              "Use --framework to specify one.", file=sys.stderr)
        sys.exit(2)

    print(f"Detected framework: {framework}")
    print(f"Project directory: {project_dir}")
    print("-" * 50)

    # Run tests
    runners = {
        "junit": run_junit,
        "javac": run_javac,
        "pytest": run_pytest,
        "unittest": run_unittest,
        "gpp": run_cpp,
        "make": run_make,
        "cmake": run_cmake,
    }

    exit_code, output = runners[framework](project_dir, args.verbose, args.timeout)
    print(output)

    if exit_code == 0:
        print("\n[OK] All tests passed.")
    elif exit_code == 2:
        print("\n[WARN] Test execution error.")
    else:
        print("\n[FAIL] Some tests failed.")

    sys.exit(exit_code)


if __name__ == "__main__":
    main()
