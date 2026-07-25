#!/usr/bin/env python3
"""Assemble a curated repository research pack from a JSON manifest."""

from __future__ import annotations

import argparse
import datetime as dt
import json
import re
import subprocess
import sys
from collections import Counter
from pathlib import Path
from typing import Any


RISKY_COMPONENTS = {
    ".env",
    ".aws",
    ".ssh",
    "credentials",
    "credential",
    "secrets",
    "secret",
    "private",
}

RISKY_SUFFIXES = {
    ".cer",
    ".der",
    ".key",
    ".mobileprovision",
    ".p8",
    ".p12",
    ".pem",
    ".pfx",
}

SECRET_PATTERNS = [
    re.compile(r"-----BEGIN (?:RSA |OPENSSH |EC )?PRIVATE KEY-----"),
    re.compile(r"\bAKIA[0-9A-Z]{16}\b"),
    re.compile(r"\bgh[pousr]_[A-Za-z0-9]{20,}\b"),
    re.compile(r"\bsk-[A-Za-z0-9_-]{20,}\b"),
    re.compile(r"\bAIza[0-9A-Za-z_-]{30,}\b"),
]

LANGUAGES = {
    ".c": "c",
    ".cc": "cpp",
    ".cpp": "cpp",
    ".css": "css",
    ".go": "go",
    ".h": "c",
    ".hpp": "cpp",
    ".html": "html",
    ".java": "java",
    ".js": "javascript",
    ".json": "json",
    ".kt": "kotlin",
    ".kts": "kotlin",
    ".md": "markdown",
    ".mjs": "javascript",
    ".mm": "objective-cpp",
    ".py": "python",
    ".rb": "ruby",
    ".rs": "rust",
    ".sh": "bash",
    ".sql": "sql",
    ".swift": "swift",
    ".toml": "toml",
    ".ts": "typescript",
    ".tsx": "tsx",
    ".xml": "xml",
    ".yaml": "yaml",
    ".yml": "yaml",
}

GENERATED_DIRS = {
    ".build",
    ".git",
    ".next",
    ".swiftpm",
    "DerivedData",
    "Pods",
    "build",
    "coverage",
    "dist",
    "node_modules",
    "output",
    "outputs",
    "tmp",
    "vendor",
}

