---
name: iysl-execute
description: Execute an approved, decision-complete software change with proportional Codex subagent delegation, deterministic validation, and fresh independent Sol review when risk warrants. Use after planning or diagnosis is complete; exclude planning, unknown-root-cause debugging, research, review-only, release-only, and trivial edits.
---

# Execution Orchestrator

## Intent

Finish an authorized software change without turning every edit into agent
ceremony. Keep scope and final judgment with the main agent; delegate only work
whose ownership and completion criteria are already clear.

## Preconditions and boundaries

- Read the current instruction, applicable repository guidance, and any active
  approved plan before changing files.
- Treat the latest user instruction as authority. Do not widen scope, infer
  destructive permission, or ask for a second approval after an executable plan
  was approved.
- If material intent, architecture, authority, or acceptance remains unresolved,
  stop the affected execution path and return it to the owning planning,
  clarification, or diagnosis workflow.
- Keep simple, low-risk, locally verifiable changes in the main agent with zero
  subagents.
- Do not treat review, commit, push, publish, release, or deployment permission
  as implied by implementation approval.

## Invariants

- The main agent owns scope, architecture, task decomposition, integration,
  acceptance, and the final response.
- Give every implementer an explicit objective, file ownership, interfaces,
  constraints, and verification contract.
- Require implementers to report actual changes, commands, results, gaps, and
  limits; never accept a bare completion claim.
- Use repository tests and deterministic validators as completion evidence.
  Agent agreement is not proof.
- Default to serial writes. Parallelize read-heavy work first; parallelize writes
  only when ownership is disjoint and the integration boundary is settled.
- Subagents must not spawn their own subagents.

## Adaptive execution

Read [references/routing.md](references/routing.md) completely before delegating,
requesting independent QA, or opening a fresh review.

1. Choose the smallest successful lane. Let the main agent implement simple
   work. Use `worker` for bounded leaf work, `executor` for architecture-set but
   context-heavy implementation, `explorer` for independent evidence gathering,
   and `planner` only for a material plan gap or premise collapse.
2. Send a bounded task packet. Do not delegate the overall goal or an unresolved
   design decision.
3. Inspect the resulting complete diff and run the narrowest relevant tests or
   validators before broader checks.
4. Use `qa` when independent test execution or evidence collection adds value.
   QA reports defects and never repairs product code.
5. Apply the fresh-review gate defined in the routing reference. A required
   review must return `ship`; otherwise continue the specified correction or
   rethink path.
6. Re-read the final diff after every correction. Stop when the authorized
   outcome and all required gates are satisfied; do not add cleanup or follow-up
   work outside scope.

## Completion

Report the observable result, modified scope, exact verification evidence,
review verdict when required, remaining limits, and any separately authorized
next step. Never report completion while required validation or fresh review is
missing, stale, or failed.
