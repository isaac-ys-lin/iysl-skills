# Equity Council Persona Rewrite

Status: complete
Last updated: 2026-08-20

## Outcome

- Replaced the sealed, no-browsing analytical lenses with an always-on,
  three-persona Council that can independently explore external evidence.
- Kept one accountable Chair and the canonical Long, Short, or Avoid judgment
  for the requested horizon; participation and implementation remain separate.
- Preserved Public Equity Investing and `equity-data` ownership of formal
  intake, provider coverage, models, valuation, and hero artifacts.

## Final contract

- The three seats are a Damodaran-inspired Fundamental Underwriter, a
  Soros-inspired Reflexive Trader, and a Mauboussin-inspired Expectations
  Strategist. Public methods shape their questions and blind spots but never
  increase evidence weight or imply private-process access.
- All seats may browse broadly within their mandates. Adopted claims require
  provenance, truth relevance, price relevance, mechanism, horizon, financial
  consequence, and a falsifier; correlated origins are not independent proof.
- A current accepted Study Flow `ambient_market_context` may be reused for a
  covered name. New, unmatched, or stale names require fresh discovery.
  Seeking Alpha gaps fall back to public web evidence and are disclosed.
- First-round memos stay isolated. The Chair may run one bounded
  cross-examination for at most two material disputes, then records each
  decisive proposition as accepted, conditional, or rejected without voting
  or averaging.
- At most two model- or sign-changing facts may enter the single targeted PEI
  refill. Other unverified leads remain outside established inputs; no second
  refill is allowed.
- If true agent isolation is unavailable, the fallback is disclosed as
  single-model persona emulation and robustness is Fragile.

## Verification

- `tools/verify-skill.sh iysl-equity-council`: 16 passed.
- Council semantic trigger corpus: 25/25, precision 1.0 and recall 1.0.
- Repository behavior contract, skill audit, live-install visibility, release
  gate, and `git diff --check`: passed.
- Fresh independent review recomputed all six quantitative distributions,
  walked all nine anonymous cases, and returned `ship` after two bounded
  contract issues were corrected.
- The all-skill trigger wrapper stops before Council in unrelated dirty
  `equity-data` work; the Council-specific trigger gate is green.
- The skill-creator quick validator could not run because the available Python
  environments lack PyYAML; the repository's own skill validator is green.

## Remaining limits

- Deterministic tests do not prove live three-agent isolation, browsing quality
  or source availability, or the Chair's probability calibration. These need
  observation in real investment trials.
