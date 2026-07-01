# Output Risk Profile

## Boundary

This skill owns animated explanatory diagrams that produce `.png`, `.gif`, and editable `.excalidraw` files from a compact JSON spec.

## Main Risks

- Wrong primitive: content forced into a layout that hides the real story.
- Misread relation: the model mistakes a loop, funnel, tradeoff, layer stack, contrast, or system map for a generic sequence.
- Template drift: outputs start looking identical even when the content calls for different structures.
- Text overload: long labels fit technically but become hard to read.
- Weak animation: motion decorates the diagram without explaining sequence, causality, or focus.
- Style overreach: dark technical finish, glow, or motion atoms are treated as templates instead of optional presentation choices.
- Editability regression: Excalidraw output becomes non-editable, embeds files unnecessarily, or loses text semantics.
- Over-constraint: rigid rules, classifier logic, or theme systems start replacing the model's semantic judgment.

## Current Controls

- `references/spec-format.md` defines layout selection, Diagram IR, and field contracts.
- The spec separates semantic layout fields from optional `style`, `animation`, and `finish` atoms.
- `scripts/render_animated_diagram.py --check` verifies dimensions, fps, frame count, motion, Excalidraw IDs, text font family, empty files, PNG dimensions, minimum text size, and text canvas bounds.
- Tests cover the legacy `architecture`, `circular_loop`, and common light primitives: `timeline`, `funnel`, `matrix`, `stack`, and `before_after`.

## Known Limits

- The renderer supports common primitives, not arbitrary freehand layout.
- New uncommon structures should be added as new primitives with tests.
- Visual taste still needs a PNG review for overlap, hierarchy, and density.
- Examples are quality anchors, not templates to copy blindly.
