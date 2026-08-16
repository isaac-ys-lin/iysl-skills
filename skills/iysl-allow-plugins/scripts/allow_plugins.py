#!/usr/bin/env python3
"""Build and maintain a reversible project plugin capability allowlist."""

from __future__ import annotations

import argparse
import hashlib
import html
import json
import os
import subprocess
import sys
import tempfile
import tomllib
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable


BEGIN_MARKER = "# BEGIN iysl-allow-plugins managed block"
END_MARKER = "# END iysl-allow-plugins managed block"
ALLOWLIST_REL = Path(".codex/allow-plugins.toml")
CONFIG_REL = Path(".codex/config.toml")
SCHEMA_VERSION = 1


class AllowPluginsError(RuntimeError):
    """A fail-closed inventory, config, or identity error."""


def _json_string(value: str) -> str:
    return json.dumps(value, ensure_ascii=False)


def _read_toml(path: Path, *, missing_ok: bool = False) -> dict[str, Any]:
    if not path.exists():
        if missing_ok:
            return {}
        raise AllowPluginsError(f"missing TOML file: {path}")
    if path.is_symlink():
        raise AllowPluginsError(f"refusing symlinked TOML file: {path}")
    try:
        value = tomllib.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, tomllib.TOMLDecodeError) as exc:
        raise AllowPluginsError(f"invalid TOML at {path}: {exc}") from exc
    if not isinstance(value, dict):
        raise AllowPluginsError(f"TOML root must be a table: {path}")
    return value


def _project_path(raw: str) -> Path:
    path = Path(raw).expanduser().resolve()
    if not path.is_dir():
        raise AllowPluginsError(f"project is not a directory: {path}")
    codex_dir = path / ".codex"
    if codex_dir.is_symlink():
        raise AllowPluginsError(f"refusing symlinked project config directory: {codex_dir}")
    return path


def _global_config_path(raw: str | None) -> Path:
    if raw:
        return Path(raw).expanduser().resolve()
    codex_home = Path(os.environ.get("CODEX_HOME", Path.home() / ".codex"))
    return codex_home / "config.toml"


def _split_managed_block(text: str) -> tuple[str, str | None]:
    starts = text.count(BEGIN_MARKER)
    ends = text.count(END_MARKER)
    if starts == ends == 0:
        return text, None
    if starts != 1 or ends != 1:
        raise AllowPluginsError("ambiguous or duplicate managed block markers")
    start = text.index(BEGIN_MARKER)
    end_start = text.index(END_MARKER, start)
    if text.find(END_MARKER) < start:
        raise AllowPluginsError("managed block markers are out of order")
    end = end_start + len(END_MARKER)
    while end < len(text) and text[end] in " \t":
        end += 1
    if end < len(text) and text[end] == "\n":
        end += 1
    # Apply always adds one separator newline immediately before the marker.
    # Treat that separator as managed so rollback restores the original bytes.
    block_start = start - 1 if start > 0 and text[start - 1] == "\n" else start
    return text[:block_start] + text[end:], text[start:end].rstrip("\n")


def _read_project_config(project: Path) -> tuple[str, dict[str, Any], str | None]:
    path = project / CONFIG_REL
    if not path.exists():
        return "", {}, None
    if path.is_symlink():
        raise AllowPluginsError(f"refusing symlinked project config: {path}")
    try:
        text = path.read_text(encoding="utf-8")
    except (OSError, UnicodeError) as exc:
        raise AllowPluginsError(f"cannot read project config {path}: {exc}") from exc
    _read_toml(path)
    base, managed = _split_managed_block(text)
    try:
        base_data = tomllib.loads(base) if base.strip() else {}
    except tomllib.TOMLDecodeError as exc:
        raise AllowPluginsError(f"invalid unmanaged project TOML at {path}: {exc}") from exc
    return base, base_data, managed


def _load_allowlist(project: Path) -> list[str] | None:
    path = project / ALLOWLIST_REL
    if not path.exists():
        return None
    data = _read_toml(path)
    if data.get("schema_version") != SCHEMA_VERSION:
        raise AllowPluginsError(f"unsupported allowlist schema at {path}")
    values = data.get("allowed_plugins")
    if (
        not isinstance(values, list)
        or any(not isinstance(item, str) or not item.strip() for item in values)
        or len(values) != len(set(values))
    ):
        raise AllowPluginsError(f"allowed_plugins must be a unique string list: {path}")
    return values


