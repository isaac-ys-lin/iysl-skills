import json
import re
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


class ExecuteContractTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.skill = (ROOT / "SKILL.md").read_text(encoding="utf-8")
        cls.routing = (ROOT / "references" / "routing.md").read_text(encoding="utf-8")
        cls.routing_text = re.sub(r"\s+", " ", cls.routing)
        cls.behavior = json.loads(
            (ROOT / "evals" / "behavior_cases.json").read_text(encoding="utf-8")
        )

    def test_frontmatter_name_matches_directory(self):
        match = re.search(r"^name:\s*([a-z0-9-]+)$", self.skill, re.MULTILINE)
        self.assertIsNotNone(match)
        self.assertEqual(match.group(1), ROOT.name)

    def test_simple_path_and_parent_authority_are_load_bearing(self):
        for phrase in (
            "zero\n  subagents",
            "main agent owns scope",
            "Default to serial writes",
            "Subagents must not spawn their own subagents",
            "Agent agreement is not proof",
        ):
            self.assertIn(phrase, self.skill)

    def test_role_efforts_are_fixed_and_luna_remains_max(self):
        for phrase in (
            "Luna `max`, fixed",
            "Terra `medium`, fixed",
            "Terra `high`, fixed",
            "Sol `high`, fixed",
            "Fresh Sol `high`, fixed",
            "automatic routing never raises it to `xhigh` or `max`",
        ):
            self.assertIn(phrase, self.routing_text)

    def test_routes_are_selective_and_bounded(self):
        for phrase in (
            "`solo` (default)",
            "One auxiliary is the default maximum",
            "Only `full` may use an implementer and reviewer",
            "Delegation, file count, or a `material` label alone does not trigger review",
            "start one new fresh reviewer",
            "do not add another reviewer or automatically increase effort",
        ):
            self.assertIn(phrase, self.routing_text)

    def test_custom_roles_forbid_full_history_forks(self):
        for phrase in (
            'Set `fork_turns="none"` for every custom role invocation',
            'Do not omit `fork_turns` or use `all`',
            "self-contained task packet",
            'reviewer` with `fork_turns="none"',
        ):
            self.assertIn(phrase, self.routing_text)

        by_id = {case["id"]: case for case in self.behavior["cases"]}
        custom_fork = by_id["custom-role-forks-never-use-full-history"]["expected"]
        self.assertIn("set fork_turns to none", custom_fork["must_do"])
        self.assertIn("omit fork_turns", custom_fork["must_not_do"])
        self.assertIn("use fork_turns all", custom_fork["must_not_do"])

        review = by_id["high-risk-production-requires-fresh-review"]["expected"]
        self.assertIn("set reviewer fork_turns to none", review["must_do"])

    def test_fresh_review_lifecycle_is_complete(self):
        for phrase in (
            "no inherited implementation history",
            "complete diff",
            "fix-first",
            "rethink",
            "Any code change invalidates the previous review",
            "never authorizes commit, push",
        ):
            self.assertIn(phrase, self.routing_text)

    def test_behavior_cases_cover_execution_and_review_failures(self):
        ids = {case["id"] for case in self.behavior["cases"]}
        self.assertTrue(
            {
                "simple-change-stays-inline",
                "bounded-worker-is-luna-max",
                "qa-is-luna-max-and-does-not-fix",
                "material-delegation-does-not-auto-review",
                "high-risk-production-requires-fresh-review",
                "fix-first-allows-one-fresh-rereview",
                "second-non-ship-stops-review-loop",
                "rethink-stops-acceptance",
                "parallel-writes-default-serial",
                "custom-role-forks-never-use-full-history",
            }
            <= ids
        )


if __name__ == "__main__":
    unittest.main()
