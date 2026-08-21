from pathlib import Path

import pytest

from tools.skill_manifest import (
    forked_skill_names,
    implicit_repo_skill_names,
    load_manifest,
    openai_policy,
    parse_frontmatter,
)


def test_openai_policy_reads_only_immediate_policy_children(tmp_path: Path):
    path = tmp_path / "openai.yaml"
    path.write_text(
        """interface:
  display_name: "Example"
  default_prompt: |
    allow_implicit_invocation: false
policy:
  allow_implicit_invocation: true
""",
        encoding="utf-8",
    )
    assert openai_policy(path) == {
        "display_name": "Example",
        "allow_implicit_invocation": "true",
    }


def test_openai_policy_rejects_duplicate_policy_sections(tmp_path: Path):
    path = tmp_path / "openai.yaml"
    path.write_text(
        """policy:
  allow_implicit_invocation: false
policy:
  allow_implicit_invocation: true
""",
        encoding="utf-8",
    )
    with pytest.raises(ValueError, match="duplicate top-level section"):
        openai_policy(path)


def test_openai_policy_rejects_quoted_boolean(tmp_path: Path):
    path = tmp_path / "openai.yaml"
    path.write_text(
        'policy:\n  allow_implicit_invocation: "false"\n',
        encoding="utf-8",
    )
    with pytest.raises(ValueError, match="canonical true or false"):
        openai_policy(path)


@pytest.mark.parametrize("value", ["True", '"true"', "yes"])
def test_frontmatter_rejects_noncanonical_disable_boolean(tmp_path: Path, value: str):
    path = tmp_path / "SKILL.md"
    path.write_text(
        f"---\nname: example\ndescription: Example\ndisable-model-invocation: {value}\n---\n",
        encoding="utf-8",
    )
    with pytest.raises(ValueError, match="canonical true or false"):
        parse_frontmatter(path)


def test_frontmatter_ignores_block_scalar_content_and_rejects_duplicate_keys(tmp_path: Path):
    path = tmp_path / "SKILL.md"
    path.write_text(
        """---
name: example
description: |
  disable-model-invocation: true
disable-model-invocation: false
---
""",
        encoding="utf-8",
    )
    assert parse_frontmatter(path)["disable-model-invocation"] == "false"

    path.write_text(
        """---
name: example
name: duplicate
description: Example
---
""",
        encoding="utf-8",
    )
    with pytest.raises(ValueError, match="duplicate frontmatter key"):
        parse_frontmatter(path)


def test_frontmatter_keeps_compatibility_authoritative_at_top_level(tmp_path: Path):
    path = tmp_path / "SKILL.md"
    path.write_text(
        """---
name: example
description: Example
metadata:
  compatibility: forged nested value
compatibility: Requires Python
---
""",
        encoding="utf-8",
    )
    metadata = parse_frontmatter(path)
    assert metadata["compatibility"] == "Requires Python"
    assert "metadata" in metadata
    assert "forged nested value" not in metadata.values()


def test_frontmatter_allows_top_level_yaml_comments(tmp_path: Path):
    path = tmp_path / "SKILL.md"
    path.write_text(
        "---\n# explanatory comment\nname: example\ndescription: Example\n---\n",
        encoding="utf-8",
    )
    assert parse_frontmatter(path)["name"] == "example"


def test_manifest_separates_maintainer_from_origin():
    manifest = load_manifest()
    assert forked_skill_names(manifest) == {"iysl-grill", "writing-great-skills"}
    assert implicit_repo_skill_names(manifest) == {
        name
        for name, entry in manifest["skills"].items()
        if entry["visibility"] == "implicit"
    }
    assert {entry["maintainer"] for entry in manifest["skills"].values()} == {"iysl"}
    assert {entry["origin"] for entry in manifest["skills"].values()} == {
        "original",
        "forked",
    }
