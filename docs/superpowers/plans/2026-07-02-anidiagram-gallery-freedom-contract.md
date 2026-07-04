# iysl-anidiagram Gallery Freedom Contract Implementation Plan (Completed)

> **Status: COMPLETED** on branch `codex/anidiagram-gallery`, 2026-07-03. This document is preserved as a design record; checkboxes reflect executed steps. Do not execute this document as a plan — the current source of truth is the shipped code, tests, and skill docs.

**Goal:** Add a source-backed decision gallery and design-latitude contract so `iysl-anidiagram` examples teach diagram judgment instead of acting like rigid templates.

**Architecture:** Keep `assets/` as renderer contract samples and add `examples/gallery/` as the higher-level judgment layer. Gallery examples are original repo-owned briefs plus runnable specs; automated tests render every gallery `spec.json` so examples cannot rot. `SKILL.md` and `references/spec-format.md` explain the usage order: decide claim/relation first, use gallery for judgment, use assets for schema contracts, render with checks.

**Tech Stack:** Markdown skill docs, JSON render specs, Python `unittest`, existing Pillow renderer at `skills/iysl-anidiagram/scripts/render_animated_diagram.py`, Bash verification script.

---

## File Structure

- Modify `.gitignore`: ignore `.superpowers/` visual companion artifacts.
- Create `skills/iysl-anidiagram/examples/gallery/README.md`: gallery index, source-backed decision ladder, and case map.
- Create `skills/iysl-anidiagram/examples/gallery/01-launch-three-readings/brief.md`: one shared product launch source brief.
- Create `skills/iysl-anidiagram/examples/gallery/01-launch-three-readings/decision.md`: explain three readings of the same source.
- Create `skills/iysl-anidiagram/examples/gallery/01-launch-three-readings/timeline/spec.json`: sequence claim.
- Create `skills/iysl-anidiagram/examples/gallery/01-launch-three-readings/funnel/spec.json`: narrowing/adoption claim.
- Create `skills/iysl-anidiagram/examples/gallery/01-launch-three-readings/composite/spec.json`: multi-part one-page claim.
- Create `skills/iysl-anidiagram/examples/gallery/02-chinese-training-loop/brief.md`, `decision.md`, `spec.json`: Chinese repeated-behavior loop.
- Create `skills/iysl-anidiagram/examples/gallery/03-chinese-capability-stack/brief.md`, `decision.md`, `spec.json`: Chinese layered mental model.
- Create `skills/iysl-anidiagram/examples/gallery/04-workflow-before-after/brief.md`, `decision.md`, `spec.json`: transformation contrast.
- Create `skills/iysl-anidiagram/examples/gallery/05-review-branching-flow/brief.md`, `decision.md`, `spec.json`: branching/retry decision flow.
- Create `skills/iysl-anidiagram/examples/gallery/06-technical-architecture-map/brief.md`, `decision.md`, `spec.json`: dense system map.
- Create `skills/iysl-anidiagram/examples/gallery/07-style-motion-contrast/brief.md`, `decision.md`, `dot/spec.json`, `arrow/spec.json`: same semantic layout with different motion intent.
- Create `skills/iysl-anidiagram/examples/gallery/08-priority-matrix-anti-template/brief.md`, `decision.md`, `spec.json`: tradeoff map that rejects timeline.
- Test `skills/iysl-anidiagram/tests/test_gallery_examples.py`: discover and render every gallery spec, and verify every spec has a nearby `decision.md`.
- Modify `skills/iysl-anidiagram/SKILL.md`: add Design Latitude Contract and gallery usage order.
- Modify `skills/iysl-anidiagram/references/spec-format.md`: clarify `assets/` vs gallery and add judgment ladder.
- Modify `tools/verify-skill.sh`: render gallery specs in addition to `assets/*-spec.json`.

---

### Task 1: Ignore Visual Companion Artifacts

**Files:**
- Modify: `.gitignore`

- [x] **Step 1: Add `.superpowers/` to `.gitignore`**

Append this line near other generated/cache entries:

```gitignore
.superpowers/
```

- [x] **Step 2: Verify status ignores companion output**

Run:

```bash
git status --short --ignored .superpowers .gitignore
```

