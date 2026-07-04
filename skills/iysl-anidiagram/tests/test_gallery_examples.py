import importlib.util
import json
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
MODULE_PATH = ROOT / "scripts" / "render_animated_diagram.py"
GALLERY = ROOT / "examples" / "gallery"
EXPECTED_SEED_SPECS = {
    Path("01-launch-three-readings/composite/spec.json"),
    Path("01-launch-three-readings/funnel/spec.json"),
    Path("01-launch-three-readings/timeline/spec.json"),
    Path("02-chinese-training-loop/spec.json"),
    Path("03-chinese-capability-stack/spec.json"),
    Path("04-workflow-before-after/spec.json"),
    Path("05-review-branching-flow/spec.json"),
    Path("06-technical-architecture-map/spec.json"),
    Path("07-style-motion-contrast/arrow/spec.json"),
    Path("07-style-motion-contrast/dot/spec.json"),
    Path("08-priority-matrix-anti-template/spec.json"),
    Path("10-cloud-spend-ranking/spec.json"),
}


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

    def test_gallery_contains_seed_specs(self):
        discovered = {p.relative_to(GALLERY) for p in self.spec_paths}
        missing = sorted(str(path) for path in EXPECTED_SEED_SPECS if path not in discovered)
        self.assertFalse(
            missing,
            f"Missing seeded gallery specs (future specs are allowed): {missing}",
        )

    def test_refusal_case_documents_a_refusal_without_a_spec(self):
        case = GALLERY / "09-no-claim-refusal"
        self.assertTrue((case / "brief.md").exists(), "refusal case needs a brief.md")
        decision_path = case / "decision.md"
        self.assertTrue(decision_path.exists(), "refusal case needs a decision.md")
        decision = decision_path.read_text(encoding="utf-8")
        for heading in ("## Primary Claim", "## Rejected Alternatives", "## Validation"):
            self.assertIn(heading, decision)
        self.assertFalse(
            list(case.glob("**/spec.json")),
            "the refusal case must not contain a spec.json; refusing is the lesson",
        )

    def decision_file_for(self, spec_path):
        candidate_dirs = [spec_path.parent, spec_path.parent.parent]
        for path in candidate_dirs:
            decision_path = path / "decision.md"
            if decision_path.exists():
                return decision_path
        self.fail(f"{spec_path} has no nearby decision.md (checked {', '.join(str(path / 'decision.md') for path in candidate_dirs)})")

    def brief_file_for(self, spec_path):
        candidate_dirs = [spec_path.parent, spec_path.parent.parent]
        for path in candidate_dirs:
            brief_path = path / "brief.md"
            if brief_path.exists():
                return brief_path
        self.fail(f"{spec_path} has no nearby brief.md (checked {', '.join(str(path / 'brief.md') for path in candidate_dirs)})")


    def test_each_gallery_spec_has_decision_file(self):
        for spec_path in self.spec_paths:
            with self.subTest(spec=str(spec_path.relative_to(GALLERY))):
                decision = self.decision_file_for(spec_path).read_text(encoding="utf-8")
                self.assertIn("## Primary Claim", decision, spec_path)
                self.assertIn("## Rejected Alternatives", decision, spec_path)
                self.assertIn("## Validation", decision, spec_path)

    def test_each_gallery_spec_has_brief_file(self):
        for spec_path in self.spec_paths:
            with self.subTest(spec=str(spec_path.relative_to(GALLERY))):
                brief = self.brief_file_for(spec_path).read_text(encoding="utf-8").strip()
                self.assertGreater(len(brief), 0, f"{spec_path}: nearby brief.md must be non-empty")
                self.assertTrue(
                    brief.startswith("# "),
                    f"{spec_path}: nearby brief.md must start with a Markdown H1 heading",
                )

    def test_gallery_specs_render_and_pass_contract_checks(self):
        for spec_path in self.spec_paths:
            with self.subTest(spec=str(spec_path.relative_to(GALLERY))):
                spec = json.loads(spec_path.read_text(encoding="utf-8"))
                basename = "-".join(spec_path.relative_to(GALLERY).parts[:-1])
                with tempfile.TemporaryDirectory() as tmp:
                    result = self.renderer.write_outputs(spec, Path(tmp), basename)
                    checks = self.renderer.check_outputs(result, spec)
                self.assertTrue(checks["ok"], f"{spec_path}: {checks}")


if __name__ == "__main__":
    unittest.main()
