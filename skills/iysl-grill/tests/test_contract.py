import re
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


class GrillContractTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.skill = (ROOT / "SKILL.md").read_text(encoding="utf-8")
        cls.skill_text = re.sub(r"\s+", " ", cls.skill)
        cls.openai = (ROOT / "agents" / "openai.yaml").read_text(encoding="utf-8")
        cls.upstream = (ROOT / "UPSTREAM.md").read_text(encoding="utf-8")

    def test_name_matches_directory_and_invocation_is_explicit(self):
        match = re.search(r"^name:\s*([a-z0-9-]+)$", self.skill, re.MULTILINE)
        self.assertIsNotNone(match)
        self.assertEqual(match.group(1), ROOT.name)
        self.assertIn("disable-model-invocation: true", self.skill)
        self.assertIn("allow_implicit_invocation: false", self.openai)

    def test_frontier_round_contract_is_complete(self):
        for phrase in (
            "decision tree",
            "Work the tree in **rounds**",
            "Ask the whole frontier in one round",
            "Recompute the frontier before every round",
            "Find facts instead of asking the user for them",
            "frontier is empty",
            "user confirms shared understanding",
        ):
            self.assertIn(phrase, self.skill_text)

    def test_questions_include_recommendations(self):
        self.assertIn("❓ **Q1**", self.skill)
        self.assertIn("➡️ <recommended answer>", self.skill)

    def test_skill_is_self_contained_and_stateless(self):
        self.assertNotIn("Run a `/grilling` session", self.skill)
        self.assertIn("Keep the session stateless", self.skill)
        self.assertIn("do not write plans, specs, tickets, ADRs, or code", self.skill_text)

    def test_upstream_snapshot_is_pinned(self):
        self.assertIn("https://github.com/mattpocock/skills", self.upstream)
        self.assertRegex(self.upstream, r"Snapshot commit: `[0-9a-f]{40}`")


if __name__ == "__main__":
    unittest.main()
