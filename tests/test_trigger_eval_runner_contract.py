from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def test_trigger_runner_is_manifest_driven_and_fails_missing_companions():
    body = (ROOT / "tools" / "verify-trigger-evals.sh").read_text(encoding="utf-8")
    assert "load_manifest" in body
    assert '"trigger" in entry.get("required_gates", [])' in body
    assert "missing required trigger cases" in body
    assert "missing required semantic config" in body
    assert "continue\n  fi" not in body