def _trust_state(project: Path, global_data: dict[str, Any]) -> str:
    projects = global_data.get("projects", {})
    if not isinstance(projects, dict):
        return "unverified"
    entry = projects.get(str(project))
    if not isinstance(entry, dict):
        return "unverified"
    trust = entry.get("trust_level")
    return trust if isinstance(trust, str) else "unverified"


def _plugin_list(path: str | None) -> list[dict[str, Any]]:
    if path:
        try:
            payload = json.loads(Path(path).read_text(encoding="utf-8"))
        except (OSError, UnicodeError, json.JSONDecodeError) as exc:
            raise AllowPluginsError(f"invalid plugin-list JSON at {path}: {exc}") from exc
    else:
        try:
            result = subprocess.run(
                ["codex", "plugin", "list", "--json"],
                check=False,
                capture_output=True,
                text=True,
                timeout=30,
            )
        except (OSError, subprocess.TimeoutExpired) as exc:
            raise AllowPluginsError(f"cannot run codex plugin list --json: {exc}") from exc
        if result.returncode != 0:
            detail = result.stderr.strip() or f"exit {result.returncode}"
            raise AllowPluginsError(f"codex plugin list --json failed: {detail}")
        try:
            payload = json.loads(result.stdout)
        except json.JSONDecodeError as exc:
            raise AllowPluginsError(f"unsupported codex plugin list JSON: {exc}") from exc
    installed = payload.get("installed") if isinstance(payload, dict) else None
    if not isinstance(installed, list):
        raise AllowPluginsError("unsupported codex plugin list JSON: missing installed array")
    for index, item in enumerate(installed):
        if not isinstance(item, dict) or not isinstance(item.get("pluginId"), str):
            raise AllowPluginsError(f"unsupported codex plugin list JSON item {index}")
        if not isinstance(item.get("enabled"), bool):
            raise AllowPluginsError(f"plugin list item {index} has no boolean enabled state")
    return installed


def _find_plugin_root(raw: Path) -> Path | None:
    current = raw.expanduser().resolve()
    if current.is_file():
        current = current.parent
    for candidate in (current, *list(current.parents)[:5]):
        if (candidate / ".codex-plugin/plugin.json").is_file():
            return candidate
    return None


def _catalog_name(root: Path) -> str:
    parts = root.parts
    if "cache" in parts:
        index = parts.index("cache")
        if index + 1 < len(parts):
            return parts[index + 1]
    if "plugins" in parts:
        index = len(parts) - 1 - list(reversed(parts)).index("plugins")
        if index + 1 < len(parts):
            return parts[index + 1]
    return root.parent.name or "host-catalog"


def _manifest(root: Path) -> dict[str, Any]:
    path = root / ".codex-plugin/plugin.json"
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        raise AllowPluginsError(f"invalid plugin manifest {path}: {exc}") from exc
    if not isinstance(data, dict) or not isinstance(data.get("name"), str):
        raise AllowPluginsError(f"plugin manifest has no name: {path}")
    return data


def _host_entries(values: Iterable[str]) -> list[dict[str, Any]]:
    entries: list[dict[str, Any]] = []
    for raw in values:
        if "=" not in raw:
            raise AllowPluginsError("--host-plugin must use NAME_OR_ID=/absolute/plugin/path")
        supplied, path_text = raw.split("=", 1)
        supplied = supplied.strip()
        if not supplied:
            raise AllowPluginsError("--host-plugin has an empty name")
        root = _find_plugin_root(Path(path_text))
        if root is None:
            raise AllowPluginsError(f"cannot find plugin manifest above host path: {path_text}")
        data = _manifest(root)
        entries.append(
            {
                "supplied": supplied,
                "name": data["name"],
                "root": root,
                "catalog": _catalog_name(root),
                "canonical_supplied": "@" in supplied,
            }
        )
    return entries


def _cache_roots(codex_home: Path, name: str) -> list[Path]:
    cache = codex_home / "plugins/cache"
    if not cache.is_dir():
        return []
    candidates = [
        path.parent.parent
        for path in cache.glob(f"*/{name}/*/.codex-plugin/plugin.json")
        if path.is_file()
    ]
    return sorted(set(candidates), key=lambda item: item.stat().st_mtime, reverse=True)


