import json
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
ALLOWED_KINDS = {"simple", "negative", "ambiguity", "failure", "complex", "compatibility", "idempotence", "quality"}
EXPECTED_FIELDS = {
    "must_do",
    "must_not_do",
    "max_questions",
    "max_subagents",
    "required_validation",
    "must_stop",
    "expected_route",
    "expected_status",
    "source_fidelity",
}


class BehaviorEvalSchemaTests(unittest.TestCase):
    def test_behavior_cases_are_machine_readable_when_present(self):
        for path in sorted((ROOT / "skills").glob("*/evals/behavior_cases.json")):
            with self.subTest(path=path):
                payload = json.loads(path.read_text(encoding="utf-8"))
                self.assertIsInstance(payload, dict)
                cases = payload.get("cases")
                self.assertIsInstance(cases, list)
                self.assertGreater(len(cases), 0)
                ids = []
                kinds = set()
                for case in cases:
                    self.assertIsInstance(case, dict)
                    case_id = case.get("id")
                    self.assertIsInstance(case_id, str)
                    self.assertTrue(case_id.strip())
                    self.assertNotIn(case_id, ids)
                    ids.append(case_id)
                    self.assertIsInstance(case.get("prompt"), str)
                    self.assertTrue(case["prompt"].strip())
                    kind = case.get("kind")
                    self.assertIn(kind, ALLOWED_KINDS)
                    kinds.add(kind)
                    expected = case.get("expected")
                    self.assertIsInstance(expected, dict)
                    self.assertTrue(EXPECTED_FIELDS.intersection(expected), case_id)
                    for field in ("must_do", "must_not_do", "required_validation"):
                        if field in expected:
                            self.assertIsInstance(expected[field], list, f"{case_id}.{field}")
                self.assertTrue(kinds.intersection({"simple", "negative", "ambiguity", "failure"}), path)


if __name__ == "__main__":
    unittest.main()
