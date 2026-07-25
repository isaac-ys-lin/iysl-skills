---
name: equity-data
description: Prepare source-backed evidence packs for Public Equity Investing workflows using filings, issuer materials, authorized provider exports or user-supplied account data, and gap-led public web research. Use when a listed issuer, ticker, watchlist, model, earnings task, memo, pitch, catalyst, thesis, or risk workflow needs collected, labeled, freshness-aware inputs before analysis; this is a support layer, not the owner of valuation, recommendations, model construction, or trade decisions.
---

# Equity Data

## Role

Prepare the smallest reliable evidence pack needed by an owning Public Equity Investing workflow.

When a plugin workflow is already selected, follow its input needs and preserve it as the owner. If no owner is clear, collect a baseline suitable for `company-tearsheet`, recommend the next workflow, and ask only when the choice would materially change what must be collected.

## Principles

- Start from the investment workflow and decision, then collect data. Do not build a universal company dossier by default.
- Prefer the source closest to the claim: filings and regulators, issuer IR and transcripts, timestamped providers, authorized internal research, then public news or social sources as leads.
- Treat provider-standardized fundamentals, consensus, ratings, targets, and factor scores as separate evidence classes. Never promote an aggregator value to an issuer-reported fact or merge unlike provider universes into one consensus.
- When embedded, let the plugin router own category-to-provider mapping, concrete routes, and provider guides; do not substitute routes or add setup gates. Outside plugin-managed routes, confirm permission before reading non-public sources.
- Keep facts, provider-standardized data, management claims, consensus, calculations, and assumptions distinct. Track freshness, conflicts, and missing evidence separately.
- Continue with a clearly limited or not-decision-ready pack when useful. Stop only when a missing input owns a required output and cannot be reliably supplied or inferred.
- Keep the evidence pack subordinate to the plugin's investor-facing artifact. Do not make valuation, thesis, recommendation, sizing, or trade decisions.

## Workflow

1. Confirm the issuer/security, owning workflow, decision use, and data cut-off. For non-US, dual-listed, or ADR issuers, also capture the home listing, reporting regime, currency, accounting standard, and share/ADR relationship when relevant.
2. Define the minimum input set from the owning workflow. Gather only the needed plugin categories:
   - `company_filings_ir`
   - `earnings_transcripts_presentations`
   - `market_data_estimates`
   - `portfolio_models_trackers`
   - `internal_research`
3. Resolve the source route and record every attempt. Prefer a callable provider selected by the plugin; otherwise use user-provided exports or excerpts, then primary-source-first public web research. Treat search results and snippets as discovery only until the underlying page is opened and verified.
4. Build a source ledger before relying on extracted values. For each material source, retain a source ID, provider/document, source kind, category, access mode, permission, route status, period or provider as-of date, retrieval time and timezone, location, freshness, confidence, intended use, and fallback reason when applicable.
5. Record material items with value/unit, definition and provider universe, period or as-of date, evidence nature, source IDs, confidence, freshness, conflict or gap status, and downstream use. A screenshot, excerpt, or export changes the access mode, not the evidence nature: provider consensus remains consensus and a proprietary score remains a provider score. For consensus or price targets, also retain the listing/currency, analyst population, statistic, lookback, forecast horizon, low/high when available, and whether estimates are GAAP or normalized.
6. Reconcile conflicts using the source closest to the claim. Preserve unresolved provider vintages and definitions as separate rows; do not average them away. For public inference, cite the inputs and show the calculation or reasoning; never reconstruct inaccessible or paywalled content.
7. For a substantial embedded pass, preserve the plugin's canonical `owning_workflow`, `decision_impact`, `readiness_effect`, `artifact_role=embedded_support_artifact`, and `hidden_unless_requested=true` fields. Pass the ledger to the owner in internal context or a support artifact, but keep it out of the reader-facing artifact unless requested. For standalone collection, use `owning_workflow=standalone_support_request`, `artifact_role=standalone_support_artifact`, and expose the requested data pack.

## Evidence And Readiness

When embedded, inherit the owning workflow's evidence and readiness contract. For a standalone pack, use the plugin-compatible labels in the collected-data template and keep evidence nature separate from freshness, conflict, and gap status.

For structured embedded handoffs, use the owning workflow's `readiness_effect`. In reader-facing output, describe practical limitations in decision-specific, investor-readable language rather than implying the entire underwrite is ready.

## Boundaries

- Outside a plugin-managed route, use public sources by default and use premium, internal, local, portfolio, or account sources only when the user supplies or explicitly authorizes them.
- Do not inspect credentials, cookies, browser storage, unrelated local files, or entitlement mechanisms; do not bypass paywalls or reproduce restricted article bodies.
- Obey provider terms. Do not automate retrieval from a site that prohibits robots, scraping, data mining, or systematic extraction. For Seeking Alpha, use a user-provided excerpt, screenshot, or export for account-only fields; use its public help pages only for methodology and provenance. If no compliant export or callable licensed route exists, record `route_status=terms_blocked` and continue with public sources.
- Keep provider content minimal: capture values, field labels, dates, definitions, and locators needed for the evidence pack, not article bodies or substitute summaries. Do not transmit restricted content to another service.
- Stop a provider route on login, CAPTCHA, payment, permission, robot challenge, or entitlement failure. A public fallback receives a new source ID, access mode, availability, and confidence; it never inherits authenticated-provider status.
- Do not normalize messy financials, build models, calculate intrinsic value, write the final memo or pitch, or recommend a position. Hand those jobs to the relevant Public Equity Investing owner.

## Resources

- Read `references/source-map.md` for plugin categories, source hierarchy, provider/web routing, Seeking Alpha field mapping, and workflow-specific minimum inputs.
- Use `templates/source-ledger.md` for source-level provenance.
- Use `templates/collected-data-matrix.md` for material facts, estimates, assumptions, conflicts, and gaps.
- Use `templates/data-request-checklist.md` only to request missing decision-relevant inputs.
