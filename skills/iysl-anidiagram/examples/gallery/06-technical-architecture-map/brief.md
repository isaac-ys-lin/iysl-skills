# Technical Architecture Brief

A platform team needs a one-page technical system map for a packaged workflow service. Multiple source systems feed a shared processing core, which applies policy and decision gates before generating packaged outputs for downstream consumers.

Required elements:

- Inputs from documents, events, APIs, and operator-provided files.
- A core processing area that normalizes, enriches, and coordinates work.
- A decision gate that determines whether outputs are approved, blocked, or need another pass.
- Packaged outputs such as reports, structured artifacts, notifications, or bundles.
- Enough density to show system shape without pretending the system is a single straight line.

The audience is technical but time-constrained, so the map should be dense, grouped, and readable.
