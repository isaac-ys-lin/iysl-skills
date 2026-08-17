import argparse
import io
import importlib.util
import json
import os
import signal
import stat
import tempfile
import tomllib
import unittest
from contextlib import redirect_stdout
from pathlib import Path
from types import SimpleNamespace


ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location(
    "allow_plugins", ROOT / "scripts" / "allow_plugins.py"
)
allow_plugins = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
SPEC.loader.exec_module(allow_plugins)


class FakeAppServerSession:
    def __init__(self, responses):
        self.responses = list(responses)
        self.requests = []
        self.notifications = []
        self.closed = False

    def request(self, message):
        self.requests.append(message)
        response = self.responses.pop(0)
        if isinstance(response, BaseException):
            raise response
        return response

    def notify(self, message):
        self.notifications.append(message)

    def close(self):
        self.closed = True


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
                }
            ),
            encoding="utf-8",
        )
        (self.plugin / ".mcp.json").write_text(
            json.dumps({"mcpServers": {"alpha-server": {"command": "alpha"}}}),
            encoding="utf-8",
        )
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

    def inventory(self, **overrides):
        return allow_plugins.build_inventory(self.args(**overrides))

    @staticmethod
    def runtime_ok(_plan):
        return {
            "ok": True,
            "runtimes": [
                {"path": "/fake/codex", "source": "desktop", "version": "codex-cli fake"}
            ],
        }

    @staticmethod
    def runtime_failure(_plan):
        return {
            "ok": False,
            "stage": "runtime_mismatch",
            "runtime": {"path": "/fake/codex", "source": "desktop", "version": "codex-cli fake"},
            "leaked_skills": [{"plugin": "alpha@market", "skill": "alpha:one"}],
            "leaked_mcp": [],
        }

    @staticmethod
    def runtime():
        return {"path": "/fake/codex", "source": "desktop", "version": "codex-cli fake"}

    def app_responses(self, *, skill_enabled=False, server_info=None, tools=None):
        return [
            {"id": 1, "result": {}},
            {"id": 2, "result": {"thread": {"id": "thread-test"}}},
            {"id": 3, "result": {"apps": {"_default": {"enabled": False}}}},
            {
                "id": 4,
                "result": {"data": [], "nextCursor": None},
            },
            {
                "id": 5,
                "result": {"apps": []},
            },
            {
                "id": 6,
                "result": {
                    "data": [
                        {
                            "cwd": str(self.project.resolve()),
                            "skills": [
                                {
                                    "name": "alpha:one",
                                    "path": str((self.plugin / "skills" / "one" / "SKILL.md").resolve()),
                                    "enabled": skill_enabled,
                                }
                            ],
                            "errors": [],
                        }
                    ]
                },
            },
            {
                "id": 7,
                "result": {
                    "data": [
                        {
                            "name": "alpha-server",
                            "serverInfo": server_info,
                            "tools": [] if tools is None else tools,
                        }
                    ],
                    "nextCursor": None,
                },
            },
        ]

    @staticmethod
    def command_result(rows, *, returncode=0, stderr=""):
        return SimpleNamespace(returncode=returncode, stdout=json.dumps(rows), stderr=stderr)

    def test_inventory_uses_canonical_cli_id_and_capabilities(self):
        inventory = self.inventory()
        self.assertTrue(inventory["trusted"])
        plugin = next(item for item in inventory["plugins"] if item["selectable"])
        self.assertEqual(plugin["id"], "alpha@market")
        self.assertTrue(plugin["canonical_known"])
        self.assertEqual(plugin["group"], "confirmed_globally_enabled")
        self.assertEqual(plugin["mcp_servers"], ["alpha-server"])
        self.assertFalse(plugin["apps"])
        self.assertEqual(
            plugin["skills"],
            [str((self.plugin / "skills" / "one" / "SKILL.md").resolve())],
        )
        cache_only = next(item for item in inventory["plugins"] if item["name"] == "beta")
        self.assertEqual(cache_only["group"], "metadata_only")
        self.assertFalse(cache_only["selectable"])
        self.assertEqual(cache_only["sources"], ["cache_metadata"])

    def test_supplied_and_cli_identity_must_match_manifest_name(self):
        for supplied in ("wrong", "wrong@catalog"):
            with self.subTest(host=supplied):
                with self.assertRaisesRegex(allow_plugins.AllowPluginsError, "does not match manifest name"):
                    self.inventory(host_plugin=[f"{supplied}={self.plugin}"])

        payload = json.loads(self.plugin_list.read_text(encoding="utf-8"))
        payload["installed"][0]["name"] = "wrong"
        self.plugin_list.write_text(json.dumps(payload), encoding="utf-8")
        with self.assertRaisesRegex(allow_plugins.AllowPluginsError, "name does not match pluginId"):
            self.inventory()

        payload["installed"][0]["name"] = "alpha"
        wrong_root = self.root / "wrong-source"
        (wrong_root / ".codex-plugin").mkdir(parents=True)
        (wrong_root / ".codex-plugin" / "plugin.json").write_text(
            json.dumps({"name": "beta"}), encoding="utf-8"
        )
        payload["installed"][0]["source"]["path"] = str(wrong_root)
        self.plugin_list.write_text(json.dumps(payload), encoding="utf-8")
        with self.assertRaisesRegex(allow_plugins.AllowPluginsError, "source manifest does not match"):
            self.inventory()

    def test_picker_uses_native_checkboxes_and_follow_up_without_writes(self):
        picker = allow_plugins.render_picker(self.inventory())
        self.assertIn('class="form-check"', picker)
        self.assertIn('type="checkbox"', picker)
        self.assertIn(" checked", picker)
        self.assertIn("window.openai.sendFollowUpMessage", picker)
        self.assertIn("$iysl-allow-plugins", picker)
        self.assertIn(">檢查並套用</button>", picker)
        self.assertIn("title: '檢查並套用'", picker)
        self.assertIn("這則訊息是唯一確認", picker)
        self.assertIn("selected_plugins = ' + JSON.stringify(selected)", picker)
        self.assertIn(str(self.project.resolve()), picker)
        self.assertNotIn("預覽", picker)
        self.assertNotIn("第二次確認", picker)
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
        self.assertFalse(plan["effects"][0]["apps_not_project_scopeable"])
        self.assertTrue(plan["scope_enforceable"])
        self.assertEqual(plan["unsupported_capabilities"], [])

    def test_malformed_app_capability_blocks_apply_without_writes(self):
        manifest_path = self.plugin / ".codex-plugin" / "plugin.json"
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        manifest["apps"] = "./.app.json"
        manifest_path.write_text(json.dumps(manifest), encoding="utf-8")
        (self.plugin / ".app.json").write_text("{}\n", encoding="utf-8")
        inventory = self.inventory()
        with self.assertRaisesRegex(allow_plugins.AllowPluginsError, "top-level apps object"):
            allow_plugins.build_plan(inventory, [])
        self.assertFalse((self.project / allow_plugins.CONFIG_REL).exists())
        self.assertFalse((self.project / allow_plugins.ALLOWLIST_REL).exists())

    def test_project_apps_conflict_stops_before_writes(self):
        manifest_path = self.plugin / ".codex-plugin" / "plugin.json"
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        manifest["apps"] = "./.app.json"
        manifest_path.write_text(json.dumps(manifest), encoding="utf-8")
        (self.plugin / ".app.json").write_text('{"apps":{"github":{"id":"github"}}}\n', encoding="utf-8")
        config_path = self.project / allow_plugins.CONFIG_REL
        config_path.parent.mkdir()
        config_path.write_bytes(b"[tool_suggest]\ndisabled_tools = []\n")
        config_path.chmod(0o600)
        config_path.write_bytes(b"[apps.foo]\nenabled = true\n")
        before = allow_plugins._snapshot_managed_files(self.project)
        with self.assertRaisesRegex(allow_plugins.AllowPluginsError, "apps config conflicts"):
            allow_plugins.build_plan(self.inventory(), [])
        self.assertEqual(allow_plugins._snapshot_managed_files(self.project), before)

    def test_selected_app_capability_does_not_block_enforceable_mask(self):
        inventory = self.inventory()
        alpha = next(item for item in inventory["plugins"] if item["id"] == "alpha@market")
        alpha["apps"] = True
        plan = allow_plugins.build_plan(inventory, ["alpha@market"])
        self.assertTrue(plan["scope_enforceable"])
        self.assertEqual(plan["unsupported_capabilities"], [])
        result = allow_plugins.apply_plan(plan, runtime_gate=self.runtime_ok)
        self.assertEqual(result["status"], "applied_runtime_verified")
        self.assertTrue(result["scope_enforceable"])

    def test_inventory_aggregates_capabilities_across_observed_roots(self):
        second = self.root / "plugin-second"
        (second / ".codex-plugin").mkdir(parents=True)
        (second / "skills" / "two").mkdir(parents=True)
        (second / "skills" / "two" / "SKILL.md").write_text(
            "---\nname: two\ndescription: test\n---\n", encoding="utf-8"
        )
        (second / ".codex-plugin" / "plugin.json").write_text(
            json.dumps(
                {
                    "name": "alpha",
                    "version": "2.0.0",
                    "skills": "./skills/",
                    "mcpServers": "./.mcp.json",
                }
            ),
            encoding="utf-8",
        )
        (second / ".mcp.json").write_text(
            json.dumps(
                {
                    "mcpServers": {
                        "alpha-server": {"command": "alpha"},
                        "alpha-extra": {"command": "alpha-extra"},
                    }
                }
            ),
            encoding="utf-8",
        )

        inventory = self.inventory(host_plugin=[f"alpha@market={second}"])
        plugin = next(item for item in inventory["plugins"] if item["id"] == "alpha@market")
        self.assertEqual(len(plugin["manifest_roots"]), 2)
        self.assertEqual(
            set(plugin["skills"]),
            {
                str((self.plugin / "skills" / "one" / "SKILL.md").resolve()),
                str((second / "skills" / "two" / "SKILL.md").resolve()),
            },
        )
        self.assertEqual(plugin["mcp_servers"], ["alpha-extra", "alpha-server"])

        block = allow_plugins.build_plan(inventory, [])["managed_block"]
        expected_skill_files = [
            str((self.plugin / "skills" / "one" / "SKILL.md").resolve()),
            str((second / "skills" / "two" / "SKILL.md").resolve()),
        ]
        generated_skill_paths = [
            line.split("=", 1)[1].strip().strip('"')
            for line in block.splitlines()
            if line.startswith("path = ")
        ]
        self.assertTrue(generated_skill_paths)
        self.assertTrue(all(path.endswith("/SKILL.md") for path in generated_skill_paths))
        for expected in expected_skill_files:
            self.assertIn(expected, generated_skill_paths)
        self.assertEqual(block.count('type = "plugin", id = "alpha@market"'), 1)
        self.assertEqual(
            block.count('[plugins."alpha@market".mcp_servers."alpha-server"]'), 1
        )
        self.assertEqual(
            block.count('[plugins."alpha@market".mcp_servers."alpha-extra"]'), 1
        )

    def test_apply_validate_and_remove_preserve_unmanaged_bytes(self):
        original = '[features]\nweb_search = true\n\n# keep trailing space \n'
        codex_dir = self.project / ".codex"
        codex_dir.mkdir()
        config_path = self.project / allow_plugins.CONFIG_REL
        config_path.write_text(original, encoding="utf-8")

        plan = allow_plugins.build_plan(self.inventory(), [])
        result = allow_plugins.apply_plan(plan, runtime_gate=self.runtime_ok)
        self.assertEqual(result["status"], "applied_runtime_verified")
        self.assertTrue(result["runtime_verified"])
        self.assertTrue(result["scope_enforceable"])
        tomllib.loads(config_path.read_text(encoding="utf-8"))
        tomllib.loads(
            (self.project / allow_plugins.ALLOWLIST_REL).read_text(encoding="utf-8")
        )
        inventory = self.inventory()
        self.assertEqual(
            allow_plugins.validate_state(inventory, runtime_gate=self.runtime_ok)["status"],
            "valid_runtime_verified",
        )

        preview = allow_plugins.remove_state(self.project, False)
        self.assertEqual(preview["status"], "preview")
        self.assertTrue(config_path.exists())
        allow_plugins.remove_state(self.project, True)
        self.assertEqual(config_path.read_text(encoding="utf-8"), original)
        self.assertFalse((self.project / allow_plugins.ALLOWLIST_REL).exists())

    def test_apply_and_remove_preserve_crlf_unmanaged_bytes_exactly(self):
        original = b"[features]\r\nweb_search = true\r\n\r\n# keep CRLF\r\n"
        codex_dir = self.project / ".codex"
        codex_dir.mkdir()
        config_path = self.project / allow_plugins.CONFIG_REL
        config_path.write_bytes(original)

        plan = allow_plugins.build_plan(self.inventory(), [])
        allow_plugins.apply_plan(plan, runtime_gate=self.runtime_ok)
        applied = config_path.read_bytes()
        self.assertTrue(applied.startswith(original))
        self.assertEqual(applied[len(original) : len(original) + 1], b"\n")

        allow_plugins.remove_state(self.project, True)
        self.assertEqual(config_path.read_bytes(), original)

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

    def test_runtime_probe_uses_required_protocol_order_and_payload(self):
        plan = allow_plugins.build_plan(self.inventory(), [])
        responses = self.app_responses()
        session = FakeAppServerSession(responses)
        commands = []

        def runner(command, *, cwd, timeout=allow_plugins.RUNTIME_TIMEOUT_SECONDS):
            commands.append((command, cwd, timeout))
            return self.command_result([{"name": "alpha-server", "enabled": False}])

        result = allow_plugins.probe_runtime(
            self.runtime(),
            self.project,
            plan["runtime_targets"],
            plan=plan,
            run_command=runner,
            session_factory=lambda _binary, _project: session,
        )
        self.assertTrue(result["ok"])
        self.assertTrue(session.closed)
        self.assertEqual([request["method"] for request in session.requests], [
            "initialize", "thread/start", "config/read", "app/list", "app/installed", "skills/list", "mcpServerStatus/list"
        ])
        self.assertEqual(session.requests[1]["params"], {"cwd": str(self.project), "ephemeral": True})
        self.assertEqual(session.requests[3]["params"], {"threadId": "thread-test", "cursor": None, "limit": 100, "forceRefetch": False})
        self.assertEqual(session.requests[4]["params"], {"threadId": "thread-test", "forceRefresh": False})
        self.assertEqual(session.notifications, [{"method": "initialized", "params": {}}])
        self.assertEqual(commands[0][0], ["/fake/codex", "mcp", "list", "--json"])
        self.assertEqual(commands[0][1], self.project)

    def test_runtime_probe_detects_skill_and_mcp_leaks(self):
        plan = allow_plugins.build_plan(self.inventory(), [])

        skill_session = FakeAppServerSession(self.app_responses(skill_enabled=True))
        skill_result = allow_plugins.probe_runtime(
            self.runtime(),
            self.project,
            plan["runtime_targets"],
            plan=plan,
            run_command=lambda *args, **kwargs: self.command_result(
                [{"name": "alpha-server", "enabled": False}]
            ),
            session_factory=lambda _binary, _project: skill_session,
        )
        self.assertFalse(skill_result["ok"])
        self.assertEqual(skill_result["leaked_skills"], [{"plugin": "alpha@market", "skill": "alpha:one"}])

        config_session = FakeAppServerSession(self.app_responses())
        config_result = allow_plugins.probe_runtime(
            self.runtime(),
            self.project,
            plan["runtime_targets"],
            plan=plan,
            run_command=lambda *args, **kwargs: self.command_result(
                [{"name": "alpha-server", "enabled": True}]
            ),
            session_factory=lambda _binary, _project: config_session,
        )
        self.assertFalse(config_result["ok"])
        self.assertIn("mcp_cli_enabled", [item["source"] for item in config_result["leaked_mcp"]])

        ready_session = FakeAppServerSession(
            self.app_responses(server_info={"name": "alpha-server"}, tools=[{"name": "leak"}])
        )
        ready_result = allow_plugins.probe_runtime(
            self.runtime(),
            self.project,
            plan["runtime_targets"],
            plan=plan,
            run_command=lambda *args, **kwargs: self.command_result(
                [{"name": "alpha-server", "enabled": False}]
            ),
            session_factory=lambda _binary, _project: ready_session,
        )
        self.assertFalse(ready_result["ok"])
        self.assertIn("app_server_ready_tools", [item["source"] for item in ready_result["leaked_mcp"]])

    def test_runtime_gate_returns_structured_protocol_and_process_failures(self):
        plan = allow_plugins.build_plan(self.inventory(), [])

        def gate_with(session_factory, runner):
            return allow_plugins.verify_runtime_gate(
                plan,
                discoverer=lambda: [self.runtime()],
                runtime_probe=lambda runtime, project, targets, *, plan: allow_plugins.probe_runtime(
                    runtime,
                    project,
                    targets,
                    plan=plan,
                    session_factory=session_factory,
                    run_command=runner,
                ),
            )

        cases = {
            "timeout": (
                lambda _binary, _project: FakeAppServerSession(
                    [allow_plugins.RuntimeProbeError("app_server_timeout", "test")]
                ),
                lambda *args, **kwargs: self.command_result([]),
                "app_server_timeout",
            ),
            "os_error": (
                lambda _binary, _project: (_ for _ in ()).throw(OSError("no process")),
                lambda *args, **kwargs: self.command_result([]),
                "no process",
            ),
            "mcp_nonzero": (
                lambda _binary, _project: FakeAppServerSession(self.app_responses()),
                lambda *args, **kwargs: self.command_result([], returncode=9, stderr="bad mcp"),
                "mcp_cli_nonzero",
            ),
            "malformed": (
                lambda _binary, _project: FakeAppServerSession(
                    [{"id": 1, "result": {}}, {"id": 2, "result": {"data": "bad"}}]
                ),
                lambda *args, **kwargs: self.command_result([]),
                "thread_schema",
            ),
            "json_rpc_error": (
                lambda _binary, _project: FakeAppServerSession(
                    [{"id": 1, "result": {}}, {"id": 2, "error": {"code": 1, "message": "no"}}]
                ),
                lambda *args, **kwargs: self.command_result([]),
                "json_rpc_error",
            ),
        }
        for name, (session_factory, runner, expected) in cases.items():
            with self.subTest(name=name):
                result = gate_with(session_factory, runner)
                self.assertFalse(result["ok"])
                self.assertEqual(result["stage"], "runtime_probe")
                self.assertIn(expected, result["probe_error"])
                self.assertEqual(result["runtime"]["path"], "/fake/codex")

        def exited_session(_binary, _project):
            session = FakeAppServerSession(self.app_responses())
            session.ensure_healthy = lambda: (_ for _ in ()).throw(
                allow_plugins.RuntimeProbeError("app_server_process_exit", "exit 9")
            )
            return session

        exited = gate_with(exited_session, lambda *args, **kwargs: self.command_result([]))
        self.assertFalse(exited["ok"])
        self.assertIn("app_server_process_exit", exited["probe_error"])

    def test_apply_runtime_failure_restores_absent_and_existing_files_exactly(self):
        plan = allow_plugins.build_plan(self.inventory(), [])
        first = allow_plugins.apply_plan(plan, runtime_gate=self.runtime_failure)
        self.assertEqual(first["status"], "rolled_back_runtime_mismatch")
        self.assertFalse(first["scope_enforceable"])
        self.assertFalse((self.project / allow_plugins.CONFIG_REL).exists())
        self.assertFalse((self.project / allow_plugins.ALLOWLIST_REL).exists())
        self.assertTrue((self.project / ".codex").is_dir())

        config_path = self.project / allow_plugins.CONFIG_REL
        allow_path = self.project / allow_plugins.ALLOWLIST_REL
        allow_plugins.apply_plan(plan, runtime_gate=self.runtime_ok)
        original_config = config_path.read_bytes()
        original_allow = allow_path.read_bytes()
        existing_plan = allow_plugins.build_plan(self.inventory(), [])
        second = allow_plugins.apply_plan(existing_plan, runtime_gate=self.runtime_failure)
        self.assertEqual(second["status"], "rolled_back_runtime_mismatch")
        self.assertEqual(config_path.read_bytes(), original_config)
        self.assertEqual(allow_path.read_bytes(), original_allow)

    def test_apply_runtime_rollback_restores_existing_posix_modes(self):
        plan = allow_plugins.build_plan(self.inventory(), [])
        allow_plugins.apply_plan(plan, runtime_gate=self.runtime_ok)
        config_path = self.project / allow_plugins.CONFIG_REL
        allow_path = self.project / allow_plugins.ALLOWLIST_REL
        config_path.chmod(0o600)
        allow_path.chmod(0o600)
        before = (config_path.read_bytes(), allow_path.read_bytes())

        existing_plan = allow_plugins.build_plan(self.inventory(), [])
        result = allow_plugins.apply_plan(existing_plan, runtime_gate=self.runtime_failure)
        self.assertEqual(result["status"], "rolled_back_runtime_mismatch")
        self.assertEqual((config_path.read_bytes(), allow_path.read_bytes()), before)
        self.assertEqual(stat.S_IMODE(config_path.stat().st_mode), 0o600)
        self.assertEqual(stat.S_IMODE(allow_path.stat().st_mode), 0o600)

    def test_apply_rolls_back_keyboard_interrupt_from_runtime_gate(self):
        plan = allow_plugins.build_plan(self.inventory(), [])
        with self.assertRaises(KeyboardInterrupt):
            allow_plugins.apply_plan(
                plan, runtime_gate=lambda _plan: (_ for _ in ()).throw(KeyboardInterrupt())
            )
        self.assertFalse((self.project / allow_plugins.CONFIG_REL).exists())
        self.assertFalse((self.project / allow_plugins.ALLOWLIST_REL).exists())

    def test_apply_rolls_back_transaction_termination_from_runtime_probe(self):
        plan = allow_plugins.build_plan(self.inventory(), [])
        with self.assertRaises(allow_plugins.TransactionTerminated):
            allow_plugins.apply_plan(
                plan,
                runtime_gate=lambda _plan: (_ for _ in ()).throw(
                    allow_plugins.TransactionTerminated()
                ),
            )
        self.assertFalse((self.project / allow_plugins.CONFIG_REL).exists())
        self.assertFalse((self.project / allow_plugins.ALLOWLIST_REL).exists())

    def test_apply_rolls_back_keyboard_interrupt_after_first_atomic_write(self):
        plan = allow_plugins.build_plan(self.inventory(), [])
        config_path = self.project / allow_plugins.CONFIG_REL
        original_write = allow_plugins._atomic_write
        writes = 0

        def interrupt_after_config(path, text, *, mode=None, expected=None):
            nonlocal writes
            original_write(path, text, mode=mode, expected=expected)
            writes += 1
            if writes == 1:
                raise KeyboardInterrupt()

        allow_plugins._atomic_write = interrupt_after_config
        try:
            with self.assertRaises(KeyboardInterrupt):
                allow_plugins.apply_plan(plan, runtime_gate=self.runtime_ok)
        finally:
            allow_plugins._atomic_write = original_write
        self.assertFalse(config_path.exists())
        self.assertFalse((self.project / allow_plugins.ALLOWLIST_REL).exists())

    def test_sigterm_after_first_write_restores_preimage_and_handler(self):
        config_path = self.project / allow_plugins.CONFIG_REL
        config_path.parent.mkdir()
        config_path.write_bytes(b"[features]\nweb_search = true\n")
        config_path.chmod(0o600)
        plan = allow_plugins.build_plan(self.inventory(), [])
        before = allow_plugins._snapshot_managed_files(self.project)
        previous_handler = signal.getsignal(signal.SIGTERM)
        original_write = allow_plugins._atomic_write
        writes = 0

        def terminate_after_config(path, text, *, mode=None, expected=None):
            nonlocal writes
            original_write(path, text, mode=mode, expected=expected)
            writes += 1
            if writes == 1:
                signal.getsignal(signal.SIGTERM)(signal.SIGTERM, None)

        allow_plugins._atomic_write = terminate_after_config
        try:
            with self.assertRaises(allow_plugins.TransactionTerminated):
                allow_plugins.apply_plan(plan, runtime_gate=self.runtime_ok)
        finally:
            allow_plugins._atomic_write = original_write
        self.assertEqual(allow_plugins._snapshot_managed_files(self.project), before)
        self.assertIs(signal.getsignal(signal.SIGTERM), previous_handler)

    def test_validate_runtime_mismatch_is_read_only(self):
        plan = allow_plugins.build_plan(self.inventory(), [])
        allow_plugins.apply_plan(plan, runtime_gate=self.runtime_ok)
        config_path = self.project / allow_plugins.CONFIG_REL
        allow_path = self.project / allow_plugins.ALLOWLIST_REL
        before = (config_path.read_bytes(), allow_path.read_bytes())
        result = allow_plugins.validate_state(self.inventory(), runtime_gate=self.runtime_failure)
        self.assertEqual(result["status"], "runtime_mismatch")
        self.assertFalse(result["runtime_verified"])
        self.assertEqual((config_path.read_bytes(), allow_path.read_bytes()), before)

    def test_validate_rejects_post_probe_managed_file_drift_without_writes(self):
        plan = allow_plugins.build_plan(self.inventory(), [])
        allow_plugins.apply_plan(plan, runtime_gate=self.runtime_ok)
        config_path = self.project / allow_plugins.CONFIG_REL
        allow_path = self.project / allow_plugins.ALLOWLIST_REL
        external = b"# changed during runtime probe\n"
        original_allow = allow_path.read_bytes()

        def runtime_ok_then_change_config(_plan):
            config_path.write_bytes(external)
            return self.runtime_ok(_plan)

        result = allow_plugins.validate_state(self.inventory(), runtime_gate=runtime_ok_then_change_config)
        self.assertEqual(result["status"], "runtime_mismatch")
        self.assertEqual(result["stage"], "post_probe_state")
        self.assertFalse(result["runtime_verified"])
        self.assertEqual(config_path.read_bytes(), external)
        self.assertEqual(allow_path.read_bytes(), original_allow)

    def test_runtime_discovery_deduplicates_samefile_and_preserves_order(self):
        desktop = self.root / "desktop-codex"
        path_binary = self.root / "path-codex"
        for binary in (desktop, path_binary):
            binary.write_text("#!/bin/sh\n", encoding="utf-8")
            binary.chmod(0o755)
        commands = []

        def runner(command, *, cwd, timeout=allow_plugins.RUNTIME_TIMEOUT_SECONDS):
            commands.append(command)
            return SimpleNamespace(returncode=0, stdout=f"version {Path(command[0]).name}\n", stderr="")

        deduped = allow_plugins.discover_runtimes(
            desktop_path=desktop, which=lambda _name: str(desktop), run_command=runner
        )
        self.assertEqual([item["source"] for item in deduped], ["desktop"])
        discovered = allow_plugins.discover_runtimes(
            desktop_path=desktop, which=lambda _name: str(path_binary), run_command=runner
        )
        self.assertEqual([item["source"] for item in discovered], ["desktop", "path"])
        self.assertEqual(commands[-2:], [[str(desktop), "--version"], [str(path_binary), "--version"]])

    def test_same_name_catalog_roots_never_cross_disable_selected_plugin(self):
        def bundle(root, skill_name):
            (root / ".codex-plugin").mkdir(parents=True)
            (root / "skills" / skill_name).mkdir(parents=True)
            (root / "skills" / skill_name / "SKILL.md").write_text(
                f"---\nname: {skill_name}\ndescription: test\n---\n", encoding="utf-8"
            )
            (root / ".codex-plugin" / "plugin.json").write_text(
                json.dumps({"name": "alpha", "skills": "./skills/", "mcpServers": "./.mcp.json"}),
                encoding="utf-8",
            )
            (root / ".mcp.json").write_text(
                json.dumps({"mcpServers": {f"{skill_name}-server": {"command": skill_name}}}),
                encoding="utf-8",
            )

        root_a = self.root / "alpha-cat-a"
        root_b = self.root / "alpha-cat-b"
        bundle(root_a, "from-a")
        bundle(root_b, "from-b")
        # These cache roots reproduce the old name-only aggregation bug. They
        # must remain metadata-only, even though their manifests are valid.
        bundle(self.root / "plugins" / "cache" / "cat-a" / "alpha" / "1", "cache-a")
        bundle(self.root / "plugins" / "cache" / "cat-b" / "alpha" / "1", "cache-b")
        self.global_config.write_text(
            f'[projects.{json.dumps(str(self.project.resolve()))}]\ntrust_level = "trusted"\n\n'
            '[plugins."alpha@cat-a"]\nenabled = true\n\n'
            '[plugins."alpha@cat-b"]\nenabled = true\n',
            encoding="utf-8",
        )
        self.plugin_list.write_text(
            json.dumps(
                {
                    "installed": [
                        {
                            "pluginId": "alpha@cat-a",
                            "name": "alpha",
                            "installed": True,
                            "enabled": True,
                            "source": {"source": "local", "path": str(root_a)},
                        },
                        {
                            "pluginId": "alpha@cat-b",
                            "name": "alpha",
                            "installed": True,
                            "enabled": True,
                            "source": {"source": "local", "path": str(root_b)},
                        },
                    ]
                }
            ),
            encoding="utf-8",
        )
        inventory = self.inventory()
        by_id = {item["id"]: item for item in inventory["plugins"]}
        path_a = str((root_a / "skills" / "from-a" / "SKILL.md").resolve())
        path_b = str((root_b / "skills" / "from-b" / "SKILL.md").resolve())
        self.assertEqual(by_id["alpha@cat-a"]["skills"], [path_a])
        self.assertEqual(by_id["alpha@cat-b"]["skills"], [path_b])
        plan = allow_plugins.build_plan(inventory, ["alpha@cat-a"])
        self.assertNotIn(path_a, plan["managed_block"])
        self.assertIn(path_b, plan["managed_block"])
        self.assertEqual(plan["runtime_targets"][0]["id"], "alpha@cat-b")
        self.assertEqual(plan["runtime_targets"][0]["skills"], [path_b])
        self.assertFalse(plan["runtime_targets"][0]["allow_name_fallback"])

        def responses(skill):
            return [
                {"id": 1, "result": {}},
                {"id": 2, "result": {"thread": {"id": "thread-test"}}},
                {"id": 3, "result": {"apps": {"_default": {"enabled": False}}}},
                {"id": 4, "result": {"data": [], "nextCursor": None}},
                {"id": 5, "result": {"apps": []}},
                {
                    "id": 6,
                    "result": {
                        "data": [
                            {
                                "cwd": str(self.project.resolve()),
                                "skills": [skill],
                                "errors": [],
                            }
                        ]
                    },
                },
                {"id": 7, "result": {"data": [], "nextCursor": None}},
            ]

        # cat-a is selected.  Its enabled, path-attributed skill must not be
        # mistaken for the disabled cat-b capability merely because the names
        # share an alpha prefix.
        safe = allow_plugins.verify_runtime_gate(
            plan,
            discoverer=lambda: [self.runtime()],
            runtime_probe=lambda runtime, project, targets, *, plan: allow_plugins.probe_runtime(
                runtime,
                project,
                targets,
                plan=plan,
                run_command=lambda *args, **kwargs: self.command_result([]),
                session_factory=lambda _binary, _project: FakeAppServerSession(
                    responses({"name": "alpha:from-a", "path": path_a, "enabled": True})
                ),
            ),
        )
        self.assertTrue(safe["ok"])

        # With the path absent, identical names have no canonical provenance.
        # The verifier must fail closed rather than report a false green gate.
        ambiguous = allow_plugins.verify_runtime_gate(
            plan,
            discoverer=lambda: [self.runtime()],
            runtime_probe=lambda runtime, project, targets, *, plan: allow_plugins.probe_runtime(
                runtime,
                project,
                targets,
                plan=plan,
                run_command=lambda *args, **kwargs: self.command_result([]),
                session_factory=lambda _binary, _project: FakeAppServerSession(
                    responses({"name": "alpha:from-a", "enabled": False})
                ),
            ),
        )
        self.assertFalse(ambiguous["ok"])
        self.assertEqual(ambiguous["stage"], "runtime_probe")
        self.assertIn("skills_provenance", ambiguous["probe_error"])

    def test_plan_rejects_shared_selected_and_disabled_skill_path(self):
        inventory = self.inventory()
        alpha = next(item for item in inventory["plugins"] if item["id"] == "alpha@market")
        selected = dict(alpha, id="selected@catalog")
        disabled = dict(alpha, id="disabled@catalog")
        inventory["plugins"] = [selected, disabled]
        with self.assertRaisesRegex(allow_plugins.AllowPluginsError, "share capability paths"):
            allow_plugins.build_plan(inventory, ["selected@catalog"])

    def test_plan_rejects_shared_selected_and_disabled_canonical_mcp_server(self):
        inventory = self.inventory()
        alpha = next(item for item in inventory["plugins"] if item["id"] == "alpha@market")
        selected = dict(alpha, id="selected@catalog", skills=[])
        disabled = dict(alpha, id="disabled@catalog")
        inventory["plugins"] = [selected, disabled]
        with self.assertRaisesRegex(allow_plugins.AllowPluginsError, "canonical MCP server names"):
            allow_plugins.build_plan(inventory, ["selected@catalog"])

    def test_capability_declaration_cannot_escape_plugin_root(self):
        escaped = self.root / "escaped-skills"
        (escaped / "one").mkdir(parents=True)
        (escaped / "one" / "SKILL.md").write_text(
            "---\nname: escaped\ndescription: test\n---\n", encoding="utf-8"
        )
        with self.assertRaisesRegex(allow_plugins.AllowPluginsError, "escapes plugin root"):
            allow_plugins._capabilities(self.plugin, {"skills": "../escaped-skills"})

    def test_app_server_request_deadline_ignores_notifications_and_wrong_ids(self):
        class Clock:
            now = 0.0

            def __call__(self):
                return self.now

        class Lines:
            def __init__(self, clock):
                self.clock = clock
                self.timeouts = []
                self.values = [
                    json.dumps({"method": "notice", "params": {}}),
                    json.dumps({"id": 99, "result": {}}),
                ]

            def get(self, *, timeout):
                self.timeouts.append(timeout)
                self.clock.now += 0.6
                return self.values.pop(0)

        class Input:
            def __init__(self):
                self.closed = False

            def write(self, _value):
                return 0

            def flush(self):
                return None

            def close(self):
                self.closed = True

        class Process:
            def __init__(self):
                self.stdin = Input()
                self.stdout = io.StringIO()
                self.pid = 999999
                self.terminated = False

            def poll(self):
                return 0 if self.terminated else None

            def terminate(self):
                self.terminated = True

            def wait(self, *, timeout):
                return 0

        class Reader:
            def __init__(self):
                self.joined = False

            def join(self, *, timeout):
                self.joined = True

        clock = Clock()
        process = Process()
        reader = Reader()
        session = object.__new__(allow_plugins._StdioAppServerSession)
        session.timeout = 1.0
        session._clock = clock
        session._lines = Lines(clock)
        session.process = process
        session._reader = reader
        with self.assertRaisesRegex(allow_plugins.RuntimeProbeError, "app_server_timeout"):
            session.request({"id": 7, "method": "test", "params": {}})
        self.assertEqual(len(session._lines.timeouts), 2)
        self.assertAlmostEqual(session._lines.timeouts[0], 1.0)
        self.assertAlmostEqual(session._lines.timeouts[1], 0.4)
        session.close()
        self.assertTrue(process.terminated)
        self.assertTrue(process.stdin.closed)
        self.assertTrue(process.stdout.closed)
        self.assertTrue(reader.joined)

    def test_app_server_constructor_cleans_child_after_thread_start_baseexception(self):
        class Stream:
            def __init__(self):
                self.closed = False

            def close(self):
                self.closed = True

        class Process:
            def __init__(self):
                self.stdin = Stream()
                self.stdout = Stream()
                self.pid = 999999
                self.terminated = False

            def poll(self):
                return 0 if self.terminated else None

            def terminate(self):
                self.terminated = True

            def wait(self, *, timeout):
                return 0

        original_popen = allow_plugins.subprocess.Popen
        original_thread = allow_plugins.threading.Thread
        try:
            for exception in (RuntimeError("thread failure"), KeyboardInterrupt()):
                with self.subTest(exception=type(exception).__name__):
                    process = Process()

                    class FailingThread:
                        def __init__(self, *args, **kwargs):
                            self.joined = False

                        def start(self):
                            raise exception

                        def join(self, *, timeout):
                            self.joined = True

                    allow_plugins.subprocess.Popen = lambda *args, **kwargs: process
                    allow_plugins.threading.Thread = FailingThread
                    with self.assertRaises(type(exception)):
                        allow_plugins._StdioAppServerSession("/fake/codex", self.project)
                    self.assertTrue(process.terminated)
                    self.assertTrue(process.stdin.closed)
                    self.assertTrue(process.stdout.closed)
        finally:
            allow_plugins.subprocess.Popen = original_popen
            allow_plugins.threading.Thread = original_thread

    def test_transaction_sigterm_guard_raises_termination_and_restores_handler(self):
        class Signals:
            SIGTERM = 15

            def __init__(self):
                self.previous = object()
                self.current = self.previous
                self.calls = []

            def getsignal(self, signum):
                if signum != self.SIGTERM:
                    raise AssertionError("unexpected signal")
                return self.current

            def signal(self, signum, handler):
                if signum != self.SIGTERM:
                    raise AssertionError("unexpected signal")
                self.calls.append(handler)
                self.current = handler

        signals = Signals()
        main_thread = object()
        with allow_plugins._transaction_sigterm_guard(
            signal_api=signals,
            current_thread=lambda: main_thread,
            main_thread=lambda: main_thread,
        ):
            with self.assertRaises(allow_plugins.TransactionTerminated):
                signals.current(signals.SIGTERM, None)
        self.assertIs(signals.current, signals.previous)
        self.assertEqual(len(signals.calls), 2)

    def test_apply_compare_and_swap_rejects_preapply_drift(self):
        plan = allow_plugins.build_plan(self.inventory(), [])
        config_path = self.project / allow_plugins.CONFIG_REL
        config_path.parent.mkdir()
        newer = b"[features]\nweb_search = true\n"
        config_path.write_bytes(newer)
        with self.assertRaisesRegex(allow_plugins.AllowPluginsError, "changed after planning"):
            allow_plugins.apply_plan(plan, runtime_gate=self.runtime_ok)
        self.assertEqual(config_path.read_bytes(), newer)
        self.assertFalse((self.project / allow_plugins.ALLOWLIST_REL).exists())

    def test_apply_compare_and_swap_rejects_preapply_mode_drift(self):
        first_plan = allow_plugins.build_plan(self.inventory(), [])
        allow_plugins.apply_plan(first_plan, runtime_gate=self.runtime_ok)
        config_path = self.project / allow_plugins.CONFIG_REL
        allow_path = self.project / allow_plugins.ALLOWLIST_REL
        before = (config_path.read_bytes(), allow_path.read_bytes())
        plan = allow_plugins.build_plan(self.inventory(), [])
        config_path.chmod(0o600)
        with self.assertRaisesRegex(allow_plugins.AllowPluginsError, "changed after planning"):
            allow_plugins.apply_plan(plan, runtime_gate=self.runtime_ok)
        self.assertEqual((config_path.read_bytes(), allow_path.read_bytes()), before)
        self.assertEqual(stat.S_IMODE(config_path.stat().st_mode), 0o600)

    def test_apply_does_not_replace_allowlist_created_between_writes(self):
        plan = allow_plugins.build_plan(self.inventory(), [])
        config_path = self.project / allow_plugins.CONFIG_REL
        allow_path = self.project / allow_plugins.ALLOWLIST_REL
        external = b"schema_version = 99\n# external actor\n"
        original_write = allow_plugins._atomic_write
        writes = 0

        def create_allowlist_after_config(path, text, *, mode=None, expected=None):
            nonlocal writes
            result = original_write(path, text, mode=mode, expected=expected)
            writes += 1
            if writes == 1:
                allow_path.write_bytes(external)
            return result

        allow_plugins._atomic_write = create_allowlist_after_config
        try:
            with self.assertRaisesRegex(allow_plugins.AllowPluginsError, "rollback failed"):
                allow_plugins.apply_plan(plan, runtime_gate=self.runtime_ok)
        finally:
            allow_plugins._atomic_write = original_write
        self.assertFalse(config_path.exists())
        self.assertEqual(allow_path.read_bytes(), external)

    def test_apply_rejects_post_probe_managed_state_drift(self):
        plan = allow_plugins.build_plan(self.inventory(), [])
        config_path = self.project / allow_plugins.CONFIG_REL
        allow_path = self.project / allow_plugins.ALLOWLIST_REL

        def runtime_ok_then_remove_config(_plan):
            config_path.unlink()
            return self.runtime_ok(_plan)

        result = allow_plugins.apply_plan(plan, runtime_gate=runtime_ok_then_remove_config)
        self.assertEqual(result["status"], "rolled_back_runtime_mismatch")
        self.assertEqual(result["stage"], "post_probe_state")
        self.assertFalse(result["runtime_verified"])
        self.assertFalse(config_path.exists())
        self.assertFalse(allow_path.exists())

    def test_remove_preserves_preexisting_empty_or_whitespace_config_across_reapply(self):
        config_path = self.project / allow_plugins.CONFIG_REL
        allow_path = self.project / allow_plugins.ALLOWLIST_REL
        config_path.parent.mkdir()
        for original in (b"", b" \r\n\t"):
            with self.subTest(original=original):
                config_path.write_bytes(original)
                config_path.chmod(0o600)
                original_mode = stat.S_IMODE(config_path.stat().st_mode)
                first = allow_plugins.build_plan(self.inventory(), [])
                self.assertTrue(first["config_preexisting"])
                allow_plugins.apply_plan(first, runtime_gate=self.runtime_ok)
                update = allow_plugins.build_plan(self.inventory(), [])
                self.assertTrue(update["config_preexisting"])
                allow_plugins.apply_plan(update, runtime_gate=self.runtime_ok)
                allow_plugins.remove_state(self.project, True)
                self.assertTrue(config_path.exists())
                self.assertEqual(config_path.read_bytes(), original)
                self.assertEqual(stat.S_IMODE(config_path.stat().st_mode), original_mode)
                self.assertFalse(allow_path.exists())

    def test_remove_deletes_config_when_it_was_absent_before_apply(self):
        plan = allow_plugins.build_plan(self.inventory(), [])
        self.assertFalse(plan["config_preexisting"])
        allow_plugins.apply_plan(plan, runtime_gate=self.runtime_ok)
        update = allow_plugins.build_plan(self.inventory(), [])
        self.assertFalse(update["config_preexisting"])
        allow_plugins.apply_plan(update, runtime_gate=self.runtime_ok)
        allow_plugins.remove_state(self.project, True)
        self.assertFalse((self.project / allow_plugins.CONFIG_REL).exists())
        self.assertFalse((self.project / allow_plugins.ALLOWLIST_REL).exists())

    def test_old_allowlist_without_preexisting_metadata_fails_closed(self):
        plan = allow_plugins.build_plan(self.inventory(), [])
        config_path = self.project / allow_plugins.CONFIG_REL
        allow_path = self.project / allow_plugins.ALLOWLIST_REL
        config_path.parent.mkdir()
        config_path.write_text(plan["managed_block"] + "\n", encoding="utf-8")
        allow_path.write_text("schema_version = 1\nallowed_plugins = []\n", encoding="utf-8")
        with self.assertRaisesRegex(allow_plugins.AllowPluginsError, "config_preexisting metadata"):
            self.inventory()

    def test_full_posix_mode_bits_survive_apply_rollback_and_remove(self):
        config_path = self.project / allow_plugins.CONFIG_REL
        allow_path = self.project / allow_plugins.ALLOWLIST_REL
        config_path.parent.mkdir()
        config_path.write_bytes(b"[features]\nweb_search = true\n")
        config_path.chmod(0o2640)
        config_mode = stat.S_IMODE(config_path.stat().st_mode)
        plan = allow_plugins.build_plan(self.inventory(), [])
        allow_plugins.apply_plan(plan, runtime_gate=self.runtime_ok)
        self.assertEqual(stat.S_IMODE(config_path.stat().st_mode), config_mode)
        allow_path.chmod(0o2640)
        allow_mode = stat.S_IMODE(allow_path.stat().st_mode)

        update = allow_plugins.build_plan(self.inventory(), [])
        result = allow_plugins.apply_plan(update, runtime_gate=self.runtime_failure)
        self.assertEqual(result["status"], "rolled_back_runtime_mismatch")
        self.assertEqual(stat.S_IMODE(config_path.stat().st_mode), config_mode)
        self.assertEqual(stat.S_IMODE(allow_path.stat().st_mode), allow_mode)

        def fail_allow_unlink(path):
            if path == allow_path:
                raise OSError("allowlist unlink failed")
            return Path.unlink(path)

        with self.assertRaisesRegex(allow_plugins.AllowPluginsError, "managed files were restored"):
            allow_plugins.remove_state(self.project, True, unlink=fail_allow_unlink)
        self.assertEqual(stat.S_IMODE(config_path.stat().st_mode), config_mode)
        self.assertEqual(stat.S_IMODE(allow_path.stat().st_mode), allow_mode)

    def test_runtime_rollback_preserves_external_edit_after_apply(self):
        plan = allow_plugins.build_plan(self.inventory(), [])
        config_path = self.project / allow_plugins.CONFIG_REL
        external = b"[features]\nweb_search = true\n# external actor\n"

        def external_then_fail(_plan):
            config_path.write_bytes(external)
            return self.runtime_failure(_plan)

        result = allow_plugins.apply_plan(plan, runtime_gate=external_then_fail)
        self.assertEqual(result["status"], "rollback_failed_runtime_mismatch")
        self.assertFalse(result["rollback_restored"])
        self.assertEqual(
            result["rollback_conflicts"],
            [str(Path(plan["project"]) / allow_plugins.CONFIG_REL)],
        )
        self.assertEqual(config_path.read_bytes(), external)
        self.assertFalse((self.project / allow_plugins.ALLOWLIST_REL).exists())

    def test_remove_second_step_failure_restores_both_managed_files(self):
        plan = allow_plugins.build_plan(self.inventory(), [])
        allow_plugins.apply_plan(plan, runtime_gate=self.runtime_ok)
        config_path = self.project / allow_plugins.CONFIG_REL
        allow_path = self.project / allow_plugins.ALLOWLIST_REL
        config_path.chmod(0o600)
        allow_path.chmod(0o600)
        before = (config_path.read_bytes(), allow_path.read_bytes())

        def fail_allow_unlink(path):
            if path == allow_path:
                raise OSError("allowlist unlink failed")
            return Path.unlink(path)

        with self.assertRaisesRegex(allow_plugins.AllowPluginsError, "remove failed; managed files were restored"):
            allow_plugins.remove_state(self.project, True, unlink=fail_allow_unlink)
        self.assertEqual((config_path.read_bytes(), allow_path.read_bytes()), before)
        self.assertEqual(stat.S_IMODE(config_path.stat().st_mode), 0o600)
        self.assertEqual(stat.S_IMODE(allow_path.stat().st_mode), 0o600)

    def test_remove_rolls_back_keyboard_interrupt(self):
        plan = allow_plugins.build_plan(self.inventory(), [])
        allow_plugins.apply_plan(plan, runtime_gate=self.runtime_ok)
        config_path = self.project / allow_plugins.CONFIG_REL
        allow_path = self.project / allow_plugins.ALLOWLIST_REL
        before = (config_path.read_bytes(), allow_path.read_bytes())

        def interrupt_allow_unlink(path):
            if path == allow_path:
                raise KeyboardInterrupt()
            return Path.unlink(path)

        with self.assertRaises(KeyboardInterrupt):
            allow_plugins.remove_state(self.project, True, unlink=interrupt_allow_unlink)
        self.assertEqual((config_path.read_bytes(), allow_path.read_bytes()), before)

    def test_remove_rollback_preserves_external_edit(self):
        plan = allow_plugins.build_plan(self.inventory(), [])
        allow_plugins.apply_plan(plan, runtime_gate=self.runtime_ok)
        config_path = self.project / allow_plugins.CONFIG_REL
        allow_path = self.project / allow_plugins.ALLOWLIST_REL
        original_allow = allow_path.read_bytes()
        external = b"[features]\nweb_search = true\n# external actor\n"

        def external_then_fail(path):
            if path == allow_path:
                config_path.write_bytes(external)
                raise OSError("allowlist unlink failed")
            return Path.unlink(path)

        with self.assertRaisesRegex(allow_plugins.AllowPluginsError, "remove failed and rollback failed"):
            allow_plugins.remove_state(self.project, True, unlink=external_then_fail)
        self.assertEqual(config_path.read_bytes(), external)
        self.assertEqual(allow_path.read_bytes(), original_allow)

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


