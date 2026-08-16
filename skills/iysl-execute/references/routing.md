# Agent Routing and Fresh Review

Read this reference before any delegation, independent QA, or fresh review.

## Role and effort matrix

| Role | Model and effort | Use | Stop or escalate when |
|---|---|---|---|
| `worker` | Luna `max`, fixed | Clear, bounded, independently verifiable leaf implementation | Scope, architecture, or acceptance is no longer settled |
| `qa` | Luna `max`, fixed | Run tests and collect evidence without changing product code | A defect needs repair or acceptance must change |
| `explorer` | Terra `high` to `xhigh` | Read-only codebase or external evidence gathering | Evidence requires a product or architecture decision |
| `executor` | Terra `high` to `xhigh` | Architecture-set, context-heavy implementation | A new architecture, permission, or product judgment is required |
| `planner` | Sol `high` to `max` | Resolve a material execution-plan gap or premise collapse without implementing | A new user decision or authority expansion is required |
| `reviewer` | Fresh Sol `high` to `xhigh` | Independent, read-only adversarial delivery review | The implementation must be corrected or the approach reconsidered |

Set `fork_turns="none"` for every custom role invocation. Do not omit
`fork_turns` or use `all`: a full-history fork inherits the parent agent
identity, model, and effort, which defeats deterministic role routing. Supply
all required context through a self-contained task packet instead.

For ranged roles, explicitly select the effort when spawning. Use `high` for the
normal specialist path. Use `xhigh` for cross-cutting logic, broad evidence,
security, migration, concurrency, or high blast radius. Reserve planner `max`
for premise collapse, conflicting evidence, or a decision whose failure would
invalidate the implementation. Do not raise effort to compensate for the wrong
role; reroute the work.

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

Require fresh review when either condition holds:

- a subagent changed material production code; or
- the main agent changed production code involving architecture, migration,
  security, concurrency, persistent data, permissions, or high rollback cost.

The main agent must first inspect the complete diff and rerun relevant
verification. Then start `reviewer` with `fork_turns="none"`, no inherited
implementation history, read-only access, and no ability to edit or delegate.
Use Sol `high` normally and Sol `xhigh` for the high-risk categories above.

Give the reviewer only the original goal, acceptance criteria, allowed scope,
complete diff, and fresh verification evidence. Do not include the planner's or
implementer's reasoning, conclusions, or preferred verdict.

The reviewer returns exactly one verdict:

- `ship`: no evidenced blocker remains for the authorized implementation.
- `fix-first`: a bounded correction is required before acceptance.
- `rethink`: the approach or premise is unsafe or materially wrong.

After `fix-first`, return the bounded findings to the implementer, inspect the
new complete diff, rerun verification, and start a new fresh reviewer. Any code
change invalidates the previous review. After `rethink`, stop implementation
acceptance and use the main agent or `planner` to reconsider the approach; seek
the user only if the corrected direction requires new authority.

`ship` is an implementation-review verdict. It never authorizes commit, push,
publish, deployment, release, or another external side effect.
