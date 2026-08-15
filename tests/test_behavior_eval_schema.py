import unittest
import tempfile
from pathlib import Path

from tools.verify_behavior_evals import _validate_semantic_config, validate_repository

ROOT = Path(__file__).resolve().parents[1]


class BehaviorEvalSchemaTests(unittest.TestCase):
    def test_behavior_cases_are_machine_readable_and_required_for_implicit_skills(self):
        self.assertEqual(validate_repository(ROOT), [])

    def test_semantic_config_rejects_non_finite_weight(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            path = Path(temp_dir) / "semantic_config.json"
            path.write_text(
                '{"positive_concepts":{"bad":{"weight":1e999,"phrases":["x"]}},'
                '"negative_concepts":{"no":{"weight":0.5,"phrases":["y"]}},'
                '"fallback_positive_concepts":["bad"]}',
                encoding="utf-8",
            )
            errors: list[str] = []
            _validate_semantic_config(path, errors)
            self.assertTrue(any("weight must be between 0 and 1" in error for error in errors))

    def test_semantic_config_rejects_exclusive_list_without_inline_flag(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            path = Path(temp_dir) / "semantic_config.json"
            path.write_text(
                '{"positive_concepts":{"yes":{"weight":0.5,"phrases":["x"]}},'
                '"negative_concepts":{"no":{"weight":0.5,"phrases":["y"]}},'
                '"fallback_positive_concepts":["yes"],'
                '"exclusive_negative_concepts":["no"]}',
                encoding="utf-8",
            )
            errors: list[str] = []
            _validate_semantic_config(path, errors)
            self.assertTrue(any("must exactly match" in error for error in errors))


if __name__ == "__main__":
    unittest.main()
