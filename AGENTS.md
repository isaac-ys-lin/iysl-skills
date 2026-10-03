# iysl-skills Project Guidance

## Scope

- This repository develops and validates reusable Codex skills. Global agent guidance remains inherited and is not duplicated here.

## Skill routing

- Use `$skill-creator` when creating or materially updating a skill.
- Use `$plugin-creator` only when the requested deliverable is a Codex plugin.
- Use `$skill-cleaner` for skill inventory, duplicate, usage, root, or prompt-budget audits.

## Development rules

- Preserve trigger nouns and keep each skill's responsibility boundary explicit.
- When `SKILL.md` references `scripts/`, `references/`, `assets/`, templates, tests, or agent metadata, validate the companion files as part of the same change.
- When the checkout already holds another task's uncommitted work, make your change in its own git worktree and branch, and land it on `main` through a PR, so each commit carries one task.

## Verification

- Run the narrowest affected skill verifier first, then the relevant repository contract or package tests.
- Run pytest directly as `PYTHONDONTWRITEBYTECODE=1 python3 -m pytest -p no:cacheprovider`; the `tools/verify-*.sh` scripts already disable bytecode, and the package-contract test rejects any `__pycache__` left under `skills/`.
- Use `tools/verify-live-install.sh <skill-name>` only when live-install parity is in scope.
- Distinguish repository tests, package validation, live-install visibility, and published plugin state.

## Agent skills

### Issue tracker

Issues and specs are tracked in this repository's GitHub Issues. See `docs/agents/issue-tracker.md`.

### Triage labels

Use the five canonical triage labels without renaming. See `docs/agents/triage-labels.md`.

### Domain docs

This repository uses the single-context layout. See `docs/agents/domain.md`.
