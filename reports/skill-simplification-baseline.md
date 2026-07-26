# Skill simplification baseline

Date: 2026-07-26
Branch: `codex/iysl-skills-simplification`
Baseline commit: `a8ad008847ee773e3278b266d46e20b0bda2f0c6`

## Starting state

The branch was created from `main` while preserving a pre-existing dirty
working tree. Those changes are concentrated in
`skills/iysl-ytdlp-html-report/` and are treated as user-owned work in
progress until their contracts are inspected and verified.

## Main skill size

| Skill | Lines | Characters |
| --- | ---: | ---: |
| `iysl-anidiagram` | 107 | 10,213 |
| `iysl-clarify` | 77 | 4,877 |
| `iysl-deckab` | 83 | 7,015 |
| `iysl-sync` | 116 | 6,015 |
| `iysl-ytdlp-html-report` | 266 | 18,882 |
| `equity-data` | 59 | 7,151 |
| `repo-research-packager` | 75 | 3,090 |
| **Total** | **783** | **57,243** |

## Gates

- Global inventory/package unit tests: **8 passed**.
- Isolated `npx skills@1.5.16` copy-install/parity: **passed for 7 skills**.
- Existing trigger evaluator: **passed for 3 skill packages** (`clarify`,
  `deckab`, `sync`); the repository had no trigger packages for the other
  four skills at baseline.
- Full `tools/verify-release.sh`: **not completed within the bounded baseline
  observation**. The gate reached the `iysl-anidiagram` suite, which reported
  7 passed and then spent at least 209 seconds in the existing Playwright/
  Chrome demo-render path without an assertion failure. The two baseline
  processes started during this observation were terminated normally; this is
  recorded as a baseline runtime limitation, not as a product test failure.

## Scope note

No push, pull request, release, or native/plugin file modification is part of
this execution. The plan's final gate will rerun the full release check with a
bounded observation and report any remaining renderer runtime limitation
separately from assertion results.