TEXTS = {
    "zh-Hant-TW": {
        "handoff_note": (
            "> 這是一份提供給無法存取本機 repository 之 AI 的精選唯讀交接包。"
            "請以內嵌原始碼為證據，區分目前行為與候選方案；證據不足時應指出缺口，"
            "不要自行猜測。"
        ),
        "research_objective": "研究目標",
        "audience_scope": "對象與範圍",
        "audience": "對象",
        "scope": "範圍",
        "default_audience": "無法存取本機 repository 的外部 AI",
        "default_scope": "本研究包所代表的目前 repository 狀態",
        "repository_state": "Repository 狀態",
        "executive_orientation": "專案導讀",
        "architecture": "架構",
        "important_flows": "重要流程",
        "constraints": "限制與不可破壞條件",
        "known_unknowns": "已知未知事項",
        "open_questions": "開放式研究問題",
        "freshness": "時效性與外部查核",
        "repository_shape": "Repository 結構摘要",
        "evidence_index": "證據索引",
        "embedded_evidence": "內嵌 Repository 證據",
        "path": "路徑",
        "included_scope": "內嵌範圍",
        "why_it_matters": "重要性",
        "file": "檔案",
        "why_selected": "選取原因",
        "lines": "第 {start}–{end} 行",
        "full_file": "完整檔案",
        "range_lines": "第 {start}–{end} 行",
        "none_stated": "未列出。",
        "not_provided": "未提供。",
        "tracked_files": "追蹤或找到的檔案",
        "top_level_shape": "頂層結構",
        "file_count": "{count} 個檔案",
        "root_files": "根目錄檔案",
        "and_more": "，另有 {count} 個",
        "selected_evidence": "已選證據",
        "generated": "產生時間",
        "repository": "Repository",
        "branch": "Branch",
        "head": "HEAD",
        "working_tree": "Working tree",
        "tracked_changes": "{count} 個 tracked change",
        "untracked_paths": "{count} 個 untracked path",
        "detached": "detached 或無法取得",
        "unavailable": "無法取得",
        "wrote": "已寫入",
        "characters": "字元數",
        "estimated_tokens": "估計 token 數",
        "selections": "選取項目",
    },
    "en": {
        "handoff_note": (
            "> This is a curated, read-only repository handoff for an AI that does not "
            "have local repository access. Treat embedded source as evidence, distinguish "
            "current behavior from proposals, and identify missing evidence instead of guessing."
        ),
        "research_objective": "Research objective",
        "audience_scope": "Audience and scope",
        "audience": "Audience",
        "scope": "Scope",
        "default_audience": "External AI with no repository access",
        "default_scope": "Current repository state represented by this pack",
        "repository_state": "Repository state",
        "executive_orientation": "Executive orientation",
        "architecture": "Architecture",
        "important_flows": "Important flows",
        "constraints": "Constraints and invariants",
        "known_unknowns": "Known unknowns",
        "open_questions": "Open research questions",
        "freshness": "Freshness and external verification",
        "repository_shape": "Repository shape",
        "evidence_index": "Evidence index",
        "embedded_evidence": "Embedded repository evidence",
        "path": "Path",
        "included_scope": "Included scope",
        "why_it_matters": "Why it matters",
        "file": "File",
        "why_selected": "Why selected",
        "lines": "Lines {start}–{end}",
        "full_file": "full file",
        "range_lines": "lines {start}-{end}",
        "none_stated": "None stated.",
        "not_provided": "Not provided.",
        "tracked_files": "Tracked or discovered files",
        "top_level_shape": "Top-level shape",
        "file_count": "{count} files",
        "root_files": "Root files",
        "and_more": ", and {count} more",
        "selected_evidence": "Selected evidence",
        "generated": "Generated",
        "repository": "Repository",
        "branch": "Branch",
        "head": "HEAD",
        "working_tree": "Working tree",
        "tracked_changes": "{count} tracked change(s)",
        "untracked_paths": "{count} untracked path(s)",
        "detached": "detached or unavailable",
        "unavailable": "unavailable",
        "wrote": "Wrote",
        "characters": "Characters",
        "estimated_tokens": "Estimated tokens",
        "selections": "Selections",
    },
}

MANIFEST_TEMPLATE = {
    "output_language": "zh-Hant-TW",
    "title": "專案研究包",
    "objective": "說明目前基準，並研究需要回答的產品或技術問題。",
    "audience": "無法存取本機 repository 的外部 AI",
    "scope": "本次研究涵蓋的版本、子系統與明確排除項目。",
    "overview": [
        "用精簡段落說明產品、使用者價值與這次研究的重要性。"
    ],
    "architecture": [
        {
            "name": "主要系統邊界",
            "details": "說明與研究問題直接相關的元件與責任。",
        }
    ],
    "flows": [
        {
            "name": "主要執行流程",
            "steps": [
                "輸入如何進入系統。",
                "狀態如何處理與持久化。",
                "輸出如何被使用。",
            ],
        }
    ],
    "constraints": ["不可破壞的產品、相容性、隱私或安全邊界。"],
    "known_unknowns": ["Repository 或現有證據無法證明的事項。"],
    "open_questions": ["希望接收 AI 開放研究與回答的問題。"],
    "freshness_notes": ["需要從第一方來源重新查核的時效性外部事實。"],
    "max_chars": 240000,
    "selections": [
        {
            "path": "README.md",
            "reason": "選取此檔案的證據理由。",
            "mode": "full",
        },
        {
            "path": "src/large-file.swift",
            "reason": "選取這些行的證據理由。",
            "lines": [[40, 130], [420, 500]],
        },
    ],
}


