import json
import re
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


class SyncContractTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.skill = (ROOT / "SKILL.md").read_text(encoding="utf-8")
        cls.template = (ROOT / "assets" / "living-plan-template.md").read_text(encoding="utf-8")
        cls.cases = json.loads((ROOT / "evals" / "trigger_cases.json").read_text(encoding="utf-8"))
        cls.semantic = json.loads((ROOT / "evals" / "semantic_config.json").read_text(encoding="utf-8"))

    def test_frontmatter_name_matches_directory(self):
        match = re.search(r"^name:\s*([a-z0-9-]+)$", self.skill, re.MULTILINE)
        self.assertIsNotNone(match)
        self.assertEqual(match.group(1), ROOT.name)

    def test_contract_is_state_driven_and_idempotent(self):
        for phrase in (
            "Update an existing active plan",
            "Create a plan only",
            "smallest idempotent edit",
            "If no material state changed,",
            "make no edit.",
            "Never mark work complete from an unverified report",
            "The plan records authority; it does not expand",
        ):
            self.assertIn(phrase, self.skill)
        self.assertNotIn("Use `think`", self.skill)
        self.assertNotIn("Use `hunt`", self.skill)
        self.assertNotIn("Use `check`", self.skill)

    def test_template_is_optional_and_minimal(self):
        for phrase in ("## Goal", "## Current contract", "## Decisions", "## Progress and evidence"):
            self.assertIn(phrase, self.template)
        self.assertIn("template is a default shape, not a checklist", self.skill)

    def test_completed_plan_lifecycle_stays_concise(self):
        normalized_skill = re.sub(r"\s+", " ", self.skill)
        for phrase in (
            "At completion, replace the working plan with a concise final-state record",
            "remove superseded content, stale execution detail, and resolved blockers",
            "docs/plans/archive/<original-filename>.md",
            "Keep only active plans in the active-plan location",
            "Archive superseded or abandoned plans by the same rule",
        ):
            self.assertIn(phrase, normalized_skill)
        self.assertNotIn("Keep completed plans at their original paths", normalized_skill)

    def test_eval_corpus_covers_routes_and_hijack_guard(self):
        self.assertGreaterEqual(len(self.cases["should_trigger"]), 6)
        negatives = self.cases["should_not_trigger"]
        self.assertIn("stale_plan_hijack", {case["family"] for case in negatives})
        self.assertTrue({"direct", "think", "hunt", "check"} <= {case["expected_route"] for case in negatives})

    def test_semantic_config_remains_test_only(self):
        self.assertEqual(self.semantic["purpose"], "test-heuristic-only")
        self.assertFalse(self.semantic["runtime_authoritative"])


if __name__ == "__main__":
    unittest.main()
