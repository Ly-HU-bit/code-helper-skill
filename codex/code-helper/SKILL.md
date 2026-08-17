---
name: code-helper
description: Review and improve student Java, Python, or C++ coursework with bounded debugging, style checks, test verification, and optimization. Use only when the user explicitly invokes CodeHelper or code-helper for a submitted code project.
---

# CodeHelper

Only activate this workflow when the user explicitly asks to use CodeHelper.

## Default outcome

Use the `quick` profile unless the user requests a comprehensive/deep review.
For ordinary submissions (up to about 20 source files or 2,000 source lines),
target a final result within 3–5 minutes. Treat the profile deadline as a hard
budget: finish essential debugging and verification first, then omit optional
work and record it in the report if the budget is nearly exhausted.

| Profile | Deadline | Default scope | Output |
|---|---:|---|---|
| `quick` | 270s | Debug, deterministic style, existing tests, obvious performance defects | `report.md` |
| `standard` | 480s | Quick + missing tests + meaningful algorithm improvements | `report.md` |
| `deep` | 900s | Full four-part audit, strict style, optional visual debugger | `doc/00-04` |

User requirements always override profile defaults. A requirements file may
contain `profile: quick|standard|deep` and/or `preset: <name>`.

## Runtime

Resolve `<skill-directory>` to the directory containing this SKILL.md before running a command. Use an available Python 3 interpreter; in Codex Desktop, load the bundled workspace Python runtime if `python` is not on PATH.

## Workflow

1. Prepare one clean, runnable workspace and reuse its manifest throughout the task:

   `python "<skill-directory>/scripts/codehelper_cli.py" prepare input/<task> output/<task>/code --profile <profile> -o output/<task>/manifest.json`

2. Read only the files listed in the manifest. Never inspect `.idea/`, `out/`,
   `build/`, dependency, cache, or binary directories.
3. Treat `output/<task>/code/` as the runnable working copy; it includes source,
   existing tests, resources, and essential build configuration.
4. In `quick` and `standard`, analyze the code once in the main context. Do not
   launch four specialists that each reread every file. For a genuinely large,
   multi-module project, parallelize by independent module, not by review type.
5. Apply changes in dependency order: debug, necessary style, tests, then
   optimization. Preserve the student's architecture and explain structural
   changes.
6. Verify style and existing tests concurrently. Respect the profile timeout
   and retry limit. Do not weaken or delete valid user tests.
7. Finalize compact output with:

   `python "<skill-directory>/scripts/codehelper_cli.py" finalize input/<task> output/<task>/code output/<task> --profile <profile>`

8. Replace the placeholder in `report.md` with a concise educational summary.
   `changes.patch` is the canonical line-level diff; do not duplicate every
   changed line in the report.

## Profile rules

### Quick

- Fix reproducible bugs and high-confidence correctness risks.
- Run lightweight style checks, but only edit meaningful/high-impact issues.
- Run existing tests. Generate a new test only when needed to reproduce a fix.
- Mention optimization only for an obvious complexity defect; do not audit
  every method.
- At most one fix-and-verify retry.
- Never generate a GUI visual debugger automatically.

### Standard

- Add missing edge-case tests for changed or high-risk public behavior.
- Apply meaningful implementation-level optimizations.
- At most two fix-and-verify retries.
- Keep the compact report unless the user requests split documentation.

### Deep

- Follow all files under `references/spec/` and the selected preset.
- Generate the split `doc/00_summary.txt` through `doc/04_optimization.txt`.
- Generate a visual debugger only when it materially helps understand an
  abstract data structure, and place it in `output/<task>/tools/`, never `src/`.
- At most three fix-and-verify retries.

## Non-negotiable constraints

- Never mutate `input/`.
- Do not change the program's main architecture without user permission.
- Do not simplify tests merely to make them pass.
- Use temporary build directories; never create build output inside `input/`.
- When a tool is unavailable or a deadline expires, produce the best verified
  result and state exactly what remains unverified.
