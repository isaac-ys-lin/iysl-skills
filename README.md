# iysl-skills

Installable skills for Codex and other agents supported by the
[`skills`](https://www.npmjs.com/package/skills) CLI.

## Public Install

List the skills available from this repository:

```bash
npx skills add isaac-ys-lin/iysl-skills --list
```

Install every skill:

```bash
npx skills add isaac-ys-lin/iysl-skills
```

Install one skill globally for Codex:

```bash
npx skills add isaac-ys-lin/iysl-skills \
  --skill iysl-clarify \
  --agent codex \
  --global \
  --yes
```

Re-run the install command to pick up a newer published revision. Public
installs are copied snapshots; they do not follow local source changes.

## Included Skills

- `iysl-anidiagram` — create animated explanatory diagrams.
- `iysl-clarify` — may trigger implicitly when material user intent is missing.
- `iysl-deckab` — create source-faithful deck and prompt workflows.
- `iysl-sync` — keep confirmed decisions and progress in one concise living plan.

## Structure

```text
skills/
  <skill-name>/
    SKILL.md
    agents/
    assets/
    evals/
    references/
    reports/
    scripts/
    tests/
tools/
  install-skill.sh
  verify-skill.sh
  verify-release.sh
  verify-npx-install.sh
```

## Maintainer Source Of Truth

- This repo is the source of truth for its skills.
- Maintainer live skills should be symlinked from
  `~/.agents/skills/<skill-name>` to `skills/<skill-name>` in this repo.
- Do not keep duplicate live copies under `~/.codex/skills/<skill-name>` for
  skills managed here.
- Generated outputs, caches, virtual environments, and local render artifacts
  do not belong in this repo.

## Maintainer Development Install

```bash
tools/install-skill.sh iysl-anidiagram
```

This creates or refreshes a development symlink under `~/.agents/skills`.
That is intentionally different from a public `npx skills` copy install and
must not be used as release evidence.

## Verification

Verify one skill's portable source contract:

```bash
tools/verify-skill.sh iysl-anidiagram
```

Run all portable repository release gates:

```bash
tools/verify-release.sh
```

Run an isolated local `npx skills` copy-install and source parity check:

```bash
tools/verify-npx-install.sh
```

Live Codex prompt visibility is a separate maintainer check:

```bash
tools/verify-live-install.sh iysl-clarify
```

## License

MIT License. Copyright (c) 2026 iysl.
