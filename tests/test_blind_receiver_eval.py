import json
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SKILL_DIR = ROOT / "skills" / "repo-research-packager"
SCRIPT = SKILL_DIR / "scripts" / "assemble_research_pack.py"
CASES = json.loads((SKILL_DIR / "evals" / "receiver_cases.json").read_text(encoding="utf-8"))["cases"]


def make_fixture(root: Path, case_id: str):
    repo = root / case_id
    (repo / "src").mkdir(parents=True)
    if case_id == "small-cli":
        files = {
            "README.md": "A small CLI has an entrypoint and validation tests.\n",
            "src/main.py": "def run(value):\n    return value\n",
        }
    elif case_id == "multi-module-app":
        files = {
            "README.md": "A multi-module app has state and failure behavior.\n",
            "src/app.py": "def module_flow(state):\n    return state\n",
        }
    else:
        files = {
            "README.md": "Safe evidence is selected; secret and generated files are excluded.\n",
            "src/app.py": "def safe_flow():\n    return 'open questions remain'\n",
            ".env": "TOKEN=ghp_ABCDEFGHIJKLMNOPQRSTUVWXYZ123456\n",
            "generated/build.js": "generated output\n",
        }
        (repo / "generated").mkdir()
    for relative, content in files.items():
        path = repo / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content, encoding="utf-8")
    return repo, files


def test_blind_receiver_evidence_covers_fixture_questions(tmp_path):
    for case in CASES:
        repo, files = make_fixture(tmp_path, case["id"])
        selected = [relative for relative in files if relative not in {".env", "generated/build.js"}]
        manifest = {
            "title": f"{case['id']} handoff",
            "objective": "讓看不到 repository 的 receiver 能回答固定問題。",
            "overview": ["Current behavior is grounded in selected evidence."],
            "architecture": [{"name": "Relevant architecture", "details": "Selected modules and entrypoint."}],
            "flows": [{"name": "Primary flow", "steps": ["Read selected source.", "Run the documented behavior."]}],
            "constraints": ["Excluded secrets and generated files."],
            "known_unknowns": ["External deployment state is not included."],
            "open_questions": case["receiver_questions"],
            "freshness_notes": ["Fixture is local and deterministic."],
            "max_chars": 20_000,
            "selections": [
                {"path": relative, "reason": "Ground-truth receiver evidence.", "mode": "full"}
                for relative in selected
            ],
        }
        manifest_path = tmp_path / f"{case['id']}.manifest.json"
        output = tmp_path / f"{case['id']}.md"
        manifest_path.write_text(json.dumps(manifest), encoding="utf-8")
        result = subprocess.run(
            [sys.executable, str(SCRIPT), "--repo", str(repo), "--manifest", str(manifest_path), "--output", str(output)],
            capture_output=True,
            text=True,
            check=False,
        )
        assert result.returncode == 0, result.stderr
        body = output.read_text(encoding="utf-8").lower()
        for term in case["ground_truth_terms"]:
            assert term.lower() in body
        assert str(tmp_path) not in body
        assert "ghp_abcdefghijklmnopqrstuvwxyz123456" not in body
        assert "generated/build.js" not in body
