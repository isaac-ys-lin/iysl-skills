"""Keep terminal plans out of the active plan directory."""

from pathlib import Path
import re


ROOT = Path(__file__).resolve().parents[1]
ACTIVE_PLANS = ROOT / "docs" / "plans"
ARCHIVE = ACTIVE_PLANS / "archive"
TERMINAL_STATUSES = frozenset(
    {"complete", "completed", "done", "archived", "abandoned", "superseded"}
)


def terminal_active_plans(root: Path = ROOT) -> list[Path]:
    """Return active root plans whose status says the lifecycle is terminal."""

    active = root / "docs" / "plans"
    terminal: list[Path] = []
    for path in sorted(active.glob("*.md")):
        text = path.read_text(encoding="utf-8")
        match = re.search(r"^Status:\s*([^\n#]+?)\s*$", text, re.MULTILINE | re.IGNORECASE)
        if match and match.group(1).strip().lower() in TERMINAL_STATUSES:
            terminal.append(path)
    return terminal


def test_active_plan_directory_contains_no_terminal_plans():
    assert terminal_active_plans() == []


def test_terminal_status_detector_rejects_completed_plan(tmp_path: Path):
    plans = tmp_path / "docs" / "plans"
    plans.mkdir(parents=True)
    completed = plans / "completed.md"
    completed.write_text("# Completed plan\n\nStatus: Complete\n", encoding="utf-8")
    assert terminal_active_plans(tmp_path) == [completed]


def test_terminal_status_detector_allows_active_plan(tmp_path: Path):
    plans = tmp_path / "docs" / "plans"
    plans.mkdir(parents=True)
    active = plans / "active.md"
    active.write_text("# Active plan\n\nStatus: In progress\n", encoding="utf-8")
    assert terminal_active_plans(tmp_path) == []


def test_completed_video_plans_are_archived():
    for filename in (
        "video-report-html-first.md",
        "video-report-local-asr.md",
    ):
        archived = ARCHIVE / filename
        assert archived.is_file()
        assert not (ACTIVE_PLANS / filename).exists()
