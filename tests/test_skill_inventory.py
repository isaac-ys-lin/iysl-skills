import re
import unittest
from pathlib import Path

from tools.skill_manifest import load_manifest


ROOT = Path(__file__).resolve().parents[1]
SKILLS = ROOT / "skills"
MANIFEST = load_manifest(ROOT)
ALLOWED_UNPREFIXED_SKILLS = set(MANIFEST["name_policy"]["allowed_unprefixed"])
EXPECTED_SKILLS = set(MANIFEST["skills"])


class SkillInventoryTest(unittest.TestCase):
    def test_skill_directories_and_frontmatter_names_follow_repo_policy(self):
        skill_dirs = sorted(path for path in SKILLS.iterdir() if path.is_dir())
        self.assertTrue(skill_dirs)
        self.assertEqual({path.name for path in skill_dirs}, EXPECTED_SKILLS)

        for skill_dir in skill_dirs:
            body = (skill_dir / "SKILL.md").read_text(encoding="utf-8")
            match = re.search(r"^name:\s*([a-z0-9-]+)\s*$", body, re.MULTILINE)
            self.assertIsNotNone(match, skill_dir)
            name = match.group(1)

            self.assertEqual(skill_dir.name, name)
            self.assertTrue(
                name.startswith(MANIFEST["name_policy"]["required_prefix"])
                or name in ALLOWED_UNPREFIXED_SKILLS,
                name,
            )


if __name__ == "__main__":
    unittest.main()
