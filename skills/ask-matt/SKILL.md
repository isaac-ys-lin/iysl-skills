---
name: ask-matt
description: Route one situation to the right skill or flow over a curated map, then render the recommended route as a self-contained HTML page. User-invoked only.
compatibility: Requires Python 3 to render the HTML map; the routing answer itself needs no dependencies. Runs fully offline.
disable-model-invocation: true
---

# Ask Matt

You don't remember every skill, so ask.

## Intent

Turn "我現在該用哪一個 skill" into one named route: where you are, what to run
next, what comes after it, and which neighbouring skill you are deliberately
not using. The route is delivered twice — as text you can act on now, and as an
HTML map that shows the route inside the whole flow.

## Use and boundaries

- `assets/flow-map.json` is the single source of the map: nodes, lanes, the two
  main-flow branches, the merges from each on-ramp, and the phase-boundary
  options. Read it before answering. Do not keep a second copy of the map in a
  reply, in this file, or in memory — two copies drift.
- Route only. Do not run the skill you recommend, and do not start the work it
  would do, until the user asks for it.
- This skill routes over the curated flow above. Enumerating the skills bundled
  in a plugin is `$iysl-plugging`; picking the phase-boundary move for a
  session is `references/phase-boundaries.md`.
- A situation the map does not cover is a valid answer: say the map does not
  cover it rather than bending a lane to fit.

## Invariants

- Establish the starting point before naming a route. Four facts change the
  answer: is there a working directory, who opened the issue, does the question
  need a runnable answer, and does the build span more than one session. Ask
  for a missing fact instead of guessing it.
- Every route step carries one reason, and the answer names the ruled-out
  neighbours with their reason. "為什麼不是 X" is half of the routing value:
  `/wayfinder` is wrong for a well-scoped feature, `/triage` is wrong for
  tickets `/to-tickets` produced, `/handoff` is wrong when nothing travels.
- `scripts/render_flow_map.py --check` must pass before any HTML is delivered.
- Write the answer file and the HTML into the OS temp directory. This skill
  leaves nothing in the user's repository unless the user asks for a path.

## Adaptive execution

1. Read `assets/flow-map.json`. Match the situation to a lane: main flow, an
   on-ramp, codebase health, vocabulary, standalone, or the precondition.
2. Settle the branch questions the lane depends on. Ask the user only for facts
   that change the route; find the rest yourself.
3. Answer in text first: the ordered route, one reason per step, then the ruled
   out neighbours and any context-hygiene warning that applies.
4. Write the same answer as JSON and render it:

   ```bash
   python3 /path/to/skill/scripts/render_flow_map.py --answer "$TMPDIR/ask-matt-answer.json" --out "$TMPDIR/ask-matt-map.html"
   ```

   The answer file is `{"situation": str, "route": [{"node", "why"}],
   "excluded": [{"node", "why"}], "notes": [str]}`; `node` values are ids from
   the map. Omit `--answer` to render the plain map when the user wants the
   whole picture rather than one route.
5. Hand over the HTML path. Stop there; the next move is the user's.

Escalate beyond one route only when the situation is genuinely two situations,
or when the user asks to compare routes. Do not turn a routing question into a
planning session.

## Validation and resources

`scripts/render_flow_map.py --check` is the hard gate: it validates the map's
ids, lanes, branch targets, step references, edges, and the answer file when
one is supplied. Read `references/phase-boundaries.md` when the question is
which of Continue / `/clear` / `/handoff` / subagent / `/compact` to take at a
boundary, not which skill to run next.
