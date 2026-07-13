import json
import re
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SKILLS = ROOT / "skills"
EXPECTED_SKILLS = {
    "iysl-anidiagram",
    "iysl-clarify",
    "iysl-deckab",
    "iysl-sync",
    "iysl-ytdlp-html-report",
}
# .DS_Store is ignored at the repository and skill levels, so Finder metadata
# cannot enter the published package. Keep this gate focused on generated files
# that can affect a checkout or release artifact.
RESIDUE_NAMES = {"__pycache__", ".pytest_cache"}


def frontmatter_value(body: str, key: str):
    match = re.search(rf"^{re.escape(key)}:\s*(.+?)\s*$", body, re.MULTILINE)
    return match.group(1).strip().strip("\"'") if match else None


class PackageContractTest(unittest.TestCase):
    def test_repository_license_is_mit_and_owned_by_iysl(self):
        licenses = [ROOT / "LICENSE", *SKILLS.glob("*/LICENSE")]
        self.assertTrue((ROOT / "LICENSE").is_file())
        for path in licenses:
            body = path.read_text(encoding="utf-8")
            self.assertTrue(body.startswith("MIT License"), path)
            self.assertIn("Copyright (c) 2026 iysl", body, path)

    def test_exact_top_level_skill_inventory(self):
        actual = {path.name for path in SKILLS.iterdir() if path.is_dir()}
        self.assertEqual(actual, EXPECTED_SKILLS)

    def test_no_nested_skill_entrypoints(self):
        actual = {
            path.relative_to(ROOT).as_posix() for path in ROOT.rglob("SKILL.md")
        }
        expected = {f"skills/{name}/SKILL.md" for name in EXPECTED_SKILLS}
        self.assertEqual(actual, expected)

    def test_required_metadata_and_prompt_identity(self):
        for name in EXPECTED_SKILLS:
            skill_dir = SKILLS / name
            body = (skill_dir / "SKILL.md").read_text(encoding="utf-8")
            self.assertEqual(frontmatter_value(body, "name"), name)
            self.assertTrue(frontmatter_value(body, "description"), name)

            openai = (skill_dir / "agents" / "openai.yaml").read_text(
                encoding="utf-8"
            )
            interface = (skill_dir / "agents" / "interface.yaml").read_text(
                encoding="utf-8"
            )
            self.assertIn("default_prompt:", openai, name)
            self.assertIn(f"${name}", openai, name)
            self.assertIn("canonical_format:", interface, name)
            self.assertIn("activation:", interface, name)

    def test_declared_relative_resources_exist(self):
        resource_pattern = re.compile(
            r"(?<![A-Za-z0-9_.-])((?:references|scripts|assets)/[A-Za-z0-9_./-]+)"
        )
        for name in EXPECTED_SKILLS:
            skill_dir = SKILLS / name
            body = (skill_dir / "SKILL.md").read_text(encoding="utf-8")
            for rel in resource_pattern.findall(body):
                rel = rel.rstrip(".,):;`")
                self.assertTrue((skill_dir / rel).exists(), f"{name}: missing {rel}")

    def test_eval_contracts_have_positive_and_negative_cases(self):
        for path in SKILLS.glob("*/evals/trigger_cases.json"):
            payload = json.loads(path.read_text(encoding="utf-8"))
            self.assertTrue(payload.get("should_trigger"), path)
            self.assertTrue(payload.get("should_not_trigger"), path)

    def test_no_generated_residue_in_package_tree(self):
        residue = [
            path.relative_to(ROOT).as_posix()
            for path in SKILLS.rglob("*")
            if path.name in RESIDUE_NAMES or path.suffix in {".pyc", ".pyo"}
        ]
        self.assertEqual(residue, [])


if __name__ == "__main__":
    unittest.main()
