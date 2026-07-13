import json
import re
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


class SyncContractTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.skill = (ROOT / "SKILL.md").read_text(encoding="utf-8")
        cls.cases = json.loads(
            (ROOT / "evals" / "trigger_cases.json").read_text(encoding="utf-8")
        )
        cls.semantic = json.loads(
            (ROOT / "evals" / "semantic_config.json").read_text(encoding="utf-8")
        )

    def test_frontmatter_name_matches_directory(self):
        match = re.search(r"^name:\s*([a-z0-9-]+)$", self.skill, re.MULTILINE)
        self.assertIsNotNone(match)
        self.assertEqual(match.group(1), ROOT.name)

    def test_contract_contains_anti_ceremony_and_authority_guards(self):
        required = [
            "Never treat the existence of a plan as authority",
            "Do not write for conversational repetition",
            "Do not create global registries",
            "The plan records authority; it does not expand it",
            "Never mark work complete",
            "If no material change passes the gate, do not edit",
            "Repository evidence may update progress",
            "must not silently replace the intended contract",
        ]
        for phrase in required:
            self.assertIn(phrase, self.skill)

    def test_plan_shape_has_small_core_and_conditional_sections(self):
        self.assertIn("Always keep these core fields", self.skill)
        self.assertIn("Add these sections only when material", self.skill)
        self.assertNotIn("Omit no required section", self.skill)

    def test_sync_has_completion_and_reference_not_duplicate_rules(self):
        self.assertIn("Done when the plan has no known contradiction", self.skill)
        self.assertIn("Reference existing specs, issues, ADRs, commits, and diffs", self.skill)

    def test_eval_corpus_covers_routes_and_hijack_guard(self):
        self.assertGreaterEqual(len(self.cases["should_trigger"]), 6)
        negatives = self.cases["should_not_trigger"]
        self.assertIn("stale_plan_hijack", {case["family"] for case in negatives})
        self.assertTrue(
            {"direct", "think", "hunt", "check"}
            <= {case["expected_route"] for case in negatives}
        )
        self.assertTrue(
            {"iysl-clarify", "think", "direct"}
            <= {case["expected_route"] for case in self.cases["near_neighbor"]}
        )

    def test_semantic_config_is_explicitly_test_only(self):
        self.assertEqual(self.semantic["purpose"], "test-heuristic-only")
        self.assertFalse(self.semantic["runtime_authoritative"])
        self.assertNotIn("recommended_threshold", self.cases)

    def test_test_heuristic_routes_trigger_and_exclusive_negative_cases(self):
        threshold = self.semantic["recommended_threshold"]

        def matches(text, phrases):
            lowered = text.casefold()
            return any(phrase.casefold() in lowered for phrase in phrases)

        def routes_to_sync(text):
            for concept in self.semantic["negative_concepts"].values():
                if concept.get("exclusive") and matches(text, concept["phrases"]):
                    return False
            score = sum(
                concept["weight"]
                for concept in self.semantic["positive_concepts"].values()
                if matches(text, concept["phrases"])
            )
            return score >= threshold

        for case in self.cases["should_trigger"]:
            self.assertTrue(routes_to_sync(case["text"]), case)
        for case in self.cases["should_not_trigger"]:
            self.assertFalse(routes_to_sync(case["text"]), case)

    def test_eval_cases_are_unique_and_nonempty(self):
        cases = sum(
            (self.cases[key] for key in ("should_trigger", "should_not_trigger", "near_neighbor")),
            [],
        )
        texts = [case["text"].strip() for case in cases]
        self.assertTrue(all(texts))
        self.assertEqual(len(texts), len(set(texts)))


if __name__ == "__main__":
    unittest.main()
