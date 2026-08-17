import unittest
from pathlib import Path


SKILL_DIR = Path(__file__).resolve().parents[1]


class PluggingContractTest(unittest.TestCase):
    def test_explicit_only_identity_is_consistent(self):
        skill = (SKILL_DIR / "SKILL.md").read_text(encoding="utf-8")
        openai = (SKILL_DIR / "agents" / "openai.yaml").read_text(encoding="utf-8")

        self.assertIn("name: iysl-plugging", skill)
        self.assertIn('display_name: "iysl-plugging"', openai)
        self.assertIn("$iysl-plugging", openai)
        self.assertIn("allow_implicit_invocation: false", openai)

    def test_catalog_completeness_and_selection_are_separate(self):
        skill = (SKILL_DIR / "SKILL.md").read_text(encoding="utf-8")

        self.assertIn("read/discovered", skill)
        self.assertIn("read every bundled skill's complete YAML frontmatter", skill)
        self.assertIn("Read each selected `SKILL.md` completely", skill)
        self.assertIn("discovered `SKILL.md` files in stable batches", skill)

    def test_resolution_fails_closed_and_stays_read_only(self):
        skill = (SKILL_DIR / "SKILL.md").read_text(encoding="utf-8")

        self.assertIn("instead of choosing the newest one", skill)
        self.assertIn("cache presence proves installation", skill)
        self.assertIn("Do not change model context or compaction settings", skill)
        self.assertIn("Keep no persistent index, hook", skill)


if __name__ == "__main__":
    unittest.main()