class PackError(RuntimeError):
    pass


def run_git(repo: Path, *args: str) -> str | None:
    result = subprocess.run(
        ["git", "-C", str(repo), *args],
        capture_output=True,
        text=True,
        check=False,
    )
    if result.returncode != 0:
        return None
    return result.stdout.rstrip("\n")


def repository_root(candidate: Path) -> Path:
    candidate = candidate.expanduser().resolve()
    if not candidate.is_dir():
        raise PackError(f"Repository path is not a directory: {candidate}")
    root = run_git(candidate, "rev-parse", "--show-toplevel")
    return Path(root).resolve() if root else candidate


def load_manifest(path: Path) -> dict[str, Any]:
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise PackError(f"Cannot read manifest: {exc}") from exc
    if not isinstance(data, dict):
        raise PackError("Manifest root must be a JSON object")
    for key in ("title", "objective", "selections"):
        if key not in data:
            raise PackError(f"Manifest is missing required key: {key}")
    if not isinstance(data["selections"], list) or not data["selections"]:
        raise PackError("Manifest selections must be a non-empty array")
    return data


def safe_relative_path(repo: Path, raw: str) -> tuple[Path, str]:
    if not isinstance(raw, str) or not raw.strip():
        raise PackError("Selection path must be a non-empty string")
    supplied = Path(raw)
    if supplied.is_absolute():
        raise PackError(f"Selection paths must be repository-relative: {raw}")
    resolved = (repo / supplied).resolve()
    try:
        relative = resolved.relative_to(repo)
    except ValueError as exc:
        raise PackError(f"Selection escapes repository: {raw}") from exc
    if not resolved.is_file():
        raise PackError(f"Selected file does not exist: {relative.as_posix()}")
    return resolved, relative.as_posix()


def reject_risky_path(relative: str) -> None:
    path = Path(relative)
    lowered = {part.lower() for part in path.parts}
    if lowered & RISKY_COMPONENTS:
        raise PackError(f"Risky path is not allowed in a research pack: {relative}")
    if path.name.lower().startswith(".env"):
        raise PackError(f"Environment files are not allowed: {relative}")
    if path.suffix.lower() in RISKY_SUFFIXES:
        raise PackError(f"Credential or signing file is not allowed: {relative}")
    if path.name.lower() in {"id_rsa", "id_ed25519", "known_hosts"}:
        raise PackError(f"SSH material is not allowed: {relative}")


def read_text(path: Path, relative: str) -> str:
    try:
        raw = path.read_bytes()
    except OSError as exc:
        raise PackError(f"Cannot read {relative}: {exc}") from exc
    if len(raw) > 1_000_000:
        raise PackError(f"Selected file exceeds 1 MB; use line slices or omit it: {relative}")
    if b"\x00" in raw[:8192]:
        raise PackError(f"Binary file is not allowed: {relative}")
    try:
        text = raw.decode("utf-8")
    except UnicodeDecodeError as exc:
        raise PackError(f"Selected file is not valid UTF-8: {relative}") from exc
    for pattern in SECRET_PATTERNS:
        match = pattern.search(text)
        if match:
            line = text.count("\n", 0, match.start()) + 1
            raise PackError(
                f"High-confidence secret pattern detected in {relative}:{line}; "
                "remove or replace this selection"
            )
    return text


def line_slices(text: str, ranges: Any, relative: str) -> list[tuple[int, int, str]]:
    if not isinstance(ranges, list) or not ranges:
        raise PackError(f"lines must be a non-empty array for {relative}")
    lines = text.splitlines(keepends=True)
    output: list[tuple[int, int, str]] = []
    previous_end = 0
    for item in ranges:
        if (
            not isinstance(item, list)
            or len(item) != 2
            or not all(isinstance(value, int) and not isinstance(value, bool) for value in item)
        ):
            raise PackError(f"Invalid line range for {relative}: {item!r}")
        start, end = item
        if start < 1 or end < start or end > len(lines):
            raise PackError(
                f"Line range {start}-{end} is outside {relative} (1-{len(lines)})"
            )
        if start <= previous_end:
            raise PackError(f"Line ranges overlap or are unsorted for {relative}")
        output.append((start, end, "".join(lines[start - 1 : end])))
        previous_end = end
    return output


