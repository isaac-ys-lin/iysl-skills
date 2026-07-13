# Demo — The Bitter Lesson

An end-to-end demo of the `iysl-anidiagram` pipeline, built from Rich Sutton's
essay [*The Bitter Lesson*](http://www.incompleteideas.net/IncIdeas/BitterLesson.html) (2019).

- **`diagram.svg`** — the primary artifact. Open it in any browser; it loops
  forever and its text is directly editable.
- **`bitter-lesson.mp4`** — H.264 render for embedding where SVG is not accepted.
- **`bitter-lesson.png`** — the poster frame, which reads as a complete diagram
  on its own.

## What it shows

- **Claim**: general methods that scale with computation win in the long run;
  researchers keep re-learning this the hard way.
- **Relation**: `loop`. The essay's own four-step pattern — build in human
  knowledge → short-term win → long-run plateau → compute (search + learning)
  breaks through — recurs across chess, Go, speech, and vision. A circulating
  pulse travels the closed ring with no start or end, encoding "this keeps
  happening" (see `references/animation-semantics.md`).
- **Three reading depths**: the title carries the claim, the four ring nodes
  carry the cycle, and the evidence chips plus closing takeaways reward a close
  read.

## Reproduce

```bash
python3 ../../scripts/render_svg.py \
  --svg diagram.svg \
  --outdir /tmp/bitter-lesson-out \
  --basename bitter-lesson \
  --check
```