Expected: `.gitignore` appears modified, and `.superpowers/` appears only as ignored output, not as `?? .superpowers/`.

- [x] **Step 3: Commit**

```bash
git add .gitignore
git commit -m "Ignore Superpowers brainstorm artifacts"
```

---

### Task 2: Add Gallery Index And Case Briefs

**Files:**
- Create: `skills/iysl-anidiagram/examples/gallery/README.md`
- Create: all `brief.md` and `decision.md` files listed in File Structure

- [x] **Step 1: Create `examples/gallery/README.md`**

Use this exact structure and keep the external links as source citations:

```markdown
# iysl-anidiagram Decision Gallery

This gallery teaches diagram judgment. Use it before copying any JSON shape.

## How To Use

1. Read the source brief.
2. State the claim the diagram must prove.
3. Choose the relation: sequence, loop, narrowing, tradeoff, layers, contrast, branching, system map, or multi-part story.
4. Pick the layout that makes that relation easiest to understand.
5. Borrow field syntax from `assets/*-spec.json` only after the relation is chosen.
6. Render with `--verify --check` and review the PNG by eye.

## Source-Backed Heuristics

- FT Visual Vocabulary: choose the relationship most important to the story before choosing a visual form.
- NN/g chart selection: fit the visual to the goal and context, not to a favorite shape.
- NN/g context, clutter, contrast: preserve needed context, remove non-explanatory clutter, and use contrast only to clarify the takeaway.
- NN/g proximity: related items should be visually close; unrelated groups need whitespace or region separation.

Sources:
- https://github.com/Financial-Times/chart-doctor/blob/main/visual-vocabulary/README.md
- https://journalismcourses.org/wp-content/uploads/2020/07/Visual-vocabulary.pdf
- https://www.nngroup.com/articles/choosing-chart-types/
- https://www.nngroup.com/videos/better-charts-analytics-quantitative-ux-data/
- https://www.nngroup.com/articles/gestalt-proximity/

## Cases

| Case | Source Type | Claim | Relation | Layout | Why Not |
| --- | --- | --- | --- | --- | --- |
| 01 timeline | Product launch | Launch risk falls when work is sequenced through gates | sequence | `timeline` | A funnel would hide chronology |
| 01 funnel | Product launch | Launch adoption narrows at each handoff | narrowing | `funnel` | A timeline would hide drop-off |
| 01 composite | Product launch | Launch readiness needs plan, adoption, and feedback loop together | multi-part story | `composite` | A single primitive would flatten the story |
| 02 | Chinese training note | Escalation grows through a repeating communication loop | loop | `circular_loop` | A timeline would imply it happens only once |
| 03 | Chinese capability note | Agent work depends on layered capabilities | layers | `stack` | A flow would imply runtime order |
| 04 | Workflow migration | The important story is before vs after operating mode | contrast | `before_after` | A stack would hide transformation |
| 05 | Review workflow | The process branches, retries, and merges | branching | `flow` | A timeline would hide decisions |
| 06 | Technical system | Multiple sources feed a core process and output package | system map | `architecture` | A flow would underrepresent system density |
| 07 dot | Support handoff | Active focus moves across the same process | sequence/focus | `timeline` | Arrow motion would imply handoff more than attention |
| 07 arrow | Support handoff | Ownership is handed forward across the same process | sequence/handoff | `timeline` | Dot motion would understate causality |
| 08 | Prioritization | Initiatives should be compared by impact and effort | tradeoff | `matrix` | A timeline would invent fake chronology |
```

- [x] **Step 2: Create case brief and decision files**

Create each case directory with Markdown files. Each `decision.md` must include these headings exactly:

```markdown
# Decision

## Source Type

## Primary Claim

## Relation

## Layout

## Why This Fits

## Rejected Alternatives

## Style And Animation

## Validation
```

Use original, repo-owned content. Do not quote external articles. Keep Chinese cases in Traditional Chinese.

- [x] **Step 3: Verify Markdown files exist**

Run:

```bash
find skills/iysl-anidiagram/examples/gallery -name 'brief.md' -o -name 'decision.md' | sort
```

Expected: 16 Markdown files: `brief.md` and `decision.md` for 8 case directories.

- [x] **Step 4: Commit**

```bash
git add skills/iysl-anidiagram/examples/gallery
git commit -m "Add anidiagram decision gallery briefs"
```

---

### Task 3: Add Runnable Gallery Specs

**Files:**
- Create: all `spec.json` files listed in File Structure

- [x] **Step 1: Create runnable specs**

Create 11 specs total:

```text
skills/iysl-anidiagram/examples/gallery/01-launch-three-readings/timeline/spec.json
skills/iysl-anidiagram/examples/gallery/01-launch-three-readings/funnel/spec.json
skills/iysl-anidiagram/examples/gallery/01-launch-three-readings/composite/spec.json
skills/iysl-anidiagram/examples/gallery/02-chinese-training-loop/spec.json
skills/iysl-anidiagram/examples/gallery/03-chinese-capability-stack/spec.json
skills/iysl-anidiagram/examples/gallery/04-workflow-before-after/spec.json
skills/iysl-anidiagram/examples/gallery/05-review-branching-flow/spec.json
skills/iysl-anidiagram/examples/gallery/06-technical-architecture-map/spec.json
skills/iysl-anidiagram/examples/gallery/07-style-motion-contrast/dot/spec.json
skills/iysl-anidiagram/examples/gallery/07-style-motion-contrast/arrow/spec.json
skills/iysl-anidiagram/examples/gallery/08-priority-matrix-anti-template/spec.json
```

Use these renderer constraints:

- Every spec must set `layout`.
- Light examples should set `canvas.frames` to 24 or 30 and `canvas.fps` to 10 or 20 to keep checks stable.
- Chinese examples should keep labels short enough for readable PNG review.
- `flow` examples should use 8 nodes or fewer.
- `composite` must not set `canvas.height`.
- `architecture` may use the legacy `default-spec.json` field family but must use original labels and content.

- [x] **Step 2: Use this minimal launch timeline shape**

```json
{
  "layout": "timeline",
  "canvas": {"width": 1210, "height": 760, "frames": 30, "fps": 10},
  "animation": {"marker": "arrow"},
  "title": {"main": "Launch Readiness Path", "subtitle": "Risk falls when gates happen in order"},
  "steps": [
    {"label": "Brief", "body": "Name the audience and promise"},
    {"label": "Beta", "body": "Test value with a small group"},
    {"label": "Risk Gate", "body": "Check support, legal, and launch notes"},
    {"label": "Release", "body": "Ship with monitored rollout"},
    {"label": "Learn", "body": "Feed issues back into the next cycle"}
  ]
}
```

- [x] **Step 3: Use this minimal launch funnel shape**

```json
{
  "layout": "funnel",
  "canvas": {"width": 1210, "height": 760, "frames": 30, "fps": 10},
  "title": {"main": "Launch Adoption Funnel", "subtitle": "Each handoff narrows the audience"},
  "stages": [
    {"label": "Reached", "value": "48k"},
    {"label": "Activated", "value": "12k"},
    {"label": "Kept week 2", "value": "5.8k"},
    {"label": "Shared", "value": "1.1k"}
  ]
}
```

- [x] **Step 4: Use this minimal Chinese loop shape**

```json
{
  "layout": "circular_loop",
  "canvas": {"width": 1210, "height": 900, "frames": 30, "fps": 10},
  "title": {"main": "會議升級循環", "subtitle": "資訊不清 -> 更多會議 -> 更少整理時間"},
  "steps": [
    {"label": "問題沒有被整理", "badge": "起點"},
    {"label": "會議先被加開", "badge": "補救"},
    {"label": "決策散在對話裡", "badge": "分散"},
    {"label": "執行者回頭確認", "badge": "返工"},
    {"label": "下次更早開會", "badge": "循環"}
  ]
}
```

- [x] **Step 5: Run each spec once during creation**

For every spec, run:

```bash
python3 skills/iysl-anidiagram/scripts/render_animated_diagram.py \
  --spec skills/iysl-anidiagram/examples/gallery/01-launch-three-readings/timeline/spec.json \
  --outdir /tmp/iysl-anidiagram-gallery-manual-check/timeline \
  --basename timeline \
  --verify \
  --check
```

Expected: exit code `0`. Repeat with a unique `--outdir` and `--basename` for each spec.

- [x] **Step 6: Commit**

```bash
git add skills/iysl-anidiagram/examples/gallery
git commit -m "Add runnable anidiagram gallery specs"
```

---

### Task 4: Add Automated Gallery Validation

**Files:**
- Create: `skills/iysl-anidiagram/tests/test_gallery_examples.py`

- [x] **Step 1: Write gallery validation test**

Create `skills/iysl-anidiagram/tests/test_gallery_examples.py` with this content:

```python
import importlib.util
import json
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
MODULE_PATH = ROOT / "scripts" / "render_animated_diagram.py"
GALLERY = ROOT / "examples" / "gallery"


def load_renderer():
    spec = importlib.util.spec_from_file_location("render_animated_diagram", MODULE_PATH)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class GalleryExamplesTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.renderer = load_renderer()
        cls.spec_paths = sorted(GALLERY.glob("**/spec.json"))

    def test_gallery_has_expected_number_of_specs(self):
        self.assertEqual(len(self.spec_paths), 11)

    def test_each_gallery_spec_has_decision_file(self):
        for spec_path in self.spec_paths:
            case_dir = next(path for path in [spec_path.parent, spec_path.parent.parent] if (path / "decision.md").exists())
            decision = (case_dir / "decision.md").read_text(encoding="utf-8")
            self.assertIn("## Primary Claim", decision, spec_path)
            self.assertIn("## Rejected Alternatives", decision, spec_path)
            self.assertIn("## Validation", decision, spec_path)

    def test_gallery_specs_render_and_pass_contract_checks(self):
        for spec_path in self.spec_paths:
            spec = json.loads(spec_path.read_text(encoding="utf-8"))
            basename = "-".join(spec_path.relative_to(GALLERY).parts[:-1])
            with tempfile.TemporaryDirectory() as tmp:
                result = self.renderer.write_outputs(spec, Path(tmp), basename)
                checks = self.renderer.check_outputs(result, spec)
            self.assertTrue(checks["ok"], f"{spec_path}: {checks}")


