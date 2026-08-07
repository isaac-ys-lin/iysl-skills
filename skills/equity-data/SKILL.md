---
name: equity-data
description: Default evidence intake for substantive Public Equity Investing work, including filings, estimates, market data, transcripts, research inputs, and a bounded Seeking Alpha or Ask SA scan. Run one decision-shaped scan, then collect and verify the smallest source-backed evidence pack required by the owning workflow. Does not own thesis, valuation, models, recommendations, or portfolio actions.
---

# Equity Data

## Role

Maximize early information recall without lowering evidentiary quality.

Use Seeking Alpha and Ask SA to surface important developments, provider
signals, market expectations, and source leads quickly. Use the source closest
to each material claim for verification. The owning Public Equity Investing
workflow retains all investor judgment.
Keep the evidence pack subordinate to the owner's investor-facing artifact.

Pair with `$public-equity-investing:public-equity-investing` for substantive
issuer- or security-specific work. The plugin router owns category-to-provider mapping,
concrete routes, and provider guides. Use account, premium, or internal sources
only through an authorized route or a user-provided artifact; runtime
availability is not proof of permission, and credentials or browser storage
must not be inspected.

## Default Seeking Alpha scan

For every substantive issuer- or security-specific workflow, run one bounded
Seeking Alpha scan before investor judgment.

Skip it only when the task is purely mechanical, the user excludes it, no
relevant security or coverage exists, or no authorized route is available.
Record the reason when skipped.

Use two stages:

1. Use Ask SA to identify developments that may change the thesis, estimates,
   valuation, catalyst path, market setup, or risk.
2. Retrieve only the relevant Seeking Alpha structured fields needed to
   measure or clarify those signals, such as ratings, estimates, revisions,
   valuation, factor grades, momentum, short interest, or peer data.

Shape the lookback and fields from the owning workflow and evidence cut-off.
Do not use a fixed metric checklist when a metric is not decision-relevant.
Ask SA queries should request material developments, relevant transcript or
filing leads, meaningful rating or estimate divergence, and the strongest
bull and bear debates while separating provider facts, analyst interpretation,
and source leads.

Attempt the authorized account or in-app browser route before classifying
Seeking Alpha as unavailable. A direct HTTP, API, or crawler `403` (for
example, `direct_http_403`) marks only that retrieval leg; record it separately
and do not bypass the restriction.
Ask SA failure does not make accessible Seeking Alpha symbol-page or
structured data unavailable.

Keep the raw Ask SA response and account artifacts as supporting artifacts.
Pass only decision-relevant findings to the owning workflow.

## Evidence treatment

- Treat Ask SA output as `provider_synthesis`, not direct proof of its
  underlying factual claims.
- Treat Seeking Alpha structured fields as timestamped provider evidence and
  preserve their basis, as-of date, analyst count, upstream provider, and
  retrieval details when available.
- Keep Quant, SA Author, and Wall Street ratings or estimates as distinct but
  potentially correlated signal families. Do not average them or treat their
  agreement as independent confirmation.
- Verify load-bearing company, financial, transaction, guidance, regulatory,
  or technical claims against the closest available primary source.
- Treat articles, news summaries, transcripts, filing indexes, search snippets,
  cached previews, and AI summaries as discovery or interpretation until the
  underlying material is opened and tied to a direct source.
- Preserve material conflicts and incompatible vintages or definitions rather
  than blending them into a synthetic consensus.

## Workflow

1. Identify the owning workflow, decision, evidence cut-off, and minimum
   decision-critical inputs.
2. Run the bounded Seeking Alpha scan and record its per-leg route status,
   permission, provider vintage, and evidence artifacts.
3. Verify or supplement material findings using the closest available sources.
4. Reconcile definitions, vintages, and conflicts, then return the smallest
   sufficient evidence handoff.
5. Stop when every required input is traceably supported or explicitly labeled
   as an unresolved gap.

Read `references/source-map.md` only when selecting sources for standalone
collection or resolving provider, provenance, or conflict details not supplied
by the embedded plugin route. Use the templates only for fields material to
the owning workflow.

## Handoff

For each material finding, include only:

- `claim_or_field`
- `finding`
- `decision_relevance`
- `evidence_nature`
- `source_id`
- `as_of`
- `retrieved_at`
- `verification_status`
- `conflict_or_gap`

Record `provider`, `upstream_provider`, `definition`, `permission`, and
`route_status` when they materially affect interpretation. Keep raw provider
artifacts and source plumbing hidden from reader-facing output unless
requested.

For embedded work, preserve the owner's canonical fields:
`owning_workflow`, `decision_impact`, `readiness_effect`,
`artifact_role=embedded_support_artifact`, and
`hidden_unless_requested=true`.

For standalone requests, use
`owning_workflow=standalone_support_request` and
`artifact_role=standalone_support_artifact`; expose only the requested
evidence, material conflicts, limitations, and unresolved gaps.
