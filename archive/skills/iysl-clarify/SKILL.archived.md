---
name: iysl-clarify
description: Resolve only material user-intent ambiguity before an actionable change when repository and conversation context cannot determine the observable result, scope, authority, destructive effect, privacy boundary, conflicting acceptance criteria, or success outcome. Do not use for reversible implementation choices, design comparison, debugging, or review.
---

# Material Intent Gate

## Intent

Resolve the smallest missing user decision that could materially change the
observable result. Then return to the original authorized workflow.

## Use and boundaries

- Use when two reasonable interpretations change behavior, scope, roles,
  permissions, data handling, recoverability, privacy, security, or success.
- Inspect repository instructions, existing behavior, tests, and conversation
  context before asking; do not ask for discoverable facts.
- Do not use for reversible implementation details, design exploration,
  debugging, existing-work review, or a concrete complete request.

## Invariants

- Default to zero questions when one defensible contract remains.
- Ask only about material intent or authority, never about ceremony or naming.
- Never infer permission for irreversible deletion, sensitive disclosure, or
  permission expansion from generic delegation.
- Recommend a grounded default and state the material consequence of each
  unresolved choice.

## Adaptive execution

Use one question for the highest-risk decision by default. Ask a minimal group
of two or three coupled questions only when separating them would create a
duplicated round trip. If more ambiguity exists, resolve the decisions that
can change correctness first and leave implementation choices to the agent.

Stop as soon as the contract is defensible. Summarize only the resolved goal,
observable behavior, scope boundary, acceptance, and agent-owned assumptions.
When implementation was already authorized, do not require a second approval.
