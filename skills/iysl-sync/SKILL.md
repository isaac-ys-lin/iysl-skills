---
name: iysl-sync
description: Synchronize confirmed material decisions and verified progress into one concise living plan when an ongoing change needs durable state, continuation, or handoff. Skip tentative discussion, trivial or read-only work, unrelated work, and unchanged resumes.
---

# State Synchronizer

## Intent

Keep one coherent change recoverable across implementation, context boundaries,
and handoff without making plan maintenance the work.

## Use and boundaries

- Update an existing active plan when confirmed decisions, acceptance,
  blockers, scope, risks, or verified progress materially changed.
- Create a plan only for an explicit plan/handoff request or work whose
  cross-session or multi-party state would otherwise be lost. Prefer the
  repository convention; otherwise use `docs/plans/<short-name>.md`.
- Do not use for interviews, design comparison, debugging, review, routine
  multi-file edits, speculative discussion, or unchanged continuation.

## Invariants

- Sync confirmed decisions and evidence, never chat transcripts or guesses.
- Keep one active plan per coherent change; remove contradictions rather than
  appending stale history.
- The plan records authority; it does not expand the current user instruction.
- Never mark work complete from an unverified report.
- Do not create registries, companion logs, or duplicate plans.

## Adaptive execution

Read the complete active plan and current repository state first. Make the
smallest idempotent edit that preserves the current contract. Use
`assets/living-plan-template.md` only when a new plan is genuinely needed; the
template is a default shape, not a checklist. If no material state changed,
make no edit.

When the current instruction conflicts with an old plan, follow the current
instruction and record the superseded decision only when the durable plan
needs that context. At handoff, record the latest verified result, blocker, and
next meaningful action, then stop.

Keep unfinished, still-active work in its active plan; do not delete or archive
it. After verifying completion, delete the working plan when a commit, spec,
ADR, or other durable artifact fully records the final contract, outcome,
material verification, and decisions still needed to explain the result. If
the completed work lacks such complete coverage, replace the plan with a
concise final-state record, remove superseded content, stale execution detail,
and resolved blockers, then move it using the repository's archive convention
or `docs/plans/archive/<original-filename>.md` when none exists. Keep only
active plans in the active-plan location. Apply the same durable-record test to
explicitly superseded or abandoned plans.

## Validation and resources

Before completion, check that the plan has no known contradiction, reflects
verified state, and names the next action. Rerunning the same input must create
no semantic diff. Read existing specs, ADRs, commits, and diffs by reference
instead of copying their full content.