def _all_cache_roots(codex_home: Path) -> list[Path]:
    cache = codex_home / "plugins/cache"
    if not cache.is_dir():
        return []
    candidates = [
        path.parent.parent
        for path in cache.glob("*/*/*/.codex-plugin/plugin.json")
        if path.is_file()
    ]
    return sorted(set(candidates), key=lambda item: item.stat().st_mtime, reverse=True)


def _capabilities(root: Path, manifest: dict[str, Any]) -> dict[str, Any]:
    skills: list[str] = []
    skills_declared = manifest.get("skills")
    if skills_declared is not None:
        if not isinstance(skills_declared, str):
            raise AllowPluginsError(f"unsupported skills declaration in {root}")
        skills_root = (root / skills_declared).resolve()
        if not skills_root.is_dir():
            raise AllowPluginsError(f"declared skills directory is missing: {skills_root}")
        skills = sorted(
            str(path.parent.resolve())
            for path in skills_root.glob("*/SKILL.md")
            if path.is_file()
        )
        if not skills:
            raise AllowPluginsError(f"declared skills directory has no skills: {skills_root}")

    servers: list[str] = []
    mcp_declared = manifest.get("mcpServers")
    if mcp_declared is not None:
        if not isinstance(mcp_declared, str):
            raise AllowPluginsError(f"unsupported mcpServers declaration in {root}")
        mcp_path = (root / mcp_declared).resolve()
        try:
            mcp_data = json.loads(mcp_path.read_text(encoding="utf-8"))
        except (OSError, UnicodeError, json.JSONDecodeError) as exc:
            raise AllowPluginsError(f"invalid declared MCP file {mcp_path}: {exc}") from exc
        mcp_servers = mcp_data.get("mcpServers") if isinstance(mcp_data, dict) else None
        if not isinstance(mcp_servers, dict) or not mcp_servers:
            raise AllowPluginsError(f"declared MCP file has no mcpServers: {mcp_path}")
        servers = sorted(mcp_servers)

    apps_declared = manifest.get("apps")
    apps = False
    if apps_declared is not None:
        if not isinstance(apps_declared, str):
            raise AllowPluginsError(f"unsupported apps declaration in {root}")
        app_path = (root / apps_declared).resolve()
        if not app_path.is_file():
            raise AllowPluginsError(f"declared apps file is missing: {app_path}")
        apps = True

    return {"skills": skills, "mcp_servers": servers, "apps": apps}


