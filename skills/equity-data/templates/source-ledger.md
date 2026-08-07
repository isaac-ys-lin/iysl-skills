# Source Ledger

Use only the columns material to the owning workflow. One source may support many items.

| Source ID | Provider / Document | Source Kind | Plugin Category | Access Mode | Permission | Route Status | Document / Period | Provider As-Of | Retrieved / TZ | URL / File Ref / Section | Freshness | Confidence | Fallback / Used For / Limits |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| S1 | [source] | [filing / issuer_ir / provider_export / account_result / user_excerpt / public_web / news / internal] | [company_filings_ir / earnings_transcripts_presentations / market_data_estimates / portfolio_models_trackers / internal_research] | [public_web / callable_connector / account_route / user_provided_account_data / local_file] | [public / user-authorized / user-provided / unclear] | [verified / unavailable / blocked / stale / not_checked] | [date or period] | [timestamp/date/unknown] | [timestamp + timezone] | [direct location + section/page/field] | [current / historical-only / stale / unknown] | [high / medium / low] | [fallback source/reason, use, conflict, caveat] |

Do not expose unrelated local paths. Permission must precede a private-source read; a successful scoped read verifies availability, not authorization. Give every fallback a new source ID. For material filings and provider exports, include the section, page, table, or field when available.
