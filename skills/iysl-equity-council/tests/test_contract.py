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
        self.assertFalse((ROOT / "references" / "judgment-contract.md").exists())

    def test_template_has_one_v5_authority_root(self):
        self.assertEqual(self.template["schema_version"], 5)
        self.assertEqual(self.template["council_runtime"], "collaboration_available")
        self.assertNotIn("evidence_cutoff", self.template)
        self.assertEqual(set(self.template["council_input_pei_receipt"]), {"path", "sha256"})
        bindings = self.template["artifact_bindings"]
        self.assertEqual(bindings["authority_version"], 4)
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
            },
        )

    def test_agent_interfaces_do_not_delegate_to_pm_chair(self):
        for body in (self.interface, self.openai):
            self.assertIn("three isolated pre-model assumption challengers", body)
            self.assertIn("same PEI owner", body)
            self.assertNotIn("PM Chair", body)

    def test_agent_interfaces_dispatch_blind_estimates_and_symmetric_cases(self):
        for body in (self.interface, self.openai):
            self.assertIn("blind packet, never the owner values", body)
            self.assertIn("own Base and range for every candidate assumption", body)
            self.assertIn("strongest upside and downside cases", body)
            self.assertIn("cost of a missed entry", body)
            self.assertNotIn("market-right countercase", body)



if __name__ == "__main__":
    unittest.main()
