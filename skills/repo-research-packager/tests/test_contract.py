import json
import os
import subprocess
import sys
from pathlib import Path


SKILL_DIR = Path(__file__).resolve().parents[1]
SCRIPT = SKILL_DIR / "scripts" / "assemble_research_pack.py"


def write_manifest(tmp_path, selection, **overrides):
    manifest = {
        "title": "測試研究包",
        "objective": "向另一個 AI 說明選取的行為。",
        "overview": ["這是一個精簡的測試 repository。"],
        "architecture": [{"name": "核心", "details": "包含一個小型模組。"}],
        "flows": [{"name": "執行", "steps": ["讀取輸入。", "回傳輸出。"]}],
        "constraints": ["不可捏造缺少的行為。"],
        "known_unknowns": ["無法取得外部部署狀態。"],
        "open_questions": ["還缺少哪些證據？"],
        "freshness_notes": ["時效性外部事實必須另外查核。"],
        "max_chars": 20_000,
        "selections": [selection],
    }
    manifest.update(overrides)
    path = tmp_path / "manifest.json"
    path.write_text(json.dumps(manifest), encoding="utf-8")
    return path


def run_assembler(repo, manifest, output, *extra):
    env = os.environ.copy()
    env["PYTHONDONTWRITEBYTECODE"] = "1"
    return subprocess.run(
        [
            sys.executable,
            str(SCRIPT),
            "--repo",
            str(repo),
            "--manifest",
            str(manifest),
            "--output",
            str(output),
            *extra,
        ],
        capture_output=True,
        text=True,
        env=env,
        check=False,
    )


def run_template():
    env = os.environ.copy()
    env["PYTHONDONTWRITEBYTECODE"] = "1"
    return subprocess.run(
        [sys.executable, str(SCRIPT), "--print-template"],
        capture_output=True,
        text=True,
        env=env,
        check=False,
    )


def run_without_arguments():
    env = os.environ.copy()
    env["PYTHONDONTWRITEBYTECODE"] = "1"
    return subprocess.run(
        [sys.executable, str(SCRIPT)],
        capture_output=True,
        text=True,
        env=env,
        check=False,
    )


def fixture_repo(tmp_path):
    repo = tmp_path / "repo"
    source = repo / "src"
    source.mkdir(parents=True)
    (source / "main.py").write_text(
        "def run(value):\n"
        "    if value is None:\n"
        "        raise ValueError('missing value')\n"
        "    return value\n",
        encoding="utf-8",
    )
    return repo


def test_print_template_is_valid_chinese_manifest():
    result = run_template()

    assert result.returncode == 0, result.stderr
    manifest = json.loads(result.stdout)
    assert manifest["output_language"] == "zh-Hant-TW"
    assert manifest["title"] == "專案研究包"
    assert manifest["objective"]
    assert manifest["max_chars"] == 240_000
    assert manifest["selections"][0]["mode"] == "full"
    assert manifest["selections"][1]["lines"] == [[40, 130], [420, 500]]


def test_packaging_arguments_remain_required():
    result = run_without_arguments()

    assert result.returncode == 2
    assert "--repo, --manifest, and --output are required" in result.stderr


def test_successful_pack_is_self_contained_and_relative(tmp_path):
    repo = fixture_repo(tmp_path)
    manifest = write_manifest(
        tmp_path,
        {
            "path": "src/main.py",
            "reason": "定義完整的測試行為。",
            "lines": [[1, 4]],
        },
    )
    output = tmp_path / "pack.md"

    result = run_assembler(repo, manifest, output)

    assert result.returncode == 0, result.stderr
    body = output.read_text(encoding="utf-8")
    assert "# 測試研究包" in body
    assert "## 證據索引" in body
    assert "src/main.py" in body
    assert "### 第 1–4 行" in body
    assert "## Evidence index" not in body
    assert str(tmp_path) not in body


def test_english_output_requires_explicit_request(tmp_path):
    repo = fixture_repo(tmp_path)
    manifest = write_manifest(
        tmp_path,
        {
            "path": "src/main.py",
            "reason": "Defines the fixture behavior.",
            "mode": "full",
        },
        output_language="en",
    )
    output = tmp_path / "pack.md"

    result = run_assembler(repo, manifest, output)

    assert result.returncode == 0, result.stderr
    body = output.read_text(encoding="utf-8")
    assert "## Evidence index" in body
    assert "## 證據索引" not in body


