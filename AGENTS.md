# iysl-skills Project Guidance

## Scope

- This repository develops and validates reusable Codex skills. Global agent guidance remains inherited and is not duplicated here.

## Skill routing

- Use `$skill-creator` when creating or materially updating a skill.
- Use `$plugin-creator` only when the requested deliverable is a Codex plugin.
- Use `$skill-cleaner` for skill inventory, duplicate, usage, root, or prompt-budget audits.
- Use `$iysl-sync` only when a confirmed ongoing change needs durable plan state.

## Development rules

- Preserve trigger nouns and keep each skill's responsibility boundary explicit.
- When `SKILL.md` references `scripts/`, `references/`, `assets/`, templates, tests, or agent metadata, validate the companion files as part of the same change.

## Verification

- Run the narrowest affected skill verifier first, then the relevant repository contract or package tests.
- Use `tools/verify-live-install.sh <skill-name>` only when live-install parity is in scope.
- Distinguish repository tests, package validation, live-install visibility, and published plugin state.

## Agent skills

### Issue tracker

Issues and specs are tracked in this repository's GitHub Issues. See `docs/agents/issue-tracker.md`.

### Triage labels

Use the five canonical triage labels without renaming. See `docs/agents/triage-labels.md`.

### Domain docs

This repository uses the single-context layout. See `docs/agents/domain.md`.
