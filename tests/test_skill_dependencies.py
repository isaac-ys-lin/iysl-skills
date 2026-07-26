import re
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SKILLS = ROOT / "skills"
HARD_DEPENDENCY = re.compile(
    r"\b(?:must|requires?|required to|必須(?:使用|呼叫|載入))\s+(?:use|run|invoke|load)?\s*[@$]([a-z][a-z0-9-]+)",
    re.IGNORECASE,
)
IGNORED_WORDS = {"the", "a", "an", "one", "this", "that", "it"}


class SkillDependencyTests(unittest.TestCase):
    def test_hard_skill_dependencies_are_packaged_or_have_generic_fallback(self):
        known = {path.name for path in SKILLS.iterdir() if path.is_dir()}
        violations = []
        for skill_path in sorted(SKILLS.glob("*/SKILL.md")):
            body = skill_path.read_text(encoding="utf-8")
            for match in HARD_DEPENDENCY.finditer(body):
                dependency = match.group(1)
                if dependency in IGNORED_WORDS or dependency in known:
                    continue
                context = body[max(0, match.start() - 140) : match.end() + 180].lower()
                has_fallback = any(token in context for token in ("optional", "when available", "fallback", "可選", "降級"))
                if not has_fallback:
                    violations.append(f"{skill_path}: {dependency}")
        self.assertEqual(violations, [], "unavailable hard dependencies without fallback: " + ", ".join(violations))


if __name__ == "__main__":
    unittest.main()