def test_absolute_and_out_of_repo_selections_fail_closed(tmp_path):
    repo = fixture_repo(tmp_path)
    outside = tmp_path / "outside.py"
    outside.write_text("print('outside')\n", encoding="utf-8")
    output = tmp_path / "pack.md"

    absolute_manifest = write_manifest(
        tmp_path,
        {"path": str(outside), "reason": "Must be rejected.", "mode": "full"},
    )
    result = run_assembler(repo, absolute_manifest, output)
    assert result.returncode == 2
    assert not output.exists()

    escape_manifest = write_manifest(
        tmp_path,
        {"path": "../outside.py", "reason": "Must be rejected.", "mode": "full"},
    )
    result = run_assembler(repo, escape_manifest, output)
    assert result.returncode == 2
    assert not output.exists()


def test_boolean_line_range_and_apple_private_key_path_are_rejected(tmp_path):
    repo = fixture_repo(tmp_path)
    output = tmp_path / "pack.md"
    boolean_manifest = write_manifest(
        tmp_path,
        {
            "path": "src/main.py",
            "reason": "Boolean is not a line number.",
            "lines": [[True, 1]],
        },
    )

    result = run_assembler(repo, boolean_manifest, output)
    assert result.returncode == 2
    assert "Invalid line range" in result.stderr
    assert not output.exists()

    auth_key = repo / "AuthKey_TEST.p8"
    auth_key.write_text("placeholder\n", encoding="utf-8")
    private_key_manifest = write_manifest(
        tmp_path,
        {
            "path": "AuthKey_TEST.p8",
            "reason": "Signing material must be rejected.",
            "mode": "full",
        },
    )
    result = run_assembler(repo, private_key_manifest, output)
    assert result.returncode == 2
    assert "Credential or signing file" in result.stderr
    assert not output.exists()


def test_secret_content_and_home_path_leak_are_rejected(tmp_path):
    repo = fixture_repo(tmp_path)
    output = tmp_path / "pack.md"
    secret = repo / "src" / "token.txt"
    secret.write_text("token=ghp_ABCDEFGHIJKLMNOPQRSTUVWXYZ123456\n", encoding="utf-8")
    secret_manifest = write_manifest(
        tmp_path,
        {
            "path": "src/token.txt",
            "reason": "High-confidence token must be rejected.",
            "mode": "full",
        },
    )

    result = run_assembler(repo, secret_manifest, output)
    assert result.returncode == 2
    assert "secret pattern" in result.stderr
    assert not output.exists()

    safe_selection = {
        "path": "src/main.py",
        "reason": "Defines the fixture behavior.",
        "mode": "full",
    }
    home_manifest = write_manifest(
        tmp_path,
        safe_selection,
        overview=[f"Leaked local path: {Path.home()}/private"],
    )
    result = run_assembler(repo, home_manifest, output)
    assert result.returncode == 2
    assert "home-directory path" in result.stderr
    assert not output.exists()


def test_budget_and_overwrite_require_explicit_resolution(tmp_path):
    repo = fixture_repo(tmp_path)
    selection = {
        "path": "src/main.py",
        "reason": "Defines the fixture behavior.",
        "mode": "full",
    }
    output = tmp_path / "pack.md"
    manifest = write_manifest(tmp_path, selection)

    first = run_assembler(repo, manifest, output)
    assert first.returncode == 0, first.stderr

    second = run_assembler(repo, manifest, output)
    assert second.returncode == 2
    assert "already exists" in second.stderr

    forced = run_assembler(repo, manifest, output, "--force")
    assert forced.returncode == 0, forced.stderr

    output.unlink()
    oversized = write_manifest(
        tmp_path,
        selection,
        overview=["x" * 20_000],
        max_chars=10_000,
    )
    result = run_assembler(repo, oversized, output)
    assert result.returncode == 2
    assert "exceeding max_chars" in result.stderr
    assert not output.exists()