def build_inventory(args: argparse.Namespace) -> dict[str, Any]:
    project = _project_path(args.project)
    global_path = _global_config_path(args.global_config)
    global_data = _read_toml(global_path)
    cli_items = _plugin_list(args.plugin_list_json)
    hosts = _host_entries(args.host_plugin)
    codex_home = global_path.parent

    plugins_config = global_data.get("plugins", {})
    if not isinstance(plugins_config, dict):
        raise AllowPluginsError("global plugins config must be a table")

    records: dict[str, dict[str, Any]] = {}
    for plugin_id, config in plugins_config.items():
        if not isinstance(plugin_id, str) or not isinstance(config, dict):
            raise AllowPluginsError("global plugin config contains an invalid entry")
        enabled = config.get("enabled")
        if enabled is not None and not isinstance(enabled, bool):
            raise AllowPluginsError(f"global plugin enabled state is not boolean: {plugin_id}")
        records[plugin_id] = {
            "id": plugin_id,
            "name": plugin_id.split("@", 1)[0],
            "canonical_known": True,
            "global_enabled": enabled,
            "cli_enabled": None,
            "cli_installed": False,
            "host_visible": False,
            "roots": [],
            "sources": ["global_config"],
        }

    for item in cli_items:
        plugin_id = item["pluginId"]
        record = records.setdefault(
            plugin_id,
            {
                "id": plugin_id,
                "name": item.get("name") or plugin_id.split("@", 1)[0],
                "canonical_known": True,
                "global_enabled": None,
                "cli_enabled": None,
                "cli_installed": False,
                "host_visible": False,
                "roots": [],
                "sources": [],
            },
        )
        record["cli_enabled"] = item["enabled"]
        record["cli_installed"] = bool(item.get("installed", True))
        record["sources"].append("codex_cli")
        source = item.get("source")
        if isinstance(source, dict) and isinstance(source.get("path"), str):
            root = _find_plugin_root(Path(source["path"]))
            if root:
                record["roots"].append(root)

    by_name: dict[str, list[str]] = {}
    for plugin_id, record in records.items():
        by_name.setdefault(record["name"], []).append(plugin_id)

    for host in hosts:
        supplied = host["supplied"]
        if host["canonical_supplied"]:
            plugin_id = supplied
            canonical = True
        else:
            candidates = by_name.get(host["name"], [])
            cli_candidates = [item for item in candidates if records[item]["cli_enabled"] is not None]
            if len(cli_candidates) == 1:
                plugin_id = cli_candidates[0]
                canonical = True
            elif len(cli_candidates) > 1 or len(candidates) > 1:
                raise AllowPluginsError(f"ambiguous plugin identity for host plugin {host['name']}")
            elif len(candidates) == 1:
                plugin_id = candidates[0]
                canonical = True
            else:
                plugin_id = f"{host['name']}@{host['catalog']}"
                canonical = False
        record = records.setdefault(
            plugin_id,
            {
                "id": plugin_id,
                "name": host["name"],
                "canonical_known": canonical,
                "global_enabled": None,
                "cli_enabled": None,
                "cli_installed": False,
                "host_visible": False,
                "roots": [],
                "sources": [],
            },
        )
        if record["name"] != host["name"]:
            raise AllowPluginsError(f"identity collision for {plugin_id}")
        record["canonical_known"] = record["canonical_known"] or canonical
        record["host_visible"] = True
        record["roots"].append(host["root"])
        record["sources"].append("current_task")

    # Surface cache-only bundles for reporting, but never make them selectable
    # or treat them as installation evidence.
    known_names = {record["name"] for record in records.values()}
    for root in _all_cache_roots(codex_home):
        try:
            data = _manifest(root)
        except AllowPluginsError:
            continue
        name = data["name"]
        if name in known_names:
            continue
        plugin_id = f"{name}@{_catalog_name(root)}"
        if plugin_id in records:
            continue
        records[plugin_id] = {
            "id": plugin_id,
            "name": name,
            "canonical_known": False,
            "global_enabled": None,
            "cli_enabled": None,
            "cli_installed": False,
            "host_visible": False,
            "roots": [root],
            "sources": ["cache_metadata"],
        }

    output_records: list[dict[str, Any]] = []
    for plugin_id, record in sorted(records.items()):
        confirmed = record["global_enabled"] is True or record["cli_enabled"] is True
        host_unverified = (
            record["host_visible"]
            and record["global_enabled"] is None
            and record["cli_enabled"] is None
        )
        selectable = confirmed or host_unverified
        if confirmed:
            group = "confirmed_globally_enabled"
        elif host_unverified:
            group = "task_visible_unverified"
        elif record["host_visible"]:
            group = "disabled_or_stale_task"
        elif record["global_enabled"] is False or record["cli_enabled"] is False:
            group = "globally_disabled"
        else:
            group = "metadata_only"

        roots = list(dict.fromkeys(record["roots"]))
        roots.extend(root for root in _cache_roots(codex_home, record["name"]) if root not in roots)
        manifest_root: Path | None = None
        manifest_data: dict[str, Any] | None = None
        manifest_errors: list[str] = []
        for root in roots:
            try:
                candidate = _manifest(root)
                if candidate["name"] != record["name"]:
                    raise AllowPluginsError(
                        f"manifest name {candidate['name']} does not match {record['name']} at {root}"
                    )
                manifest_root, manifest_data = root, candidate
                break
            except AllowPluginsError as exc:
                manifest_errors.append(str(exc))
        capabilities = {"skills": [], "mcp_servers": [], "apps": False}
        capability_error: str | None = None
        if manifest_root and manifest_data:
            try:
                capabilities = _capabilities(manifest_root, manifest_data)
            except AllowPluginsError as exc:
                capability_error = str(exc)

        output_records.append(
            {
                "id": plugin_id,
                "name": record["name"],
                "canonical_known": record["canonical_known"],
                "global_enabled": record["global_enabled"],
                "cli_enabled": record["cli_enabled"],
                "cli_installed": record["cli_installed"],
                "host_visible": record["host_visible"],
                "selectable": selectable,
                "group": group,
                "manifest_root": str(manifest_root) if manifest_root else None,
                "manifest_error": capability_error or (manifest_errors[-1] if manifest_errors else None),
                "skills": capabilities["skills"],
                "mcp_servers": capabilities["mcp_servers"],
                "apps": capabilities["apps"],
                "sources": sorted(set(record["sources"])),
            }
        )

    previous = _load_allowlist(project)
    _, _, managed = _read_project_config(project)
    if (previous is None) != (managed is None):
        raise AllowPluginsError("allowlist file and managed config block are out of sync")
    trust = _trust_state(project, global_data)
    return {
        "schema_version": SCHEMA_VERSION,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "project": str(project),
        "trusted": trust == "trusted",
        "trust_state": trust,
        "previous_allowlist": previous,
        "plugins": output_records,
    }