class SkillContractTest(AllowPluginsTest):
    def test_skill_is_explicit_only_and_has_no_sync_entrypoint(self):
        skill = (ROOT / "SKILL.md").read_text(encoding="utf-8")
        metadata = (ROOT / "agents" / "openai.yaml").read_text(encoding="utf-8")
        self.assertIn("$iysl-allow-plugins", skill)
        self.assertIn("native `.form-check` controls", skill)
        self.assertIn("window.openai.sendFollowUpMessage", skill)
        self.assertIn("not access control", skill)
        self.assertIn("Project Plugin Capability Profile", skill)
        self.assertIn("default-deny", skill)
        self.assertIn("CODEX_HOME", skill)
        self.assertIn("explicit apply confirmation", skill)
        self.assertIn("fail-closed preflight", skill)
        self.assertIn("second user-facing preview or confirmation", skill)
        self.assertIn("allow_implicit_invocation: false", metadata)
        self.assertNotIn("$iysl-allow-plugins sync", skill)


    def test_v2_app_policy_and_v1_migration_contract(self):
        manifest_path = self.plugin / ".codex-plugin" / "plugin.json"
        manifest = json.loads(manifest_path.read_text(encoding="utf-8")); manifest["apps"] = "./apps.json"
        manifest_path.write_text(json.dumps(manifest), encoding="utf-8")
        (self.plugin / "apps.json").write_text('{"apps":{"github":{"id":"github","required":true}}}')
        plan = allow_plugins.build_plan(self.inventory(), [])
        self.assertIn("[apps._default]", plan["managed_block"])
        self.assertIn('[apps."github"]\nenabled = false', plan["managed_block"])
        allow_plugins.apply_plan(plan, runtime_gate=self.runtime_ok)
        allow_path = self.project / allow_plugins.ALLOWLIST_REL
        allow_path.write_text("schema_version = 1\nconfig_preexisting = false\nallowed_plugins = []\n")
        self.assertEqual(allow_plugins.validate_state(self.inventory())["status"], "migration_required")

    def test_nonmac_and_desktop_requirement_are_injectable(self):
        original = allow_plugins.platform.system
        allow_plugins.platform.system = lambda: "Linux"
        try:
            self.assertEqual(allow_plugins.main(["inventory", "--project", str(self.project), "--global-config", str(self.global_config), "--plugin-list-json", str(self.plugin_list)]), 2)
        finally:
            allow_plugins.platform.system = original
        with self.assertRaisesRegex(allow_plugins.RuntimeProbeError, "desktop_required"):
            allow_plugins.discover_runtimes(desktop_path=self.root / "missing", which=lambda _name: None)

    def test_hook_check_silent_changed_and_read_only(self):
        plan = allow_plugins.build_plan(self.inventory(), [])
        allow_plugins.apply_plan(plan, runtime_gate=self.runtime_ok)
        original = allow_plugins._plugin_list
        allow_plugins._plugin_list = lambda _path, **_kwargs: [json.loads(self.plugin_list.read_text())["installed"][0]]
        try:
            before = allow_plugins._snapshot_managed_files(self.project)
            stream = io.StringIO()
            with redirect_stdout(stream):
                self.assertEqual(allow_plugins.hook_check(str(self.project), global_config=str(self.global_config)), 0)
            self.assertEqual(stream.getvalue(), "")
            self.assertEqual(allow_plugins._snapshot_managed_files(self.project), before)
            self.global_config.write_text(
                self.global_config.read_text(encoding="utf-8").replace("enabled = true", "enabled = false"),
                encoding="utf-8",
            )
            stream = io.StringIO()
            with redirect_stdout(stream):
                allow_plugins.hook_check(str(self.project), global_config=str(self.global_config))
            envelope = json.loads(stream.getvalue())
            self.assertIn("systemMessage", envelope)
            self.assertEqual(envelope["hookSpecificOutput"]["hookEventName"], "SessionStart")
            self.assertIn("additionalContext", envelope["hookSpecificOutput"])
            self.assertEqual(allow_plugins._snapshot_managed_files(self.project), before)
        finally:
            allow_plugins._plugin_list = original

    def test_hook_check_warns_when_managed_block_was_edited(self):
        plan = allow_plugins.build_plan(self.inventory(), [])
        allow_plugins.apply_plan(plan, runtime_gate=self.runtime_ok)
        config_path = self.project / allow_plugins.CONFIG_REL
        config_path.write_text(
            config_path.read_text(encoding="utf-8").replace(
                "enabled = false", "enabled = true", 1
            ),
            encoding="utf-8",
        )
        original = allow_plugins._plugin_list
        allow_plugins._plugin_list = lambda _path, **_kwargs: [
            json.loads(self.plugin_list.read_text())["installed"][0]
        ]
        try:
            stream = io.StringIO()
            with redirect_stdout(stream):
                allow_plugins.hook_check(
                    str(self.project), global_config=str(self.global_config)
                )
            self.assertIn("systemMessage", json.loads(stream.getvalue()))
        finally:
            allow_plugins._plugin_list = original

    def test_validate_reports_saved_fingerprint_drift_without_runtime_probe(self):
        plan = allow_plugins.build_plan(self.inventory(), [])
        allow_plugins.apply_plan(plan, runtime_gate=self.runtime_ok)
        skill = self.plugin / "skills" / "one" / "SKILL.md"
        skill.write_text(
            skill.read_text(encoding="utf-8") + "changed\n", encoding="utf-8"
        )
        result = allow_plugins.validate_state(
            self.inventory(),
            runtime_gate=lambda _plan: self.fail("runtime probe must not run on drift"),
        )
        self.assertEqual(result["status"], "capability_drift")
        self.assertFalse(result["runtime_verified"])

    def test_app_policy_helper_rejects_schema_and_shared_id_warns(self):
        with self.assertRaisesRegex(allow_plugins.RuntimeProbeError, "app_config_mismatch"):
            allow_plugins._effective_apps({"apps": {"_default": {"enabled": False}, "github": {"enabled": True}}}, [], ["github"])
        with self.assertRaisesRegex(allow_plugins.RuntimeProbeError, "app_schema"):
            allow_plugins._app_rows({"data": "bad", "nextCursor": None})
        inventory = self.inventory()
        alpha = inventory["plugins"][0]
        alpha["apps"] = [{"id": "github", "alias": "github"}]
        beta = dict(alpha, id="beta@market", name="beta", skills=[], mcp_servers=[], apps=[{"id": "github", "alias": "github"}])
        inventory["plugins"].append(beta)
        plan = allow_plugins.build_plan(inventory, ["alpha@market"])
        self.assertIn("shared app IDs selected and excluded", " ".join(plan["warnings"]))
        self.assertIn('[apps."github"]\nenabled = true', plan["managed_block"])

    def test_fingerprint_tracks_manifest_version_and_declared_capability_content(self):
        first = self.inventory()
        first_digest = first["plugins"][0]["capability_digests"]
        manifest_path = self.plugin / ".codex-plugin" / "plugin.json"
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        manifest["version"] = "2.0.0"
        manifest_path.write_text(json.dumps(manifest), encoding="utf-8")
        second = self.inventory()
        self.assertNotEqual(first_digest, second["plugins"][0]["capability_digests"])
        self.assertEqual(second["plugins"][0]["capability_digests"][0]["manifest_version"], "2.0.0")
        skill = self.plugin / "skills" / "one" / "SKILL.md"
        skill.write_text(skill.read_text(encoding="utf-8") + "changed\n", encoding="utf-8")
        self.assertNotEqual(
            allow_plugins._capability_fingerprint(second, "block"),
            allow_plugins._capability_fingerprint(self.inventory(), "block"),
        )

    def test_app_server_uses_thread_scoped_real_protocol_shapes(self):
        manifest_path = self.plugin / ".codex-plugin" / "plugin.json"
        manifest = json.loads(manifest_path.read_text(encoding="utf-8")); manifest["apps"] = "./apps.json"
        manifest_path.write_text(json.dumps(manifest), encoding="utf-8")
        (self.plugin / "apps.json").write_text('{"apps":{"github":{"id":"github"}}}', encoding="utf-8")
        plan = allow_plugins.build_plan(self.inventory(), [])
        responses = [
            {"id": 1, "result": {}}, {"id": 2, "result": {"thread": {"id": "thread-real"}}},
            {"id": 3, "result": {"apps": {"_default": {"enabled": False}, "github": {"enabled": False}}}},
            {"id": 4, "result": {"data": [{"id": "github", "isEnabled": False}], "nextCursor": None}},
            {"id": 5, "result": {"apps": [{"id": "github", "enabled": False, "callable": False}]}},
            {"id": 6, "result": {"data": [{"cwd": str(self.project.resolve()), "skills": [], "errors": []}]}},
            {"id": 7, "result": {"data": [], "nextCursor": None}},
        ]
        session = FakeAppServerSession(responses)
        result = allow_plugins.probe_runtime(self.runtime(), self.project, plan["runtime_targets"], plan=plan,
            session_factory=lambda *_: session, run_command=lambda *args, **kwargs: self.command_result([]))
        self.assertTrue(result["ok"])
        self.assertEqual(session.requests[3]["params"], {"threadId": "thread-real", "cursor": None, "limit": 100, "forceRefetch": False})
        self.assertEqual(session.requests[4]["params"], {"threadId": "thread-real", "forceRefresh": False})

    def test_hook_reconstructs_host_only_roots_and_warns_for_sibling_cache_version(self):
        host = self.root / "host-only"; (host / ".codex-plugin").mkdir(parents=True)
        (host / "skills" / "host").mkdir(parents=True)
        (host / "skills" / "host" / "SKILL.md").write_text("---\nname: host\ndescription: test\n---\n")
        (host / ".codex-plugin" / "plugin.json").write_text(json.dumps({"name": "host-only", "version": "1", "skills": "./skills"}))
        inventory = self.inventory(host_plugin=[f"host-only={host}"])
        host_id = next(item["id"] for item in inventory["plugins"] if "current_task" in item["sources"])
        plan = allow_plugins.build_plan(inventory, [host_id])
        allow_plugins.apply_plan(plan, runtime_gate=self.runtime_ok)
        saved = allow_plugins._load_allowlist(self.project)
        self.assertEqual(saved["host_plugins"], [f"host-only={host.resolve()}"])
        original = allow_plugins._plugin_list
        allow_plugins._plugin_list = lambda _path, **_kwargs: [json.loads(self.plugin_list.read_text())["installed"][0]]
        try:
            stream = io.StringIO()
            with redirect_stdout(stream): allow_plugins.hook_check(str(self.project), global_config=str(self.global_config))
            self.assertEqual(stream.getvalue(), "")
            # Match the host-only canonical catalog ID.  The normal records
            # path intentionally ignores this cache root; the independent
            # cache snapshot must still make SessionStart warn.
            sibling = self.root / "plugins" / "cache" / self.root.name / "host-only" / "2.0.0"
            (sibling / ".codex-plugin").mkdir(parents=True)
            (sibling / ".codex-plugin" / "plugin.json").write_text(json.dumps({"name": "host-only", "version": "2.0.0"}))
            stream = io.StringIO()
            with redirect_stdout(stream): allow_plugins.hook_check(str(self.project), global_config=str(self.global_config))
            self.assertIn("systemMessage", stream.getvalue())
        finally:
            allow_plugins._plugin_list = original

    def test_inventory_uses_injected_desktop_binary_not_path(self):
        desktop = self.root / "desktop-codex"; desktop.write_text("#!/bin/sh\n"); desktop.chmod(0o755)
        original = allow_plugins.subprocess.run; calls = []
        def runner(command, **kwargs):
            calls.append(command)
            return SimpleNamespace(returncode=0, stdout=self.plugin_list.read_text(), stderr="")
        allow_plugins.subprocess.run = runner
        try:
            inventory = allow_plugins.build_inventory(self.args(plugin_list_json=None, desktop_codex=str(desktop)))
        finally:
            allow_plugins.subprocess.run = original
        self.assertTrue(inventory["plugins"])
        self.assertEqual(calls[0], [str(desktop.resolve()), "plugin", "list", "--json"])
        plan = allow_plugins.build_plan(inventory, [])
        allow_plugins.apply_plan(plan, runtime_gate=self.runtime_ok)
        stream = io.StringIO()
        original = allow_plugins.subprocess.run
        allow_plugins.subprocess.run = runner
        try:
            with redirect_stdout(stream):
                allow_plugins.hook_check(str(self.project), global_config=str(self.global_config), desktop_codex=str(desktop))
        finally:
            allow_plugins.subprocess.run = original
        self.assertEqual(stream.getvalue(), "")

    def test_remove_sigterm_after_first_write_restores_exact_preimage(self):
        config = self.project / allow_plugins.CONFIG_REL; config.parent.mkdir()
        config.write_text("[features]\nweb_search = true\n", encoding="utf-8")
        plan = allow_plugins.build_plan(self.inventory(), [])
        allow_plugins.apply_plan(plan, runtime_gate=self.runtime_ok)
        before = allow_plugins._snapshot_managed_files(self.project)
        original = allow_plugins._atomic_write; writes = [0]
        def terminate(*args, **kwargs):
            original(*args, **kwargs); writes[0] += 1
            if writes[0] == 1: signal.getsignal(signal.SIGTERM)(signal.SIGTERM, None)
        allow_plugins._atomic_write = terminate
        try:
            with self.assertRaises(allow_plugins.TransactionTerminated):
                allow_plugins.remove_state(self.project, True)
        finally:
            allow_plugins._atomic_write = original
        self.assertEqual(allow_plugins._snapshot_managed_files(self.project), before)

    def test_remove_unexpected_exception_restores_exact_preimage(self):
        plan = allow_plugins.build_plan(self.inventory(), [])
        allow_plugins.apply_plan(plan, runtime_gate=self.runtime_ok)
        before = allow_plugins._snapshot_managed_files(self.project)
        with self.assertRaisesRegex(allow_plugins.AllowPluginsError, "managed files were restored"):
            allow_plugins.remove_state(self.project, True, unlink=lambda _path: (_ for _ in ()).throw(RuntimeError("unexpected")))
        self.assertEqual(allow_plugins._snapshot_managed_files(self.project), before)


if __name__ == "__main__":
    unittest.main()
