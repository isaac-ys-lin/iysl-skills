# Public Equity Investing Source Map

Read this only when selecting sources or defining the minimum handoff packet.

## Source Hierarchy

Use the source closest to the claim:

1. Filed, audited, executed, regulator-published, or exchange-published material.
2. Issuer releases, presentations, transcripts, and IR material.
3. Timestamped market-data and estimate providers.
4. Authorized internal research, models, and portfolio context.
5. News, forums, and social sources as leads or sentiment context.

For non-US, dual-listed, or ADR issuers, prefer the home regulator, home exchange, and issuer filing. A provider configuration is not proof of live access; verify the scoped route before relying on it.

Search results, snippets, cached previews, and AI summaries are discovery aids, not evidence for material financial, transaction, guidance, consensus, or target-price claims. Open the underlying source and record its direct locator before marking a claim verified.

## Plugin Source Categories

| Category | Typical content |
|---|---|
| `company_filings_ir` | Filings, IR materials, reported financials, governance, and disclosures |
| `earnings_transcripts_presentations` | Earnings calls, investor events, presentations, and management commentary |
| `market_data_estimates` | Price, estimates, ownership, positioning, factors, and comparable-company data |
| `portfolio_models_trackers` | Models, workbooks, watchlists, trackers, positions, and analyst workpapers |
| `internal_research` | Notes, saved theses, meetings, expert context, email, and team research |

Resolve only the categories needed by the owning workflow. When embedded, the plugin router owns category mapping, the concrete provider route, and any provider guide. Follow that route and use additional sources only when they materially improve recency, confidence, or the investment decision. For standalone collection, prefer a user-named source, then an authorized and callable provider, file, export, pasted input, or public fallback.

## Provider And Public-Web Route

Use this order unless the owning workflow specifies a stronger route:

1. Retrieve the claim from the regulator, exchange, executed agreement, or issuer IR when it exists.
2. Use one timestamped provider snapshot for market data, consensus, ratings, targets, or standardized comparables. Prefer a callable licensed route; otherwise use an account route, export, screenshot, or excerpt.
3. Search the public web to discover missing primary documents and corroborating sources. Query the issuer/ticker plus the exact document, metric, period, and site or regulator; open the result before using it.
4. If only a weaker public aggregator is available, label it separately and preserve its provider, upstream data source when disclosed, as-of date, analyst count, definition, and limits.
5. Log unavailable, unauthorized, stale, and empty routes. Do not silently replace a failed premium route with public data under the same source ID.

### Seeking Alpha

Treat Seeking Alpha as a provider/aggregator, not a primary issuer source. Its public methodology states that quotes come from Quodd/Cboe/Nasdaq feeds and that fundamentals, estimates, and Wall Street ratings come from S&P Global Market Intelligence. Its standardized financial statements may differ from issuer-reported statements.

Use account-only fields through an account route, including Seeking Alpha Chat, and retain the returned evidence artifact. Record `provider=Seeking Alpha`, `upstream_provider` when disclosed, `access_mode=account_route`, and the page field/date. Use public Seeking Alpha help pages only for methodology or provenance.

When the account route is available in the in-app browser, attempt it before
classifying Seeking Alpha Chat as unavailable. A `403` from direct HTTP,
programmatic retrieval, or a crawler is a failed retrieval leg, not evidence
that the browser account route or Chat failed. Record the direct-fetch status
separately (for example, `direct_http_403`) and do not bypass the restriction.

The delivery surface does not change the claim type. For example, a user-supplied screenshot of Wall Street revenue estimates is still `estimate_consensus`, not a user assumption; a screenshot of a Quant Rating is still `provider_proprietary_score`, not analyst consensus.

| Seeking Alpha area | Useful evidence | Evidence nature | Required treatment |
|---|---|---|---|
| Summary / market data | Price, volume, market cap, 52-week range, short interest, beta | `fact_provider_standardized` | Timestamp and timezone; prefer exchange data for decisive market inputs |
| Ratings | SA author, Wall Street, and Quant ratings | `analyst_interpretation`, `estimate_consensus`, `provider_proprietary_score` | Keep all three separate; retain lookback and analyst count |
| Financials | Standardized income statement, balance sheet, cash flow | `fact_provider_standardized` | Reconcile material values to filing/XBRL; preserve reclassification differences |
| Earnings | Actual/estimate surprise, annual and quarterly estimates, revisions, analyst counts | actuals as standardized facts; estimates as `estimate_consensus` | Retain GAAP/normalized basis, period, low/high, and provider as-of |
| Valuation / Growth / Profitability | Multiples, forward growth, margins, returns, sector medians | `derived_provider_metric` | Retain formulas/definitions where available; recompute decisive multiples from cited inputs |
| Momentum / Options | Returns, technicals, IV, volume, open interest, implied move | `market_positioning_context` | Treat as high-frequency context with strict cutoff; never as fundamental proof |
| Peers | Provider peer set and relative metrics | `provider_comparison` | Validate the peer universe and business-model comparability before downstream use |
| Articles / transcripts / filings index | Research interpretation and document leads | `analyst_interpretation` or discovery | Do not reproduce article bodies; follow filing/IR links to the primary document |

Seeking Alpha can materially strengthen consensus coherence, estimate revisions, valuation cross-checks, and positioning context. It cannot close undisclosed transaction financing, final dilution, purchase accounting, synergy, capex, tax, or technical-execution gaps. Keep those as decision blockers until the issuer or regulator publishes them.

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

## Minimum Handoff By Workflow

| Owning workflow | Minimum useful evidence pack |
|---|---|
| `company-tearsheet` / `initiating-coverage` | Verified issuer identity, fiscal calendar, business/KPI baseline, financial history, current market snapshot, material gaps |
| `financials-normalizer` / `three-statement-model-builder` | Source statements, periods, units, currency, accounting definitions, KPIs, reconciliation issues |
| `dcf-model-builder` | Historical cash-flow inputs, forecast drivers, net debt, diluted shares, current price, WACC/terminal support, explicit blockers |
| `comps-valuation` | Verified peers, metric definitions, fiscal periods, current EV/equity inputs, estimates, outlier and conflict notes |
| `earnings-preview` | Event date, expectation baseline, guidance, KPI watch items, scenarios, and source cut-off |
| `earnings-deep-dive` / `equity-model-update` | Release, filing, transcript, reported-vs-expected bridge, guidance changes, price reaction, source-to-model inputs |
| `scenario-sensitivity-generator` / `event-driven-analyzer` / `economic-impact-report` | Base case, key drivers, dated event or policy inputs, probability/payoff anchors, current price, missing evidence |
| `thesis-tracker` / `catalyst-calendar` / `meeting-prep` | Thesis proof points and falsifiers, dated events, monitoring triggers, recent developments, open questions |
| `long-short-pitch` / `memo-builder` | Source-backed thesis evidence, variant perception, catalysts, valuation support, disconfirmers, unresolved gaps |
| `portfolio-risk-management` | Explicitly authorized position context, price/liquidity, ADV, borrow/options when relevant, benchmark and risk constraints |
| `model-audit-tieout` / `deck-report-qc` | Source IDs, source-to-output mapping, calculation/assumption gaps, stale or conflicting evidence |

## Conflict And Inference

- Preserve conflicting values with their dates and definitions; do not average them away.
- Prefer mechanical `derived calculation` from cited inputs over an opaque estimate.
- Mark judgment-based proxies as inferred assumptions and show what direct source would replace them.
- Never infer proprietary consensus, broker-only implementation data, private portfolio context, or restricted article bodies from public metadata.