if __name__ == "__main__":
    unittest.main()
```

- [x] **Step 2: Run test and verify it passes**

Run:

```bash
python3 -m unittest skills/iysl-anidiagram/tests/test_gallery_examples.py
```

Expected: `OK`.

- [x] **Step 3: Commit**

```bash
git add skills/iysl-anidiagram/tests/test_gallery_examples.py
git commit -m "Validate anidiagram gallery examples"
```

---

### Task 5: Update Skill And Reference Docs

**Files:**
- Modify: `skills/iysl-anidiagram/SKILL.md`
- Modify: `skills/iysl-anidiagram/references/spec-format.md`

- [x] **Step 1: Update `SKILL.md`**

Add a new section after `Core Approach`:

```markdown
## Design Latitude Contract

1. Extract the claim before choosing the layout.
2. Choose the relation first: sequence, loop, narrowing, tradeoff, layers, contrast, branching, system map, or multi-part story.
3. Use `examples/gallery/` for judgment patterns, not visual copying.
4. Use `assets/*-spec.json` only to confirm valid fields and renderer contracts.
5. Vary label density, grouping, emphasis, tone, and animation when it clarifies the source.
6. Do not use style atoms as a classifier; choose style after relation and layout.
7. If no primitive fits, extend the renderer with tests instead of distorting an unrelated layout.
8. Always render with `--verify --check` and human-review the PNG for hierarchy, overlap, clipping, and readability.
```

Update the existing sentence about schemas/assets to:

```markdown
Schemas live in `references/spec-format.md`. Renderer contract samples live in `assets/*-spec.json`. Judgment examples live in `examples/gallery/`; read their `decision.md` files when a source could reasonably become more than one layout.
```

- [x] **Step 2: Update `references/spec-format.md`**

Add this subsection before `## Design Atoms`:

