import unittest
from pathlib import Path

from tools.verify_behavior_evals import validate_repository

ROOT = Path(__file__).resolve().parents[1]


class BehaviorEvalSchemaTests(unittest.TestCase):
    def test_behavior_cases_are_machine_readable_and_required_for_implicit_skills(self):
        self.assertEqual(validate_repository(ROOT), [])


if __name__ == "__main__":
    unittest.main()
