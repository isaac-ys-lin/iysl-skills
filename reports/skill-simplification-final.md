# Skill simplification final report

Date: 2026-07-26
Branch: `codex/iysl-skills-simplification`
Baseline commit: `a8ad008847ee773e3278b266d46e20b0bda2f0c6`

## Scope

The seven target skills were simplified in place. The work preserves the
pre-existing dirty `iysl-ytdlp-html-report` work and adds the missing portable
source-preparation and report-finalization contracts around it.

## Size comparison

| Skill | Baseline lines | Candidate lines | Baseline chars | Candidate chars |
| --- | ---: | ---: | ---: | ---: |
| `iysl-anidiagram` | 107 | 52 | 10,213 | 2,662 |
| `iysl-clarify` | 77 | 40 | 4,877 | 1,970 |
| `iysl-deckab` | 83 | 55 | 7,015 | 2,807 |
| `iysl-sync` | 116 | 50 | 6,015 | 2,278 |
| `iysl-ytdlp-html-report` | 266 | 79 | 18,882 | 4,470 |
| `equity-data` | 59 | 50 | 7,151 | 2,631 |
| `repo-research-packager` | 75 | 50 | 3,090 | 2,425 |
| **Total** | **783** | **376** | **57,243** | **19,243** |

The baseline includes the user's pre-existing dirty video-report changes;
therefore the ytdlp row is a worktree baseline, not a clean-HEAD comparison.

## Routing A/B

The heuristic evaluator was run on the same baseline cases and semantic
configurations for the three packages that already had baseline routing evals:

| Skill | Baseline | Candidate | Candidate FP/FN |
| --- | ---: | ---: | ---: |
| `iysl-clarify` | 20/20 | 20/20 | 0/0 |
| `iysl-deckab` | 10/10 | 10/10 | 0/0 |
| `iysl-sync` | 19/19 | 19/19 | 0/0 |

Candidate routing coverage is now 7/7 packages, 90/90 cases passed, with 0
false positives and 0 false negatives. The baseline repository only had
routing packages for three skills, so no honest baseline comparison exists for
the other four.

## Verification

- Global deterministic tests: 12 passed.
- Skill gates: equity-data, clarify, deckab, sync, repo-research-packager, and
  ytdlp all passed; ytdlp passed 30 tests plus 14 subtests.
- anidiagram targeted structure tests: 35 passed; gallery contract tests: 3
  passed; sample render check: 7/7 checks passed.
- Blind receiver evaluator for `repo-research-packager`: passed.
- `tools/audit-skills.py --fail-on-error`: all seven skills `ok`.
- Isolated `skills@1.5.16` npx copy-install parity: 7/7 skills passed.
- `git diff --check`: passed; generated Python caches were removed.

## Limits

- The full `tools/verify-release.sh` was bounded rather than claimed green. It
  reached the anidiagram demo-render suite, had 8 tests passed, and was
  normally interrupted after 147 seconds while Playwright/Chrome rendering
  continued. This is the known slow demo-render path; targeted structural and
  sample-render gates passed.
- Behavior evals are schema plus deterministic contract/receiver coverage;
  no new blind human/LLM preference run was performed, so source-fidelity
  quality is not claimed from routing numbers alone.
- No commit, push, PR, or release was created.
