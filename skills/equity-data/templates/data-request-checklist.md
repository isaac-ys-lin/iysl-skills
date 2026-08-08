# Decision-Relevant Data Request

Request only inputs that materially improve or unblock the owning Public Equity Investing workflow. Do not send this entire checklist by default.

## Context

- [ ] Verified ticker, exchange, legal issuer, fiscal year, and reporting currency
- [ ] Owning workflow, decision use, audience, and data cut-off
- [ ] For non-US, dual-listed, or ADR securities: home listing, regulator, accounting standard, and share/ADR relationship

## Source Categories

- [ ] `company_filings_ir`: required filings, releases, presentations, financials, KPIs, and definitions
- [ ] `earnings_transcripts_presentations`: relevant transcript, event, guidance, and management commentary
- [ ] `market_data_estimates`: timestamped price, shares/EV bridge, estimates, ownership, liquidity, borrow, or options only as needed
- [ ] `portfolio_models_trackers`: specifically authorized model, workbook, tracker, watchlist, or position context
- [ ] `internal_research`: specifically authorized notes, thesis, meeting context, or expert research

## Provider And Web Route

- [ ] Callable licensed provider checked when the owning workflow requires estimates or standardized data
- [ ] One bounded two-stage Seeking Alpha intake completed for substantive issuer/security work: Ask SA recall followed by targeted structured data, or the skip reason recorded
- [ ] Structured Seeking Alpha fields targeted only to material signals found by the scan or required by the owning workflow
- [ ] Authorized account or in-app browser route attempted before classifying Seeking Alpha as unavailable
- [ ] User-provided account export, screenshot, or excerpt used when an authorized non-public provider route is otherwise unavailable
- [ ] Provider, upstream source, fiscal basis, analyst population, statistic, lookback/horizon, as-of, retrieval time, and timezone captured for consensus/targets
- [ ] Public web search used for discovery; each material result opened and tied to a direct primary or corroborating source
- [ ] Failed direct-fetch, blocked, unauthorized, stale, or empty routes logged separately with a distinct source ID

## Decision Blockers

- [ ] Missing source or field and the conclusion/workflow it blocks
- [ ] Stale market-sensitive value and required as-of date
- [ ] Conflicting values, definitions, periods, units, or currencies
- [ ] Required user assumption or permitted public proxy
- [ ] Provider/export needed because no callable source is available

## Handoff

- [ ] Owning workflow
- [ ] Evidence cut-off
- [ ] Decision impact of remaining gaps
- [ ] Next smallest source request
- [ ] Owner-defined readiness or artifact metadata, if required
