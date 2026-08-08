# Public Equity Investing Source Map

Optional source-selection notes. Read only when selecting sources for
standalone collection or resolving provider, provenance, or conflict details
not supplied by the embedded plugin route.

## Source Hierarchy

Use the source closest to the claim:

1. Filed, audited, executed, regulator-published, or exchange-published material.
2. Issuer releases, presentations, transcripts, and IR material.
3. Timestamped market-data and estimate providers.
4. Authorized internal research, models, and portfolio context.
5. News, forums, and social sources as leads or sentiment context.

For non-US, dual-listed, or ADR issuers, prefer the home regulator, home exchange, and issuer filing. A provider configuration is not proof of live access; verify the scoped route before relying on it.

Search results, snippets, cached previews, and AI summaries are discovery aids, not evidence for material financial, transaction, guidance, consensus, or target-price claims. Open the underlying source and record its direct locator before marking a claim verified.

## Provider And Public-Web Route

Use this order unless the owning workflow specifies a stronger route:

1. Retrieve the claim from the regulator, exchange, executed agreement, or issuer IR when it exists.
2. Use one timestamped provider snapshot for market data, consensus, ratings, targets, or standardized comparables. Prefer a callable licensed route; otherwise use an account route, export, screenshot, or excerpt.
3. Search the public web to discover missing primary documents and corroborating sources. Query the issuer/ticker plus the exact document, metric, period, and site or regulator; open the result before using it.
4. If only a weaker public aggregator is available, label it separately and preserve its provider, upstream data source when disclosed, as-of date, analyst count, definition, and limits.
5. Log unavailable, unauthorized, stale, and empty routes. Do not silently replace a failed premium route with public data under the same source ID.

### Seeking Alpha

Treat Seeking Alpha as a timestamped provider or aggregator, not a primary
issuer source. Record the upstream provider when disclosed; do not hard-code or
assume it. Standardized financials, estimates, ratings, and peer data may
differ from issuer-reported or other provider definitions, so preserve the
provider basis and reconcile load-bearing values when necessary.

Use account-only fields through an authorized account route, including Ask SA,
and retain the returned evidence artifact. Record `provider=Seeking Alpha`,
`upstream_provider` when disclosed, `access_mode=account_route`, and the
relevant page, field, and as-of date.

When the account route is available in the in-app browser, attempt it before
classifying Seeking Alpha Chat as unavailable. A `403` from direct HTTP,
programmatic retrieval, or a crawler is a failed retrieval leg, not evidence
that the browser account route or Chat failed. Record the direct-fetch status
separately (for example, `direct_http_403`) and do not bypass the restriction.

The delivery surface does not change the claim type. For example, a user-supplied screenshot of Wall Street revenue estimates is still `estimate_consensus`, not a user assumption; a screenshot of a Quant Rating is still `provider_proprietary_score`, not analyst consensus.

| Seeking Alpha area | Useful evidence | Evidence nature | Required treatment |
|---|---|---|---|
| Ask SA | Bounded search and synthesis of recent coverage, signals, and source leads | `provider_synthesis` | Use for recall and prioritization; verify load-bearing claims at the underlying source |
| Summary / market data | Price, volume, market cap, 52-week range, short interest, beta | `fact_provider_standardized` | Timestamp and timezone; prefer exchange data for decisive market inputs |
| Ratings | SA author, Wall Street, and Quant ratings | `analyst_interpretation`, `estimate_consensus`, `provider_proprietary_score` | Keep all three separate; retain lookback and analyst count |
| Financials | Standardized income statement, balance sheet, cash flow | `fact_provider_standardized` | Reconcile material values to filing/XBRL; preserve reclassification differences |
| Earnings | Actual/estimate surprise, annual and quarterly estimates, revisions, analyst counts | actuals as standardized facts; estimates as `estimate_consensus` | Retain GAAP/normalized basis, period, low/high, and provider as-of |
| Valuation / Growth / Profitability | Multiples, forward growth, margins, returns, sector medians | `derived_provider_metric` | Retain formulas/definitions where available; recompute decisive multiples from cited inputs |
| Momentum / Options | Returns, technicals, IV, volume, open interest, implied move | `market_positioning_context` | Treat as high-frequency context with strict cutoff; never as fundamental proof |
| Peers | Provider peer set and relative metrics | `provider_comparison` | Validate the peer universe and business-model comparability before downstream use |
| Articles / transcript or filing indexes | Research interpretation and document leads | `analyst_interpretation` or discovery | Do not reproduce article bodies or index summaries; follow links to the primary document. An opened full transcript may support attributed management commentary; prefer issuer disclosures for reported figures and guidance |

Seeking Alpha can materially strengthen consensus coherence, estimate
revisions, valuation cross-checks, and positioning context, but it cannot by
itself resolve undisclosed financing, dilution, purchase accounting, synergy,
capex, tax, or technical-execution gaps. Preserve those as unresolved gaps
until an authoritative primary source addresses them; the owning workflow
determines their effect on underwriting and participation readiness.

### Consensus And Target Integrity

- Keep each provider snapshot as a separate vintage. Never blend revenue from one provider, EBITDA from another, and targets from a third into a purported single consensus package.
- Record provider, upstream provider when disclosed, security/listing, currency, fiscal basis, as-of and retrieval times, analyst population, statistic, lookback, forecast horizon, low/high, and GAAP/normalized basis.
- Keep author ratings, Wall Street ratings, proprietary quant scores, and price targets in separate rows.
- Mark methodology as `method_unknown` when the provider does not expose it. Do not infer mean, median, or a 12-month horizon.
- When two providers disagree, preserve both and explain the likely universe/date/definition difference. Do not average them.

### Public-Web Search Protocol

- Search primary domains first: regulator/EDGAR, issuer IR, exchange, government procurement, and executed counterparties.
- Use news and aggregators to discover events, dates, broker actions, and missing documents; verify material claims at the closest available source.
- Open and cite the actual page or document. A search snippet, cached result, or generative summary cannot satisfy a required source.
- Record publication time, data as-of time, retrieval time, and timezone separately when material.
- If a primary source is not yet public, state what filing or disclosure would close the gap and continue with a clearly labeled proxy only when the owner permits it.

## Conflict And Inference

- Preserve conflicting values with their dates and definitions; do not average them away.
- Prefer mechanical `derived calculation` from cited inputs over an opaque estimate.
- Mark judgment-based proxies as inferred assumptions and show what direct source would replace them.
- Never infer proprietary consensus, broker-only implementation data, private portfolio context, or restricted article bodies from public metadata.
