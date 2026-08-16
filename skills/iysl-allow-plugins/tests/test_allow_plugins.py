import argparse
import importlib.util
import json
import tempfile
import tomllib
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location(
    "allow_plugins", ROOT / "scripts" / "allow_plugins.py"
)
allow_plugins = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
SPEC.loader.exec_module(allow_plugins)


class AllowPluginsTest(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        self.project = self.root / "project"
        self.project.mkdir()
        self.plugin = self.root / "plugin"
        (self.plugin / ".codex-plugin").mkdir(parents=True)
        (self.plugin / "skills" / "one").mkdir(parents=True)
        (self.plugin / "skills" / "one" / "SKILL.md").write_text(
            "---\nname: one\ndescription: test\n---\n", encoding="utf-8"
        )
        (self.plugin / ".codex-plugin" / "plugin.json").write_text(
            json.dumps(
                {
                    "name": "alpha",
                    "version": "1.0.0",
                    "skills": "./skills/",
                    "mcpServers": "./.mcp.json",
                    "apps": "./.app.json",
                }
            ),
            encoding="utf-8",
        )
        (self.plugin / ".mcp.json").write_text(
            json.dumps({"mcpServers": {"alpha-server": {"command": "alpha"}}}),
            encoding="utf-8",
        )
        (self.plugin / ".app.json").write_text("{}\n", encoding="utf-8")
        self.global_config = self.root / "config.toml"
        self.global_config.write_text(
            f'[projects.{json.dumps(str(self.project.resolve()))}]\ntrust_level = "trusted"\n\n'
            '[plugins."alpha@market"]\nenabled = true\n',
            encoding="utf-8",
        )
        self.plugin_list = self.root / "plugins.json"
        self.plugin_list.write_text(
            json.dumps(
                {
                    "installed": [
                        {
                            "pluginId": "alpha@market",
                            "name": "alpha",
                            "installed": True,
                            "enabled": True,
                            "source": {"source": "local", "path": str(self.plugin)},
                        }
                    ],
                    "available": [],
                }
            ),
            encoding="utf-8",
        )
        cached = self.root / "plugins" / "cache" / "catalog" / "beta" / "2.0.0"
        (cached / ".codex-plugin").mkdir(parents=True)
        (cached / ".codex-plugin" / "plugin.json").write_text(
            json.dumps({"name": "beta", "version": "2.0.0"}), encoding="utf-8"
        )

    def tearDown(self):
        self.temp.cleanup()

    def args(self, **overrides):
        values = {
            "project": str(self.project),
            "global_config": str(self.global_config),
            "plugin_list_json": str(self.plugin_list),
            "host_plugin": [],
        }
        values.update(overrides)
        return argparse.Namespace(**values)

    def inventory(self):
        return allow_plugins.build_inventory(self.args())

    def test_inventory_uses_canonical_cli_id_and_capabilities(self):
        inventory = self.inventory()
        self.assertTrue(inventory["trusted"])
        plugin = next(item for item in inventory["plugins"] if item["selectable"])
        self.assertEqual(plugin["id"], "alpha@market")
        self.assertTrue(plugin["canonical_known"])
        self.assertEqual(plugin["group"], "confirmed_globally_enabled")
        self.assertEqual(plugin["mcp_servers"], ["alpha-server"])
        self.assertTrue(plugin["apps"])
        self.assertEqual(len(plugin["skills"]), 1)
        cache_only = next(item for item in inventory["plugins"] if item["name"] == "beta")
        self.assertEqual(cache_only["group"], "metadata_only")
        self.assertFalse(cache_only["selectable"])
        self.assertEqual(cache_only["sources"], ["cache_metadata"])

    def test_picker_uses_native_checkboxes_and_follow_up_without_writes(self):
        picker = allow_plugins.render_picker(self.inventory())
        self.assertIn('class="form-check"', picker)
        self.assertIn('type="checkbox"', picker)
        self.assertIn(" checked", picker)
        self.assertIn("window.openai.sendFollowUpMessage", picker)
        self.assertIn("$iysl-allow-plugins", picker)
        self.assertIn("先不要寫檔", picker)
        self.assertNotIn("<html", picker)
        self.assertFalse((self.project / ".codex").exists())

    def test_existing_allowlist_prechecks_only_saved_plugins(self):
        inventory = self.inventory()
        inventory["previous_allowlist"] = []
        picker = allow_plugins.render_picker(inventory)
        checkbox = next(line for line in picker.splitlines() if 'type="checkbox"' in line)
        self.assertNotIn(" checked", checkbox)

    def test_plan_masks_unselected_capabilities_and_never_enables_selected(self):
        plan = allow_plugins.build_plan(self.inventory(), [])
        block = plan["managed_block"]
        self.assertIn("[[skills.config]]", block)
        self.assertIn("enabled = false", block)
        self.assertIn('[tool_suggest]', block)
        self.assertIn('id = "alpha@market"', block)
        self.assertIn(
            '[plugins."alpha@market".mcp_servers."alpha-server"]', block
        )
        self.assertNotIn("enabled = true", block)
        self.assertTrue(plan["effects"][0]["apps_not_project_scopeable"])
        self.assertTrue(any("apps/connectors" in item for item in plan["warnings"]))

    def test_apply_validate_and_remove_preserve_unmanaged_bytes(self):
        original = '[features]\nweb_search = true\n\n# keep trailing space \n'
        codex_dir = self.project / ".codex"
        codex_dir.mkdir()
        config_path = self.project / allow_plugins.CONFIG_REL
        config_path.write_text(original, encoding="utf-8")

        plan = allow_plugins.build_plan(self.inventory(), [])
        result = allow_plugins.apply_plan(plan)
        self.assertEqual(result["status"], "applied")
        tomllib.loads(config_path.read_text(encoding="utf-8"))
        tomllib.loads(
            (self.project / allow_plugins.ALLOWLIST_REL).read_text(encoding="utf-8")
        )
        inventory = self.inventory()
        self.assertEqual(allow_plugins.validate_state(inventory)["status"], "valid")

        preview = allow_plugins.remove_state(self.project, False)
        self.assertEqual(preview["status"], "preview")
        self.assertTrue(config_path.exists())
        allow_plugins.remove_state(self.project, True)
        self.assertEqual(config_path.read_text(encoding="utf-8"), original)
        self.assertFalse((self.project / allow_plugins.ALLOWLIST_REL).exists())

    def test_conflicting_tool_suggest_stops_before_writes(self):
        codex_dir = self.project / ".codex"
        codex_dir.mkdir()
        (codex_dir / "config.toml").write_text(
            '[tool_suggest]\ndisabled_tools = []\n', encoding="utf-8"
        )
        with self.assertRaisesRegex(allow_plugins.AllowPluginsError, "tool_suggest"):
            allow_plugins.build_plan(self.inventory(), [])
        self.assertFalse((codex_dir / "allow-plugins.toml").exists())

    def test_missing_manifest_stops_before_writes(self):
        payload = json.loads(self.plugin_list.read_text(encoding="utf-8"))
        payload["installed"][0]["source"]["path"] = str(self.root / "missing")
        self.plugin_list.write_text(json.dumps(payload), encoding="utf-8")
        inventory = self.inventory()
        with self.assertRaisesRegex(allow_plugins.AllowPluginsError, "manifest unavailable"):
            allow_plugins.build_plan(inventory, [])
        self.assertFalse((self.project / ".codex").exists())

    def test_apply_command_requires_confirmation(self):
        code = allow_plugins.main(
            [
                "apply",
                "--project",
                str(self.project),
                "--global-config",
                str(self.global_config),
                "--plugin-list-json",
                str(self.plugin_list),
            ]
        )
        self.assertEqual(code, 2)
        self.assertFalse((self.project / ".codex").exists())


class SkillContractTest(unittest.TestCase):
    def test_skill_is_explicit_only_and_has_no_sync_entrypoint(self):
        skill = (ROOT / "SKILL.md").read_text(encoding="utf-8")
        metadata = (ROOT / "agents" / "openai.yaml").read_text(encoding="utf-8")
        self.assertIn("$iysl-allow-plugins", skill)
        self.assertIn("native `.form-check` controls", skill)
        self.assertIn("window.openai.sendFollowUpMessage", skill)
        self.assertIn("not access control", skill)
        self.assertIn("allow_implicit_invocation: false", metadata)
        self.assertNotIn("$iysl-allow-plugins sync", skill)


if __name__ == "__main__":
    unittest.main()