```markdown
## Assets Versus Gallery

- `assets/*-spec.json` are compact renderer contract samples. Use them to confirm field names, supported layout structures, and output checks.
- `examples/gallery/` contains decision examples. Use these to understand how a source brief, claim, relation, rejected alternatives, and style choices lead to a spec.
- Do not copy a gallery spec as a template before stating the claim and relation. The gallery demonstrates judgment; the renderer validates contracts.
```

Add this subsection under `## Principle-Led Workflow`:

```markdown
Decision ladder:

1. Claim: what should the reader understand first?
2. Relation: sequence, loop, narrowing, tradeoff, layers, contrast, branching, system map, or multi-part story.
3. Layout: choose the primitive that makes that relation easiest to scan.
4. Emphasis: choose density, grouping, tone, motion marker, and block styles.
5. Validation: render, run `--check`, and review the PNG by eye.
```

- [x] **Step 3: Run a docs sanity grep**

Run:

```bash
rg -n "examples/gallery|Design Latitude|Assets Versus Gallery|Decision ladder" skills/iysl-anidiagram/SKILL.md skills/iysl-anidiagram/references/spec-format.md
```

Expected: all four phrases appear.

- [x] **Step 4: Commit**

```bash
git add skills/iysl-anidiagram/SKILL.md skills/iysl-anidiagram/references/spec-format.md
git commit -m "Document anidiagram gallery decision workflow"
```

---

### Task 6: Include Gallery Specs In Skill Verification

**Files:**
- Modify: `tools/verify-skill.sh`

- [x] **Step 1: Extend render verification loop**

After the existing `assets/*-spec.json` loop, add:

```bash
if [[ -f scripts/render_animated_diagram.py ]] && [[ -d examples/gallery ]]; then
  while IFS= read -r -d '' spec; do
    rel="${spec#./}"
    base="${rel%/spec.json}"
    base="${base//\//-}"
    "$python_bin" scripts/render_animated_diagram.py \
      --spec "$spec" \
      --outdir "$outdir/gallery-$base" \
      --basename "$base" \
      --verify \
      --check >/dev/null
  done < <(find examples/gallery -name spec.json -print0 | sort -z)
fi
```

- [x] **Step 2: Run verification**

Run:

```bash
tools/verify-skill.sh iysl-anidiagram
```

Expected: `verified iysl-anidiagram`.

- [x] **Step 3: Commit**

```bash
git add tools/verify-skill.sh
git commit -m "Verify anidiagram gallery specs"
```

---

### Task 7: Full Verification And Final Review

**Files:**
- Review all modified files

- [x] **Step 1: Run unit tests**

Run:

```bash
cd skills/iysl-anidiagram
python3 -m unittest discover -s tests
```

Expected: all tests pass with `OK`.

- [x] **Step 2: Run repo skill verification**

Run:

```bash
tools/verify-skill.sh iysl-anidiagram
```

Expected: `verified iysl-anidiagram`.

- [x] **Step 3: Render a small visual sample for human review**

Run:

```bash
python3 skills/iysl-anidiagram/scripts/render_animated_diagram.py \
  --spec skills/iysl-anidiagram/examples/gallery/01-launch-three-readings/composite/spec.json \
  --outdir /tmp/iysl-anidiagram-final-gallery-review \
  --basename composite-review \
  --verify \
  --check
```

Expected: exit code `0`; manually inspect `/tmp/iysl-anidiagram-final-gallery-review/composite-review.png` for hierarchy, overlap, clipping, and readability.

- [x] **Step 4: Check git diff**

Run:

```bash
git status --short
git diff --stat HEAD~6..HEAD
```

Expected: committed changes cover `.gitignore`, gallery docs/specs, gallery test, skill/reference docs, and verification script. No `.superpowers/` files are tracked.

- [x] **Step 5: Final summary**

Report:

- Gallery case count and spec count.
- Verification commands and results.
- Any human-review limitations.
- Whether the live installed skill was updated. Do not claim live installation unless `tools/install-skill.sh iysl-anidiagram` was run and followed by `tools/verify-skill.sh iysl-anidiagram`.

---

## Self-Review

- Spec coverage: this plan implements `.superpowers/` hygiene, gallery index, 8 case directories, 11 runnable specs, Design Latitude Contract, assets-vs-gallery reference docs, automated gallery validation, and full verification.
- Placeholder scan: no unfinished-marker steps are present.
- Type consistency: all paths use `skills/iysl-anidiagram/examples/gallery/**/spec.json`; validation code uses existing renderer functions `write_outputs` and `check_outputs`.
