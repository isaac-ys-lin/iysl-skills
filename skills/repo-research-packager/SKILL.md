---
name: repo-research-packager
description: Curate a software repository into one focused, self-contained Markdown research handoff for another AI when that receiver cannot access the repository. Preserve evidence and safety boundaries; do not use for an ordinary architecture review or a shipped artifact.
compatibility: Requires Python for the deterministic assembler; packaging itself is read-only and does not require network access.
---

# Repository Research Packager

## Intent

Produce one evidence-dense Markdown handoff that lets a receiver understand the
research objective, relevant architecture and flow, current behavior, and
evidence gaps without repository access.

## Use and boundaries

- Use when the deliverable is explicitly for another AI or reviewer without
  repository access.
- Select the smallest evidence set that explains the relevant contracts, state,
  failure behavior, tests, and constraints.
- Do not package an ordinary code review, implementation plan, or deployment
  baseline unless the user asks for a handoff.
- Default to one Taiwan Traditional Chinese `.md`; support another language or
  ZIP only when explicitly requested.

## Invariants

- Keep repository facts, external facts, hypotheses, proposals, and open
  questions distinct.
- Use repository-relative paths and line ranges; every major claim needs an
  embedded evidence source and a short selection reason.
- Exclude secrets, personal data, binaries, generated outputs, dependencies,
  unrelated details, absolute home paths, and credentials.
- Packaging is read-only. The assembler owns format, safety, overwrite, and
  character-budget checks; do not bypass a failed check by silently dropping
  load-bearing evidence.

## Adaptive execution

Read project instructions and map the research question before selecting files;
use the bundled assembler's `--print-template` and `--help` when needed. Choose
full files or focused line slices by evidence density, then stop when a blind receiver can answer the required questions. Add a second pass, fixture, or ZIP
only when uncertainty or an explicit request justifies it.

## Validation and resources

Run assembler/tests; before delivery inspect generated UTF-8 Markdown for
relative evidence, source commit, exclusions, known gaps, no secrets/personal
data, and no temporary manifest residue. Use blind-receiver cases as
calibration, not as a claim of human judgment.
