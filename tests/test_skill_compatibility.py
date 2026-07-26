import json
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SKILLS = ROOT / "skills"
EXPECTED = json.loads((ROOT / "tests" / "skill_compatibility.json").read_text(encoding="utf-8"))


def frontmatter(path: Path):
    text = path.read_text(encoding="utf-8")
    if not text.startswith("---\n") or "\n---\n" not in text[4:]:
        return {}
    raw = text[4 : text.index("\n---\n", 4)]
    result = {}
    for line in raw.splitlines():
        if ":" in line:
            key, value = line.split(":", 1)
            result[key.strip()] = value.strip().strip('"').strip("'")
    return result


class SkillCompatibilityTests(unittest.TestCase):
    def test_declared_runtime_skills_have_compatibility(self):
        for skill_dir in sorted(SKILLS.iterdir()):
            if not skill_dir.is_dir() or not (skill_dir / "scripts").is_dir():
                continue
            if not any(path.is_file() for path in (skill_dir / "scripts").iterdir()):
                continue
            metadata = frontmatter(skill_dir / "SKILL.md")
            self.assertTrue(metadata.get("compatibility"), skill_dir.name)

    def test_expected_runtime_requirements_are_visible(self):
        for skill, requirements in EXPECTED.items():
            metadata = frontmatter(SKILLS / skill / "SKILL.md")
            compatibility = metadata.get("compatibility", "").lower()
            for requirement in requirements:
                self.assertIn(requirement.lower(), compatibility, f"{skill}: {requirement}")


if __name__ == "__main__":
    unittest.main()
