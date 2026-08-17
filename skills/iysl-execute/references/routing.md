# Agent Routing and Fresh Review

Read this reference before any delegation, independent QA, or fresh review.

## Role and effort matrix

| Role | Model and effort | Use | Stop or escalate when |
|---|---|---|---|
| `worker` | Luna `max`, fixed | Clear, bounded, independently verifiable leaf implementation | Scope, architecture, or acceptance is no longer settled |
| `qa` | Luna `max`, fixed | Run tests and collect evidence without changing product code | A defect needs repair or acceptance must change |
| `explorer` | Terra `medium`, fixed | Read-only codebase or external evidence gathering | Evidence requires a product or architecture decision |
| `executor` | Terra `high`, fixed | Architecture-set, judgment-heavy implementation | A new architecture, permission, or product judgment is required |
| `planner` | Sol `high`, fixed | Resolve a material execution-plan gap or premise collapse without implementing | A new user decision or authority expansion is required |
| `reviewer` | Fresh Sol `high`, fixed | Independent, read-only adversarial delivery review | The implementation must be corrected or the approach reconsidered |

Set `fork_turns="none"` for every custom role invocation. Do not omit
`fork_turns` or use `all`: a full-history fork inherits the parent agent
identity, model, and effort, which defeats deterministic role routing. Supply
all required context through a self-contained task packet instead.

Effort is fixed by role; automatic routing never raises it to `xhigh` or `max`
outside the Luna roles. If a fixed role cannot safely finish its bounded packet,
diagnose missing evidence, narrow the packet, or return the unresolved decision
to the main agent instead of increasing effort.

Use one declared route:

- `solo` (default): the main agent implements, verifies, and self-reviews.
- `delegate`: one implementer substitutes for main-agent implementation; the
  main agent verifies. Select Luna `worker` for bounded work or Terra
  `executor` for judgment-heavy implementation.
- `audit`: the main agent implements and a fresh Sol `reviewer` inspects the
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
Use fresh Sol `high`.

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
is not `ship`, stop the review loop and return the unresolved findings to the
main agent; do not add another reviewer or automatically increase effort. After
`rethink`, stop implementation acceptance. The main agent reconsiders the
approach and uses `planner` only for an actual premise collapse; seek the user
only if the corrected direction requires new authority.

`ship` is an implementation-review verdict. It never authorizes commit, push,
publish, deployment, release, or another external side effect.
