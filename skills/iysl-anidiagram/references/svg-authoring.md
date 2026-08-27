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

- No `<script>`, `<style>`, or `style=` attributes. Use SVG presentation attributes
  (`fill`, `stroke`, `font-*`, and so on) and SMIL only: `animate`, `animateMotion`,
  `animateTransform`, `set`. Removing CSS surfaces keeps the browser input contract
  auditable and prevents escaped or newly introduced CSS fetch syntax.
- No external references of any kind: no external `href`, no `@import`, no webfonts.
  `<image>` content must be a data URI. `href` values must be fragments (`#id`) or
  data URIs. `src` attributes, HTML/foreign active elements, event attributes, and
  SMIL mutations of `href`, `src`, `style`, or event attributes are rejected before
  the source is inserted into the browser harness.
- Fonts come from the system stack. Type feel (geometric sans, humanist sans, serif
  editorial, mono, display) is a **style choice** — see `references/style-directions.md`;
  do not treat one stack as the house font. The only hard rule is a CJK fallback: every
  font-family stack must include at least one of `"PingFang TC"` / `"Noto Sans TC"` so
  Chinese text never renders as tofu. Validation rejects documents whose stacks never
  mention either family. A serif-led example stack:
  `"Songti TC", "Noto Serif TC", "PingFang TC", Georgia, serif`; a neutral default:
  `"PingFang TC", "Noto Sans TC", "Helvetica Neue", Arial, sans-serif`.

## Text Rules

- All text stays as `<text>` (with `<tspan>` where needed). Never convert text to
  paths: text must remain editable and machine-checkable.
- Font size at viewBox width 1200 (scale proportionally for other widths). These are
  starting points for a reading depth, not a validated range: the renderer never
  inspects `font-size`, and the shipped examples legitimately use in-between values
  such as 14 and 26. Treat a size as belonging to the depth it reads as.
  - Page title: around 30-36
  - Lead claim or section title: around 20-26
  - Labels: around 14-17
  - Annotations / footnotes: around 12-13
- The hierarchy must support three reading depths: the main claim lands in 3 seconds
  (title), the structure lands in 10 seconds (section titles and layout), and details
  reward a close read (labels and annotations).
- Size alone does not build hierarchy. Separate each tier from its neighbour with at
  least two signals drawn from size, weight, ink value, italic, and letter-spacing.
  Every shipped example already does this: two weights (600 and 700) plus three to
  eight distinct text inks, and `print` adds italic and letter-spacing on top.
- Quality gates enforced by the renderer:
  - `readability_text_collision`: at t=0 and t=loop/2, no two visible text bounding
    boxes may overlap beyond `--collision-tolerance` px (default 2) on both axes.
  - `readability_canvas_margin`: every visible text bounding box stays at least
    `--margin` px (default 8) away from the SVG edges.
  - `loop_position_seam`: a visible animated target may not jump substantially
    farther across the video boundary than it moves between adjacent end frames.
    Hidden reset motion is allowed.
  - `external_resource_runtime`: the browser request guard observes no subresource
    request. Any network or extra local-file fetch is aborted and fails the render.

## Surface and Color Discipline

The renderer checks text collisions and margins, never color. These rules describe what
the shipped examples already do; they are what keeps a diagram from going to mush.

- **Every nested surface must separate from the surface it sits on**, by a lightness
  step of `dL* >= 4` or by a visible stroke or shadow. `scripts/validate_visual_contract.py`
  checks this one mechanically; `render_svg.py` does not. Compare against the parent
  surface, not the page ground: a pale pill on a white card is judged against the card.
  Both routes are in use, often inside one diagram. `blueprint` builds four dark
  surfaces out of lightness steps because a dark ground cannot host white cards; the
  `07` pair strokes its stage cards, then separates the pills inside them by a lightness
  step. A surface with neither route reads as absent, and that is what this rule caught
  on its first pass: `editorial`'s footer panel sat 2.13 L* from the ground and the `07`
  owner pills sat 2.79 L* from their card, all of them unstroked.

- **The accent hue names exactly one idea.** Pick the thing the reader must not miss,
  the failure state, the payoff, the recurrence, and spend the accent only there. Every
  shipped example spends its accent sparingly on one idea, and `07/dot` deliberately
  uses none. An accent scattered across unrelated elements stops meaning anything and
  becomes decoration. A tonal pair of one hue still counts as one accent.

Count roles, not hex values. A tint earns its place by filling a named role: ground,
surface, ink, muted ink, structure, primary, accent. `blueprint` earns 19 distinct
colors because a dark ground needs more surface steps to stay legible; `print` needs
only 10. Neither number is a target.

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