def _tracked(project: Path, relative: Path) -> bool:
    result = subprocess.run(
        ["git", "-C", str(project), "ls-files", "--error-unmatch", relative.as_posix()],
        check=False,
        capture_output=True,
        text=True,
    )
    return result.returncode == 0


def _check_conflicts(
    base_data: dict[str, Any],
    skill_paths: list[str],
    tools: list[str],
    mcp: list[tuple[str, str]],
) -> None:
    existing_skills = base_data.get("skills", {})
    configs = existing_skills.get("config", []) if isinstance(existing_skills, dict) else []
    if configs and not isinstance(configs, list):
        raise AllowPluginsError("existing skills.config is not an array")
    seen: set[str] = set()
    targets = {str(Path(path).resolve()) for path in skill_paths}
    for item in configs:
        if not isinstance(item, dict) or not isinstance(item.get("path"), str):
            raise AllowPluginsError("existing skills.config contains an ambiguous entry")
        normalized = str(Path(item["path"]).expanduser().resolve())
        if normalized in seen:
            raise AllowPluginsError(f"existing skills.config duplicates path {normalized}")
        seen.add(normalized)
        if normalized in targets:
            raise AllowPluginsError(f"existing config already controls managed skill path {normalized}")

    if tools and "tool_suggest" in base_data:
        raise AllowPluginsError("existing tool_suggest config conflicts with managed disabled_tools")

    plugins = base_data.get("plugins", {})
    if plugins and not isinstance(plugins, dict):
        raise AllowPluginsError("existing plugins config is not a table")
    for plugin_id, server in mcp:
        plugin = plugins.get(plugin_id, {}) if isinstance(plugins, dict) else {}
        if plugin and not isinstance(plugin, dict):
            raise AllowPluginsError(f"existing plugin config is ambiguous: {plugin_id}")
        servers = plugin.get("mcp_servers", {}) if isinstance(plugin, dict) else {}
        if servers and not isinstance(servers, dict):
            raise AllowPluginsError(f"existing MCP config is ambiguous: {plugin_id}")
        if server in servers:
            raise AllowPluginsError(f"existing config already controls {plugin_id} MCP server {server}")


def _managed_block(skill_paths: list[str], tools: list[str], mcp: list[tuple[str, str]]) -> str:
    lines = [BEGIN_MARKER, "# Generated by $iysl-allow-plugins; edit through the skill."]
    for path in sorted(set(skill_paths)):
        lines.extend(["", "[[skills.config]]", f"path = {_json_string(path)}", "enabled = false"])
    if tools:
        lines.extend(["", "[tool_suggest]", "disabled_tools = ["])
        lines.extend(
            f"  {{ type = \"plugin\", id = {_json_string(plugin_id)} }},"
            for plugin_id in sorted(set(tools))
        )
        lines.append("]")
    for plugin_id, server in sorted(set(mcp)):
        lines.extend(
            [
                "",
                f"[plugins.{_json_string(plugin_id)}.mcp_servers.{_json_string(server)}]",
                "enabled = false",
            ]
        )
    lines.append(END_MARKER)
    return "\n".join(lines)


