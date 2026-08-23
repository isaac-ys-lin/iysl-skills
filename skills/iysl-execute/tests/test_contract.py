import json
import re
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


class ExecuteContractTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.skill = (ROOT / "SKILL.md").read_text(encoding="utf-8")
        cls.skill_text = re.sub(r"\s+", " ", cls.skill)
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

    def test_luna_max_is_fixed_and_other_role_configuration_is_not_mirrored(self):
        for phrase in (
            "Luna `max`, fixed",
            "All other model and effort choices remain owned by their TOML files",
            "Do not automatically raise or lower any configured role effort",
            "without model or effort overrides",
        ):
            self.assertIn(phrase, self.routing_text)
        for phrase in ("Terra `medium`", "Terra `high`", "Sol `high`"):
            self.assertNotIn(phrase, self.routing_text)

    def test_routes_are_selective_and_bounded(self):
        for phrase in (
            "`solo` (default)",
            "One auxiliary is the default maximum",
            "Only `full` may use an implementer and reviewer",
            "Delegation, file count, or a `material` label alone does not trigger review",
            "start one new fresh reviewer",
            "stop recursive reviewer spawning",
            "This ends the automated review loop, not the authorized task",
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

    def test_configured_roles_are_preflighted_without_overrides(self):
        for phrase in (
            "~/.codex/agents/*.toml",
            "preflight the named role's availability and identity",
            "worker` and `qa` must resolve to the configured Luna Max",
            "Pass no model, effort, sandbox, or other role overrides",
            "Never silently substitute a generic agent",
            "Use `solo` only after confirming",
        ):
            self.assertIn(phrase, self.skill)
        for phrase in (
            "~/.codex/agents/*.toml",
            "worker` and `qa` must be the configured Luna Max roles",
            "Do not pass model, effort, sandbox, or other role overrides",
            "do not silently substitute a generic agent",
        ):
            self.assertIn(phrase, self.routing_text)

    def test_completion_receipt_is_inline_and_gate_complete(self):
        for phrase in (
            "observable, inline delegation receipt",
            "`declared_route`",
            "`dispatched_roles`",
            "`required_gates_passed`",
            "persistent log",
        ):
            self.assertIn(phrase, self.skill)
        for phrase in (
            "Completion receipt",
            "declared_route:",
            "dispatched_roles:",
            "required_gates_passed:",
            "not written to a persistent artifact",
        ):
            self.assertIn(phrase, self.routing_text)

    def test_fresh_review_lifecycle_is_complete(self):
        for phrase in (
            "no inherited implementation history",
            "complete diff",
            "fix-first",
            "rethink",
            "Any code change invalidates the previous review",
            "continue directly when the correction remains bounded",
            "never authorizes commit, push",
        ):
            self.assertIn(phrase, self.routing_text)

    def test_evidenced_review_defects_route_through_hunt(self):
        for phrase in (
            "If QA or a fresh reviewer reports an evidenced product defect",
            "invoke `$hunt`",
            "bounded, authorized, and decision-complete",
            "Keep non-defect feedback here",
        ):
            self.assertIn(phrase, self.skill_text)

        for routing_only_phrase in (
            "functional error, crash, regression, race",
            "one root-cause sentence",
            "observed failing repro before the product fix",
            "same-shape sibling paths",
            "naming, formatting, documentation",
        ):
            self.assertNotIn(routing_only_phrase, self.skill_text)
            self.assertIn(routing_only_phrase, self.routing_text)

        for phrase in (
            "When QA reports a product defect or a reviewer returns `fix-first`",
            "treat each finding as evidence, not a correction plan",
            "route the correction through `$hunt`",
            "Do not invoke `$hunt` for naming, formatting, documentation",
        ):
            self.assertIn(phrase, self.routing_text)

        qa_case = {
            case["id"]: case for case in self.behavior["cases"]
        }["qa-is-luna-max-and-does-not-fix"]["expected"]
        self.assertIn(
            "route an evidenced product failure through hunt before correction",
            qa_case["must_do"],
        )
        self.assertIn(
            "patch the failure directly without root-cause diagnosis",
            qa_case["must_not_do"],
        )

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
                "reviewed-product-defect-routes-through-hunt",
                "non-defect-review-feedback-stays-in-execute",
                "second-non-ship-ends-review-loop-not-task",
                "rethink-stops-acceptance",
                "parallel-writes-default-serial",
                "custom-role-forks-never-use-full-history",
                "configured-role-preflight-and-inline-receipt",
            }
            <= ids
        )


if __name__ == "__main__":
    unittest.main()
