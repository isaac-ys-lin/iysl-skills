# Artifact Design Profile

## Direction

The artifact should feel like a compact explanatory diagram, not a generic slide template. The content chooses the structure: loop, timeline, funnel, ranking, matrix, stack, before/after, branching flow, or system map. The diagram is a hand-authored SMIL animated SVG, so composition and motion are chosen freely to fit the source rather than assembled from fixed layout primitives.

## Visual System

- A quiet, editorial system by default: clear typographic hierarchy, generous whitespace, restrained accent color used only to mark emphasis or a semantic state.
- Three reading depths on every diagram: the claim lands in ~3 seconds (title), the structure lands in ~10 seconds (sections and layout), and a close read rewards with details (labels and annotations). Density should earn the "does not miss details" bar without becoming clutter.
- Motion encodes the content relation and nothing else: sequence advances in one direction, a loop travels a closed path with no start/end break, a contrast alternates emphasis between sides, a decision lights its branches in turn. See `references/animation-semantics.md`.
- One animation story at a time; motion that explains nothing is removed.
- Match the source language and tone; preserve Chinese labels when the source is Chinese.
- The static poster frame must read as a complete diagram before animation adds sequence, causality, or focus.

## Review Checklist

- The first read makes the central claim obvious.
- Composition matches the underlying relation.
- Every `must-keep` source fact is present; drops are deliberate and justified.
- Labels are short enough to scan; three reading depths are all present.
- The poster PNG is understandable without animation.
- Motion matches semantics per `references/animation-semantics.md`; a mismatched pattern is a defect.
- The SVG is self-contained and its text stays editable `<text>` (no external resources, no text-to-path).

## Next Design Directions

- Grow the gallery when a new case teaches a judgment the existing cases do not cover, not when it repeats a relation already shown.
- Add authoring-contract or animation-semantics guidance when real cases reveal a repeated shortcoming.
