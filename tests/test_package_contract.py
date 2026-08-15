import json
import re
import unittest
from pathlib import Path

from tools.skill_manifest import load_manifest, openai_policy, parse_frontmatter


ROOT = Path(__file__).resolve().parents[1]
SKILLS = ROOT / "skills"
MANIFEST = load_manifest(ROOT)
SKILL_ENTRIES = MANIFEST["skills"]
REPO_OWNED_SKILLS = {
    name for name, entry in SKILL_ENTRIES.items() if entry["ownership"] == "repo"
}
THIRD_PARTY_SKILLS = {
    name
    for name, entry in SKILL_ENTRIES.items()
    if entry["ownership"] == "third_party"
}
EXPECTED_SKILLS = set(SKILL_ENTRIES)
# .DS_Store is ignored at the repository and skill levels, so Finder metadata
# cannot enter the published package. Keep this gate focused on generated files
# that can affect a checkout or release artifact.
RESIDUE_NAMES = {"__pycache__", ".pytest_cache"}


class PackageContractTest(unittest.TestCase):
    def test_manifest_is_the_single_inventory_and_has_valid_gate_metadata(self):
        self.assertEqual(MANIFEST["schema_version"], 1)
        self.assertEqual(
            set(MANIFEST["name_policy"]["allowed_unprefixed"]),
            {name for name in EXPECTED_SKILLS if not name.startswith(MANIFEST["name_policy"]["required_prefix"])},
        )
        self.assertEqual(REPO_OWNED_SKILLS | THIRD_PARTY_SKILLS, EXPECTED_SKILLS)
        for name, entry in SKILL_ENTRIES.items():
            self.assertIn(entry["ownership"], {"repo", "third_party"}, name)
            self.assertIn(entry["visibility"], {"implicit", "explicit"}, name)
            self.assertIn(entry["license"], {"repository", "skill"}, name)
            self.assertIsInstance(entry["required_gates"], list, name)
            if entry["ownership"] == "repo" and entry["visibility"] == "implicit":
                self.assertEqual(set(entry["required_gates"]), {"trigger", "behavior"}, name)
            if entry["license"] == "repository":
                self.assertEqual(entry["ownership"], "repo", name)
                self.assertFalse((SKILLS / name / "LICENSE").exists(), name)
            else:
                self.assertTrue((SKILLS / name / "LICENSE").is_file(), name)

    def test_repository_license_is_mit_and_owned_by_iysl(self):
        licenses = [ROOT / "LICENSE"]
        licenses.extend(
            SKILLS / name / "LICENSE"
            for name, entry in SKILL_ENTRIES.items()
            if entry["ownership"] == "repo" and entry["license"] == "skill"
        )
        for path in licenses:
            self.assertTrue(path.is_file(), path)
            body = path.read_text(encoding="utf-8")
            self.assertTrue(body.startswith("MIT License"), path)
            self.assertIn("Copyright (c) 2026 iysl", body, path)

    def test_third_party_skills_retain_license_and_provenance(self):
        for name in THIRD_PARTY_SKILLS:
            skill_dir = SKILLS / name
            self.assertEqual(SKILL_ENTRIES[name]["license"], "skill", name)
            license_body = (skill_dir / "LICENSE").read_text(encoding="utf-8")
            upstream_body = (skill_dir / "UPSTREAM.md").read_text(encoding="utf-8")
            self.assertTrue(license_body.startswith("MIT License"), name)
            self.assertIn("Copyright (c) 2026 Matt Pocock", license_body, name)
            self.assertIn("https://github.com/mattpocock/skills", upstream_body, name)
            self.assertRegex(upstream_body, r"\b[0-9a-f]{40}\b")

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
            metadata = parse_frontmatter(skill_dir / "SKILL.md")
            self.assertEqual(metadata.get("name"), name)
            self.assertTrue(metadata.get("description"), name)

            openai = (skill_dir / "agents" / "openai.yaml").read_text(
                encoding="utf-8"
            )
            self.assertIn("display_name:", openai, name)
            policy = openai_policy(skill_dir / "agents" / "openai.yaml")
            expected_implicit = SKILL_ENTRIES[name]["visibility"] == "implicit"
            self.assertEqual(policy.get("allow_implicit_invocation"), str(expected_implicit).lower(), name)

            if SKILL_ENTRIES[name]["visibility"] == "explicit":
                self.assertEqual(
                    metadata.get("disable-model-invocation"),
                    "true",
                    name,
                )
                continue

            interface = (skill_dir / "agents" / "interface.yaml").read_text(
                encoding="utf-8"
            )
            self.assertIn("default_prompt:", openai, name)
            self.assertIn(f"${name}", openai, name)
            self.assertIn("allow_implicit_invocation: true", openai, name)
            self.assertIn("canonical_format:", interface, name)
            self.assertIn("activation:", interface, name)
            self.assertIn('mode: "implicit"', interface, name)
            self.assertIn('openai: "native-implicit-skill"', interface, name)

    def test_readme_lists_exact_manifest_inventory(self):
        readme = (ROOT / "README.md").read_text(encoding="utf-8")
        listed = set(re.findall(r"^- `([^`]+)`\s+—", readme, re.MULTILINE))
        self.assertEqual(listed, EXPECTED_SKILLS)

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
