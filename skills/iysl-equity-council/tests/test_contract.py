import json
import re
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


class EquityCouncilContractTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.skill = (ROOT / "SKILL.md").read_text(encoding="utf-8")
        cls.protocol = (ROOT / "references" / "council-protocol.md").read_text(
            encoding="utf-8"
        )
        cls.template = json.loads(
            (ROOT / "templates" / "council-run.json").read_text(encoding="utf-8")
        )
        cls.interface = (ROOT / "agents" / "interface.yaml").read_text(
            encoding="utf-8"
        )
        cls.openai = (ROOT / "agents" / "openai.yaml").read_text(encoding="utf-8")

    def test_frontmatter_name_matches_directory(self):
        match = re.search(r"^name:\s*([a-z0-9-]+)$", self.skill, re.MULTILINE)
        self.assertIsNotNone(match)
        self.assertEqual(match.group(1), ROOT.name)

    def test_current_flow_is_agent_led_and_owner_adjudicated(self):
        combined = re.sub(r"\s+", " ", " ".join((self.skill, self.protocol)))
        for phrase in (
            "exactly three isolated",
            "same PEI",
            "owner",
            "accept",
            "conditional",
            "reject",
            "before the owner model",
            "does not issue the final investment stance",
            "final deliverable is the PEI-owned full research paper",
        ):
            self.assertIn(phrase, combined)
        for seat in ("Aswath Damodaran", "George Soros", "Michael Mauboussin"):
            self.assertIn(seat, combined)

    def test_agents_are_evidence_closed_and_runtime_is_required(self):
        combined = " ".join((self.skill, self.protocol))
        for phrase in (
            "no browsing",
            "no new evidence",
            "no further delegation",
            "First-round memos stay sealed",
            "collaboration is unavailable",
            "BLOCKED",
            "Do not emulate the three seats",
        ):
            self.assertIn(phrase, combined)

    def test_current_contract_removes_machine_judgment_and_pm_chair(self):
        for token in (
            "method_artifact",
            "mechanism_tags",
            "decision_matrix",
            "scenario_probability_basis",
        ):
            self.assertNotIn(token, self.template)
            self.assertNotIn(token, self.protocol)
        self.assertNotIn("pm_chair", self.template["artifact_bindings"])
        self.assertIn("no PM Chair receipt", self.skill)
        self.assertFalse((ROOT / "references" / "judgment-contract.md").exists())

    def test_base_is_primary_and_probabilities_are_optional(self):
        skill = re.sub(r"\s+", " ", self.skill)
        self.assertIn("Base fair value is primary", skill)
        self.assertIn("Probability-weighted fair value is optional", skill)
        self.assertIn("Missing scenario probabilities do not imply", skill)

    def test_template_has_one_v3_authority_root(self):
        self.assertEqual(self.template["schema_version"], 3)
        self.assertEqual(self.template["council_runtime"], "collaboration_available")
        bindings = self.template["artifact_bindings"]
        self.assertEqual(bindings["authority_version"], 2)
        self.assertEqual(set(bindings["seat_packets"]), {"damodaran", "soros", "mauboussin"})
        self.assertEqual(set(bindings["sealed_memos"]), {"damodaran", "soros", "mauboussin"})
        self.assertEqual(
            set(bindings),
            {
                "authority_version",
                "validator_sha256",
                "preliminary_underwrite",
                "seat_packets",
                "sealed_memos",
                "owner_adjudication",
                "final_model_spec",
                "model_committed_at",
                "fv_freeze_receipt",
            },
        )

    def test_agent_interfaces_do_not_delegate_to_pm_chair(self):
        for body in (self.interface, self.openai):
            self.assertIn("three isolated pre-model assumption challengers", body)
            self.assertIn("same PEI owner", body)
            self.assertNotIn("PM Chair", body)

    def test_agent_interfaces_require_symmetric_calibration_and_market_right_case(self):
        for body in (self.interface, self.openai):
            self.assertIn("too conservative", body)
            self.assertIn("too aggressive", body)
            self.assertIn("uncertain", body)
            self.assertIn("market-right countercase", body)

    def test_preliminary_underwrite_covers_all_load_bearing_assumption_families(self):
        combined = re.sub(r"\s+", " ", " ".join((self.skill, self.protocol)))
        for phrase in (
            "revenue and order conversion",
            "product mix and operating margin",
            "reinvestment and FCFF conversion",
            "capital structure and WACC",
            "explicit growth duration, competitive-advantage fade, and terminal economics",
            "12-month earnings path and market-implied expectations",
        ):
            self.assertIn(phrase, combined)


if __name__ == "__main__":
    unittest.main()
