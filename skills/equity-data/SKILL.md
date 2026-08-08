---
name: equity-data
description: "Collect the smallest source-backed evidence pack for substantive Public Equity Investing or standalone filings, estimates, market data, transcript, consensus, and provider-reconciliation requests. For issuer/security work, run a bounded two-stage Seeking Alpha scan as evidence intake: Ask SA recall, targeted structured data, and verification of load-bearing claims. Does not own investment judgment."
---

# Equity Data

## Role

Maximize early information recall without lowering evidentiary quality or
crowding out the owning workflow's decision context.

Use Seeking Alpha and Ask SA to surface important developments, provider
signals, market expectations, and source leads quickly. Use the source closest
to each material claim for verification. The owning Public Equity Investing
workflow retains all investor judgment. The owner defines the decision,
required inputs, and analytical standard; this skill returns evidence only.
Keep the evidence pack subordinate to the owner's investor-facing artifact.

Pair with `$public-equity-investing:public-equity-investing` for substantive
issuer- or security-specific work. The plugin router owns category-to-provider mapping,
concrete routes, and provider guides. Use account, premium, or internal sources
only through an authorized route or a user-provided artifact; runtime
availability is not proof of permission, and credentials or browser storage
must not be inspected.

## Default Seeking Alpha scan

For every substantive issuer- or security-specific workflow, run one bounded
two-stage Seeking Alpha scan before investor judgment. For a multi-security
screen, scan only priority names, outliers, and decision-critical securities
selected by the owning workflow; record the selection rule and any material
exclusions, not every unscanned name.

Skip it only when the task is purely mechanical, the user excludes it, no
relevant security or coverage exists, or no authorized route is available.
Record the reason when skipped.

Use two stages:

1. Use Ask SA to identify developments that may change the thesis, estimates,
   valuation, catalyst path, market setup, or risk.
2. Retrieve only the relevant Seeking Alpha structured fields surfaced by the
   scan or independently required by the owning workflow, such as ratings,
   estimates, revisions, valuation, factor grades, momentum, short interest,
   or peer data.

Require the Ask SA response to separate provider facts, analyst
interpretation, and source leads. The second stage is the targeted retrieval
leg; do not treat the two stages as interchangeable.

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
- Treat articles, news summaries, transcript indexes or summaries, filing
  indexes, search snippets, cached previews, and AI summaries as discovery or
  interpretation until the underlying material is opened and tied to a direct
  source.
- Once a full transcript is opened and its provenance is recorded, it may
  support attributed management commentary. Prefer formal issuer disclosures
  for reported figures, guidance, and other load-bearing financial claims.
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

Read `references/source-map.md` only for standalone collection or when the
embedded plugin route does not supply provider, provenance, or conflict
details. Use the templates only for fields material to the owning workflow.

## Handoff

For each material finding, include only:

- `claim_or_field`
- `finding`
- `decision_relevance`
- `evidence_nature`
- `source_id`
- `as_of`
- `verification_status`
- `conflict_or_gap`

Record `retrieved_at`, `provider`, `upstream_provider`, `definition`,
`permission`, and `route_status` when they materially affect interpretation or
route auditability. Keep raw provider artifacts and source plumbing hidden
from reader-facing output unless requested.

For embedded work, include the owner's `owning_workflow` and
`decision_impact`. When required by the owner, preserve its canonical
`readiness_effect`, `artifact_role=embedded_support_artifact`, and
`hidden_unless_requested=true` metadata without inventing readiness or an
investor-facing conclusion.

For standalone requests, use
`owning_workflow=standalone_support_request` and
`artifact_role=standalone_support_artifact`; expose only the requested
evidence, material conflicts, limitations, and unresolved gaps.
