# Animation Semantics Contract

Motion in an animated diagram must encode the content relation. Animation is part of
the argument, not decoration: a mismatched motion pattern is a review failure, exactly
like a wrong label. Before animating anything, name the relation the diagram claims,
then pick the matching motion pattern below.

## Relation-to-Motion Table

| Relation | Required motion | Anti-patterns |
| --- | --- | --- |
| **Sequence / process** | Staged reveal in step order, or an arrow/particle advancing along the main line. Direction stays consistent from first to last step. | Steps appearing out of order; motion running against the reading direction. |
| **Loop / cycle** | Continuous circulation with no visible start/end seam: an element travels a closed path, or nodes are emphasized in ring order, wrapping around forever. | A linear sweep; any one-directional motion that visibly "finishes" — a cycle never finishes. |
| **Branching / decision** | Branch paths light up in turn; the decision node gets the emphasis pulse. Retry/fallback edges animate as a backflow toward the earlier node. | Animating all branches simultaneously (hides the either/or); ignoring the decision point. |
| **Contrast / before-after** | Alternating emphasis between the two sides, or a transition wipe/slide from one state to the other. | A single flowing dot on one side only — that reads as process, not contrast. |
| **Narrowing / funnel** | Stage-by-stage convergence that visualizes volume shrinking: each stage reveals smaller/denser than the last, or particles drop out at each gate. | Uniform reveal that hides the attrition; motion that grows instead of narrows. |
| **Ranking** | Bars/values growing to their magnitude, or items called out one by one in rank order. Ranking encodes magnitude and order, not causation. | Flow arrows between ranks — ranking is not a process; do not imply steps. |
| **Layers / stack** | Layer-by-layer reveal from bottom to top (or along the dependency direction), each layer settling before the next appears. | Random-order reveal; animating layers as if data flows through them when the claim is composition. |
| **System map** | Data-flow particles traveling along edges, with a clear source -> processing -> output direction. Edge motion direction must match the real data direction. | Particles moving both ways on a one-way edge; edges pulsing with no direction. |
| **Focus / emphasis** | A single pulse (scale/glow/opacity) on one element, meaning "this is the current point". | Pulsing multiple elements at once; using pulse as generic decoration. |

## Universal Anti-Patterns

These fail review regardless of relation:

- **Decorative motion**: any animation that explains nothing. If removing the motion
  loses no meaning, remove the motion.
- **Multiple simultaneous animation stories**: at any moment the viewer should be
  able to say what the animation is currently explaining. Two unrelated motions at
  once means neither is read.
- **Pacing faster than reading**: every reveal segment must hold for at least 1.2
  seconds so its label can actually be read. If the loop cannot fit all steps at a
  readable pace, cut steps or lengthen `data-loop-seconds` — never speed past the
  labels.

## Motion Craft: Easing

SMIL animations default to **constant-velocity interpolation** (`calcMode="linear"`),
which reads mechanical. Ease every value-based reveal unless it is continuous. Easing
is set **per `<animate>` / `<animateTransform>`, not per document** — a diagram can loop
forever (the Loop relation above) while each internal reveal inside it is eased. "Use
constant velocity for loops" is about one animation's rate; it does not contradict the
loop-relation guidance about one-directional sweeps.

| Motion | Easing | Spline |
| --- | --- | --- |
| Entering / exiting (fade in, reveal, pop) | ease-out | `keySplines="0.23 1 0.32 1"` |
| Moving / morphing something already on screen | ease-in-out | `keySplines="0.77 0 0.175 1"` |
| Continuous loop (orbit dot, marquee, ambient pulse) | constant velocity | `calcMode="linear"` (default) |

- **Never ease-in** (slow start) on a reveal: it delays the exact moment the viewer is
  watching for. Default to **ease-out** when unsure.

SMIL syntax — get these exact. Invalid spline metadata may disable the animation;
do not assume the browser will safely fall back to linear:

- `keySplines` requires `calcMode="spline"`.
- `values` with **N** stops has **N−1** intervals: `keySplines` needs **N−1**
  control-point sets separated by `;`, and `keyTimes` needs **N** entries.
- **All four control-point numbers must be in `[0,1]`.** A value outside that range is
  invalid and gets dropped.
- Constant hold intervals (`0;0`, `1;1`) may use any valid spline; `0 0 1 1` is fine.

Example — fade in, hold, fade out (`values="0;0;1;1;0"`, 5 stops → 4 splines), rises and
falls eased-out, holds linear:

```
calcMode="spline"
keySplines="0 0 1 1 ; 0.23 1 0.32 1 ; 0 0 1 1 ; 0.23 1 0.32 1"
```

## Motion Craft: Staging & Physicality

- **Overshoot / pop is done with keyframes, never a bezier.** An overshoot curve needs
  `y>1`, which is out of range in SMIL. To pop an element in, add a keyframe —
  `values="0.94;1.02;1"` on scale — never a "bouncy" `keySplines`.
- **Never scale from 0.** Real objects do not materialize from nothing; start reveals at
  `scale(0.94–0.97)` + `opacity:0`.
- **Origin-aware scaling.** An element scales out of its own anchor — a callout grows
  from the node it annotates, not from the canvas center.
- **Stagger group entrances** 60–150ms apart (offset each element's `begin` or
  keyTimes) so a set reads as a cascade, not a flash. Slower than app UI's 30–80ms
  because these reveals are read, not glanced.
- **Hold ≥ 1.2s** per reveal (see Universal Anti-Patterns). This is the explanatory
  carve-out: the sub-300ms ceilings that govern app UI do **not** apply here — internal
  transitions still ease, but the overall pace is deliberately slower.

## Motion Vocabulary

Name motion with precise terms so Direction, Creative, and Review mean the same thing:

- **Reveal** — content uncovered gradually via clip-path/mask or a growing shape.
- **Line-draw** — a path draws itself in by animating `stroke-dashoffset`.
- **Stagger** — items animate one after another with a small delay: a cascade.
- **Orchestration** — timing multiple animations so they feel like one coordinated motion.
- **Crossfade** — one element fades out as another fades in, in the same spot.
- **Continuity transition** — a change that keeps the viewer oriented by connecting before and after.
- **Morph** — one shape smoothly becomes another.
- **Pulse** — a gentle repeating scale/opacity change meaning "this is the current point".
- **Orbit** — an element circling a center on a continuous path (the canonical loop motion).
- **Float** — a gentle continuous drift that keeps a static element alive.
- **Follow-through** — parts keep moving and settle slightly after the main motion stops, adding weight.

## Review Question

For each animated element, answer: *which relation does this motion encode, and would
a viewer infer that relation from the motion alone?* If the answer names no relation
from the table, or names a different one than the diagram claims, the animation is
wrong even if it looks polished.

---

The easing curves, staging thresholds, and vocabulary in the Motion Craft sections are
distilled from Emil Kowalski's animation standards (github.com/emilkowalski/skills) and
adapted from web-UI motion to SMIL explanatory diagrams — app-only concerns (runtime
performance, `prefers-reduced-motion` gating, gestures, interruptible springs) are
deliberately dropped from the SVG runtime. A delivery surface that supports reduced-motion
users must explicitly select or offer the static poster; merely generating a PNG does not
make the looping SVG honor `prefers-reduced-motion` by itself.
