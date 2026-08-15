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
- `iysl-grill` — run a user-invoked, stateless decision-tree interview that works through frontier rounds before any action.
- `iysl-deckab` — turn source material into faithful deck outlines, Mode A/B prompts, or style-anchor workflows; it does not export PPTX.
- `iysl-sync` — record confirmed decisions and verified progress in one living plan when durable continuation or handoff is needed.
- `iysl-ytdlp-html-report` — turn one public video into a transcript-first Traditional Chinese v2 Markdown/HTML report plus verification sidecar; it does not read browser credentials.
- `equity-data` — run a bounded two-stage Seeking Alpha intake—Ask SA for recall and targeted structured data for measurement—then return the smallest verified evidence pack for substantive public-equity work, not routine issuer Q&A or investor judgment.
- `writing-great-skills` — a user-invoked reference for writing predictable skills, preserved from [mattpocock/skills](https://github.com/mattpocock/skills/tree/main/skills/productivity/writing-great-skills).

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

skills-manifest.json is the single package inventory. It records ownership,
visibility, license location (`repository` or `skill`), and required release
gates; license text stays in the referenced `LICENSE`, while skill names and descriptions
remain sourced from each `SKILL.md`. The release gate also runs
`tools/verify_behavior_evals.py` for deterministic trigger/behavior contract
checks. Semantic model or human judgment is intentionally outside that CI
gate.

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

The behavior evaluator's default mode is a deterministic, blocking contract
check:

```bash
tools/verify_behavior_evals.py
```

To hand cases to a human or model evaluator, emit a JSON packet. The packet
contains each prompt and its declared checks, but this command does not call a
model:

```bash
tools/verify_behavior_evals.py --emit-case-packet /tmp/behavior-cases.json
```

After an external evaluator records one structured result for every case, run
the blocking result gate. `must_do`, `must_not_do`, and `required_validation`
are maps of item to a boolean satisfied verdict; for `must_not_do`, `true`
means the prohibited action was not observed. Results must copy the emitted
`packet_sha256` and record evaluator `kind`, `name`, and `evaluated_at`; this
binds the verdicts to the current cases and packaged skill runtime inputs and
preserves provenance. It does not bind a model, host, system prompt, or tool
policy version, and it still does not independently prove that a human or model
evaluated honestly.

```bash
tools/verify_behavior_evals.py --results /tmp/behavior-results.json
```

CI runs only the deterministic contract mode. It never presents an external
model or human semantic review as automated evidence.

Run an isolated local `npx skills` copy-install and source parity check:

```bash
tools/verify-npx-install.sh
```

Live Codex prompt visibility is a separate maintainer check:

```bash
tools/verify-live-install.sh iysl-clarify
```

For an explicit-only skill, this command verifies the live source link and
metadata parity only. Invoke `$<skill-name>` in a fresh task to verify runtime
resolution.

## License

MIT License. Copyright (c) 2026 iysl.

Third-party skills retain their upstream license and attribution in their
skill directory.
