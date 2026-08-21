#!/usr/bin/env python3
"""Audit installable skill packages without judging prose quality."""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

try:
    from tools.skill_manifest import parse_frontmatter
except ModuleNotFoundError:  # Direct `python tools/audit-skills.py` execution.
    from skill_manifest import parse_frontmatter


FRONTMATTER_RE = re.compile(r"\A---\n(.*?)\n---\n", re.DOTALL)
RESOURCE_RE = re.compile(
    r"(?<![A-Za-z0-9_./-])((?:references|scripts|assets|evals|templates|tests|reports)/[A-Za-z0-9_./-]+)"
)
HARD_DEP_RE = re.compile(
    r"\b(?:must|requires?|required to|必須(?:使用|呼叫|載入))\s+(?:use|run|invoke|load)?\s*[@$]([a-z][a-z0-9-]+)",
    re.IGNORECASE,
)


def frontmatter_body(path: Path) -> tuple[str, list[str]]:
    text = path.read_text(encoding="utf-8")
    match = FRONTMATTER_RE.match(text)
    if not match:
        return text, ["missing frontmatter"]
    return text[match.end() :], []


def audit_skill(skill_dir: Path, known_skills: set[str]) -> dict:
    skill_path = skill_dir / "SKILL.md"
    errors: list[str] = []
    warnings: list[str] = []
    if not skill_path.is_file():
        return {
            "name": skill_dir.name,
            "lines": 0,
            "characters": 0,
            "references": 0,
            "scripts": 0,
            "eval_cases": {"trigger": 0, "behavior": 0},
            "errors": ["missing SKILL.md"],
            "warnings": [],
        }

    body, frontmatter_errors = frontmatter_body(skill_path)
    errors.extend(frontmatter_errors)
    try:
        fields = parse_frontmatter(skill_path)
    except ValueError as exc:
        fields = {}
        errors.append(str(exc))
    if fields.get("name") != skill_dir.name:
        errors.append(f"frontmatter name is {fields.get('name', '<missing>')!r}")
    if not fields.get("description"):
        errors.append("missing frontmatter description")

    resources = sorted(set(RESOURCE_RE.findall(body)))
    missing_resources = [resource for resource in resources if not (skill_dir / resource).exists()]
    errors.extend(f"missing referenced resource: {resource}" for resource in missing_resources)

    hard_dependencies: set[str] = set()
    for match in HARD_DEP_RE.finditer(body):
        candidate = match.group(1)
        if candidate in {"the", "a", "an", "one", "this", "that", "it"}:
            continue
        if candidate not in known_skills:
            hard_dependencies.add(candidate)
    if hard_dependencies:
        errors.append("unavailable hard skill dependency: " + ", ".join(sorted(hard_dependencies)))

    scripts_dir = skill_dir / "scripts"
    script_count = sum(1 for path in scripts_dir.iterdir() if path.is_file()) if scripts_dir.is_dir() else 0
    if script_count and not fields.get("compatibility"):
        errors.append("runtime scripts require frontmatter compatibility")

    eval_dir = skill_dir / "evals"
    trigger_count = 0
    behavior_count = 0
    trigger_path = eval_dir / "trigger_cases.json"
    behavior_path = eval_dir / "behavior_cases.json"
    if trigger_path.is_file():
        try:
            trigger_data = json.loads(trigger_path.read_text(encoding="utf-8"))
            trigger_count = sum(
                len(trigger_data.get(key, []))
                for key in ("should_trigger", "should_not_trigger", "near_neighbor")
            )
        except (OSError, json.JSONDecodeError) as exc:
            errors.append(f"invalid trigger_cases.json: {exc}")
    if behavior_path.is_file():
        try:
            behavior_count = len(json.loads(behavior_path.read_text(encoding="utf-8")).get("cases", []))
        except (OSError, json.JSONDecodeError) as exc:
            errors.append(f"invalid behavior_cases.json: {exc}")

    text = skill_path.read_text(encoding="utf-8")
    return {
        "name": skill_dir.name,
        "lines": len(text.splitlines()),
        "characters": len(text),
        "references": sum(1 for path in (skill_dir / "references").iterdir() if path.is_file()) if (skill_dir / "references").is_dir() else 0,
        "scripts": script_count,
        "eval_cases": {"trigger": trigger_count, "behavior": behavior_count},
        "errors": errors,
        "warnings": warnings,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=Path(__file__).resolve().parents[1])
    parser.add_argument("--json", action="store_true", dest="as_json")
    parser.add_argument("--fail-on-error", action="store_true")
    args = parser.parse_args()

    skills_root = args.root / "skills"
    skill_dirs = sorted(path for path in skills_root.iterdir() if path.is_dir())
    known_skills = {path.name for path in skill_dirs}
    results = [audit_skill(path, known_skills) for path in skill_dirs]
    payload = {"root": str(args.root), "skills": results}

    if args.as_json:
        print(json.dumps(payload, ensure_ascii=False, indent=2))
    else:
        print("| Skill | Lines | Chars | References | Scripts | Trigger cases | Behavior cases | Status |")
        print("| --- | ---: | ---: | ---: | ---: | ---: | ---: | --- |")
        for result in results:
            eval_cases = result["eval_cases"]
            status = "error" if result["errors"] else "ok"
            print(
                f"| `{result['name']}` | {result['lines']} | {result['characters']} | "
                f"{result['references']} | {result['scripts']} | {eval_cases['trigger']} | "
                f"{eval_cases['behavior']} | {status} |"
            )
            for error in result["errors"]:
                print(f"  - ERROR `{result['name']}`: {error}")
            for warning in result["warnings"]:
                print(f"  - WARNING `{result['name']}`: {warning}")

    return 1 if args.fail_on_error and any(result["errors"] for result in results) else 0


if __name__ == "__main__":
    sys.exit(main())
