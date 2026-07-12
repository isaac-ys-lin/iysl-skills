# Demo — Survivorship Bias (Abraham Wald's bombers)

A second end-to-end dogfood of the skill, chosen to exercise a **different
relation** from the `bitter-lesson` demo. That one was a `loop`; this one is a
**contrast with a hidden-population reveal**, so the motion is a forward reveal
that advances to the corrected conclusion — deliberately *not* a closed ring.

## Claim (lands in 3 seconds)

> 返航飛機上的彈孔，標示的是「中彈還能飛回來」的位置 —— 該補強的是**沒有彈孔**的地方，不是彈孔最多的地方。

## Relation → motion

Contrast (naive reading vs corrected reading). The animation enacts the bias
itself: a squadron flies out, the planes hit in the engines fall away (the
invisible sample), bullet holes accumulate on the survivor's wings/fuselage/tail,
the naive instinct highlights those holes, then the armor migrates onto the
*empty* engine/cockpit zones as the fallen planes return labelled as the missing
data. Motion carries the causality; the static poster already holds the whole
argument (red holes **and** green armor in one frame).

## How it was produced

The full three-role pipeline, dogfooded:

1. **Direction** (aligned with the user): claim, `F1..F9` fact list with
   must-keep/droppable tags, composition, the forward-reveal animation story, and
   two divergent style directions.
2. **Creative** — two parallel candidates in visibly different houses:
   - **A · wartime archival schematic** (this deliverable): mid-kraft ground,
     military stencil display, red = bullet holes, olive-green = armor, centered
     hero bomber inside a ruled technical plate.
   - **B · statistician's chalkboard**: dark slate, chalk-white hand-drawn
     line-art, off-center hero with a left-hand derivation column.
3. **Review** — one adversarial pass over both, checking coverage, animation
   semantics, three reading depths, visual quality, and diversity by inspecting
   the posters and six MP4 frames each.

Both candidates passed every gate. **A won on 3-second reading speed:** its
two-colour scheme (damage vs armor) makes "reinforce where there are no holes"
legible at a glance, and its poster is the one that shows the full contrast
statically. B's chalkboard rendered both the problem (holes) and the solution
(armor) in the same coral, which softens the core contrast on a fast glance —
excellent on a 10-second read, but the claim here must land in three.

## Files

- `diagram.svg` — the deliverable; loops in any browser, text stays editable.
- `survivorship-bias.mp4` — H.264, for embedding where SVG is not accepted.
- `survivorship-bias.png` — the poster frame (`data-poster-t`), complete on its own.

All three pass `scripts/render_svg.py --check` (exit 0).