def build_plan(inventory: dict[str, Any], allowed: Iterable[str]) -> dict[str, Any]:
    project = Path(inventory["project"])
    if not inventory.get("trusted"):
        raise AllowPluginsError(
            f"project is not confirmed trusted (state: {inventory.get('trust_state', 'unverified')})"
        )
    selected = sorted(set(allowed))
    selectable = {item["id"]: item for item in inventory["plugins"] if item["selectable"]}
    unknown = sorted(set(selected) - set(selectable))
    if unknown:
        raise AllowPluginsError(f"selection contains unavailable plugin IDs: {unknown}")
    disabled = [item for plugin_id, item in selectable.items() if plugin_id not in selected]

    skill_paths: list[str] = []
    tools: list[str] = []
    mcp: list[tuple[str, str]] = []
    app_limits: list[str] = []
    warnings: list[str] = []
    effects: list[dict[str, Any]] = []
    for item in disabled:
        if not item.get("manifest_root") or item.get("manifest_error"):
            detail = item.get("manifest_error") or "manifest unavailable"
            raise AllowPluginsError(f"cannot safely mask {item['id']}: {detail}")
        missing = [path for path in item["skills"] if not (Path(path) / "SKILL.md").is_file()]
        if missing:
            raise AllowPluginsError(f"skill paths disappeared for {item['id']}: {missing}")
        skill_paths.extend(item["skills"])
        if item["canonical_known"]:
            tools.append(item["id"])
            mcp.extend((item["id"], server) for server in item["mcp_servers"])
        else:
            warnings.append(
                f"{item['id']} has a synthesized ID; tool suggestion and MCP routing are not changed"
            )
        if item["apps"]:
            app_limits.append(item["id"])
        effects.append(
            {
                "id": item["id"],
                "skills_disabled": len(item["skills"]),
                "tool_suggestion_disabled": bool(item["canonical_known"]),
                "mcp_servers_disabled": item["mcp_servers"] if item["canonical_known"] else [],
                "apps_not_project_scopeable": bool(item["apps"]),
            }
        )

    base, base_data, existing_managed = _read_project_config(project)
    _check_conflicts(base_data, skill_paths, tools, mcp)
    block = _managed_block(skill_paths, tools, mcp)
    previous = inventory.get("previous_allowlist")
    added = sorted(set(selected) - set(previous or []))
    removed = sorted(set(previous or []) - set(selected))
    if _tracked(project, CONFIG_REL):
        warnings.append(f"{CONFIG_REL.as_posix()} is tracked by Git")
    if _tracked(project, ALLOWLIST_REL):
        warnings.append(f"{ALLOWLIST_REL.as_posix()} is tracked by Git")
    if skill_paths:
        warnings.append("generated absolute skill paths are machine- and plugin-version-specific")
    if app_limits:
        warnings.append("plugin apps/connectors are not project-scopeable by this workaround")
    return {
        "schema_version": SCHEMA_VERSION,
        "project": str(project),
        "allowed_plugins": selected,
        "disabled_plugins": [item["id"] for item in disabled],
        "selection_diff": {"added": added, "removed": removed},
        "effects": effects,
        "warnings": warnings,
        "files": [str(project / ALLOWLIST_REL), str(project / CONFIG_REL)],
        "managed_block": block,
        "existing_managed_block": existing_managed,
        "base_config": base,
    }


def _allowlist_text(allowed: Iterable[str]) -> str:
    lines = [f"schema_version = {SCHEMA_VERSION}", "allowed_plugins = ["]
    lines.extend(f"  {_json_string(item)}," for item in allowed)
    lines.extend(["]", ""])
    return "\n".join(lines)


