import json
import re
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


class ClarifyContractTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.skill = (ROOT / "SKILL.md").read_text(encoding="utf-8")
        cls.cases = json.loads((ROOT / "evals" / "trigger_cases.json").read_text(encoding="utf-8"))

    def test_frontmatter_name_matches_directory(self):
        match = re.search(r"^name:\s*([a-z0-9-]+)$", self.skill, re.MULTILINE)
        self.assertIsNotNone(match)
        self.assertEqual(match.group(1), ROOT.name)

    def test_contract_keeps_materiality_and_authority_guards(self):
        for phrase in (
            "Default to zero questions",
            "materially change",
            "do not ask for discoverable facts",
            "Never infer permission",
            "generic delegation",
            "do not require a second approval",
        ):
            self.assertIn(phrase, self.skill)
        self.assertNotIn("Use `think`", self.skill)
        self.assertNotIn("Use `hunt`", self.skill)
        self.assertNotIn("Use `check`", self.skill)

    def test_eval_corpus_covers_positive_and_competing_routes(self):
        self.assertGreaterEqual(len(self.cases["should_trigger"]), 5)
        negative_families = {case["family"] for case in self.cases["should_not_trigger"]}
        self.assertTrue({"mechanical_edit", "bug_hunt", "solution_design", "existing_work_review"} <= negative_families)
        self.assertEqual({case["expected_route"] for case in self.cases["should_trigger"]}, {"iysl-clarify"})
        self.assertTrue({"direct", "think", "hunt", "check"} <= {case["expected_route"] for case in self.cases["should_not_trigger"]})

    def test_eval_cases_are_unique_and_nonempty(self):
        cases = self.cases["should_trigger"] + self.cases["should_not_trigger"] + self.cases["near_neighbor"]
        texts = [case["text"].strip() for case in cases]
        self.assertTrue(all(texts))
        self.assertEqual(len(texts), len(set(texts)))


if __name__ == "__main__":
    unittest.main()
