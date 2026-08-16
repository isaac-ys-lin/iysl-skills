---
name: iysl-allow-plugins
description: Interactively choose which globally enabled or current-task-visible Codex plugins may contribute capabilities in the current project. Use only when the user explicitly invokes $iysl-allow-plugins to create, inspect, change, validate, or remove a per-project plugin allowlist; do not trigger for ordinary plugin use, installation, discovery, or global plugin management.
disable-model-invocation: true
compatibility: Requires Python 3.11 or later and the Codex CLI; Visualize is optional because a numbered text fallback is built in. No network access is required.
---

# Project Plugin Allowlist

## Intent

Treat global plugin enablement as the supply of available plugins and the
project allowlist as a reversible capability mask. Do not claim this turns an
entire plugin on or off, creates a security boundary, or project-scopes apps and
connectors.

Use `scripts/allow_plugins.py` for inventory, picker generation, previews,
writes, rollback, and validation. It uses only the Python standard library.

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
- Preview the exact selection, capability effects, warnings, and file changes;
  obtain user confirmation before calling an apply or remove command.
- Modify only `.codex/allow-plugins.toml` and the marked managed block in
  `.codex/config.toml`. Preserve every unrelated byte.

## Workflow

### 1. Resolve and inventory

Resolve the intended project root before running commands. Represent each
current task-visible plugin as `NAME=PLUGIN_ROOT` and pass repeated
`--host-plugin` arguments. A plugin root contains `.codex-plugin/plugin.json`;
the script also accepts its `skills/` directory or an individual bundled skill
directory.

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
uses native `.form-check` controls and sends the selected canonical IDs back
through `window.openai.sendFollowUpMessage`. It never edits project files.

On first use, precheck all selectable plugins. On later use, precheck only the
saved allowlist, so newly discovered plugins remain unchecked. Add the built-in
text filter only when more than 30 plugins are selectable.

If `$visualize` is unavailable or disallowed, show the same grouped inventory as
a numbered text multi-select. Do not force-enable `$visualize`.

### 3. Preview, then confirm

Parse the picker follow-up as an exact set of IDs and keep this skill explicitly
invoked. Regenerate live inventory, then preview:

```bash
python3 scripts/allow_plugins.py plan \
  --project /absolute/project \
  --allow plugin-id-1 \
  --allow plugin-id-2
```

Repeat all `--host-plugin` arguments used for inventory. Explain the diff in
plain language:

- unselected bundled skills receive documented `skills.config.path` entries
  with `enabled = false`;
- unselected canonical plugins enter `tool_suggest.disabled_tools` when no
  config conflict exists;
- unselected bundled MCP servers receive plugin-scoped `enabled = false`;
- apps/connectors are reported as not project-scopeable by this workaround;
- selected plugins receive no project `enabled = true` override.

Warn before apply when either managed file is tracked by Git or generated paths
are machine/version-specific. Ask for one confirmation after the preview.

### 4. Apply and verify

Only after explicit confirmation, regenerate the same live inputs and run:

```bash
python3 scripts/allow_plugins.py apply \
  --project /absolute/project \
  --allow plugin-id-1 \
  --allow plugin-id-2 \
  --confirm-apply
```

Validate deterministic state immediately:

```bash
python3 scripts/allow_plugins.py validate --project /absolute/project
codex -C /absolute/project debug prompt-input
```

Repeat current host arguments for `validate`. CLI verification proves only the
CLI host. Tell the user to start a fresh Desktop task in the project; invoking
`$iysl-allow-plugins` there enters validation first and checks the new task's
actual plugin-prefixed skill catalog. Do not claim the current task unloaded a
plugin after a config write.

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
  connectors, external account permissions, and host-owned capability routing
  may remain available.
- New plugins are not processed in the background. They appear unchecked the
  next time this skill runs.
- Generated absolute skill paths can drift when plugin versions or machines
  change; rerun the skill after plugin updates.
- Do not add a user-facing `sync` command. The only entrypoint is
  `$iysl-allow-plugins`; planning, apply, validate, and rollback are internal
  workflow phases.