def _atomic_write(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.parent.is_symlink() or path.is_symlink():
        raise AllowPluginsError(f"refusing symlinked write target: {path}")
    mode = path.stat().st_mode & 0o777 if path.exists() else 0o644
    handle = tempfile.NamedTemporaryFile(
        mode="w", encoding="utf-8", dir=path.parent, prefix=f".{path.name}.", delete=False
    )
    temp_path = Path(handle.name)
    try:
        with handle:
            handle.write(text)
            handle.flush()
            os.fsync(handle.fileno())
        os.chmod(temp_path, mode)
        os.replace(temp_path, path)
    finally:
        if temp_path.exists():
            temp_path.unlink()


def apply_plan(plan: dict[str, Any]) -> dict[str, Any]:
    project = Path(plan["project"])
    base = plan["base_config"]
    separator = "\n" if base else ""
    config_text = base + separator + plan["managed_block"] + "\n"
    try:
        tomllib.loads(config_text)
        tomllib.loads(_allowlist_text(plan["allowed_plugins"]))
    except tomllib.TOMLDecodeError as exc:
        raise AllowPluginsError(f"generated TOML did not validate: {exc}") from exc
    _atomic_write(project / CONFIG_REL, config_text)
    _atomic_write(project / ALLOWLIST_REL, _allowlist_text(plan["allowed_plugins"]))
    return {
        "status": "applied",
        "project": str(project),
        "allowed_plugins": plan["allowed_plugins"],
        "fresh_task_required": True,
    }


def validate_state(inventory: dict[str, Any]) -> dict[str, Any]:
    allowed = inventory.get("previous_allowlist")
    if allowed is None:
        return {"status": "not_configured", "project": inventory["project"]}
    plan = build_plan(inventory, allowed)
    _, _, actual = _read_project_config(Path(inventory["project"]))
    if actual != plan["managed_block"]:
        raise AllowPluginsError("managed block does not match the saved allowlist and live inventory")
    return {
        "status": "valid",
        "project": inventory["project"],
        "allowed_plugins": allowed,
        "fresh_task_required_for_host_visibility": True,
    }


def remove_state(project: Path, confirm: bool) -> dict[str, Any]:
    base, _, managed = _read_project_config(project)
    allow_path = project / ALLOWLIST_REL
    if allow_path.is_symlink():
        raise AllowPluginsError(f"refusing symlinked allowlist: {allow_path}")
    preview = {
        "status": "preview" if not confirm else "removed",
        "project": str(project),
        "remove_allowlist": allow_path.exists(),
        "remove_managed_block": managed is not None,
        "files": [str(allow_path), str(project / CONFIG_REL)],
    }
    if not confirm:
        return preview
    if managed is None and not allow_path.exists():
        return preview
    config_path = project / CONFIG_REL
    if managed is not None:
        if base.strip():
            try:
                tomllib.loads(base)
            except tomllib.TOMLDecodeError as exc:
                raise AllowPluginsError(f"remaining project TOML would be invalid: {exc}") from exc
            _atomic_write(config_path, base)
        elif config_path.exists():
            config_path.unlink()
    if allow_path.exists():
        allow_path.unlink()
    preview["fresh_task_required"] = True
    return preview


def render_picker(inventory: dict[str, Any]) -> str:
    selectable = [item for item in inventory["plugins"] if item["selectable"]]
    previous = inventory.get("previous_allowlist")
    checked = {item["id"] for item in selectable} if previous is None else set(previous)
    digest = hashlib.sha256(inventory["project"].encode("utf-8")).hexdigest()[:12]
    root_id = "iysl-allow-plugins-" + digest
    chunks = [f'<div id="{root_id}">', "<h2>這個 Project 允許哪些 plugins？</h2>"]
    if len(selectable) > 30:
        chunks.extend(
            [
                '<label class="form-label" for="plugin-filter">篩選</label>',
                '<input class="form-control" id="plugin-filter" type="search" placeholder="輸入 plugin 名稱">',
            ]
        )
    labels = {
        "confirmed_globally_enabled": "全域已開啟",
        "task_visible_unverified": "目前 Desktop task 可見（全域狀態未確認）",
    }
    for group in ("confirmed_globally_enabled", "task_visible_unverified"):
        entries = [item for item in selectable if item["group"] == group]
        if not entries:
            continue
        chunks.append(f'<section data-plugin-group="{group}"><h3>{labels[group]}</h3>')
        for index, item in enumerate(entries):
            control_id = f"plugin-{group}-{index}"
            state = " checked" if item["id"] in checked else ""
            suffix = "（識別碼為推定）" if not item["canonical_known"] else ""
            search = html.escape(f"{item['name']} {item['id']}".lower(), quote=True)
            chunks.extend(
                [
                    f'<div class="form-check" data-plugin-row data-search="{search}">',
                    f'<input class="form-check-input" type="checkbox" value="{html.escape(item["id"], quote=True)}" id="{control_id}"{state}>',
                    f'<label class="form-check-label" for="{control_id}">{html.escape(item["name"])} <code>{html.escape(item["id"])}</code> {suffix}</label>',
                    "</div>",
                ]
            )
        chunks.append("</section>")
    chunks.extend(
        [
            '<div class="viz-controls">',
            '<button class="btn btn-primary" type="button" data-preview>預覽設定變更</button>',
            '<span class="text-small text-muted" role="status" data-status></span>',
            "</div>",
            "<script>",
            "(() => {",
            f"  const root = document.getElementById({_json_string(root_id)});",
            "  const filter = root.querySelector('#plugin-filter');",
            "  if (filter) filter.addEventListener('input', () => {",
            "    const query = filter.value.trim().toLowerCase();",
            "    root.querySelectorAll('[data-plugin-row]').forEach(row => { row.hidden = !row.dataset.search.includes(query); });",
            "  });",
            "  root.querySelector('[data-preview]').addEventListener('click', async () => {",
            "    const selected = [...root.querySelectorAll('input[type=checkbox]:checked')].map(input => input.value);",
            "    const status = root.querySelector('[data-status]');",
            "    status.textContent = '正在送出選擇…';",
            "    try {",
            "      await window.openai.sendFollowUpMessage({",
            f"        prompt: '$iysl-allow-plugins 請針對 Project ' + {_json_string(inventory['project'])} + ' 預覽這份選擇；先不要寫檔。\\nselected_plugins = ' + JSON.stringify(selected),",
            "        title: '預覽 Project plugin 變更'",
            "      });",
            "      status.textContent = '已送出，接下來會先顯示差異。';",
            "    } catch (error) { status.textContent = '無法送出，請改用文字列出勾選項目。'; }",
            "  });",
            "})();",
            "</script>",
            "</div>",
        ]
    )
    return "\n".join(chunks) + "\n"


def _write_output(path: str | None, payload: Any) -> None:
    text = payload if isinstance(payload, str) else json.dumps(payload, ensure_ascii=False, indent=2) + "\n"
    if path:
        _atomic_write(Path(path).expanduser().resolve(), text)
    else:
        sys.stdout.write(text)


def _add_inventory_args(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--project", required=True)
    parser.add_argument("--global-config")
    parser.add_argument("--plugin-list-json", help="Use captured CLI JSON instead of running codex")
    parser.add_argument("--host-plugin", action="append", default=[], metavar="NAME_OR_ID=PATH")


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    subparsers = parser.add_subparsers(dest="command", required=True)
    inventory = subparsers.add_parser("inventory")
    _add_inventory_args(inventory)
    inventory.add_argument("--output")

    picker = subparsers.add_parser("picker")
    picker.add_argument("--inventory", required=True)
    picker.add_argument("--output", required=True)

    for name in ("plan", "apply"):
        sub = subparsers.add_parser(name)
        _add_inventory_args(sub)
        sub.add_argument("--allow", action="append", default=[])
        if name == "apply":
            sub.add_argument("--confirm-apply", action="store_true")

    validate = subparsers.add_parser("validate")
    _add_inventory_args(validate)

    remove = subparsers.add_parser("remove")
    remove.add_argument("--project", required=True)
    remove.add_argument("--confirm-remove", action="store_true")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    try:
        if args.command == "inventory":
            _write_output(args.output, build_inventory(args))
        elif args.command == "picker":
            try:
                inventory = json.loads(Path(args.inventory).read_text(encoding="utf-8"))
            except (OSError, UnicodeError, json.JSONDecodeError) as exc:
                raise AllowPluginsError(f"invalid inventory JSON: {exc}") from exc
            _write_output(args.output, render_picker(inventory))
        elif args.command in {"plan", "apply"}:
            plan = build_plan(build_inventory(args), args.allow)
            if args.command == "apply":
                if not args.confirm_apply:
                    raise AllowPluginsError("apply requires --confirm-apply after user confirmation")
                _write_output(None, apply_plan(plan))
            else:
                public_plan = {key: value for key, value in plan.items() if key != "base_config"}
                _write_output(None, public_plan)
        elif args.command == "validate":
            _write_output(None, validate_state(build_inventory(args)))
        elif args.command == "remove":
            _write_output(None, remove_state(_project_path(args.project), args.confirm_remove))
        return 0
    except AllowPluginsError as exc:
        sys.stderr.write(f"error: {exc}\n")
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
