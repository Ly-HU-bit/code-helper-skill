"""Execution profiles and their hard time budgets."""

from __future__ import annotations

from dataclasses import asdict, dataclass


@dataclass(frozen=True)
class Profile:
    """A bounded CodeHelper execution policy."""

    name: str
    deadline_seconds: int
    test_timeout_seconds: int
    max_fix_retries: int
    generate_tests: bool
    analyze_optimization: bool
    generate_visual_debugger: bool
    split_reports: bool
    strict_style: bool

    def to_dict(self) -> dict:
        """Return a JSON-serializable representation."""
        return asdict(self)


PROFILES = {
    "quick": Profile(
        name="quick",
        deadline_seconds=270,
        test_timeout_seconds=75,
        max_fix_retries=1,
        generate_tests=False,
        analyze_optimization=False,
        generate_visual_debugger=False,
        split_reports=False,
        strict_style=False,
    ),
    "standard": Profile(
        name="standard",
        deadline_seconds=480,
        test_timeout_seconds=150,
        max_fix_retries=2,
        generate_tests=True,
        analyze_optimization=True,
        generate_visual_debugger=False,
        split_reports=False,
        strict_style=False,
    ),
    "deep": Profile(
        name="deep",
        deadline_seconds=900,
        test_timeout_seconds=300,
        max_fix_retries=3,
        generate_tests=True,
        analyze_optimization=True,
        generate_visual_debugger=True,
        split_reports=True,
        strict_style=True,
    ),
}


def get_profile(name: str) -> Profile:
    """Resolve a profile name or raise a clear error."""
    try:
        return PROFILES[name]
    except KeyError as exc:
        choices = ", ".join(PROFILES)
        message = f"Unknown profile {name!r}; choose one of: {choices}"
        raise ValueError(message) from exc
