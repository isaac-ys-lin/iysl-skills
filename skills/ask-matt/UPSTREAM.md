# Upstream

- Repository: https://github.com/mattpocock/skills
- Path: `skills/engineering/ask-matt`
- Snapshot commit: `321658273cb1d20b76026717d027d505790106d4`
- Saved: 2026-08-24
- License: MIT; copyright Matt Pocock

`SKILL.md` and `PHASE-BOUNDARIES.md` at that commit were byte-identical to the
locally installed copy under `~/.agents/skills/ask-matt`, verified against
`raw.githubusercontent.com` before this fork was taken.

## What this fork changes

- The routing map moved out of prose into `assets/flow-map.json`, the single
  source of truth for nodes, routes, branch questions, and the exclusions that
  upstream buried in paragraphs. `SKILL.md` now carries the routing procedure
  and its invariants instead of a second copy of the map.
- `scripts/render_flow_map.py` renders the map as one self-contained
  Traditional Chinese HTML page, and highlights the recommended route when an
  answer file is supplied. `--check` is the structural gate.
- Upstream `PHASE-BOUNDARIES.md` is kept verbatim as
  `references/phase-boundaries.md`, so the SKILL.md link is covered by the
  repository's declared-resource test.
- Local agent metadata; the skill stays user-invoked only, as upstream is.
