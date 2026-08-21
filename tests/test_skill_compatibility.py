import json
import unittest
from pathlib import Path

from tools.skill_manifest import parse_frontmatter


ROOT = Path(__file__).resolve().parents[1]
SKILLS = ROOT / "skills"
EXPECTED = json.loads((ROOT / "tests" / "skill_compatibility.json").read_text(encoding="utf-8"))


class SkillCompatibilityTests(unittest.TestCase):
    def test_declared_runtime_skills_have_compatibility(self):
        for skill_dir in sorted(SKILLS.iterdir()):
            if not skill_dir.is_dir() or not (skill_dir / "scripts").is_dir():
                continue
            if not any(path.is_file() for path in (skill_dir / "scripts").iterdir()):
                continue
            metadata = parse_frontmatter(skill_dir / "SKILL.md")
            self.assertTrue(metadata.get("compatibility"), skill_dir.name)

    def test_expected_runtime_requirements_are_visible(self):
        for skill, requirements in EXPECTED.items():
            metadata = parse_frontmatter(SKILLS / skill / "SKILL.md")
            compatibility = metadata.get("compatibility", "").lower()
            for requirement in requirements:
                self.assertIn(requirement.lower(), compatibility, f"{skill}: {requirement}")

    def test_equity_data_declares_official_top_level_compatibility(self):
        path = SKILLS / "equity-data" / "SKILL.md"
        metadata = parse_frontmatter(path)
        self.assertIn("compatibility", metadata)
        self.assertNotIn("metadata", metadata)


if __name__ == "__main__":
    unittest.main()
