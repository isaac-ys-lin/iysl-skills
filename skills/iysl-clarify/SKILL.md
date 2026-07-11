---
name: iysl-clarify
description: Clarify material requirement ambiguity before implementation. Use automatically when an actionable change lacks user intent that could alter observable behavior, scope, roles or flow, destructive effects, privacy or security boundaries, or acceptance criteria, and repository context cannot resolve it. Do not use for unspecified implementation details, concrete small edits, solution design, bug diagnosis, or review of existing work.
---

# Clarify Material Requirements

Resolve only the user-intent decisions that can materially change the result. Do not turn clarification into planning, specification writing, or a completeness exercise.

## Route Before Asking

Choose one primary workflow:

- Use this skill when **what the result must do** is materially ambiguous.
- Use `think` when the outcome is known and the user asks **how to design it**, compare solutions, judge feasibility, or decide whether it is worthwhile.
- Use `hunt` for errors, regressions, crashes, or failing tests. If investigation proves that correct behavior itself is undefined, clarify only that behavior.
- Use `check` to review an existing diff, PR, commit, or deliverable.
- Proceed directly when the request is concrete or only reversible implementation choices remain.

When `clarify` and `think` both appear applicable, resolve `WHAT` before `HOW`. Do not run both at once.

## Apply the Materiality Gate

Ask only when two reasonable interpretations would produce a meaningful difference in at least one of these areas:

- user-visible behavior or user flow
- included or excluded scope
- user roles, access, or permissions
- data creation, replacement, deletion, migration, or recoverability
- privacy, security, compliance, or sensitive-data handling
- conflicting plausible acceptance outcomes or definitions of success that would change whether the work is considered correct

Missing class names, internal structure, libraries, test seams, cache policy, naming, minor styling, and other reversible technical choices do not pass this gate.
The mere absence of explicit acceptance criteria does not pass it either; infer ordinary success from existing behavior, tests, and conventions when only one reasonable observable outcome remains.

## Resolve Context First

Before asking:

1. Read only the relevant repository files, project instructions, and prior decisions needed to resolve the ambiguity.
2. Reuse facts and decisions already present in the conversation.
3. Follow established project conventions for reversible, low-risk choices.
4. Identify the smallest set of decisions that truly require user intent.

Do not ask the user to restate discoverable facts. Do not turn repository inspection into a broad audit.

## Ask Efficiently

- Default to zero questions.
- Handle at most three user-intent decisions in one clarification pass.
- Ask exactly one question at a time and wait for the answer before continuing.
- For each decision, state the material consequence in one sentence, recommend one answer grounded in current context or the safest conventional default, and offer at most two genuinely different alternatives.
- Treat “yes,” “照建議,” “你決定,” or equivalent delegation as acceptance of the recommendation for reversible or low-risk choices. Do not ask again in different words.
- Always ask about unresolved destructive, privacy, security, or permission boundaries; never silently choose a risky default. Do not re-ask when the user has already given explicit authorization.
- For irreversible deletion, sensitive-data disclosure, or permission expansion, name the exact data, actors, scope, and recoverability before asking for explicit confirmation. Generic delegation such as “你決定” is not authorization for these actions.

If more than three material ambiguities appear, synthesize a coherent recommended contract and ask only about the one to three highest-risk decisions. Do not extend the interview to exhaust a checklist.

## Stop

Stop as soon as no remaining unknown user intent could change the observable result, scope, high-risk boundary, or acceptance decision. Remaining implementation choices belong to the agent or to `think`.

Respect requests to stop, proceed, or accept the recommendation. Never fill a question quota.

## Hand Back a Compact Contract

Summarize only the fields that add information:

- Goal
- Observable behavior
- Scope boundary
- Acceptance criteria
- Agent-owned assumptions

Keep the summary brief and use the user's terminology. Do not create a spec, plan, tickets, branch, commit, or code merely because this skill ran.

If the user asked only to clarify, stop after the contract. If the original request also authorized implementation, return to the normal execution workflow after the necessary answers are resolved; do not require a second approval.
