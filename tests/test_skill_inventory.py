import re
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SKILLS = ROOT / "skills"


class SkillInventoryTest(unittest.TestCase):
    def test_skill_directories_and_frontmatter_names_are_iysl_prefixed(self):
        skill_dirs = sorted(path for path in SKILLS.iterdir() if path.is_dir())
        self.assertTrue(skill_dirs)

        for skill_dir in skill_dirs:
            body = (skill_dir / "SKILL.md").read_text(encoding="utf-8")
            match = re.search(r"^name:\s*([a-z0-9-]+)\s*$", body, re.MULTILINE)
            self.assertIsNotNone(match, skill_dir)
            name = match.group(1)

            self.assertEqual(skill_dir.name, name)
            self.assertTrue(name.startswith("iysl-"), name)


if __name__ == "__main__":
    unittest.main()
