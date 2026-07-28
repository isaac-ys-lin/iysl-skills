# Video report HTML-first delivery

Status: Complete
Last updated: 2026-07-26

## Goal

Make desktop HTML the primary video-report deliverable while preserving transcript-grounded content and delegating presentation to Kami without vendoring its assets.

## Current contract

- In scope: Standard output is HTML + Markdown; PDF and visual QA run only when explicitly requested. Reader-facing reports use `內容重述 → 洞見 → food for thoughts → 可行啟發`.
- Out of scope: Kami source changes, copied Kami templates/diagrams, mobile acceptance, default screenshots, and default PDF generation.
- Acceptance criteria: deterministic HTML/schema/content/sidecar checks pass; `驗證與限制`, evidence ids, operator paths, commands, and extraction limitations do not appear in reader-facing Markdown/HTML.

## Decisions

- **Confirmed** — Target desktop browser use; Standard runs deterministic checks only and reports visuals as unconfirmed.
- **Confirmed** — Keep extraction limitations and verification evidence only in `<video_id>.verification.md`.
- **Confirmed** — Let prompt-visible Kami own HTML layout and diagrams; do not duplicate its assets or implementation.
- **Superseded** — Standard/Deep no longer produces PDF or runs visual/density/font/page-count checks by default.

## Progress and evidence

- Reader-facing v1/v2 outputs now contain only the four confirmed chapters; legacy `驗證與限制` content is discarded.
- v2 supports a text-only `narrative` block, so interviews and ordinary narratives do not need invented process/comparison visuals.
- `validate_report_artifacts.mjs` deterministically compares spec, Markdown, final HTML, and sidecar; it rejects missing content, extra sections, source/transcript limitations, operator paths, empty sidecar fields, and empty evidence/limits sections.
- Verification: `24 passed, 14 subtests passed`; live install visible; adversarial review passed; `tools/verify-release.sh` finished with `portable release gates passed`.
- Visual status: not manually inspected by design; PDF, screenshots, mobile, font, density, and page-count checks were not run.
