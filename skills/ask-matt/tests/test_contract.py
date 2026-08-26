import json
import re
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
RENDERER = ROOT / "scripts" / "render_flow_map.py"
MAP = ROOT / "assets" / "flow-map.json"

sys.dont_write_bytecode = True
sys.path.insert(0, str(ROOT / "scripts"))
import render_flow_map  # noqa: E402


def run(*args: str) -> subprocess.CompletedProcess:
    return subprocess.run(
        [sys.executable, str(RENDERER), *args],
        capture_output=True,
        text=True,
        check=False,
    )


class AskMattContractTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.skill = (ROOT / "SKILL.md").read_text(encoding="utf-8")
        cls.openai = (ROOT / "agents" / "openai.yaml").read_text(encoding="utf-8")
        cls.upstream = (ROOT / "UPSTREAM.md").read_text(encoding="utf-8")
        cls.map = json.loads(MAP.read_text(encoding="utf-8"))

    def test_name_matches_directory_and_invocation_is_explicit(self):
        match = re.search(r"^name:\s*([a-z0-9-]+)$", self.skill, re.MULTILINE)
        self.assertIsNotNone(match)
        self.assertEqual(match.group(1), ROOT.name)
        self.assertIn('display_name: "ask-matt"', self.openai)
        self.assertIn("disable-model-invocation: true", self.skill)
        self.assertIn("allow_implicit_invocation: false", self.openai)

    def test_upstream_snapshot_is_pinned(self):
        self.assertIn("https://github.com/mattpocock/skills", self.upstream)
        self.assertRegex(self.upstream, r"Snapshot commit: `[0-9a-f]{40}`")

    def test_routing_contract_is_complete(self):
        text = re.sub(r"\s+", " ", self.skill)
        for phrase in (
            "single source of the map",
            "Route only",
            "Establish the starting point before naming a route",
            "ruled-out neighbours",
            "--check` must pass before any HTML is delivered",
            "OS temp directory",
        ):
            self.assertIn(phrase, text)

    def test_declared_resources_exist(self):
        for rel in ("assets/flow-map.json", "scripts/render_flow_map.py", "references/phase-boundaries.md"):
            self.assertIn(rel, self.skill)
            self.assertTrue((ROOT / rel).is_file(), rel)

    def test_map_covers_every_lane_and_passes_check(self):
        lanes = {lane["id"] for lane in self.map["lanes"]}
        self.assertEqual(
            lanes,
            {"main", "onramp", "health", "vocabulary", "standalone", "precondition"},
        )
        self.assertEqual(lanes, {node["lane"] for node in self.map["nodes"]})
        self.assertEqual(run("--check").returncode, 0)

    def test_check_rejects_a_dangling_reference(self):
        broken = dict(self.map)
        broken["edges"] = self.map["edges"] + [{"from": "implement", "to": "nope", "kind": "flow"}]
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "flow-map.json"
            path.write_text(json.dumps(broken, ensure_ascii=False), encoding="utf-8")
            with self.assertRaises(render_flow_map.MapError):
                render_flow_map.check_map(broken, ROOT)
            result = run("--map", str(path), "--check")
        self.assertEqual(result.returncode, 1)
        self.assertIn("unknown node nope", result.stderr)

    def test_check_rejects_an_answer_with_an_unknown_node_or_empty_reason(self):
        nodes = render_flow_map.check_map(self.map, ROOT)
        for answer in (
            {"situation": "x", "route": [{"node": "nope", "why": "y"}]},
            {"situation": "x", "route": [{"node": "implement", "why": " "}]},
            {"situation": " ", "route": [{"node": "implement", "why": "y"}]},
            {"situation": "x", "route": []},
        ):
            with self.assertRaises(render_flow_map.MapError):
                render_flow_map.check_answer(answer, nodes)

    def test_render_is_self_contained_and_highlights_the_route(self):
        answer = {
            "situation": "跨工作階段的功能建置。",
            "route": [
                {"node": "grill-with-docs", "why": "先問清楚。"},
                {"node": "to-spec", "why": "收斂成規格。"},
            ],
            "excluded": [{"node": "wayfinder", "why": "方向已經清楚。"}],
            "notes": ["到 /to-tickets 之前不要 compact。"],
        }
        with tempfile.TemporaryDirectory() as tmp:
            answer_path = Path(tmp) / "answer.json"
            out = Path(tmp) / "map.html"
            answer_path.write_text(json.dumps(answer, ensure_ascii=False), encoding="utf-8")
            self.assertEqual(run("--answer", str(answer_path), "--out", str(out)).returncode, 0)
            html = out.read_text(encoding="utf-8")

        self.assertNotRegex(html, r"(src|href)=\"https?://")
        self.assertIn('lang="zh-Hant"', html)
        self.assertIn('class="card on-route" id="node-grill-with-docs"', html)
        self.assertIn('class="card on-route" id="node-to-spec"', html)
        self.assertNotIn('class="card on-route" id="node-wayfinder"', html)
        for node in self.map["nodes"]:
            self.assertIn(f'id="node-{node["id"]}"', html)

    def test_render_without_an_answer_has_no_route_panel(self):
        with tempfile.TemporaryDirectory() as tmp:
            out = Path(tmp) / "map.html"
            self.assertEqual(run("--out", str(out)).returncode, 0)
            html = out.read_text(encoding="utf-8")
        self.assertNotIn('<section class="route-panel">', html)
        self.assertNotIn('class="card on-route"', html)
        self.assertNotIn('class="chip on-route"', html)


if __name__ == "__main__":
    unittest.main()
