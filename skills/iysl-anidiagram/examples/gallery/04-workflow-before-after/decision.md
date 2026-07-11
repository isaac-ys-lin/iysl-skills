# Decision

## Composition

Two side-by-side panels — "BEFORE / Ad hoc manual" (warm palette, dashed card borders) and "AFTER / Verified agent-assisted" (blue palette, solid borders, check markers) — joined by a center spine of four shared checkpoint labels: Intake, Execution, Verification, Handoff. Each row pairs the same checkpoint under the two modes, so the reader compares row by row instead of re-reading two unrelated lists. Per-panel summary lines ("Outcome depends on who remembers" / "Outcome is verifiable by anyone") compress each mode into one sentence.

Three reading depths: the title carries the claim; the two panel headers plus the four center labels carry the structure; card sub-lines, markers, and the footnote carry the details. The visual styling itself argues: dashed/improvised on the left, solid/checked on the right — restrained, per the brief's instruction to highlight the mode shift rather than sub-steps.

## Rejected Alternatives

- A layer stack of the new workflow's components: shows what the new mode contains but hides the transformation the brief is about.
- A timeline: would imply a rollout schedule; the source contrasts two stable operating modes, not dates.
- A branching flow of the workflow internals: overemphasizes mechanics and violates the brief's explicit constraint (F9) to skip sub-steps.

## Animation Semantics

Relation is contrast / before-after. Per the Contrast row of `references/animation-semantics.md`, the required motion is "alternating emphasis between the two sides." Implementation: the Before content holds full opacity for the first half of the 8s loop while After sits at 0.45, then emphasis crosses over for the second half; the active panel also gets a colored border and header underline. All animated values return to their start, so the alternation loops seamlessly.

Avoided anti-pattern (same table row): a single flowing dot on one side would read as process, not contrast — nothing travels in this diagram, because nothing is a step.

## Coverage

| Fact | Tag | Where it lands |
| --- | --- | --- |
| F1 requests arrive with inconsistent context | must-keep | Before row 1 title + sub-line |
| F2 manual collection, retyping, improvised tools | must-keep | Before row 2 title + sub-line |
| F3 optional verification; memory and luck | must-keep | Before row 3 title + sub-line + panel summary |
| F4 decisions and follow-ups get lost | must-keep | Before row 4 title + sub-line |
| F5 reusable intake pattern up front | must-keep | After row 1 title + sub-line |
| F6 explicit, tool-backed, verified steps | must-keep | After row 2 title + sub-line |
| F7 high-risk side effects reviewed pre-execution | must-keep | After row 3 title + sub-line |
| F8 outputs include evidence, files, known limits | must-keep | After row 4 title + sub-line + panel summary |
| F9 highlight the mode shift, not sub-steps | droppable | Not drawn as content — encoded as the design constraint (4 paired rows, no workflow internals) and echoed in the footnote |

## Validation

```bash
python3 skills/iysl-anidiagram/scripts/render_svg.py \
  --svg skills/iysl-anidiagram/examples/gallery/04-workflow-before-after/diagram.svg \
  --outdir /tmp/anidiagram-04 --basename diagram --check
```

Exit 0. Poster (`data-poster-t="3.8"`, mid-crossfade) shows both panels at near-equal emphasis so the static PNG reads as a fair two-sided comparison.
