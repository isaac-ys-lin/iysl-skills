---
name: equity-data
description: Collect, verify, and reconcile source-backed public-equity inputs when the user explicitly requests a data or evidence pack, or when an owning investment workflow needs filings, estimates, market data, transcripts, or research inputs. Do not use for routine issuer questions, valuation, thesis writing, recommendations, model construction, or trade decisions.
---

# Equity Data

## Intent

Prepare the smallest reliable evidence pack for the owning Public Equity
Investing workflow. The owner, not this support layer, decides valuation,
thesis, model construction, recommendation, sizing, and trades.

## Use and boundaries

- Use for an explicit data/evidence-pack request or an owner-requested input
  collection pass; do not intercept a routine issuer fact question or thesis.
- Start from the decision and minimum input set. Let the plugin router own
  category-to-provider mapping, concrete routes, and provider guides.
- Read non-public, premium, account, or internal sources only when supplied or
  explicitly authorized. Never inspect credentials or browser storage.

## Invariants

- Prefer the source closest to the claim and keep issuer facts, provider data,
  consensus, management claims, calculations, and assumptions distinct.
- Preserve source IDs, freshness, provider vintage, definitions, conflicts,
  gaps, route status, permission, and retrieval evidence.
- Treat search results and snippets as discovery only; open and verify the
  underlying source before relying on a material claim.
- Reconcile conflicts without averaging unlike vintages; do not average them
  away or synthesize a consensus across provider universes.
- Keep the evidence pack subordinate to the owner's investor-facing artifact.
- Do not automate retrieval or bypass paywalls, login, CAPTCHA, robots rules,
  or provider terms. For Seeking Alpha, use a user-provided excerpt,
  screenshot, or export and record `route_status=terms_blocked` when needed.

## Adaptive execution

Collect only what the owner needs, continue with clearly labeled gaps when the
missing input is non-critical, and stop only when a conclusion-blocking input
cannot be supplied reliably. Read `references/source-map.md` for provider and
workflow detail; use the templates for the source ledger and data matrix.

## Handoff and validation

For embedded work, preserve the owner's canonical handoff fields and keep the
ledger hidden from reader-facing output by default. For standalone work, expose
the requested pack. Verify provenance, freshness, conflicts, gaps, permissions,
and evidence nature before handing the pack back.
