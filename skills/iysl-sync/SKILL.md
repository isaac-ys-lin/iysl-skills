---
name: iysl-sync
description: Synchronize confirmed material changes and verified progress into one concise living plan for an ongoing, non-trivial change. Use before implementation, continuation, handoff, or a known context boundary when the goal, contract, decisions, risks, sequencing, blockers, or progress changed. Skip tentative discussion, trivial or read-only work, unrelated work, and unchanged resumes.
---

# Sync Confirmed Work

Keep the current change recoverable without turning plan maintenance into the work. Synchronize confirmed state; do not add another planning ceremony.

## Keep Clear Boundaries

- Use `iysl-clarify` to resolve **what the user wants**. Sync accepted answers afterward.
- Use `think` to decide **how to approach the work**. Sync only decisions the user approved or delegated.
- Use `hunt` to diagnose failures. Sync findings only when they change the intended fix, scope, acceptance criteria, risk, or next action.
- Use `check` to review or verify. Sync only verified progress, new blockers, or an agreed plan correction.
- Do not use this skill to interview, compare solutions, diagnose, review, or implement. After syncing, return control to the authorized workflow.

Never treat the existence of a plan as authority to resume it when the user's current request is unrelated.

## Pass the Sync Gate

Create or update a plan only when both conditions hold:

1. The work is non-trivial: it spans meaningful decisions, multiple coherent steps, multiple files or sessions, or needs durable handoff.
2. New confirmed information changes at least one of: goal, observable behavior, scope, acceptance criteria, chosen approach, constraints, risks, sequencing, blockers, or verified progress.

Do not write for conversational repetition, speculative options, unaccepted recommendations, minor wording, discoverable implementation detail, every tool call, or every small completed action.

## Select One Active Plan

Follow an existing repository planning convention first. Otherwise use:

`docs/plans/<short-change-name>.md`

Before creating a file, search for a plan that matches the current change. Update it instead of creating a duplicate. Infer the active plan from the user's request, current branch, linked task, and plan contents; ask only if choosing incorrectly could materially alter the work.

Use one plan per coherent change. Do not create global registries, findings logs, progress logs, or companion files unless the repository already requires them.

## Synchronize Minimally

1. Read the complete active plan.
2. Compare it with the latest confirmed discussion and fresh repository evidence.
3. Make the smallest coherent edit that removes contradictions and stale state.
4. Preserve valid decisions and user terminology.
5. Mark assumptions explicitly; never promote a tentative idea to a confirmed decision.
6. When a decision changes, replace the stale current state and record the superseded decision plus reason in the decision log.
7. Record evidence-backed progress, including the verification performed. Never mark work complete from intent or an unverified report.
8. Keep the plan short enough to reread at the start of a session. Reference existing specs, issues, ADRs, commits, and diffs by path or URL instead of duplicating them. Summarize; do not transcribe chat.

Use this precedence when sources disagree:

1. the user's current explicit instruction or newly accepted decision
2. still-valid confirmed decisions in the active plan
3. repository evidence about actual implementation state
4. agent assumptions

Repository evidence may update progress, drift, risks, or open questions. It must not silently replace the intended contract merely because the current code still reflects an older decision.

Done when the plan has no known contradiction, reflects the latest confirmed contract and verified state, and names the next meaningful action.

If no material change passes the gate, do not edit or announce a sync.

## Use This Plan Shape

Always keep these core fields. Keep empty core content concise.

```markdown
# <Change name>

Status: Clarifying | Ready | Implementing | Blocked | Complete
Last updated: YYYY-MM-DD

## Goal

## Current contract

- In scope:
- Out of scope:
- Acceptance criteria:

## Decisions

- **Confirmed | Assumed | Superseded** — Decision and short rationale.

## Progress and evidence

- Completed result, verification, blocker, and exact next meaningful action.
```

Add these sections only when material:

- `Open questions` for unresolved questions that could change correctness or scope.
- `Implementation outline` for coherent deliverables, not tiny actions.
- `Risks and constraints` when they affect execution or acceptance.
- `Decision log` when a material decision is added, changed, or superseded.

Do not force technical detail into a plan before it is known.

## Respect Execution Boundaries

When a material sync occurs immediately before planned implementation or continuation:

1. Read the active plan.
2. Check relevant repository state for drift.
3. Stop only if an open question blocks correctness or requires new authority.
4. Return to the user's authorized workflow, which executes against the current plan.

The plan records authority; it does not expand it. A previous plan cannot authorize destructive actions, external publication, commits, or other side effects that the current request does not authorize.

Before handoff or the end of a long task, sync confirmed decisions, verified progress, blockers, and the next meaningful action. Do not claim access to an automatic compaction event; sync when a context boundary is known or requested.

## Report Briefly

After a material automatic update, say only what changed and name the plan path. Do not reproduce the plan unless the user asks.
