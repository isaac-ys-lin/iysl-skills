# Artifact Design Profile

## Direction

The artifact should feel like a compact explanatory diagram, not a generic slide template. The content chooses the structure: loop, timeline, funnel, matrix, stack, before/after, flow, composite page, or architecture map.

## Visual System

- Light primitives use a quiet blue editorial system for clarity and broad reuse.
- `flow` renders branching in the same light system: cards and pills on lanes, a diamond for decisions, dashed gutter edges for retry loops.
- `composite` stacks sections as cards on one page; each section keeps its own title and one claim, and the page animation activates sections sequentially.
- The legacy `architecture` primitive keeps its dark technical sketch style only when a system map needs that density.
- The original Lanshu repo contributes reusable atoms: dark technical tone, glow/pulse motion, grain, vignette, and signature-like brand slots.
- These atoms should tune presentation after the layout is chosen; they should not choose the layout.
- Animation should guide attention through sequence, causality, active state, or feedback.
- Examples guide taste and density; they are not templates to copy blindly.
- Static PNG must read clearly before animation adds emphasis.

## Review Checklist

- The first read makes the central claim obvious.
- Layout choice matches the underlying idea.
- Labels are short enough to scan.
- Static PNG is understandable without animation.
- GIF shows real motion and does not distract from the message.
- Motion marker matches semantics: arrows for handoff/progression, dots for focus/orbit/activity.
- Excalidraw source remains editable text and shapes.

## Next Design Directions

- Add a `comparison_grid` primitive only if matrix and before/after are not enough.
- Add per-layout visual polish after real examples reveal repeated shortcomings.
