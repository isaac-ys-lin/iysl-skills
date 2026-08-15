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
        if not line or line[0].isspace() or ":" not in line:
            continue
        key, value = line.split(":", 1)
        key = key.strip()
        if key in values:
            raise ValueError(f"duplicate frontmatter key {key!r} in {path}")
        raw_value = value.strip()
        if key == "disable-model-invocation" and raw_value not in {"true", "false"}:
            raise ValueError(f"{key} must use canonical true or false in {path}")
        values[key] = raw_value.strip('"').strip("'")
    return values


def openai_policy(path: Path) -> dict[str, str]:
    """Read the small scalar interface and policy surface without YAML deps."""

    lines = path.read_text(encoding="utf-8").splitlines()
    values: dict[str, str] = {}
    section: str | None = None
    section_count: dict[str, int] = {}
    child_indent: dict[str, int] = {}
    wanted = {
        "interface": {"display_name"},
        "policy": {"allow_implicit_invocation"},
    }

    for line in lines:
        if not line.strip() or line.lstrip().startswith("#"):
            continue
        indent = len(line) - len(line.lstrip(" "))
        top_level = re.fullmatch(r"([A-Za-z0-9_-]+):\s*", line) if indent == 0 else None
        if top_level:
            section = top_level.group(1)
            section_count[section] = section_count.get(section, 0) + 1
            if section_count[section] > 1:
                raise ValueError(f"duplicate top-level section {section!r} in {path}")
            continue
        if section not in wanted or indent == 0:
            continue
        child_indent.setdefault(section, indent)
        if indent != child_indent[section]:
            continue
        match = re.fullmatch(r"\s*([A-Za-z0-9_-]+):\s*[\"']?([^\"']*?)[\"']?\s*", line)
        if not match or match.group(1) not in wanted[section]:
            continue
        key, value = match.group(1), match.group(2).strip()
        if key in values:
            raise ValueError(f"duplicate key {section}.{key} in {path}")
        if key == "allow_implicit_invocation":
            raw_scalar = line.split(":", 1)[1].strip()
            if raw_scalar not in {"true", "false"}:
                raise ValueError(
                    f"{section}.{key} must use canonical true or false in {path}"
                )
        values[key] = value
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
