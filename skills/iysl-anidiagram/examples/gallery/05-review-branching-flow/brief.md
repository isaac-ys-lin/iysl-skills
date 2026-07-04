# Review Workflow Brief

A team uses a lightweight review process for changes that may pass immediately, require revision, or be escalated for deeper checks before merge. The source needs a diagram that shows branch points, retry loops, and the final merge path.

Core path:

- Draft change is prepared for review.
- Reviewer checks clarity, correctness, and risk.
- Low-risk changes can pass directly.
- Issues can send the work back for revision and resubmission.
- High-risk or unclear changes escalate to deeper review before approval.
- Approved work is merged and announced.

This is not a simple sequence, because the path can branch, loop, and rejoin.
