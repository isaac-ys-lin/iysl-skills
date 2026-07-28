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

- `iysl-anidiagram` — turn a supported claim or relation into a source-faithful animated SVG, MP4, and PNG, with render checks.
- `iysl-clarify` — resolve only material intent, scope, authority, safety, or success-criteria ambiguity before an actionable change.
- `iysl-deckab` — turn source material into faithful deck outlines, Mode A/B prompts, or style-anchor workflows; it does not export PPTX.
- `iysl-sync` — record confirmed decisions and verified progress in one living plan when durable continuation or handoff is needed.
- `iysl-ytdlp-html-report` — turn one public video into a transcript-first Traditional Chinese v2 Markdown/HTML report plus verification sidecar; it does not read browser credentials.
- `equity-data` — collect and reconcile source-backed public-equity inputs for explicit evidence-pack or owner-requested workflows, not routine issuer Q&A.

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
