"""Shared manifest and SKILL.md metadata helpers for repository gates."""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
MANIFEST_PATH = ROOT / "skills-manifest.json"


def load_manifest(root: Path = ROOT) -> dict[str, Any]:
    """Load the repository's single skill inventory manifest."""

    path = root / "skills-manifest.json"
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict) or not isinstance(payload.get("skills"), dict):
        raise ValueError(f"invalid skill manifest: {path}")
    return payload


def parse_frontmatter(path: Path) -> dict[str, str]:
    """Parse the scalar frontmatter used by SKILL.md without extra dependencies."""

    text = path.read_text(encoding="utf-8")
    if not text.startswith("---\n") or "\n---\n" not in text[4:]:
        return {}
    raw = text[4 : text.index("\n---\n", 4)]
    values: dict[str, str] = {}
    for line in raw.splitlines():
        if ":" not in line:
            continue
        key, value = line.split(":", 1)
        values[key.strip()] = value.strip().strip('"').strip("'")
    return values


def openai_policy(path: Path) -> dict[str, str]:
    """Read the small scalar policy surface in agents/openai.yaml."""

    text = path.read_text(encoding="utf-8")
    values: dict[str, str] = {}
    for key in ("display_name", "allow_implicit_invocation"):
        match = re.search(rf"^\s*{re.escape(key)}:\s*[\"']?([^\"'\n]+?)[\"']?\s*$", text, re.MULTILINE)
        if match:
            values[key] = match.group(1).strip()
    return values


def repo_skill_names(manifest: dict[str, Any]) -> set[str]:
    return {
        name
        for name, entry in manifest["skills"].items()
        if entry.get("ownership") == "repo"
    }


def implicit_repo_skill_names(manifest: dict[str, Any]) -> set[str]:
    return {
        name
        for name, entry in manifest["skills"].items()
        if entry.get("ownership") == "repo"
        and entry.get("visibility") == "implicit"
    }


def third_party_skill_names(manifest: dict[str, Any]) -> set[str]:
    return {
        name
        for name, entry in manifest["skills"].items()
        if entry.get("ownership") == "third_party"
    }
