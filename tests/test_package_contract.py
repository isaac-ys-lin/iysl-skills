import json
import re
import unittest
from pathlib import Path

from tools.skill_manifest import load_manifest, openai_policy, parse_frontmatter


ROOT = Path(__file__).resolve().parents[1]
SKILLS = ROOT / "skills"
MANIFEST = load_manifest(ROOT)
SKILL_ENTRIES = MANIFEST["skills"]
MAINTAINED_SKILLS = {
    name for name, entry in SKILL_ENTRIES.items() if entry["maintainer"] == "iysl"
}
FORKED_SKILLS = {
    name
    for name, entry in SKILL_ENTRIES.items()
    if entry["origin"] == "forked"
}
EXPECTED_SKILLS = set(SKILL_ENTRIES)
# .DS_Store is ignored at the repository and skill levels, so Finder metadata
# cannot enter the published package. Keep this gate focused on generated files
# that can affect a checkout or release artifact.
RESIDUE_NAMES = {"__pycache__", ".pytest_cache"}


class PackageContractTest(unittest.TestCase):
    def test_manifest_is_the_single_inventory_and_has_valid_gate_metadata(self):
        self.assertEqual(MANIFEST["schema_version"], 2)
        self.assertEqual(
            set(MANIFEST["name_policy"]["allowed_unprefixed"]),
            {name for name in EXPECTED_SKILLS if not name.startswith(MANIFEST["name_policy"]["required_prefix"])},
        )
        self.assertEqual(MAINTAINED_SKILLS, EXPECTED_SKILLS)
        for name, entry in SKILL_ENTRIES.items():
            self.assertEqual(entry["maintainer"], "iysl", name)
            self.assertIn(entry["origin"], {"original", "forked"}, name)
            self.assertNotIn("ownership", entry, name)
            self.assertIn(entry["visibility"], {"implicit", "explicit"}, name)
            self.assertIn(entry["license"], {"repository", "skill", "bundled-upstream"}, name)
            self.assertIsInstance(entry["required_gates"], list, name)
            self.assertEqual(len(entry["required_gates"]), len(set(entry["required_gates"])), name)
            self.assertTrue(set(entry["required_gates"]) <= {"trigger", "behavior"}, name)
            if entry["origin"] == "original" and entry["visibility"] == "implicit":
                self.assertEqual(set(entry["required_gates"]), {"trigger", "behavior"}, name)
            if entry["license"] == "repository":
                self.assertEqual(entry["origin"], "original", name)
                self.assertFalse((SKILLS / name / "LICENSE").exists(), name)
            elif entry["license"] == "skill":
                self.assertTrue((SKILLS / name / "LICENSE").is_file(), name)
            else:
                self.assertEqual(entry["origin"], "forked", name)
                self.assertTrue((SKILLS / name / "LICENSE").is_file(), name)

    def test_repository_license_is_mit_and_owned_by_iysl(self):
        licenses = [ROOT / "LICENSE"]
        licenses.extend(
            SKILLS / name / "LICENSE"
            for name, entry in SKILL_ENTRIES.items()
            if entry["license"] == "skill"
        )
        for path in licenses:
            self.assertTrue(path.is_file(), path)
            body = path.read_text(encoding="utf-8")
            self.assertTrue(body.startswith("MIT License"), path)
            self.assertIn("Copyright (c) 2026 iysl", body, path)

    def test_forked_skills_retain_license_and_provenance(self):
        for name in FORKED_SKILLS:
            skill_dir = SKILLS / name
            entry = SKILL_ENTRIES[name]
            self.assertEqual(entry["maintainer"], "iysl", name)
            self.assertEqual(entry["origin"], "forked", name)
            self.assertEqual(entry["license"], "bundled-upstream", name)
            upstream = entry.get("upstream")
            self.assertIsInstance(upstream, dict, name)
            self.assertRegex(upstream["repository"], r"^https://github\.com/[^/]+/[^/]+$", name)
            self.assertRegex(upstream["snapshot_commit"], r"^[0-9a-f]{40}$", name)
            self.assertEqual(upstream["license"], "MIT", name)
            self.assertTrue(upstream["copyright"].strip(), name)
            license_body = (skill_dir / "LICENSE").read_text(encoding="utf-8")
            upstream_body = (skill_dir / "UPSTREAM.md").read_text(encoding="utf-8")
            self.assertTrue(license_body.startswith(f"{upstream['license']} License\n"), name)
            self.assertIn(f"Copyright (c) 2026 {upstream['copyright']}", license_body, name)
            self.assertIn(f"- Repository: {upstream['repository']}", upstream_body, name)
            self.assertIn(
                f"- Snapshot commit: `{upstream['snapshot_commit']}`",
                upstream_body,
                name,
            )
            self.assertIn(
                f"- License: {upstream['license']}; copyright {upstream['copyright']}",
                upstream_body,
                name,
            )

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
                legacy_disable = metadata.get("disable-model-invocation")
                if legacy_disable is not None:
                    self.assertEqual(legacy_disable, "true", name)
                continue

            self.assertNotIn("disable-model-invocation", metadata, name)

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

    def test_packaged_skills_do_not_depend_on_symlinks(self):
        symlinks = [
            path.relative_to(ROOT).as_posix()
            for path in SKILLS.rglob("*")
            if path.is_symlink()
        ]
        self.assertEqual(symlinks, [])


if __name__ == "__main__":
    unittest.main()
