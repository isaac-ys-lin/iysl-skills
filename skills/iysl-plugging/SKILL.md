---
name: iysl-plugging
description: Read every bundled skill name and description from one specified Codex plugin, prove completeness, then load only the relevant full SKILL.md instructions for the user's task. Use only when the user explicitly invokes $iysl-plugging; do not trigger for ordinary plugin use, plugin installation, discovery, enablement, removal, or permission management.
---

# Read Plugin Skills

## Intent

Build a complete, current catalog for one specified plugin before choosing its
skills. Keep the operation read-only. Do not install, enable, disable, remove,
configure, or invoke plugin tools while reading the catalog.

`iysl-plugging` is the supported successor to the archived
`$iysl-allow-plugins` capability-mask attempt, but it deliberately covers
read-only plugin discovery and skill selection only. Do not restore, call, or
modify the archived `allow_plugins.py` workflow, and do not claim to provide
project-level capability controls.

By default, read every bundled skill's complete YAML frontmatter and retain its
exact `name` and `description` in the active context. Read a full `SKILL.md`
body only after selecting that skill for the user's task. If the user explicitly
asks to read every full instruction body, finish all bodies before starting the
downstream task.

Keep the default response compact. Do not print the full catalog unless the
user explicitly asks to list it. Report the completeness receipt, the selected
skill names, and a short selection reason. If there is no downstream task,
report only the receipt and resolved plugin identity unless the user asks for
the catalog.

## Input

Require exactly one target in any of these forms:

- canonical plugin ID, such as `data-analytics@openai-curated-remote`;
- an explicit plugin mention supplied by the host;
- an absolute plugin root containing `.codex-plugin/plugin.json`.

If no target is present, ask one short question for the plugin ID, mention, or
root. Do not inventory unrelated plugins as a substitute.

## Resolve the current plugin root

Use evidence in this order:

1. Prefer paths from task-visible skills whose plugin prefix matches the target.
   Walk upward to the nearest `.codex-plugin/plugin.json`.
2. If needed, run the available Codex runtime's
   `plugin list --json`. Accept only an exact `pluginId` match that reports
   `installed: true`, and use its exact `source.path`.
3. Accept an absolute root explicitly supplied by the user.
4. Inspect cache candidates only to diagnose a miss. Never call a cache-only
   candidate current or installed. If multiple versions remain possible, list
   the exact candidates and stop instead of choosing the newest one.

Resolve symlinks before validation. Require the manifest name to match the name
portion of the requested plugin ID when an ID is available. Report the resolved
plugin ID or name, manifest version, and root. Do not continue through a missing,
malformed, mismatched, or escaping manifest path.

## Read every description

Read `.codex-plugin/plugin.json` and resolve its declared `skills` path relative
to the plugin root. Require every resolved path to remain inside that root.

Enumerate every regular file named `SKILL.md` recursively under the declared
skills path in stable path order. Do not follow a skill symlink outside the
plugin root. Then:

1. Record the discovered file count before reading any description.
2. Read each YAML frontmatter block completely through its closing delimiter;
   do not truncate multiline descriptions.
3. Retain the exact path, `name`, and `description` for every file.
4. Report malformed frontmatter, missing fields, unreadable files, and duplicate
   names explicitly.
5. Emit a completeness receipt with `read/discovered`. Say `complete` only when
   every discovered file produced a nonempty name and description.

Retain every resulting name and description for selection, but do not list the
full catalog by default. List every exact name and description only when the
user explicitly asks for the complete catalog. If the plugin declares no
skills, report `0/0` and do not pretend it offers a skill workflow.

## Select and load instructions

When the same request includes a downstream task, compare that task against all
cataloged descriptions before choosing. Select the smallest relevant skill set.
Read each selected `SKILL.md` completely and follow its instructions, including
required directly linked resources. If no description matches, say so and do
not force a plugin skill.

When the user explicitly asks for every full instruction body, read all
discovered `SKILL.md` files in stable batches, retain a second `read/discovered`
receipt for bodies, and do not begin the downstream task until it is complete.
If output or context limits prevent completion, report the exact partial count;
never silently summarize unread files.

## Failure and scope boundaries

- Stay read-only during resolution and catalog loading.
- Do not change model context or compaction settings.
- Do not treat a plugin mention alone as permission to invoke every child skill.
- Do not claim that cache presence proves installation, enablement, or current
  session visibility.
- Do not claim completeness after any file, manifest, identity, or version
  ambiguity.
- Re-resolve and reread on every invocation. Keep no persistent index, hook,
  service, or background refresh state.