def tracked_files(repo: Path) -> list[str]:
    listed = run_git(repo, "ls-files", "-z")
    if listed is not None:
        return sorted(
            item
            for item in listed.split("\0")
            if item and not any(part in GENERATED_DIRS for part in Path(item).parts)
        )
    results: list[str] = []
    for path in repo.rglob("*"):
        if not path.is_file():
            continue
        relative = path.relative_to(repo)
        if any(part in GENERATED_DIRS for part in relative.parts):
            continue
        results.append(relative.as_posix())
    return sorted(results)


def repository_shape(paths: list[str], selected: list[str], texts: dict[str, str]) -> str:
    root_files: list[str] = []
    top_counts: Counter[str] = Counter()
    for item in paths:
        parts = Path(item).parts
        if len(parts) == 1:
            root_files.append(item)
        else:
            top_counts[parts[0]] += 1
    lines = [
        f"- {texts['tracked_files']}: {len(paths)}",
        f"- {texts['top_level_shape']}:",
    ]
    for name, count in sorted(top_counts.items()):
        lines.append(f"  - `{name}/` — {texts['file_count'].format(count=count)}")
    if root_files:
        shown = ", ".join(f"`{name}`" for name in sorted(root_files)[:30])
        suffix = (
            ""
            if len(root_files) <= 30
            else texts["and_more"].format(count=len(root_files) - 30)
        )
        lines.append(f"- {texts['root_files']}: {shown}{suffix}")
    lines.append(f"- {texts['selected_evidence']}:")
    lines.extend(f"  - `{path}`" for path in selected)
    return "\n".join(lines)


def git_metadata(repo: Path, texts: dict[str, str]) -> list[str]:
    branch = run_git(repo, "branch", "--show-current") or f"({texts['detached']})"
    head = run_git(repo, "rev-parse", "HEAD") or f"({texts['unavailable']})"
    status = run_git(repo, "status", "--porcelain")
    modified = untracked = 0
    if status:
        rows = status.splitlines()
        untracked = sum(1 for row in rows if row.startswith("??"))
        modified = len(rows) - untracked
    return [
        f"- {texts['generated']}: {dt.datetime.now().astimezone().isoformat(timespec='seconds')}",
        f"- {texts['repository']}: `{repo.name}`",
        f"- {texts['branch']}: `{branch}`",
        f"- {texts['head']}: `{head}`",
        (
            f"- {texts['working_tree']}: "
            f"{texts['tracked_changes'].format(count=modified)}, "
            f"{texts['untracked_paths'].format(count=untracked)}"
        ),
    ]


def markdown_list(values: Any, empty: str = "None stated.") -> str:
    if not values:
        return empty
    if not isinstance(values, list) or not all(isinstance(value, str) for value in values):
        raise PackError("Expected an array of strings in manifest")
    return "\n".join(f"- {value}" for value in values)


def markdown_paragraphs(values: Any, empty: str) -> str:
    if not values:
        return empty
    if not isinstance(values, list) or not all(isinstance(value, str) for value in values):
        raise PackError("overview must be an array of strings")
    return "\n\n".join(value.strip() for value in values if value.strip()) or empty


def table_cell(value: str) -> str:
    return value.replace("|", "\\|").replace("\n", " ").strip()


