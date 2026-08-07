# Seeking Alpha Evidence Intake

Use this as the standard first-pass source route for every Public Equity
Investing analysis. It captures the recorded Seeking Alpha Chat workflow as a
semantic route.

## Inputs

Collect only what the owner needs:

- `ticker` and listing/exchange when ambiguous.
- `lookback`, defaulting to the last two weeks when the owner has not specified
  a window.
- Requested fields. Use current ratings, forward non-GAAP P/E and PEG, RSI,
  price versus SMA, 52-week high/low, short interest/shares outstanding, recent
  articles/news/PRs, SEC filing leads, and the latest earnings-call insights as
  a default menu; prune or extend it for the owner's decision.
- `owning_workflow`, `decision_impact`, and the evidence cut-off.

## Standard route

1. Derive the ticker, lookback, and minimum field set from the owning workflow.
   Use defaults only where the owner leaves them open; proceed when the query is
   specific enough to run.
2. Use the available account route in the in-app browser to open the Seeking
   Alpha portfolio or symbol page and select the requested ticker. A direct
   HTTP fetch, API call, or search-crawl `403` only establishes that *that
   retrieval leg* is unavailable; it does not establish that the account route
   or Ask Chat is unavailable. Do not try to bypass that restriction.
3. Open Ask Chat for that symbol and submit a query shaped like this, replacing
   placeholders with the confirmed inputs:

   > What is likely driving the recent moves in {{TICKER}} over the last
   > {{LOOKBACK}} of Seeking Alpha coverage? Use the most recent available
   > values, and check {{FIELDS}}. Also look for recent articles, news, press
   > releases, SEC filings, and the latest earnings-call insights.

4. Record the returned answer as an evidence artifact: a connected tool result,
   excerpt, screenshot, or export. The returned answer is evidence; navigation
   only identifies the route.

If Chat returns no result after the in-app account route is attempted, record
the Chat leg as `unavailable`, `blocked`, or `empty` as applicable and continue
with the next source. Separately record any failed direct-fetch leg (for
example, `direct_http_403`) so it is not mistaken for a Chat failure. Use public
pages for provider methodology or as discovery leads, then verify material
claims at the closest primary source.

## Normalize and label

For every accepted artifact, preserve `provider=Seeking Alpha`,
`access_mode=account_route`, page/field, provider as-of time,
retrieval time and timezone, listing, lookback, definitions, analyst count when
available, permission, and per-leg route status. Keep these signal families in
separate rows:

- Quant rating: `provider_proprietary_score`.
- SA Author rating: `analyst_interpretation`.
- Wall Street rating or estimates: `estimate_consensus`.
- Price, technicals, short interest, or standardized fundamentals:
  `fact_provider_standardized` or `market_positioning_context` as appropriate.
- Articles, transcripts, and filing indexes: `analyst_interpretation` or
  discovery only until the underlying source is opened.

Reconcile material values against filings, issuer IR, regulator, exchange, or
another timestamped source. Preserve conflicts and vintages; never
blend unlike provider universes into a synthetic consensus.

## Handoff

Read `plugin-handoff.md` for embedded work. Return the smallest evidence pack
with `source_id`, `provider`, `evidence_nature`, `as_of`, `retrieved_at`,
`route_status`, `permission`, `fields_observed`, `unverified_gaps`, and
`primary_followups`. Keep the account artifact and source ledger hidden from
reader-facing output unless requested. This route is complete when every
requested field is observed or marked unavailable and the handoff is traceable
to its evidence artifacts.
