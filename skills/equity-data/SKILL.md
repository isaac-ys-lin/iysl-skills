---
name: equity-data
description: Default evidence-collection support for every Public Equity Investing analysis, including a Seeking Alpha Chat pass, and for standalone evidence-pack requests covering filings, estimates, market data, transcripts, or research inputs. The owning investment workflow retains valuation, thesis, models, recommendations, and trade decisions.
---

# Equity Data

## Intent

Prepare the smallest reliable evidence pack before the owning Public Equity
Investing workflow makes investor judgments.

## Use and boundaries

- Pair with `$public-equity-investing:public-equity-investing` for every listed-
  equity analysis and run this collection pass before investor judgment.
- Start from the decision and minimum input set. Let the plugin router own
  category-to-provider mapping, concrete routes, and provider guides.
- Use non-public, premium, account, or internal sources through the available
  account or internal route.

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

## Execution

1. Resolve the owning workflow, decision use, evidence cut-off, and minimum
   input set. Read `references/source-map.md` when selecting sources. Proceed
   when the required fields are clear enough to collect without widening scope.
2. Collect the closest available evidence and include the standard Seeking
   Alpha Chat pass from `references/seeking-alpha-intake.md`. Adapt its lookback
   and fields to the decision; broaden only when the first pass is thin, stale,
   or conflicting. Proceed when each requested input has evidence or a labeled
   gap.
3. Reconcile definitions, vintages, and conflicts, then build the smallest
   handoff using the source-ledger and data-matrix templates. Finish when the
   owner can trace every material input to a source ID and see each unresolved
   gap.

## Handoff and validation

For embedded work, read `references/plugin-handoff.md`, preserve the owner's
canonical handoff fields, and keep the ledger hidden from reader-facing output
by default. For standalone work, expose the requested pack.
