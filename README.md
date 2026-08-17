# CodeHelper Skill

CodeHelper is a personal coding-assistant skill for reviewing student Java,
Python, and C++ projects. It combines bounded debugging, deterministic style
checks, test execution, and focused optimization while preserving the original
project structure.

The default `quick` profile targets a final result within 3–5 minutes. The
skill activates only when explicitly invoked.

## Packages

- `codex/code-helper/` — Codex personal skill
- `claude/code-helper/` — Claude Code personal skill

Both packages are self-contained and include their workflow, reference specs,
presets, CLI orchestrator, style checkers, test runner, report templates, and
diff generator.

## Install on Windows

Clone this repository, then copy the package for your assistant:

```powershell
git clone https://github.com/Ly-HU-bit/code-helper-skill.git

# Codex
Copy-Item -Recurse `
  .\code-helper-skill\codex\code-helper `
  "$HOME\.agents\skills\code-helper"

# Claude Code
Copy-Item -Recurse `
  .\code-helper-skill\claude\code-helper `
  "$HOME\.claude\skills\code-helper"
```

Restart the assistant or open a new session after first installation.

## Invoke

In Codex:

```text
$code-helper Review this project with the quick profile: <project-path>
```

In Claude Code:

```text
/code-helper Review this project with the quick profile: <project-path>
```

Use `standard` for broader test and optimization work, or `deep` for a full
four-part audit. Python 3 is required for the bundled helper scripts.

## Profiles

| Profile | Budget | Intended use |
|---|---:|---|
| `quick` | 270 seconds | Daily debugging and verification |
| `standard` | 480 seconds | Broader tests and focused optimization |
| `deep` | 900 seconds | Comprehensive audit and split reports |
