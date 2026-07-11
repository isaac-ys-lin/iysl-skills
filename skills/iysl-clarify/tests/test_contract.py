import json
import re
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


class ClarifyContractTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.skill = (ROOT / "SKILL.md").read_text(encoding="utf-8")
        cls.cases = json.loads(
            (ROOT / "evals" / "trigger_cases.json").read_text(encoding="utf-8")
        )

    def test_frontmatter_name_matches_directory(self):
        match = re.search(r"^name:\s*([a-z0-9-]+)$", self.skill, re.MULTILINE)
        self.assertIsNotNone(match)
        self.assertEqual(match.group(1), ROOT.name)

    def test_contract_contains_anti_ceremony_guards(self):
        required = [
            "Default to zero questions",
            "at most three user-intent decisions",
            "Ask exactly one question at a time",
            "Do not ask the user to restate discoverable facts",
            "Do not run both at once",
            "do not require a second approval",
        ]
        for phrase in required:
            self.assertIn(phrase, self.skill)

    def test_eval_corpus_covers_positive_and_competing_routes(self):
        self.assertGreaterEqual(len(self.cases["should_trigger"]), 5)
        negative_families = {
            case["family"] for case in self.cases["should_not_trigger"]
        }
        self.assertTrue(
            {"mechanical_edit", "bug_hunt", "solution_design", "existing_work_review"}
            <= negative_families
        )
        self.assertEqual(
            {case["expected_route"] for case in self.cases["should_trigger"]},
            {"iysl-clarify"},
        )
        self.assertTrue(
            {"direct", "think", "hunt", "check"}
            <= {case["expected_route"] for case in self.cases["should_not_trigger"]}
        )
        self.assertEqual(
            {case["expected_route"] for case in self.cases["near_neighbor"]},
            {"direct", "think", "hunt", "check"},
        )
        self.assertTrue(
            {"context_resolves_requirements", "bug_with_deferred_ambiguity"}
            <= negative_families
        )

    def test_eval_cases_are_unique_and_nonempty(self):
        cases = (
            self.cases["should_trigger"]
            + self.cases["should_not_trigger"]
            + self.cases["near_neighbor"]
        )
        texts = [case["text"].strip() for case in cases]
        self.assertTrue(all(texts))
        self.assertEqual(len(texts), len(set(texts)))

    def test_high_risk_delegation_is_not_authorization(self):
        self.assertIn("Generic delegation", self.skill)
        self.assertIn("is not authorization", self.skill)


if __name__ == "__main__":
    unittest.main()
