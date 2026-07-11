# Animated SVG Authoring Contract

Use this reference when hand-writing a SMIL animated SVG for `scripts/render_svg.py`.
The renderer validates structure first (exit `2` with a `messages` list on violation),
then renders deterministically in a browser and runs quality checks (exit `1` on failure).

## Root Element Requirements

- `viewBox` is mandatory, with positive width and height. Also declare explicit
  `width`/`height` attributes matching the viewBox size.
- `data-loop-seconds` is mandatory: a float between 2 and 15. Aim for 6-10 seconds;
  shorter loops feel frantic, longer loops lose the reader before the loop point.
- `data-poster-t` is optional (float, default 0): the timestamp used for the static
  poster PNG. Pick the moment where the diagram is most complete and informative —
  usually late in the loop, after every staged reveal has landed and before any
  end-of-loop fade-out.

Example root:

```xml
<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 1200 675" width="1200" height="675"
     data-loop-seconds="8" data-poster-t="6.5"
     font-family="'PingFang TC', 'Noto Sans TC', 'Helvetica Neue', Arial, sans-serif">
```

## Self-Contained, No Script, No External Resources

- No `<script>` elements. Animation is SMIL only: `animate`, `animateMotion`,
  `animateTransform`, `set`. CSS `@keyframes`, `animation:`, and `transition:`
  (in `<style>` or `style` attributes) are rejected.
- No external references of any kind: no external `href`, no `@import`, no webfonts.
  `<image>` content must be a data URI. `href` values must be fragments (`#id`) or
  data URIs.
- Fonts come from the system stack. Always use:
  `"PingFang TC", "Noto Sans TC", "Helvetica Neue", Arial, sans-serif`
  (or a stack that includes at least one of the CJK families). Validation rejects
  documents whose font stacks never mention `PingFang TC` or `Noto Sans TC`.

## Text Rules

- All text stays as `<text>` (with `<tspan>` where needed). Never convert text to
  paths: text must remain editable and machine-checkable.
- Font-size hierarchy at viewBox width 1200 (scale proportionally for other widths):
  - Page title: 30-36
  - Section titles: 20-24
  - Labels: 15-17
  - Annotations / footnotes: 12-13
- The hierarchy must support three reading depths: the main claim lands in 3 seconds
  (title), the structure lands in 10 seconds (section titles and layout), and details
  reward a close read (labels and annotations).
- Quality gates enforced by the renderer:
  - `readability_text_collision`: at t=0 and t=loop/2, no two visible text bounding
    boxes may overlap beyond `--collision-tolerance` px (default 2) on both axes.
  - `readability_canvas_margin`: every visible text bounding box stays at least
    `--margin` px (default 8) away from the SVG edges.

## SMIL Patterns

- **Staged reveal**: offset `begin` times (or `keyTimes` on an opacity `animate`) so
  elements appear in reading order. Give every reveal step at least 1.2 seconds
  before the next one starts.
- **Flow along an edge**: `animateMotion` with a child `<mpath href="#edge"/>`
  referencing the visible path, so motion literally travels the drawn connection.
- **Pacing**: use `keyTimes` + `calcMode` (`linear`, `spline`, `discrete`) to hold,
  ease, and release. Hold states long enough to read the labels they reveal.
- **Seamless looping is mandatory**: every animated value must return to its start
  value at the end of the cycle, every animation uses `repeatCount="indefinite"`,
  and every `dur` (or the least common multiple of all durs) equals
  `data-loop-seconds`. A loop that visibly snaps or drifts is a defect.

## Budget and Focus

- Keep the SVG source under 200KB.
- One animation story at a time: the timeline should explain exactly one thing at any
  moment. Parallel unrelated motion is noise, not richness.
- The renderer's `motion_nonzero` check fails a file whose sampled frames are all
  (near-)identical — a static SVG is not an animated diagram.

## Quality Knobs Are Not Escape Hatches

`--collision-tolerance` and `--margin` may be relaxed only with a stated reason
(for example, intentionally kerned overlapping display type). Never raise them to
silence a real collision — fix the layout instead.