def render_named_details(values: Any, label: str, empty: str) -> str:
    if not values:
        return empty
    if not isinstance(values, list):
        raise PackError(f"{label} must be an array")
    chunks: list[str] = []
    for item in values:
        if not isinstance(item, dict) or not isinstance(item.get("name"), str):
            raise PackError(f"Each {label} entry needs a string name")
        details = item.get("details")
        steps = item.get("steps")
        chunks.append(f"### {item['name']}")
        if isinstance(details, str) and details.strip():
            chunks.append(details.strip())
        elif isinstance(steps, list) and all(isinstance(step, str) for step in steps):
            chunks.extend(f"{index}. {step}" for index, step in enumerate(steps, 1))
        else:
            raise PackError(f"Each {label} entry needs details or steps")
        chunks.append("")
    return "\n".join(chunks).rstrip()


def code_fence(content: str) -> str:
    runs = [len(match.group(0)) for match in re.finditer(r"`+", content)]
    return "`" * max(3, (max(runs) + 1) if runs else 3)


def language_for(path: str) -> str:
    return LANGUAGES.get(Path(path).suffix.lower(), "text")


def build_pack(repo: Path, manifest: dict[str, Any]) -> str:
    output_language = manifest.get("output_language", "zh-Hant-TW")
    if output_language not in TEXTS:
        raise PackError("output_language must be zh-Hant-TW or en")
    texts = TEXTS[output_language]
    seen: set[str] = set()
    evidence_rows: list[str] = []
    embedded: list[str] = []
    selected_paths: list[str] = []

    for index, selection in enumerate(manifest["selections"], 1):
        if not isinstance(selection, dict):
            raise PackError(f"Selection {index} must be an object")
        full_path, relative = safe_relative_path(repo, selection.get("path"))
        reject_risky_path(relative)
        if relative in seen:
            raise PackError(f"Duplicate selection: {relative}")
        seen.add(relative)
        selected_paths.append(relative)
        reason = selection.get("reason")
        if not isinstance(reason, str) or not reason.strip():
            raise PackError(f"Selection needs a reason: {relative}")
        text = read_text(full_path, relative)
        mode = selection.get("mode")
        ranges = selection.get("lines")
        if mode == "full" and ranges is not None:
            raise PackError(f"Choose mode=full or lines, not both: {relative}")
        if mode not in (None, "full"):
            raise PackError(f"Unsupported selection mode for {relative}: {mode}")

        if ranges is None:
            slices = [(1, len(text.splitlines()) or 1, text)]
            scope = texts["full_file"]
        else:
            slices = line_slices(text, ranges, relative)
            scope = ", ".join(
                texts["range_lines"].format(start=start, end=end)
                for start, end, _ in slices
            )

        evidence_rows.append(
            f"| `{relative}` | {table_cell(scope)} | {table_cell(reason)} |"
        )
        embedded.append(f"## {texts['file']}: `{relative}`")
        embedded.append(f"{texts['why_selected']}: {reason.strip()}")
        embedded.append("")
        for start, end, content in slices:
            if ranges is not None:
                embedded.append(
                    f"### {texts['lines'].format(start=start, end=end)}"
                )
                embedded.append("")
            fence = code_fence(content)
            embedded.extend(
                [
                    f"{fence}{language_for(relative)}",
                    content.rstrip("\n"),
                    fence,
                    "",
                ]
            )

    title = manifest["title"]
    objective = manifest["objective"]
    if not isinstance(title, str) or not title.strip():
        raise PackError("title must be a non-empty string")
    if not isinstance(objective, str) or not objective.strip():
        raise PackError("objective must be a non-empty string")

    sections = [
        f"# {title.strip()}",
        "",
        texts["handoff_note"],
        "",
        f"## {texts['research_objective']}",
        "",
        objective.strip(),
        "",
        f"## {texts['audience_scope']}",
        "",
        f"- {texts['audience']}: {manifest.get('audience', texts['default_audience'])}",
        f"- {texts['scope']}: {manifest.get('scope', texts['default_scope'])}",
        "",
        f"## {texts['repository_state']}",
        "",
        *git_metadata(repo, texts),
        "",
        f"## {texts['executive_orientation']}",
        "",
        markdown_paragraphs(manifest.get("overview"), texts["not_provided"]),
        "",
        f"## {texts['architecture']}",
        "",
        render_named_details(
            manifest.get("architecture"), "architecture", texts["none_stated"]
        ),
        "",
        f"## {texts['important_flows']}",
        "",
        render_named_details(manifest.get("flows"), "flows", texts["none_stated"]),
        "",
        f"## {texts['constraints']}",
        "",
        markdown_list(manifest.get("constraints"), texts["none_stated"]),
        "",
        f"## {texts['known_unknowns']}",
        "",
        markdown_list(manifest.get("known_unknowns"), texts["none_stated"]),
        "",
        f"## {texts['open_questions']}",
        "",
        markdown_list(manifest.get("open_questions"), texts["none_stated"]),
        "",
        f"## {texts['freshness']}",
        "",
        markdown_list(manifest.get("freshness_notes"), texts["none_stated"]),
        "",
        f"## {texts['repository_shape']}",
        "",
        repository_shape(tracked_files(repo), selected_paths, texts),
        "",
        f"## {texts['evidence_index']}",
        "",
        (
            f"| {texts['path']} | {texts['included_scope']} | "
            f"{texts['why_it_matters']} |"
        ),
        "| --- | --- | --- |",
        *evidence_rows,
        "",
        f"# {texts['embedded_evidence']}",
        "",
        *embedded,
    ]
    return "\n".join(sections).rstrip() + "\n"


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Assemble a curated repository research pack from a JSON manifest."
    )
    parser.add_argument(
        "--print-template",
        action="store_true",
        help="Print a Taiwan Traditional Chinese manifest template and exit.",
    )
    parser.add_argument("--repo", type=Path)
    parser.add_argument("--manifest", type=Path)
    parser.add_argument("--output", type=Path)
    parser.add_argument(
        "--force",
        action="store_true",
        help="Overwrite an existing generated Markdown output.",
    )
    args = parser.parse_args()

    if args.print_template:
        print(json.dumps(MANIFEST_TEMPLATE, ensure_ascii=False, indent=2))
        return 0
    if args.repo is None or args.manifest is None or args.output is None:
        parser.error(
            "--repo, --manifest, and --output are required unless "
            "--print-template is used"
        )

    try:
        repo = repository_root(args.repo)
        manifest = load_manifest(args.manifest.expanduser().resolve())
        output = args.output.expanduser().resolve()
        if output.suffix.lower() != ".md":
            raise PackError("Output must use the .md extension")
        if output.exists() and output.is_dir():
            raise PackError("Output must be a Markdown file, not a directory")
        if output.exists() and not args.force:
            raise PackError(
                f"Output already exists: {output}. Use --force only for a verified "
                "generated research pack."
            )
        pack = build_pack(repo, manifest)
        output_language = manifest.get("output_language", "zh-Hant-TW")
        texts = TEXTS[output_language]
        max_chars = manifest.get("max_chars", 240_000)
        if not isinstance(max_chars, int) or max_chars < 10_000:
            raise PackError("max_chars must be an integer of at least 10000")
        if len(pack) > max_chars:
            estimate = (len(pack) + 3) // 4
            limit_estimate = (max_chars + 3) // 4
            raise PackError(
                f"Pack is {len(pack)} characters (~{estimate} tokens), exceeding "
                f"max_chars={max_chars} (~{limit_estimate} tokens). Refine selections."
            )
        home = str(Path.home())
        if home and home in pack:
            raise PackError("Completed pack contains an absolute home-directory path")
        for pattern in SECRET_PATTERNS:
            if pattern.search(pack):
                raise PackError("Completed pack contains a high-confidence secret pattern")
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(pack, encoding="utf-8")
        estimate = (len(pack) + 3) // 4
        print(f"{texts['wrote']}: {output}")
        print(f"{texts['characters']}: {len(pack)}")
        print(f"{texts['estimated_tokens']}: {estimate}")
        print(f"{texts['selections']}: {len(manifest['selections'])}")
        return 0
    except PackError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
