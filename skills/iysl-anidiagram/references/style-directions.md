# Style Directions — Diverge, Don't Default

This is the aesthetic counterpart to `svg-authoring.md` (which fixes *structure*) and
`animation-semantics.md` (which fixes *motion meaning*). Neither of those says anything
about how a diagram should *look* — and that silence is why outputs drift toward one
house look. This reference exists to widen the aesthetic basin on purpose.

**The failure this prevents:** every diagram rendering as the same pale-blue editorial
card layout (`#f6f8fb` ground, `#2459c7` primary, white rounded cards). That look is
*one* option, not the default. Derive the look from the content's mood; never auto-reach
for it.

## Derive the Look From Content, Not From a Menu

Before choosing colors, read the content's **emotional temperature, domain vocabulary,
era and cultural context, and data density**. A post-mortem of a failure is not the same
mood as a product launch; a 1970s research lineage is not the same mood as a real-time
dashboard. Let that mood pick the ground, the palette, and the type. Write the initial
visual fingerprint before opening the calibration family below; the family is a range
check, not the source of the idea.

## Two Kinds of Divergence

Color variation is not composition variation. Two candidates must differ in both
categories below: **at least one visual axis and at least one spatial axis**. Placed
side by side, they should not be mistaken for the same publication or the same
wireframe.

### Visual axes

- **Value key**: light ground · dark ground · mid-tone ground
- **Color strategy**: mono + one accent · two-color clash · multi-hue system · desaturated · high-saturation
- **Type feel**: geometric sans · humanist sans · serif editorial · display · mono
- **Stroke & shape language**: hairline vector · bold blocks · organic/rounded · grid-ruled · hand-sketch
- **Density & whitespace**: dense technical · airy editorial
- **Finish**: flat · grain · soft-glow · paper texture
- **Motion feel** (within the relation's required motion per `animation-semantics.md`): crisp/mechanical · soft/drifting · energetic/pulsing

### Spatial axes

- **Focal topology**: centered hero · off-center hero · distributed field · split-stage
- **Balance**: symmetric · asymmetric · deliberately weighted to one edge
- **Containment**: cards/panels · continuous field · open annotations · nested regions
- **Reading path**: axial · radial · perimeter · zig-zag · overview-to-detail
- **Scale rhythm**: uniform peers · one dominant object with supporting details · progressive scale
- **Edge behavior**: framed with margins · full-bleed · cropped/continuing beyond the canvas

The content relation still governs semantic geometry: a loop must read as recurring
and a sequence must preserve order. Spatial divergence changes how that relation is
staged on the page, not what the relation means.

## Visual Fingerprint

Make the decision inspectable before authoring. Every candidate emits two compact
lines plus a content-derived reason:

```text
visual: dark · mono+amber · mono type · ruled hairlines · soft glow
spatial: off-center hero · asymmetric · open annotations · full-bleed
reason: the source is a technical post-mortem, so it should feel diagnostic rather than promotional
```

Within a multi-diagram run, pass the accepted fingerprint to the next Direction step
and state what may repeat and what must change. For a one-off diagram, compare the two
Creative candidates; there is no hidden cross-run memory.

## Calibration Family (a springboard, not a menu)

Eight coherent directions with concrete palettes, so range is actionable. **Do not
just pick one** — derive the fingerprint from the content first, then use the table to
notice whether the idea is still trapped in a familiar basin. If the result closely
matches a family, declare that anchor and deliberately mutate at least one visual choice
and one spatial choice, explaining both. The list exists to show how wide the range is,
and to name the default look (#1) so you can consciously avoid over-using it.

| # | Direction | Ground / Ink / Primary / Accent (hex) | Type & finish | Fits content that is… |
| --- | --- | --- | --- | --- |
| 1 | Cool editorial *(the overused default — avoid unless it truly fits)* | `#f6f8fb` / `#182032` / `#2459c7` / `#b3452e` | geometric sans, flat | neutral business, product, training |
| 2 | Dark technical blueprint | `#0f1620` / `#e6edf5` / `#4da3ff` / `#ffb454` | mono labels, grid rules, soft-glow | systems, architecture, real-time/technical |
| 3 | Warm humanist print | `#f7f1e6` / `#2b2723` / `#3f6f5e` / `#c0562f` | serif editorial, grain | human stories, values, reflective essays |
| 4 | Swiss grid modernism | `#ffffff` / `#111111` / `#111111` / `#e5322d` | tight geometric sans, ruled grid, airy | rigorous comparisons, principles, manifestos |
| 5 | Brutalist poster | `#eae7df` / `#0a0a0a` / `#0a0a0a` / `#ff5c00` | oversized display, heavy strokes | provocations, bold single claims, warnings |
| 6 | Soft data-humanism | `#fbfaf8` / `#33302b` / `#6d8a7e` / `#c98a5e` | rounded humanist sans, airy | surveys, gentle explainers, wellbeing |
| 7 | Retro scientific journal | `#f3efe4` / `#22201b` / `#2f6d6a` / `#8a3b32` | serif + mono, hairline rules, grain | lineages, history of a field, methods |
| 8 | High-contrast vivid | `#101012` / `#f2f2f4` / `#ff3b6b` / `#37e0a4` | bold sans, saturated chips | energetic launches, rankings, momentum |

Every palette here still needs real text/ground contrast. `render_svg.py` checks text
collisions and margins, not color contrast, so the Review role must inspect contrast by
eye. A direction that looks striking but fails contrast is not a valid choice.

## Composition Also Varies

Sameness is not only color. The universal atom has been "white rounded card + title +
subtitle." Break it too: full-bleed grounds, asymmetric layouts, a hero diagram with
sparse chrome, annotation-dense margins, deliberate grid-breaks, off-center focal points.
The relation fixes *what* structure encodes the content (loop, contrast, branching); it
does not fix the card style, the symmetry, or where the weight sits.

This separation mirrors useful open-source precedents without adding dependencies:

- [FT Visual Vocabulary](https://github.com/Financial-Times/chart-doctor/blob/main/visual-vocabulary/README.md) starts from the relationship the story needs to communicate.
- [D2](https://github.com/terrastruct/d2) exposes layout engine and theme as separate choices, a useful reminder that spatial organization and skin are different decisions.
- [Rough.js](https://github.com/rough-stuff/rough) shows how stroke, fill, hachure, and roughness can vary finish without changing the underlying semantic geometry.

These are judgment references, not code or template dependencies. All shipped examples
remain original and repo-owned.

## The Tension To Avoid

A fixed set of eight looks, mechanically applied, just replaces one sameness with eight.
This list is a springboard: show the range, then blend or invent, and let each diagram's
own content — not habit — set its look.
