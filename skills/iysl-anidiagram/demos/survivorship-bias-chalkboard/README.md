# Demo — Survivorship Bias, chalkboard house

The **same content** as [`../survivorship-bias/`](../survivorship-bias/) — Abraham
Wald's WWII bombers — rendered in a second, visibly different visual house. It is
kept as a style-diversity example: identical claim, fact list, relation, and
forward-reveal motion, but a different look and a different page wireframe.

- `../survivorship-bias/` — **wartime archival schematic** (the pipeline winner):
  mid-kraft ground, military stencil, red = holes / olive-green = armor, centered
  hero inside a ruled technical plate.
- this one — **statistician's chalkboard**: dark slate ground, chalk-white
  hand-drawn line-art, an off-center hero pulled right, and a left-hand column
  that walks Wald's derivation (①②③) like chalk notes.

## Why both are here

The two came out of the same Creative fan-out as divergent candidates. Both passed
every review gate; the archival version won on **3-second reading speed**. This
house makes the corrective *motion* more explicit — a sweep arrow physically moves
the armor from the holes to the clean nose.

## The one fix applied before landing

The review flagged a real defect in the original candidate: the bullet holes
(damage) and the corrective armor plates (solution) were both coral-red, so the
core "wrong place vs right place" contrast softened on a fast glance. Fixed here by
recoloring the **solution** — armor plates, sweep arrow, and the corrected
conclusion — to **chalk-cyan**, leaving the **damage** (bullet holes, the fatal-hit
notes, the missing-sample ghosts) red. Damage = red, reinforcement = cyan.

## Files

- `diagram.svg` — loops in any browser, text stays editable.
- `survivorship-bias-chalkboard.mp4` — H.264 (rendered at 10 fps; the heavy chalk
  filters make a higher frame rate needlessly expensive for this slow reveal).
- `survivorship-bias-chalkboard.png` — the poster frame (`data-poster-t`).

All three pass `scripts/render_svg.py --check` (exit 0).
