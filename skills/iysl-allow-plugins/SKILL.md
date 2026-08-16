---
name: iysl-allow-plugins
description: Interactively choose and runtime-verify which globally enabled or current-task-visible Codex plugin skills and MCP servers may contribute capabilities in the current project. Use only when the user explicitly invokes $iysl-allow-plugins to create, inspect, change, validate, or remove a per-project plugin allowlist; do not trigger for ordinary plugin use, installation, discovery, or global plugin management.
disable-model-invocation: true
compatibility: Requires Python 3.11 or later and the Codex CLI; Visualize is optional because a numbered text fallback is built in. No network access is required.
---

# Project Plugin Allowlist

## Intent

Treat global plugin enablement as the supply of available plugins and the
project allowlist as a reversible, runtime-verified mask for bundled skills and
canonical MCP servers. Do not claim access control, security isolation, or
project scoping of apps, connectors, account permissions, or host-owned
capabilities.

Use `scripts/allow_plugins.py` for inventory, picker generation, internal
preflight, writes, rollback, and validation. It uses only the Python standard
library.

## Invariants

- Operate on the resolved current project only. Require it to be trusted before
  proposing or applying project config.
- Inventory from the global config, `codex plugin list --json`, and the current
  task's plugin-prefixed skill catalog. Treat cache manifests as metadata, never
  proof that a plugin is installed or enabled.
- Prefer canonical identity in this order: CLI `pluginId`, exact global config
  table ID, then manifest name plus catalog root. Label synthesized IDs and do
  not use them for tool-suggestion config.
- Fail closed without writing on invalid TOML, missing declared manifests or
  capability files, missing skill paths, identity collisions, duplicate config,
  managed-block drift, config conflicts, or unsupported CLI JSON.
- Never write project `enabled = true` for a selected plugin. Selection inherits
  global state; this workflow cannot reliably re-enable a globally disabled
  plugin.
- Treat the picker submission, or an apply-language text fallback, as the one
  explicit apply confirmation. Regenerate live inventory and run the internal
  fail-closed preflight before applying; never ask for a second user-facing
  preview or confirmation for that selection. Keep remove/rollback
  preview-then-confirm.
- Aggregate only canonically attributed valid capability roots for each disabled
  plugin and deduplicate paths, tools, and MCP servers. Treat cache-only roots
  as metadata; never mix same-name catalog variants. If an attributed root or
  declared capability cannot be inspected, fail closed without writing.
- Record bundled skills as absolute `SKILL.md` file paths; generated
  `skills.config.path` entries must target those files, not their directories.
- Modify only `.codex/allow-plugins.toml` and the marked managed block in
  `.codex/config.toml`. Preserve every unrelated byte.
- Treat apply as a transaction. Snapshot both managed files, write atomically,
  then probe every discovered executable runtime in this order: Desktop Codex,
  then PATH Codex after same-file deduplication. Use a fresh App Server
  `skills/list(forceReload=true)` catalog and that binary's `mcp list --json`.
  If a skill/MCP leak, protocol/process/schema failure, or timeout occurs,
  restore the two files exactly and report the runtime evidence. Never call a
  file-only result applied or valid.
- Detect observable managed-file drift after the plan snapshot, immediately
  before each atomic replacement, and after runtime probing. Preserve observed
  newer content and report rollback failure instead of overwriting it. Do not
  claim cross-process linearization: ordinary filesystem replacement cannot
  prevent every uncooperative external race.

## Workflow

### 1. Resolve and inventory

Resolve the intended project root before running commands. Represent each
current task-visible plugin as `NAME=PLUGIN_ROOT` and pass repeated
`--host-plugin` arguments. A plugin root contains `.codex-plugin/plugin.json`;
the script also accepts its `skills/` directory or an individual bundled skill
directory. If one canonical plugin has multiple observed roots, pass every
root; all valid capability paths are then included in the mask.

Create a task-owned temporary inventory file:

```bash
python3 scripts/allow_plugins.py inventory \
  --project /absolute/project \
  --host-plugin visualize=/absolute/plugin/root \
  --output /absolute/task-temp/plugin-inventory.json
```

Do not expose cache-only entries as choices. Group selectable entries as:

1. confirmed globally enabled;
2. current Desktop task-visible with global state unverified.

Explicitly report globally disabled, stale, cache-only, ambiguous, or
uninspectable entries outside the picker.

### 2. Ask with checkboxes

If `$visualize` is available, use it and generate its native checkbox fragment:

```bash
python3 scripts/allow_plugins.py picker \
  --inventory /absolute/task-temp/plugin-inventory.json \
  --output /absolute/thread-visualization/plugin-allowlist.html
```

Show the returned fragment with the visualization content reference. The picker
uses native `.form-check` controls, a concise `套用設定` button, and
`window.openai.sendFollowUpMessage`. It preserves the exact project path and
`selected_plugins` JSON; the picker itself never edits project files.

On first use, precheck all selectable plugins. On later use, precheck only the
saved allowlist, so newly discovered plugins remain unchecked. Add the built-in
text filter only when more than 30 plugins are selectable.

If `$visualize` is unavailable or disallowed, show the same grouped inventory as
a numbered text multi-select. When the user submits that selection with apply
language, treat it as the same one explicit confirmation. Do not force-enable
`$visualize`.

### 3. Submit once, preflight internally, then apply

Parse the picker follow-up as an exact set of IDs and keep this skill explicitly
invoked. Its apply language is the one explicit apply confirmation; do not ask a
second user-facing preview or confirmation. Regenerate live inventory and run
the plan as an internal fail-closed preflight:

```bash
python3 scripts/allow_plugins.py plan \
  --project /absolute/project \
  --allow plugin-id-1 \
  --allow plugin-id-2
```

Repeat all `--host-plugin` arguments used for inventory. Use the plan output to
check the exact selection, capability effects, warnings, and file changes:

- unselected bundled skills receive documented `skills.config.path` entries
  targeting absolute `SKILL.md` files with `enabled = false`;
- unselected canonical plugins enter `tool_suggest.disabled_tools` when no
  config conflict exists;
- unselected bundled MCP servers receive plugin-scoped `enabled = false`;
- apps/connectors are reported as not project-scopeable by this workaround;
- selected plugins receive no project `enabled = true` override.

If preflight is clean, invoke `apply --confirm-apply` immediately; that CLI flag
records the already received picker confirmation and is not another user-facing
question. Report tracked-file and machine/version warnings with the result.

### 4. Apply as one runtime-gated transaction

Regenerate the same live inputs and run immediately after the picker follow-up:

```bash
python3 scripts/allow_plugins.py apply \
  --project /absolute/project \
  --allow plugin-id-1 \
  --allow plugin-id-2 \
  --confirm-apply
```

`apply` snapshots the exact two managed files, writes them, then checks every
discovered local runtime with a fresh App Server skill catalog and the same
binary's MCP configuration. Desktop is checked first. A matching enabled skill,
an enabled MCP config row, or a runtime-ready MCP row with tools causes an
automatic exact rollback and nonzero structured result. Do not retry by
weakening the mask.

Validate file consistency and the same runtime gate immediately:

```bash
python3 scripts/allow_plugins.py validate --project /absolute/project
```

Repeat current host arguments for `validate`. Report success only as runtime
verified. Validation is read-only: a runtime mismatch is nonzero and leaves both
files unchanged. Tool-suggestion suppression is not runtime-enforcement proof.

### 5. Remove restrictions

When the user chooses “remove project restrictions,” preview first:

```bash
python3 scripts/allow_plugins.py remove --project /absolute/project
```

After explicit confirmation:

```bash
python3 scripts/allow_plugins.py remove \
  --project /absolute/project \
  --confirm-remove
```

Remove only the allowlist file and managed block. Revalidate remaining TOML and
report that a fresh task is required.

## Scope limits

- This is a project convenience layer, not access control. Plugin apps,
  connectors, external account permissions, host-owned capability routing, and
  other host capabilities remain out of scope.
- New plugins are not processed in the background. They appear unchecked the
  next time this skill runs.
- Generated absolute skill paths can drift when plugin versions or machines
  change; rerun the skill after plugin updates.
- Do not add a user-facing `sync` command. The only entrypoint is
  `$iysl-allow-plugins`; planning, apply, validate, and rollback are internal
  workflow phases.
