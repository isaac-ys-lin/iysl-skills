# Agent Routing and Fresh Review

Read this reference before any delegation, independent QA, or fresh review.

## Role and configuration matrix

| Role | Required configuration | Use | Stop or escalate when |
|---|---|---|---|
| `worker` | Luna `max`, fixed | Clear, bounded, independently verifiable leaf implementation | Scope, architecture, or acceptance is no longer settled |
| `qa` | Luna `max`, fixed | Run tests and collect evidence without changing product code | A defect needs repair or acceptance must change |
| `explorer` | Configured custom role | Read-only codebase or external evidence gathering | Evidence requires a product or architecture decision |
| `executor` | Configured custom role | Architecture-set, judgment-heavy implementation | A new architecture, permission, or product judgment is required |
| `planner` | Configured custom role | Resolve a material execution-plan gap or premise collapse without implementing | A new user decision or authority expansion is required |
| `reviewer` | Fresh configured custom role | Independent, read-only adversarial delivery review | The implementation must be corrected or the approach reconsidered |

Set `fork_turns="none"` for every custom role invocation. Do not omit
`fork_turns` or use `all`: a full-history fork inherits the parent agent
identity, model, and effort, which defeats deterministic role routing. Supply
all required context through a self-contained task packet instead.

The role matrix is backed by the executable configuration in
`~/.codex/agents/*.toml`. Before dispatch, verify that the named role exists
and that its configured identity matches its responsibility; in particular,
`worker` and `qa` must be the configured Luna Max roles. All other model and
effort choices remain owned by their TOML files. Do not pass model, effort,
sandbox, or other role overrides. If the role is unavailable or mismatched,
stop with the preflight failure and do not silently substitute a generic agent
or another role. Choose `solo` only when the main agent can safely satisfy the
scope and gates without delegation.

Do not automatically raise or lower any configured role effort. If a role
cannot safely finish its bounded packet,
diagnose missing evidence, narrow the packet, or return the unresolved decision
to the main agent instead of overriding its configuration.

Use one declared route:

- `solo` (default): the main agent implements, verifies, and self-reviews.
- `delegate`: one implementer substitutes for main-agent implementation; the
  main agent verifies. Select Luna Max `worker` for bounded work or the
  configured `executor` for judgment-heavy implementation.
- `audit`: the main agent implements and a fresh `reviewer` inspects the
  verified delivery.
- `full`: an explicit broad or high-risk exception with one implementer, main
  verification, and one fresh reviewer.

One auxiliary is the default maximum. `qa`, `explorer`, or `planner` may replace
the auxiliary when their responsibility is the actual bottleneck; do not stack
them as preliminary ceremony. Only `full` may use an implementer and reviewer
in sequence.

## Task packet

Give an implementer exactly these five sections:

1. `OBJECTIVE`: the observable result and completion condition.
2. `FILES AND OWNERSHIP`: allowed paths plus anything explicitly out of scope.
3. `INTERFACES`: contracts that must remain compatible.
4. `CONSTRAINTS`: repository rules, authority, safety, and non-goals.
5. `VERIFICATION`: exact tests, validators, or runtime evidence to return.

The implementer must return changed files, commands, outcomes, remaining gaps,
and any reason the task could not stay within its packet.

## Fresh independent review gate

Require fresh review when the user requests independent review or when the
production change involves architecture, migration, security, concurrency,
persistent data, permissions, or high rollback cost. Delegation, file count, or
a `material` label alone does not trigger review; the main agent's complete-diff
inspection and deterministic verification remain mandatory.

The main agent must first inspect the complete diff and rerun relevant
verification. Then start `reviewer` with `fork_turns="none"`, no inherited
implementation history, read-only access, and no ability to edit or delegate.
Use the fresh configured reviewer without model or effort overrides.

Give the reviewer only the original goal, acceptance criteria, allowed scope,
complete diff, and fresh verification evidence. Do not include the planner's or
implementer's reasoning, conclusions, or preferred verdict.

The reviewer returns exactly one verdict:

- `ship`: no evidenced blocker remains for the authorized implementation.
- `fix-first`: a bounded correction is required before acceptance.
- `rethink`: the approach or premise is unsafe or materially wrong.

After the first `fix-first`, return only the bounded findings to the implementer,
inspect the new complete diff, rerun verification, and start one new fresh
reviewer. Any code change invalidates the previous review. If that second review
is not `ship`, stop recursive reviewer spawning and return control with the
unresolved findings to the main agent; do not add another reviewer or
automatically increase effort. This ends the automated review loop, not the
authorized task. The main agent classifies the remaining findings: continue
directly when the correction remains bounded, authorized, and decision-complete;
start a newly scoped execution pass when ownership or verification must change;
or return to planning when the approach or premise is materially wrong. Seek the
user only when the corrected direction requires new authority. After `rethink`,
stop implementation acceptance and apply the same main-agent decision boundary.

`ship` is an implementation-review verdict. It never authorizes commit, push,
publish, deployment, release, or another external side effect.

## Completion receipt

Every completed route returns one inline receipt; it is not written to a
persistent artifact. Use these fields so the handoff is observable:

```yaml
declared_route: delegate
dispatched_roles:
  - role: worker
    task_name: implement-approved-change
required_gates_passed:
  complete_diff: true
  deterministic_verification: true
  fresh_review: true
```

For `solo`, keep `dispatched_roles` empty. Include one boolean in
`required_gates_passed` for every required validation or review gate, including
failed gates.
