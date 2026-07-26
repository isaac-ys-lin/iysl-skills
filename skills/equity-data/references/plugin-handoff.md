# Plugin handoff

When `equity-data` is embedded inside a Public Equity Investing workflow, keep
these fields in the internal handoff:

- `owning_workflow`: the workflow that consumes the evidence.
- `decision_impact`: which decision or output the evidence supports.
- `readiness_effect`: the owner's readiness effect, without inventing a new
  global readiness enum.
- `artifact_role=embedded_support_artifact`.
- `hidden_unless_requested=true` for source ledgers and operator plumbing.

The plugin router remains authoritative for category-to-provider mapping and
provider-specific routes. A support artifact may carry a new source ID,
permission, availability, route status, provider vintage, retrieval timestamp,
and unresolved gap when a route changes. Do not copy private content into a
reader-facing artifact or use successful availability as proof of permission.

For a standalone collection request, use
`owning_workflow=standalone_support_request` and
`artifact_role=standalone_support_artifact`; expose only the data the user
requested.
