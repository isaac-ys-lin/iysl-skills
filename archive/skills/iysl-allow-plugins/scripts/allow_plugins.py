#!/usr/bin/env python3
"""Build and maintain a reversible project plugin capability allowlist."""

from __future__ import annotations

import argparse
from contextlib import contextmanager
import hashlib
import html
import json
import os
import platform
import queue
import shlex
import shutil
import signal
import stat
import subprocess
import sys
import tempfile
import threading
import time
import tomllib
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable


BEGIN_MARKER = "# BEGIN iysl-allow-plugins managed block"
END_MARKER = "# END iysl-allow-plugins managed block"
ALLOWLIST_REL = Path(".codex/allow-plugins.toml")
CONFIG_REL = Path(".codex/config.toml")
SCHEMA_VERSION = 2
DESKTOP_CODEX = Path("/Applications/ChatGPT.app/Contents/Resources/codex")
RUNTIME_TIMEOUT_SECONDS = 30
RUNTIME_SHUTDOWN_SECONDS = 3
MCP_PAGE_LIMIT = 100
MAX_MCP_PAGES = 100


class AllowPluginsError(RuntimeError):
    """A fail-closed inventory, config, or identity error."""


class RuntimeProbeError(AllowPluginsError):
    """A runtime process, protocol, or schema failure that must fail closed."""

    def __init__(self, stage: str, detail: str):
        self.stage = stage
        self.detail = detail
        super().__init__(f"{stage}: {detail}")


class RollbackConflictError(AllowPluginsError):
    """Refuse rollback when another actor changed a managed file after this run."""

    def __init__(self, conflicts: list[str]):
        self.conflicts = conflicts
        super().__init__("rollback would overwrite newer managed-file content: " + "; ".join(conflicts))


class ConcurrentModificationError(AllowPluginsError):
    """Refuse an atomic replace after its target changed since the last observation."""

    def __init__(self, path: Path):
        self.path = path
        super().__init__(f"managed target changed before atomic replace: {path}")


class TransactionTerminated(KeyboardInterrupt):
    """SIGTERM received while a managed-file transaction is probing runtimes."""


@contextmanager
def _transaction_sigterm_guard(
    *,
    signal_api: Any = signal,
    current_thread: Any = threading.current_thread,
    main_thread: Any = threading.main_thread,
) -> Iterable[None]:
    """Turn SIGTERM into a rollback-triggering interruption in the main thread only."""
    if current_thread() is not main_thread():
        yield
        return
    previous = signal_api.getsignal(signal_api.SIGTERM)

    def interrupt(_signum: int, _frame: Any) -> None:
        raise TransactionTerminated()

    signal_api.signal(signal_api.SIGTERM, interrupt)
    try:
        yield
    finally:
        signal_api.signal(signal_api.SIGTERM, previous)


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
        # Do not use text-mode universal-newline translation.  Project config
        # preimages are byte-sensitive transaction inputs.
        value = tomllib.loads(path.read_bytes().decode("utf-8"))
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
    if text.startswith("\r\n", end):
        end += 2
    elif end < len(text) and text[end] in "\r\n":
        end += 1
    # Apply always adds one separator newline immediately before the marker.
    # Treat that separator as managed so rollback restores the original bytes.
    if text[:start].endswith("\r\n"):
        block_start = start - 2
    elif start > 0 and text[start - 1] in "\r\n":
        block_start = start - 1
    else:
        block_start = start
    return text[:block_start] + text[end:], text[start:end].rstrip("\r\n")


def _read_project_config(project: Path) -> tuple[str, dict[str, Any], str | None]:
    path = project / CONFIG_REL
    if not path.exists():
        return "", {}, None
    if path.is_symlink():
        raise AllowPluginsError(f"refusing symlinked project config: {path}")
    try:
        # Preserve CRLF and every unmanaged byte through apply/remove.
        text = path.read_bytes().decode("utf-8")
    except (OSError, UnicodeError) as exc:
        raise AllowPluginsError(f"cannot read project config {path}: {exc}") from exc
    _read_toml(path)
    base, managed = _split_managed_block(text)
    try:
        base_data = tomllib.loads(base) if base.strip() else {}
    except tomllib.TOMLDecodeError as exc:
        raise AllowPluginsError(f"invalid unmanaged project TOML at {path}: {exc}") from exc
    return base, base_data, managed


def _load_allowlist(project: Path) -> dict[str, Any] | None:
    path = project / ALLOWLIST_REL
    if not path.exists():
        return None
    data = _read_toml(path)
    version = data.get("schema_version")
    if version not in (1, SCHEMA_VERSION):
        raise AllowPluginsError(f"unsupported allowlist schema at {path}")
    values = data.get("allowed_plugins")
    if (
        not isinstance(values, list)
        or any(not isinstance(item, str) or not item.strip() for item in values)
        or len(values) != len(set(values))
    ):
        raise AllowPluginsError(f"allowed_plugins must be a unique string list: {path}")
    config_preexisting = data.get("config_preexisting")
    if not isinstance(config_preexisting, bool):
        raise AllowPluginsError(
            f"allowlist lacks config_preexisting metadata at {path}; refuse ambiguous removal"
        )
    fingerprint = data.get("fingerprint")
    if version == SCHEMA_VERSION and (not isinstance(fingerprint, str) or len(fingerprint) != 64):
        raise AllowPluginsError(f"allowlist lacks a valid v2 fingerprint: {path}")
    host_plugins = data.get("host_plugins", [])
    if not isinstance(host_plugins, list) or any(not isinstance(item, str) or not item for item in host_plugins) or len(host_plugins) != len(set(host_plugins)):
        raise AllowPluginsError(f"allowlist has malformed host_plugins metadata: {path}")
    return {
        "allowed_plugins": values,
        "config_preexisting": config_preexisting,
        "schema_version": version,
        "fingerprint": fingerprint,
        "host_plugins": host_plugins,
    }


def _trust_state(project: Path, global_data: dict[str, Any]) -> str:
    projects = global_data.get("projects", {})
    if not isinstance(projects, dict):
        return "unverified"
    entry = projects.get(str(project))
    if not isinstance(entry, dict):
        return "unverified"
    trust = entry.get("trust_level")
    return trust if isinstance(trust, str) else "unverified"


def _plugin_list(path: str | None, *, desktop_path: Path = DESKTOP_CODEX) -> list[dict[str, Any]]:
    if path:
        try:
            payload = json.loads(Path(path).read_text(encoding="utf-8"))
        except (OSError, UnicodeError, json.JSONDecodeError) as exc:
            raise AllowPluginsError(f"invalid plugin-list JSON at {path}: {exc}") from exc
    else:
        if not desktop_path.is_file() or not os.access(desktop_path, os.X_OK):
            raise AllowPluginsError(f"Codex Desktop runtime is required for plugin inventory: {desktop_path}")
        try:
            result = subprocess.run(
                [str(desktop_path), "plugin", "list", "--json"],
                check=False,
                capture_output=True,
                text=True,
                timeout=30,
            )
        except (OSError, subprocess.TimeoutExpired) as exc:
            raise AllowPluginsError(f"cannot run Desktop codex plugin list --json: {exc}") from exc
        if result.returncode != 0:
            detail = result.stderr.strip() or f"exit {result.returncode}"
            raise AllowPluginsError(f"Desktop codex plugin list --json failed: {detail}")
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
        plugin_name = _identity_name(item["pluginId"])
        supplied_name = item.get("name")
        if supplied_name is not None and (
            not isinstance(supplied_name, str) or supplied_name != plugin_name
        ):
            raise AllowPluginsError(
                f"plugin list item {index} name does not match pluginId: {item['pluginId']}"
            )
        source = item.get("source")
        if isinstance(source, dict) and isinstance(source.get("path"), str):
            root = _find_plugin_root(Path(source["path"]))
            if root is not None and _manifest(root)["name"] != plugin_name:
                raise AllowPluginsError(
                    f"plugin list item {index} source manifest does not match pluginId: {item['pluginId']}"
                )
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


def _identity_name(identifier: str) -> str:
    name = identifier.split("@", 1)[0]
    if not name:
        raise AllowPluginsError(f"plugin identity has an empty name component: {identifier!r}")
    return name


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
        if _identity_name(supplied) != data["name"]:
            raise AllowPluginsError(
                f"host plugin identity {supplied!r} does not match manifest name {data['name']!r}"
            )
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


def _is_within_root(root: Path, path: Path) -> bool:
    try:
        return os.path.commonpath((str(root.resolve()), str(path.resolve()))) == str(root.resolve())
    except (OSError, ValueError):
        return False


def _parse_apps(root: Path, declared: str) -> list[dict[str, Any]]:
    """Read canonical connector IDs.  Aliases are descriptive, never policy keys."""
    app_path = (root / declared).resolve()
    if not _is_within_root(root, app_path) or not app_path.is_file():
        raise AllowPluginsError(f"declared apps file is missing: {app_path}")
    try:
        data = json.loads(app_path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        raise AllowPluginsError(f"invalid declared apps file {app_path}: {exc}") from exc
    entries = data.get("apps") if isinstance(data, dict) else None
    if not isinstance(entries, dict):
        raise AllowPluginsError(f"declared apps file must have a top-level apps object: {app_path}")
    output: list[dict[str, Any]] = []
    seen: set[str] = set()
    for alias, entry in entries.items():
        if not isinstance(alias, str) or not alias or not isinstance(entry, dict):
            raise AllowPluginsError(f"declared apps file has malformed app entry: {app_path}")
        app_id = entry.get("id")
        if not isinstance(app_id, str) or not app_id.strip() or app_id != app_id.strip():
            raise AllowPluginsError(f"declared apps file app {alias!r} has no canonical nonempty id: {app_path}")
        if app_id in seen:
            raise AllowPluginsError(f"declared apps file repeats canonical app id {app_id!r}: {app_path}")
        seen.add(app_id)
        metadata: dict[str, Any] = {"id": app_id, "alias": alias}
        for key in ("required", "optional"):
            if key in entry:
                if not isinstance(entry[key], bool):
                    raise AllowPluginsError(f"declared app {app_id!r} has non-boolean {key}: {app_path}")
                metadata[key] = entry[key]
        output.append(metadata)
    return sorted(output, key=lambda item: item["id"])


def _capabilities(root: Path, manifest: dict[str, Any]) -> dict[str, Any]:
    root = root.resolve()
    skills: list[str] = []
    fingerprint_paths: list[Path] = [root / ".codex-plugin/plugin.json"]
    skills_declared = manifest.get("skills")
    if skills_declared is not None:
        if not isinstance(skills_declared, str):
            raise AllowPluginsError(f"unsupported skills declaration in {root}")
        skills_root = (root / skills_declared).resolve()
        if not _is_within_root(root, skills_root):
            raise AllowPluginsError(f"declared skills directory escapes plugin root: {skills_root}")
        if not skills_root.is_dir():
            raise AllowPluginsError(f"declared skills directory is missing: {skills_root}")
        skill_files = [path.resolve() for path in skills_root.glob("*/SKILL.md") if path.is_file()]
        if any(not _is_within_root(root, path) for path in skill_files):
            raise AllowPluginsError(f"declared skill escapes plugin root: {skills_root}")
        skills = sorted(str(path) for path in skill_files)
        fingerprint_paths.extend(skill_files)
        if not skills:
            raise AllowPluginsError(f"declared skills directory has no skills: {skills_root}")

    servers: list[str] = []
    mcp_declared = manifest.get("mcpServers")
    if mcp_declared is not None:
        if not isinstance(mcp_declared, str):
            raise AllowPluginsError(f"unsupported mcpServers declaration in {root}")
        mcp_path = (root / mcp_declared).resolve()
        if not _is_within_root(root, mcp_path):
            raise AllowPluginsError(f"declared MCP file escapes plugin root: {mcp_path}")
        try:
            mcp_data = json.loads(mcp_path.read_text(encoding="utf-8"))
        except (OSError, UnicodeError, json.JSONDecodeError) as exc:
            raise AllowPluginsError(f"invalid declared MCP file {mcp_path}: {exc}") from exc
        mcp_servers = mcp_data.get("mcpServers") if isinstance(mcp_data, dict) else None
        if not isinstance(mcp_servers, dict) or not mcp_servers:
            raise AllowPluginsError(f"declared MCP file has no mcpServers: {mcp_path}")
        servers = sorted(mcp_servers)
        fingerprint_paths.append(mcp_path)

    apps_declared = manifest.get("apps")
    apps: list[dict[str, Any]] = []
    if apps_declared is not None:
        if not isinstance(apps_declared, str):
            raise AllowPluginsError(f"unsupported apps declaration in {root}")
        apps = _parse_apps(root, apps_declared)
        fingerprint_paths.append((root / apps_declared).resolve())

    digest = hashlib.sha256()
    for path in sorted(set(fingerprint_paths), key=lambda item: str(item)):
        try:
            digest.update(str(path.relative_to(root)).encode("utf-8") + b"\0")
            digest.update(hashlib.sha256(path.read_bytes()).digest())
        except OSError as exc:
            raise AllowPluginsError(f"cannot fingerprint declared capability {path}: {exc}") from exc
    return {
        "skills": skills, "mcp_servers": servers, "apps": apps,
        "manifest_version": manifest.get("version"), "capability_digest": digest.hexdigest(),
    }


def build_inventory(args: argparse.Namespace) -> dict[str, Any]:
    project = _project_path(args.project)
    global_path = _global_config_path(args.global_config)
    global_data = _read_toml(global_path)
    desktop_path = Path(getattr(args, "desktop_codex", None) or DESKTOP_CODEX).expanduser().resolve()
    cli_items = _plugin_list(args.plugin_list_json, desktop_path=desktop_path)
    hosts = _host_entries(args.host_plugin)
    codex_home = global_path.parent
    cache_snapshot: list[dict[str, Any]] = []
    cache_roots = _all_cache_roots(codex_home)
    for root in cache_roots:
        entry: dict[str, Any] = {"root": str(root), "catalog": _catalog_name(root)}
        try:
            manifest = _manifest(root)
            observed = _capabilities(root, manifest)
            entry.update({
                "name": manifest["name"], "manifest_version": observed["manifest_version"],
                "capability_digest": observed["capability_digest"],
            })
        except AllowPluginsError as exc:
            entry["error"] = str(exc)
        cache_snapshot.append(entry)

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
    # or attach their capability roots to a canonical record by manifest name.
    for root in cache_roots:
        try:
            data = _manifest(root)
        except AllowPluginsError:
            continue
        name = data["name"]
        plugin_id = f"{name}@{_catalog_name(root)}"
        if plugin_id in records and records[plugin_id].get("sources") != ["cache_metadata"]:
            continue
        if plugin_id in records:
            records[plugin_id]["roots"].append(root)
        else:
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

        # Roots are attached only by a CLI source path or an exact/resolved host
        # identity. Cache discovery is metadata only: name equality is not a
        # canonical identity and must never mix two catalog variants.
        roots = list(dict.fromkeys(record["roots"]))
        manifest_errors: list[str] = []
        capability_errors: list[str] = []
        manifest_roots: list[Path] = []
        capabilities = {"skills": [], "mcp_servers": [], "apps": []}
        capability_digests: list[dict[str, Any]] = []
        for root in roots:
            try:
                candidate = _manifest(root)
                if candidate["name"] != record["name"]:
                    raise AllowPluginsError(
                        f"manifest name {candidate['name']} does not match {record['name']} at {root}"
                    )
            except AllowPluginsError as exc:
                manifest_errors.append(str(exc))
                continue
            manifest_roots.append(root)
            try:
                observed = _capabilities(root, candidate)
            except AllowPluginsError as exc:
                capability_errors.append(str(exc))
                continue
            capabilities["skills"].extend(observed["skills"])
            capabilities["mcp_servers"].extend(observed["mcp_servers"])
            capabilities["apps"].extend(observed["apps"])
            capability_digests.append({
                "root": str(root), "manifest_version": observed["manifest_version"],
                "digest": observed["capability_digest"],
            })

        capabilities["skills"] = sorted(set(capabilities["skills"]))
        capabilities["mcp_servers"] = sorted(set(capabilities["mcp_servers"]))
        app_by_id: dict[str, dict[str, Any]] = {}
        for app in capabilities["apps"]:
            previous_app = app_by_id.get(app["id"])
            if previous_app is not None and previous_app != app and "cache_metadata" not in record["sources"]:
                raise AllowPluginsError(
                    f"ambiguous app declaration for {app['id']!r} across roots of {plugin_id}"
                )
            app_by_id[app["id"]] = app
        capabilities["apps"] = [app_by_id[key] for key in sorted(app_by_id)]
        manifest_root = manifest_roots[0] if manifest_roots else None
        manifest_error = "; ".join(manifest_errors + capability_errors) or None

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
                "manifest_roots": [str(root) for root in manifest_roots],
                "manifest_error": manifest_error,
                "skills": capabilities["skills"],
                "mcp_servers": capabilities["mcp_servers"],
                "apps": capabilities["apps"],
                "capability_digests": sorted(capability_digests, key=lambda item: item["root"]),
                "sources": sorted(set(record["sources"])),
            }
        )

    allowlist_state = _load_allowlist(project)
    previous = allowlist_state["allowed_plugins"] if allowlist_state is not None else None
    config_preexisting = allowlist_state["config_preexisting"] if allowlist_state is not None else None
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
        "config_preexisting": config_preexisting,
        "allowlist_schema_version": allowlist_state["schema_version"] if allowlist_state else None,
        "saved_fingerprint": allowlist_state["fingerprint"] if allowlist_state else None,
        "host_plugins": sorted(f"{entry['supplied']}={entry['root']}" for entry in hosts),
        "cache_snapshot": sorted(cache_snapshot, key=lambda item: item["root"]),
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
    app_ids: list[str],
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
    if "apps" in base_data:
        raise AllowPluginsError("existing Project apps config conflicts with managed app policy")

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


def _managed_block(
    skill_paths: list[str], tools: list[str], mcp: list[tuple[str, str]],
    selected_app_ids: list[str], excluded_app_ids: list[str], hook_command: str,
) -> str:
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
    lines.extend(["", "[apps._default]", "enabled = false"])
    for app_id in sorted(set(selected_app_ids)):
        lines.extend(["", f"[apps.{_json_string(app_id)}]", "enabled = true"])
    for app_id in sorted(set(excluded_app_ids) - set(selected_app_ids)):
        lines.extend(["", f"[apps.{_json_string(app_id)}]", "enabled = false"])
    lines.extend([
        "", "[[hooks.SessionStart]]", 'matcher = "startup|resume|clear"',
        "hooks = [{ type = \"command\", command = " + _json_string(hook_command) + ", async = true }]",
    ])
    lines.append(END_MARKER)
    return "\n".join(lines)


def _item_skill_paths(item: dict[str, Any], *, require_ready: bool) -> list[str]:
    paths = item.get("skills")
    roots = item.get("manifest_roots")
    if not isinstance(paths, list) or not all(isinstance(path, str) for path in paths):
        raise AllowPluginsError(f"plugin {item.get('id', '<unknown>')} has malformed skill paths")
    if not paths:
        return []
    if not isinstance(roots, list) or not all(isinstance(root, str) for root in roots):
        raise AllowPluginsError(f"plugin {item.get('id', '<unknown>')} has malformed manifest roots")
    resolved_roots = [Path(root).resolve() for root in roots]
    if require_ready and (not resolved_roots or item.get("manifest_error")):
        detail = item.get("manifest_error") or "manifest unavailable"
        raise AllowPluginsError(f"cannot safely mask {item['id']}: {detail}")
    for raw_path in paths:
        path = Path(raw_path).resolve()
        if not path.is_file():
            raise AllowPluginsError(f"skill path disappeared for {item['id']}: {path}")
        if not any(_is_within_root(root, path) for root in resolved_roots):
            raise AllowPluginsError(f"skill path escapes plugin root for {item['id']}: {path}")
    return sorted(set(paths))


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
    selected_items = [item for plugin_id, item in selectable.items() if plugin_id in selected]
    disabled = [item for plugin_id, item in selectable.items() if plugin_id not in selected]
    previous = inventory.get("previous_allowlist")
    added = sorted(set(selected) - set(previous or []))
    removed = sorted(set(previous or []) - set(selected))
    selectable_name_counts: dict[str, int] = {}
    for item in selectable.values():
        name = item.get("name")
        if not isinstance(name, str):
            raise AllowPluginsError(f"plugin {item.get('id', '<unknown>')} has malformed name")
        selectable_name_counts[name] = selectable_name_counts.get(name, 0) + 1
    selected_skill_paths: set[str] = set()
    selected_mcp_servers: set[str] = set()
    for item in selected_items:
        if item.get("manifest_error"):
            raise AllowPluginsError(f"cannot safely profile {item['id']}: {item['manifest_error']}")
        # Selected plugins need no write, but their observed paths are needed to
        # reject a cross-canonical root collision before masking another plugin.
        selected_skill_paths.update(_item_skill_paths(item, require_ready=False))
        if item.get("canonical_known"):
            selected_mcp_servers.update(item["mcp_servers"])

    skill_paths: list[str] = []
    tools: list[str] = []
    mcp: list[tuple[str, str]] = []
    def app_ids(item: dict[str, Any]) -> list[str]:
        apps = item.get("apps", [])
        if isinstance(apps, bool):  # compatibility with a caller-built v1 inventory
            return []
        if not isinstance(apps, list) or any(not isinstance(app, dict) or not isinstance(app.get("id"), str) for app in apps):
            raise AllowPluginsError(f"plugin {item.get('id', '<unknown>')} has malformed app declarations")
        return [app["id"] for app in apps]
    selected_app_ids = sorted({app_id for item in selected_items for app_id in app_ids(item)})
    excluded_app_ids = sorted({app_id for item in disabled for app_id in app_ids(item)})
    warnings: list[str] = []
    effects: list[dict[str, Any]] = []
    runtime_targets: list[dict[str, Any]] = []
    for item in disabled:
        if not item.get("manifest_root") or item.get("manifest_error"):
            detail = item.get("manifest_error") or "manifest unavailable"
            raise AllowPluginsError(f"cannot safely mask {item['id']}: {detail}")
        item_paths = _item_skill_paths(item, require_ready=True)
        overlap = selected_skill_paths.intersection(item_paths)
        if overlap:
            raise AllowPluginsError(
                f"selected and disabled plugins share capability paths: {sorted(overlap)}"
            )
        if item["canonical_known"]:
            mcp_overlap = selected_mcp_servers.intersection(item["mcp_servers"])
            if mcp_overlap:
                raise AllowPluginsError(
                    "selected and disabled plugins share canonical MCP server names: "
                    f"{sorted(mcp_overlap)}"
                )
        skill_paths.extend(item_paths)
        if item["canonical_known"]:
            tools.append(item["id"])
            mcp.extend((item["id"], server) for server in item["mcp_servers"])
        else:
            warnings.append(
                f"{item['id']} has a synthesized ID; tool suggestion and MCP routing are not changed"
            )
        effects.append(
            {
                "id": item["id"],
                "skills_disabled": len(item_paths),
                "tool_suggestion_disabled": bool(item["canonical_known"]),
                "mcp_servers_disabled": item["mcp_servers"] if item["canonical_known"] else [],
                "apps_default_denied": app_ids(item),
                "apps_not_project_scopeable": False,
            }
        )
        runtime_targets.append(
            {
                "id": item["id"],
                "name": item["name"],
                "canonical_known": item["canonical_known"],
                "allow_name_fallback": selectable_name_counts[item["name"]] == 1,
                "skills": item_paths,
                "mcp_servers": sorted(set(item["mcp_servers"])),
            }
        )

    managed_preimage = _snapshot_managed_files(project)
    base, base_data, existing_managed = _read_project_config(project)
    if _snapshot_managed_files(project) != managed_preimage:
        raise AllowPluginsError("managed files changed while building the plan; rebuild inventory and plan")
    if previous is None:
        config_preexisting = managed_preimage[project / CONFIG_REL][0]
    else:
        config_preexisting = inventory.get("config_preexisting")
        if not isinstance(config_preexisting, bool):
            raise AllowPluginsError("saved allowlist has no valid config_preexisting metadata")
    _check_conflicts(base_data, skill_paths, tools, mcp, selected_app_ids + excluded_app_ids)
    hook_command = shlex.join([sys.executable, str(Path(__file__).resolve()), "hook-check", "--project", str(project)])
    block = _managed_block(skill_paths, tools, mcp, selected_app_ids, excluded_app_ids, hook_command)
    if _tracked(project, CONFIG_REL):
        warnings.append(f"{CONFIG_REL.as_posix()} is tracked by Git")
    if _tracked(project, ALLOWLIST_REL):
        warnings.append(f"{ALLOWLIST_REL.as_posix()} is tracked by Git")
    if skill_paths:
        warnings.append("generated absolute skill paths are machine- and plugin-version-specific")
    shared_apps = sorted(set(selected_app_ids).intersection(excluded_app_ids))
    if shared_apps:
        warnings.append("shared app IDs selected and excluded; selected capability wins: " + ", ".join(shared_apps))
    return {
        "schema_version": SCHEMA_VERSION,
        "project": str(project),
        "allowed_plugins": selected,
        "disabled_plugins": [item["id"] for item in disabled],
        "selection_diff": {"added": added, "removed": removed},
        "scope_enforceable": True,
        "unsupported_capabilities": [],
        "effects": effects,
        "warnings": warnings,
        "files": [str(project / ALLOWLIST_REL), str(project / CONFIG_REL)],
        "managed_block": block,
        "existing_managed_block": existing_managed,
        "base_config": base,
        "config_preexisting": config_preexisting,
        "runtime_targets": runtime_targets,
        "selected_app_ids": selected_app_ids,
        "excluded_app_ids": excluded_app_ids,
        "managed_preimage": managed_preimage,
        "fingerprint": _capability_fingerprint(inventory, block),
        "host_plugins": list(inventory.get("host_plugins", [])),
    }


def _capability_fingerprint(inventory: dict[str, Any], managed_block: str) -> str:
    """Hash deterministic effective inputs for the read-only SessionStart check."""
    plugins = []
    for item in inventory.get("plugins", []):
        if item.get("selectable"):
            plugins.append({key: item.get(key) for key in (
                "id", "manifest_roots", "manifest_error", "skills", "mcp_servers", "apps", "capability_digests",
                "global_enabled", "cli_enabled", "cli_installed",
            )})
    payload = {
        "plugins": sorted(plugins, key=lambda item: str(item["id"])),
        # Cache roots are drift evidence only.  Keep this independent of
        # selectable records so a new cache version colliding with a host/CLI
        # identity cannot disappear from the SessionStart fingerprint.
        "cache_snapshot": inventory.get("cache_snapshot", []),
        "managed_block": managed_block,
    }
    return hashlib.sha256(json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")).hexdigest()


def _allowlist_text(allowed: Iterable[str], *, config_preexisting: bool, fingerprint: str, host_plugins: Iterable[str]) -> str:
    lines = [
        f"schema_version = {SCHEMA_VERSION}",
        f"config_preexisting = {'true' if config_preexisting else 'false'}",
        f"fingerprint = {_json_string(fingerprint)}",
        "host_plugins = [",
    ]
    lines.extend(f"  {_json_string(item)}," for item in sorted(set(host_plugins)))
    lines.extend(["]", "allowed_plugins = ["])
    lines.extend(f"  {_json_string(item)}," for item in allowed)
    lines.extend(["]", ""])
    return "\n".join(lines)


def _atomic_write(
    path: Path,
    text: str,
    *,
    mode: int | None = None,
    expected: ManagedFileState | None = None,
) -> None:
    _atomic_write_bytes(path, text.encode("utf-8"), mode=mode, expected=expected)


def _atomic_write_bytes(
    path: Path,
    content: bytes,
    *,
    mode: int | None = None,
    expected: ManagedFileState | None = None,
) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.parent.is_symlink() or path.is_symlink():
        raise AllowPluginsError(f"refusing symlinked write target: {path}")
    if mode is None:
        mode = stat.S_IMODE(path.stat().st_mode) if path.exists() else 0o644
    handle = tempfile.NamedTemporaryFile(
        mode="wb", dir=path.parent, prefix=f".{path.name}.", delete=False
    )
    temp_path = Path(handle.name)
    try:
        with handle:
            handle.write(content)
            handle.flush()
            os.fsync(handle.fileno())
        os.chmod(temp_path, mode)
        if expected is not None and _snapshot_file(path) != expected:
            raise ConcurrentModificationError(path)
        os.replace(temp_path, path)
    finally:
        if temp_path.exists():
            temp_path.unlink()


ManagedFileState = tuple[bool, bytes | None, int | None]


def _snapshot_file(path: Path) -> ManagedFileState:
    if path.is_symlink():
        raise AllowPluginsError(f"refusing symlinked managed target: {path}")
    if not path.exists():
        return False, None, None
    try:
        return True, path.read_bytes(), stat.S_IMODE(path.stat().st_mode)
    except OSError as exc:
        raise AllowPluginsError(f"cannot snapshot managed target {path}: {exc}") from exc


def _snapshot_managed_files(project: Path) -> dict[Path, ManagedFileState]:
    return {project / relative: _snapshot_file(project / relative) for relative in (CONFIG_REL, ALLOWLIST_REL)}


def _unlink_if_expected(path: Path, *, expected: ManagedFileState, unlink: Any = Path.unlink) -> None:
    if _snapshot_file(path) != expected:
        raise ConcurrentModificationError(path)
    unlink(path)


def _restore_managed_files(
    snapshots: dict[Path, ManagedFileState],
    *,
    expected_current: dict[Path, ManagedFileState] | None = None,
) -> None:
    """Restore only the two managed files; never remove their shared .codex directory."""
    errors: list[str] = []
    conflicts: list[str] = []
    for path, (existed, content, mode) in snapshots.items():
        try:
            current: ManagedFileState | None = None
            if expected_current is not None:
                current = _snapshot_file(path)
                # A signal may land between preparing an expected state and its
                # atomic replacement.  Treat the untouched preimage as already
                # restored, but never overwrite any third state.
                if current == snapshots[path]:
                    continue
                if current != expected_current[path]:
                    conflicts.append(str(path))
                    continue
            if existed:
                assert content is not None and mode is not None
                _atomic_write_bytes(path, content, mode=mode, expected=current)
            elif path.exists():
                if current is None:
                    path.unlink()
                else:
                    _unlink_if_expected(path, expected=current)
        except (AllowPluginsError, OSError) as exc:
            errors.append(str(exc))
    if conflicts:
        raise RollbackConflictError(conflicts)
    if errors:
        raise AllowPluginsError("rollback could not restore managed files: " + "; ".join(errors))


def _run_command(
    command: list[str], *, cwd: Path | None, timeout: int = RUNTIME_TIMEOUT_SECONDS
) -> subprocess.CompletedProcess[str]:
    try:
        return subprocess.run(
            command,
            cwd=str(cwd) if cwd else None,
            check=False,
            capture_output=True,
            text=True,
            timeout=timeout,
            shell=False,
        )
    except subprocess.TimeoutExpired as exc:
        raise RuntimeProbeError("process_timeout", " ".join(command)) from exc
    except OSError as exc:
        raise RuntimeProbeError("process_os_error", f"{' '.join(command)}: {exc}") from exc


def discover_runtimes(
    *,
    desktop_path: Path = DESKTOP_CODEX,
    which: Any = shutil.which,
    run_command: Any = _run_command,
) -> list[dict[str, str]]:
    """Discover Desktop first, then PATH, while preserving their independent evidence."""
    if not (desktop_path.is_file() and os.access(desktop_path, os.X_OK)):
        raise RuntimeProbeError("desktop_required", f"Codex Desktop runtime is required: {desktop_path}")
    raw_paths: list[tuple[str, Path]] = [("desktop", desktop_path)]
    path_binary = which("codex")
    if path_binary:
        raw_paths.append(("path", Path(path_binary)))

    runtimes: list[dict[str, str]] = []
    accepted: list[Path] = []
    for source, candidate in raw_paths:
        try:
            usable = candidate.is_file() and os.access(candidate, os.X_OK)
        except OSError:
            usable = False
        if not usable:
            continue
        try:
            if any(candidate.samefile(previous) for previous in accepted):
                continue
        except OSError as exc:
            raise RuntimeProbeError("runtime_discovery", f"cannot compare {candidate}: {exc}") from exc
        result = run_command([str(candidate), "--version"], cwd=None)
        if result.returncode != 0:
            detail = result.stderr.strip() or f"exit {result.returncode}"
            raise RuntimeProbeError("version_nonzero", f"{candidate}: {detail}")
        version = result.stdout.strip()
        if not version:
            raise RuntimeProbeError("version_schema", f"{candidate}: empty --version output")
        accepted.append(candidate)
        runtimes.append({"path": str(candidate), "source": source, "version": version})
    if not runtimes:
        raise RuntimeProbeError("runtime_discovery", "no executable Desktop or PATH Codex runtime found")
    return runtimes


class _StdioAppServerSession:
    """A bounded JSONL App Server session with no JSON-RPC header on the wire."""

    def __init__(
        self,
        binary: str,
        project: Path,
        *,
        timeout: int = RUNTIME_TIMEOUT_SECONDS,
        clock: Any = time.monotonic,
    ):
        self.timeout = timeout
        self._clock = clock
        self.process: Any = None
        self._reader: Any = None
        try:
            self.process = subprocess.Popen(
                [binary, "app-server"],
                cwd=str(project),
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=subprocess.DEVNULL,
                text=True,
                encoding="utf-8",
                errors="replace",
                bufsize=1,
                shell=False,
                start_new_session=True,
            )
        except OSError as exc:
            raise RuntimeProbeError("app_server_os_error", f"{binary}: {exc}") from exc
        try:
            if self.process.stdin is None or self.process.stdout is None:
                raise RuntimeProbeError("app_server_stdio", "missing stdio pipe")
            self._lines: queue.Queue[str | None] = queue.Queue()
            self._reader = threading.Thread(target=self._read_stdout, daemon=True)
            self._reader.start()
        except BaseException:
            # Popen already succeeded: no constructor failure, including Ctrl-C
            # during Thread.start, may leave an App Server child behind.
            self.close()
            raise

    def _read_stdout(self) -> None:
        assert self.process.stdout is not None
        try:
            for line in self.process.stdout:
                self._lines.put(line)
        finally:
            self._lines.put(None)

    def _send(self, message: dict[str, Any]) -> None:
        if "jsonrpc" in message:
            raise RuntimeProbeError("protocol_schema", "jsonrpc header is forbidden on App Server JSONL")
        try:
            assert self.process.stdin is not None
            self.process.stdin.write(json.dumps(message, ensure_ascii=False) + "\n")
            self.process.stdin.flush()
        except (AssertionError, OSError, BrokenPipeError) as exc:
            raise RuntimeProbeError("app_server_write", str(exc)) from exc

    def request(self, message: dict[str, Any]) -> dict[str, Any]:
        request_id = message.get("id")
        if not isinstance(request_id, int):
            raise RuntimeProbeError("protocol_schema", "request ID must be an integer")
        self._send(message)
        deadline = self._clock() + self.timeout
        while True:
            remaining = deadline - self._clock()
            if remaining <= 0:
                raise RuntimeProbeError("app_server_timeout", f"waiting for response id {request_id}")
            try:
                line = self._lines.get(timeout=remaining)
            except queue.Empty as exc:
                raise RuntimeProbeError("app_server_timeout", f"waiting for response id {request_id}") from exc
            if line is None:
                code = self.process.poll()
                detail = f"EOF while waiting for response id {request_id}"
                if code is not None:
                    detail += f" (exit {code})"
                raise RuntimeProbeError("app_server_eof", detail)
            try:
                response = json.loads(line)
            except json.JSONDecodeError as exc:
                raise RuntimeProbeError("protocol_json", f"invalid JSONL response: {exc}") from exc
            if not isinstance(response, dict):
                raise RuntimeProbeError("protocol_schema", "App Server response must be an object")
            if "jsonrpc" in response:
                raise RuntimeProbeError("protocol_schema", "unexpected jsonrpc header in App Server response")
            if "id" not in response:
                continue  # Notifications are intentionally ignored.
            if response.get("id") != request_id:
                continue
            if "error" in response:
                raise RuntimeProbeError("json_rpc_error", json.dumps(response["error"], ensure_ascii=False))
            if "result" not in response:
                raise RuntimeProbeError("protocol_schema", f"response id {request_id} has no result")
            return response

    def notify(self, message: dict[str, Any]) -> None:
        if "id" in message:
            raise RuntimeProbeError("protocol_schema", "notification must not include an ID")
        self._send(message)

    def ensure_healthy(self) -> None:
        code = self.process.poll()
        if code is not None:
            raise RuntimeProbeError("app_server_process_exit", f"exited with {code}")

    def close(self) -> None:
        process = getattr(self, "process", None)
        if process is None:
            return
        if process.stdin is not None:
            try:
                process.stdin.close()
            except OSError:
                pass
        if process.poll() is None:
            try:
                os.killpg(process.pid, signal.SIGTERM)
            except (AttributeError, OSError):
                process.terminate()
            try:
                process.wait(timeout=RUNTIME_SHUTDOWN_SECONDS)
            except subprocess.TimeoutExpired:
                try:
                    os.killpg(process.pid, signal.SIGKILL)
                except (AttributeError, OSError):
                    process.kill()
                process.wait(timeout=RUNTIME_SHUTDOWN_SECONDS)
        reader = getattr(self, "_reader", None)
        if reader is not None:
            try:
                reader.join(timeout=RUNTIME_SHUTDOWN_SECONDS)
            except RuntimeError:
                # A failed Thread.start cannot be joined.
                pass
        if process.stdout is not None:
            try:
                process.stdout.close()
            except OSError:
                pass


def _result(response: Any, method: str) -> dict[str, Any]:
    if not isinstance(response, dict):
        raise RuntimeProbeError("protocol_schema", f"{method} response must be an object")
    if "error" in response:
        raise RuntimeProbeError("json_rpc_error", f"{method}: {json.dumps(response['error'], ensure_ascii=False)}")
    result = response.get("result")
    if not isinstance(result, dict):
        raise RuntimeProbeError("protocol_schema", f"{method} result must be an object")
    return result


def _skill_entries(result: dict[str, Any], project: Path) -> list[dict[str, Any]]:
    groups = result.get("data")
    if not isinstance(groups, list):
        raise RuntimeProbeError("skills_schema", "skills/list result.data must be an array")
    expected_cwd = str(project.resolve())
    if len(groups) != 1 or not isinstance(groups[0], dict) or groups[0].get("cwd") != expected_cwd:
        raise RuntimeProbeError("skills_schema", f"expected one skills/list group for {expected_cwd}")
    group = groups[0]
    errors = group.get("errors")
    skills = group.get("skills")
    if not isinstance(errors, list) or not isinstance(skills, list):
        raise RuntimeProbeError("skills_schema", "skills/list group lacks errors or skills arrays")
    if errors:
        raise RuntimeProbeError("skills_cwd_errors", json.dumps(errors, ensure_ascii=False))
    for item in skills:
        if not isinstance(item, dict) or not isinstance(item.get("name"), str):
            raise RuntimeProbeError("skills_schema", "skills/list contains malformed skill")
        if not isinstance(item.get("enabled"), bool):
            raise RuntimeProbeError("skills_schema", f"skill {item['name']} has no boolean enabled field")
        for field in ("path", "skillPath", "filePath"):
            if field in item and not isinstance(item[field], str):
                raise RuntimeProbeError("skills_schema", f"skill {item['name']} has non-string {field}")
    return skills


def _mcp_entries(result: dict[str, Any]) -> tuple[list[dict[str, Any]], str | None]:
    rows = result.get("data")
    cursor = result.get("nextCursor")
    if (
        not isinstance(rows, list)
        or "nextCursor" not in result
        or (cursor is not None and not isinstance(cursor, str))
    ):
        raise RuntimeProbeError("mcp_schema", "mcpServerStatus/list must return data and string-or-null nextCursor")
    for row in rows:
        if not isinstance(row, dict) or not isinstance(row.get("name"), str):
            raise RuntimeProbeError("mcp_schema", "mcpServerStatus/list contains malformed server")
        if "serverInfo" in row and row["serverInfo"] is not None and not isinstance(row["serverInfo"], dict):
            raise RuntimeProbeError("mcp_schema", f"server {row['name']} has malformed serverInfo")
        if "tools" in row:
            tools = row["tools"]
            valid_list = isinstance(tools, list) and all(isinstance(tool, dict) for tool in tools)
            valid_map = isinstance(tools, dict) and all(
                isinstance(name, str) and isinstance(tool, dict) for name, tool in tools.items()
            )
            if not valid_list and not valid_map:
                raise RuntimeProbeError("mcp_schema", f"server {row['name']} has malformed tools")
    return rows, cursor


def _canonical_skill_path(raw_path: str) -> str:
    try:
        return str(Path(raw_path).expanduser().resolve())
    except (OSError, ValueError) as exc:
        raise RuntimeProbeError("skills_schema", f"cannot normalize runtime skill path {raw_path!r}: {exc}") from exc


def _skill_matches(item: dict[str, Any], target: dict[str, Any]) -> bool:
    path_fields = ("path", "skillPath", "filePath")
    present_paths = [item[field] for field in path_fields if field in item]
    if present_paths:
        # A runtime-supplied path is authoritative provenance.  Never fall
        # back to a display-name prefix after it identifies a different root.
        target_paths = {_canonical_skill_path(path) for path in target["skills"]}
        return any(_canonical_skill_path(path) in target_paths for path in present_paths)
    if not item["name"].startswith(target["name"] + ":"):
        return False
    if not target["allow_name_fallback"]:
        raise RuntimeProbeError(
            "skills_provenance",
            f"runtime skill {item['name']} has no path for ambiguous plugin name {target['name']}",
        )
    return True


def _verify_skills(entries: list[dict[str, Any]], targets: list[dict[str, Any]]) -> list[dict[str, str]]:
    leaks: list[dict[str, str]] = []
    for target in targets:
        for item in entries:
            if _skill_matches(item, target) and item["enabled"]:
                leaks.append({"plugin": target["id"], "skill": item["name"]})
    return leaks


def _parse_mcp_cli(result: Any) -> dict[str, bool]:
    if result.returncode != 0:
        detail = result.stderr.strip() or f"exit {result.returncode}"
        raise RuntimeProbeError("mcp_cli_nonzero", detail)
    try:
        rows = json.loads(result.stdout)
    except json.JSONDecodeError as exc:
        raise RuntimeProbeError("mcp_cli_json", str(exc)) from exc
    if not isinstance(rows, list):
        raise RuntimeProbeError("mcp_cli_schema", "mcp list --json root must be an array")
    output: dict[str, bool] = {}
    for row in rows:
        if not isinstance(row, dict) or not isinstance(row.get("name"), str) or not isinstance(row.get("enabled"), bool):
            raise RuntimeProbeError("mcp_cli_schema", "MCP list row needs string name and boolean enabled")
        if row["name"] in output:
            raise RuntimeProbeError("mcp_cli_schema", f"duplicate MCP server {row['name']}")
        output[row["name"]] = row["enabled"]
    return output


def _verify_mcp(
    cli_servers: dict[str, bool], status_rows: list[dict[str, Any]], targets: list[dict[str, Any]]
) -> list[dict[str, str]]:
    leaks: list[dict[str, str]] = []
    for target in targets:
        if not target["canonical_known"]:
            continue
        for server in target["mcp_servers"]:
            if cli_servers.get(server) is True:
                leaks.append({"plugin": target["id"], "server": server, "source": "mcp_cli_enabled"})
            for row in status_rows:
                if row["name"] != server:
                    continue
                if row.get("serverInfo") is not None and row.get("tools"):
                    leaks.append({"plugin": target["id"], "server": server, "source": "app_server_ready_tools"})
    return leaks


def _runtime_targets(plan: dict[str, Any]) -> list[dict[str, Any]]:
    targets = plan.get("runtime_targets")
    if not isinstance(targets, list):
        raise RuntimeProbeError("runtime_targets", "plan has no runtime targets")
    for target in targets:
        if (
            not isinstance(target, dict)
            or not isinstance(target.get("id"), str)
            or not isinstance(target.get("name"), str)
            or not isinstance(target.get("canonical_known"), bool)
            or not isinstance(target.get("allow_name_fallback"), bool)
            or not isinstance(target.get("skills"), list)
            or not all(isinstance(value, str) for value in target["skills"])
            or not isinstance(target.get("mcp_servers"), list)
            or not all(isinstance(value, str) for value in target["mcp_servers"])
        ):
            raise RuntimeProbeError("runtime_targets", "plan has malformed runtime target")
    return targets


def _app_policy(plan: dict[str, Any]) -> tuple[list[str], list[str]]:
    selected, excluded = plan.get("selected_app_ids", []), plan.get("excluded_app_ids", [])
    if not all(isinstance(values, list) and all(isinstance(item, str) and item for item in values)
               for values in (selected, excluded)):
        raise RuntimeProbeError("app_policy", "plan has malformed app policy")
    return sorted(set(selected)), sorted(set(excluded) - set(selected))


def _effective_apps(result: dict[str, Any], selected: list[str], excluded: list[str]) -> None:
    config = result.get("data", result)
    if isinstance(config, dict):
        config = config.get("config", config)
    if not isinstance(config, dict) or not isinstance(config.get("apps"), dict):
        raise RuntimeProbeError("config_schema", "config/read has no apps object")
    apps = config["apps"]
    default = apps.get("_default")
    if not isinstance(default, dict) or default.get("enabled") is not False:
        raise RuntimeProbeError("app_config_mismatch", "apps._default.enabled must be false")
    for app_id, expected in [(item, True) for item in selected] + [(item, False) for item in excluded]:
        row = apps.get(app_id)
        if not isinstance(row, dict) or row.get("enabled") is not expected:
            raise RuntimeProbeError("app_config_mismatch", f"app {app_id!r} does not have enabled={expected}")


def _app_rows(result: dict[str, Any]) -> tuple[list[dict[str, Any]], str | None]:
    rows = result.get("data")
    cursor = result.get("nextCursor")
    if not isinstance(rows, list) or (cursor is not None and not isinstance(cursor, str)):
        raise RuntimeProbeError("app_schema", "app/list must return data and optional string-or-null nextCursor")
    for row in rows:
        if not isinstance(row, dict) or not isinstance(row.get("id"), str) or not isinstance(row.get("isEnabled"), bool):
            raise RuntimeProbeError("app_schema", "app/list row needs string id and boolean isEnabled")
        if "callable" in row and not isinstance(row["callable"], bool):
            raise RuntimeProbeError("app_schema", f"app {row['id']} has non-boolean callable")
    return rows, cursor


def _installed_apps(result: dict[str, Any]) -> dict[str, dict[str, Any]]:
    rows = result.get("apps")
    if not isinstance(rows, list):
        raise RuntimeProbeError("app_schema", "app/installed result.apps must be an array")
    output: dict[str, dict[str, Any]] = {}
    for row in rows:
        if not isinstance(row, dict) or not isinstance(row.get("id"), str):
            raise RuntimeProbeError("app_schema", "app/installed row needs string id")
        if row["id"] in output:
            raise RuntimeProbeError("app_schema", f"app/installed repeats app {row['id']!r}")
        output[row["id"]] = row
    return output


def probe_runtime(
    runtime: dict[str, str],
    project: Path,
    targets: list[dict[str, Any]],
    *,
    plan: dict[str, Any],
    run_command: Any = _run_command,
    session_factory: Any = _StdioAppServerSession,
) -> dict[str, Any]:
    """Probe one runtime App Server session, including effective app policy."""
    session: Any = None
    status_rows: list[dict[str, Any]] = []
    try:
        session = session_factory(runtime["path"], project)
        initialized = session.request(
            {
                "id": 1,
                "method": "initialize",
                "params": {
                    "clientInfo": {
                        "name": "iysl-allow-plugins",
                        "title": "iysl-allow-plugins",
                        "version": "1",
                    },
                    "capabilities": {"experimentalApi": True},
                },
            }
        )
        _result(initialized, "initialize")
        session.notify({"method": "initialized", "params": {}})
        thread_response = session.request({"id": 2, "method": "thread/start", "params": {"cwd": str(project), "ephemeral": True}})
        thread_result = _result(thread_response, "thread/start")
        thread = thread_result.get("thread")
        if not isinstance(thread, dict) or not isinstance(thread.get("id"), str) or not thread["id"]:
            raise RuntimeProbeError("thread_schema", "thread/start result.thread.id must be a nonempty string")
        thread_id = thread["id"]
        selected_apps, excluded_apps = _app_policy(plan)
        config_response = session.request(
            {
                "id": 3, "method": "config/read",
                "params": {"cwd": str(project), "includeLayers": True},
            }
        )
        _effective_apps(_result(config_response, "config/read"), selected_apps, excluded_apps)

        app_rows: list[dict[str, Any]] = []
        cursor: str | None = None
        request_id = 4
        for _ in range(MAX_MCP_PAGES):
            response = session.request({
                "id": request_id, "method": "app/list",
                "params": {"threadId": thread_id, "cursor": cursor, "limit": 100, "forceRefetch": False},
            })
            rows, cursor = _app_rows(_result(response, "app/list"))
            app_rows.extend(rows)
            if cursor is None:
                break
            request_id += 1
        else:
            raise RuntimeProbeError("app_pagination", "too many app/list pages")
        by_id = {row["id"]: row for row in app_rows}
        for app_id in selected_apps:
            if app_id in by_id and by_id[app_id]["isEnabled"] is not True:
                raise RuntimeProbeError("app_runtime_mismatch", f"selected app {app_id!r} is disabled")
        for app_id in excluded_apps:
            if app_id in by_id and by_id[app_id]["isEnabled"] is not False:
                raise RuntimeProbeError("app_runtime_mismatch", f"excluded app {app_id!r} is enabled")
        response = session.request({
            "id": request_id + 1, "method": "app/installed",
            "params": {"threadId": thread_id, "forceRefresh": False},
        })
        request_id += 1
        installed_apps = _installed_apps(_result(response, "app/installed"))
        for app_id in excluded_apps:
            installed = installed_apps.get(app_id)
            if installed is not None and (
                not isinstance(installed.get("enabled"), bool) or not isinstance(installed.get("callable"), bool)
            ):
                raise RuntimeProbeError("app_schema", f"excluded installed app {app_id!r} lacks enabled/callable booleans")
            if installed is not None and (installed["enabled"] or installed["callable"]):
                raise RuntimeProbeError("app_runtime_mismatch", f"excluded installed app {app_id!r} is enabled or callable")

        skills_response = session.request({
            "id": request_id + 1, "method": "skills/list",
            "params": {"cwds": [str(project)], "forceReload": True},
        })
        request_id += 1
        skill_entries = _skill_entries(_result(skills_response, "skills/list"), project)

        cursor = None
        request_id += 1
        for _ in range(MAX_MCP_PAGES):
            status_response = session.request(
                {
                    "id": request_id,
                    "method": "mcpServerStatus/list",
                    "params": {"cursor": cursor, "limit": MCP_PAGE_LIMIT, "detail": "toolsAndAuthOnly"},
                }
            )
            rows, next_cursor = _mcp_entries(_result(status_response, "mcpServerStatus/list"))
            status_rows.extend(rows)
            if next_cursor is None:
                break
            cursor = next_cursor
            request_id += 1
        else:
            raise RuntimeProbeError("mcp_pagination", "too many MCP status pages")
        healthy = getattr(session, "ensure_healthy", None)
        if callable(healthy):
            healthy()
    finally:
        if session is not None:
            session.close()

    mcp_result = run_command([runtime["path"], "mcp", "list", "--json"], cwd=project)
    cli_servers = _parse_mcp_cli(mcp_result)
    skill_leaks = _verify_skills(skill_entries, targets)
    mcp_leaks = _verify_mcp(cli_servers, status_rows, targets)
    return {
        "ok": not skill_leaks and not mcp_leaks,
        "runtime": runtime,
        "leaked_skills": skill_leaks,
        "leaked_mcp": mcp_leaks,
    }


def verify_runtime_gate(
    plan: dict[str, Any],
    *,
    discoverer: Any = discover_runtimes,
    runtime_probe: Any = probe_runtime,
) -> dict[str, Any]:
    """Require every discoverable local runtime to enforce the generated mask."""
    try:
        targets = _runtime_targets(plan)
        runtimes = discoverer()
    except Exception as exc:
        return {"ok": False, "stage": "runtime_discovery", "probe_error": str(exc)}
    evidence: list[dict[str, str]] = []
    for runtime in runtimes:
        try:
            result = runtime_probe(runtime, Path(plan["project"]), targets, plan=plan)
        except Exception as exc:
            return {
                "ok": False,
                "stage": "runtime_probe",
                "runtime": runtime,
                "probe_error": str(exc),
            }
        if not isinstance(result, dict) or not isinstance(result.get("ok"), bool):
            return {
                "ok": False,
                "stage": "runtime_probe_schema",
                "runtime": runtime,
                "probe_error": "runtime probe did not return boolean ok",
            }
        if not result["ok"]:
            result.setdefault("runtime", runtime)
            result.setdefault("stage", "runtime_mismatch")
            return result
        evidence.append({key: runtime[key] for key in ("path", "source", "version")})
    return {"ok": True, "runtimes": evidence}


def _runtime_failure_result(
    project: Path, plan: dict[str, Any], evidence: dict[str, Any], *, rollback_error: Exception | None = None
) -> dict[str, Any]:
    result: dict[str, Any] = {
        "status": "rolled_back_runtime_mismatch" if rollback_error is None else "rollback_failed_runtime_mismatch",
        "project": str(project),
        "runtime_verified": False,
        "scope_enforceable": False,
        "allowed_plugins": plan["allowed_plugins"],
        "rollback_restored": rollback_error is None,
        "stage": evidence.get("stage", "runtime_mismatch"),
        "probe_error": evidence.get("probe_error"),
    }
    if rollback_error is not None:
        result["rollback_error"] = str(rollback_error)
        if isinstance(rollback_error, RollbackConflictError):
            result["rollback_conflicts"] = rollback_error.conflicts
    for key in ("runtime", "leaked_skills", "leaked_mcp"):
        if key in evidence:
            result[key] = evidence[key]
    return result


def _unsupported_scope_result(project: Path, plan: dict[str, Any]) -> dict[str, Any]:
    return {
        "status": "unsupported_project_scope",
        "project": str(project),
        "allowed_plugins": plan["allowed_plugins"],
        "runtime_verified": False,
        "scope_enforceable": False,
        "unsupported_capabilities": plan["unsupported_capabilities"],
    }


def _plan_preimage(project: Path, plan: dict[str, Any]) -> dict[Path, ManagedFileState]:
    preimage = plan.get("managed_preimage")
    expected_paths = {project / CONFIG_REL, project / ALLOWLIST_REL}
    if not isinstance(preimage, dict) or set(preimage) != expected_paths:
        raise AllowPluginsError("plan has no valid managed-file preimage")
    for state in preimage.values():
        if (
            not isinstance(state, tuple)
            or len(state) != 3
            or not isinstance(state[0], bool)
            or (state[0] and (not isinstance(state[1], bytes) or not isinstance(state[2], int)))
            or (not state[0] and (state[1] is not None or state[2] is not None))
        ):
            raise AllowPluginsError("plan has malformed managed-file preimage")
    return preimage


def apply_plan(plan: dict[str, Any], *, runtime_gate: Any = verify_runtime_gate) -> dict[str, Any]:
    project = Path(plan["project"])
    if plan.get("scope_enforceable") is False:
        return _unsupported_scope_result(project, plan)
    base = plan["base_config"]
    config_preexisting = plan.get("config_preexisting")
    if not isinstance(config_preexisting, bool):
        raise AllowPluginsError("plan has no valid config_preexisting metadata")
    separator = "\n" if base else ""
    config_text = base + separator + plan["managed_block"] + "\n"
    try:
        tomllib.loads(config_text)
        tomllib.loads(_allowlist_text(plan["allowed_plugins"], config_preexisting=config_preexisting, fingerprint=plan["fingerprint"], host_plugins=plan["host_plugins"]))
    except tomllib.TOMLDecodeError as exc:
        raise AllowPluginsError(f"generated TOML did not validate: {exc}") from exc
    snapshots = _snapshot_managed_files(project)
    if snapshots != _plan_preimage(project, plan):
        raise AllowPluginsError("managed files changed after planning; rebuild inventory and plan before apply")
    config_path = project / CONFIG_REL
    allow_path = project / ALLOWLIST_REL
    allow_text = _allowlist_text(plan["allowed_plugins"], config_preexisting=config_preexisting, fingerprint=plan["fingerprint"], host_plugins=plan["host_plugins"])
    generated = dict(snapshots)
    with _transaction_sigterm_guard():
        try:
            try:
                config_mode = snapshots[config_path][2] if snapshots[config_path][0] else 0o644
                generated[config_path] = (True, config_text.encode("utf-8"), config_mode)
                _atomic_write(config_path, config_text, mode=config_mode, expected=snapshots[config_path])
                allow_mode = snapshots[allow_path][2] if snapshots[allow_path][0] else 0o644
                generated[allow_path] = (True, allow_text.encode("utf-8"), allow_mode)
                _atomic_write(allow_path, allow_text, mode=allow_mode, expected=snapshots[allow_path])
            except Exception as exc:
                try:
                    _restore_managed_files(snapshots, expected_current=generated)
                except Exception as rollback_error:
                    raise AllowPluginsError(f"apply write failed and rollback failed: {rollback_error}") from exc
                raise
            try:
                evidence = runtime_gate(plan)
            except Exception as exc:
                evidence = {"ok": False, "stage": "runtime_gate_exception", "probe_error": str(exc)}
            if isinstance(evidence, dict) and evidence.get("ok") is True:
                try:
                    final_state = _snapshot_managed_files(project)
                except Exception as exc:
                    evidence = {
                        "ok": False,
                        "stage": "post_probe_state",
                        "probe_error": f"cannot read managed files after runtime verification: {exc}",
                    }
                else:
                    if final_state == generated:
                        return {
                            "status": "applied_runtime_verified",
                            "project": str(project),
                            "allowed_plugins": plan["allowed_plugins"],
                            "runtime_verified": True,
                            "scope_enforceable": True,
                            "runtimes": evidence.get("runtimes", []),
                        }
                    evidence = {
                        "ok": False,
                        "stage": "post_probe_state",
                        "probe_error": "managed files changed after runtime verification",
                    }
            if not isinstance(evidence, dict) or evidence.get("ok") is not True:
                if not isinstance(evidence, dict):
                    evidence = {
                        "ok": False,
                        "stage": "runtime_gate_schema",
                        "probe_error": "runtime gate did not return an object",
                    }
                try:
                    _restore_managed_files(snapshots, expected_current=generated)
                except Exception as exc:
                    return _runtime_failure_result(project, plan, evidence, rollback_error=exc)
                return _runtime_failure_result(project, plan, evidence)
            raise AllowPluginsError("runtime gate returned an unsupported success state")
        except KeyboardInterrupt:
            try:
                _restore_managed_files(snapshots, expected_current=generated)
            except Exception as rollback_error:
                raise AllowPluginsError(f"apply interrupted and rollback failed: {rollback_error}") from None
            raise


def validate_state(inventory: dict[str, Any], *, runtime_gate: Any = verify_runtime_gate) -> dict[str, Any]:
    allowed = inventory.get("previous_allowlist")
    if allowed is None:
        return {"status": "not_configured", "project": inventory["project"]}
    if inventory.get("allowlist_schema_version") == 1:
        return {
            "status": "migration_required", "project": inventory["project"],
            "allowed_plugins": allowed, "runtime_verified": False,
            "message": "rerun $iysl-allow-plugins and confirm apply to migrate schema v1 to v2",
        }
    plan = build_plan(inventory, allowed)
    if plan["scope_enforceable"] is False:
        return _unsupported_scope_result(Path(inventory["project"]), plan)
    if plan["fingerprint"] != inventory.get("saved_fingerprint"):
        return {
            "status": "capability_drift",
            "project": inventory["project"],
            "allowed_plugins": allowed,
            "runtime_verified": False,
            "scope_enforceable": False,
            "message": "plugin capability inputs changed; rerun $iysl-allow-plugins",
        }
    _, _, actual = _read_project_config(Path(inventory["project"]))
    if actual != plan["managed_block"]:
        raise AllowPluginsError("managed block does not match the saved allowlist and live inventory")
    try:
        evidence = runtime_gate(plan)
    except Exception as exc:
        evidence = {"ok": False, "stage": "runtime_gate_exception", "probe_error": str(exc)}
    if isinstance(evidence, dict) and evidence.get("ok") is True:
        try:
            final_state = _snapshot_managed_files(Path(inventory["project"]))
        except Exception as exc:
            evidence = {
                "ok": False,
                "stage": "post_probe_state",
                "probe_error": f"cannot read managed files after runtime verification: {exc}",
            }
        else:
            if final_state != _plan_preimage(Path(inventory["project"]), plan):
                evidence = {
                    "ok": False,
                    "stage": "post_probe_state",
                    "probe_error": "managed files changed during runtime verification",
                }
    if not isinstance(evidence, dict) or evidence.get("ok") is not True:
        if not isinstance(evidence, dict):
            evidence = {
                "ok": False,
                "stage": "runtime_gate_schema",
                "probe_error": "runtime gate did not return an object",
            }
        result: dict[str, Any] = {
            "status": "runtime_mismatch",
            "project": inventory["project"],
            "allowed_plugins": allowed,
            "runtime_verified": False,
            "scope_enforceable": False,
            "stage": evidence.get("stage", "runtime_mismatch"),
            "probe_error": evidence.get("probe_error"),
        }
        for key in ("runtime", "leaked_skills", "leaked_mcp"):
            if key in evidence:
                result[key] = evidence[key]
        return result
    return {
        "status": "valid_runtime_verified",
        "project": inventory["project"],
        "allowed_plugins": allowed,
        "runtime_verified": True,
        "scope_enforceable": True,
        "runtimes": evidence.get("runtimes", []),
    }


def remove_state(project: Path, confirm: bool, *, unlink: Any = Path.unlink) -> dict[str, Any]:
    base, _, managed = _read_project_config(project)
    allow_path = project / ALLOWLIST_REL
    if allow_path.is_symlink():
        raise AllowPluginsError(f"refusing symlinked allowlist: {allow_path}")
    allowlist_state = _load_allowlist(project)
    if (allowlist_state is None) != (managed is None):
        raise AllowPluginsError("allowlist file and managed config block are out of sync")
    config_preexisting = allowlist_state["config_preexisting"] if allowlist_state is not None else False
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
    snapshots = _snapshot_managed_files(project)
    base, _, managed = _read_project_config(project)
    if _snapshot_managed_files(project) != snapshots:
        raise AllowPluginsError("managed files changed before remove; retry from a fresh preview")
    config_path = project / CONFIG_REL
    generated = dict(snapshots)
    try:
        with _transaction_sigterm_guard():
            if managed is not None:
                if base.strip():
                    try:
                        tomllib.loads(base)
                    except tomllib.TOMLDecodeError as exc:
                        raise AllowPluginsError(f"remaining project TOML would be invalid: {exc}") from exc
                if base.strip() or config_preexisting:
                    config_mode = snapshots[config_path][2] if snapshots[config_path][0] else 0o644
                    generated[config_path] = (True, base.encode("utf-8"), config_mode)
                    _atomic_write(
                        config_path,
                        base,
                        mode=config_mode,
                        expected=snapshots[config_path],
                    )
                elif config_path.exists():
                    generated[config_path] = (False, None, None)
                    _unlink_if_expected(config_path, expected=snapshots[config_path], unlink=unlink)
            if allow_path.exists():
                generated[allow_path] = (False, None, None)
                _unlink_if_expected(allow_path, expected=snapshots[allow_path], unlink=unlink)
    except TransactionTerminated:
        try:
            _restore_managed_files(snapshots, expected_current=generated)
        except Exception as rollback_error:
            raise AllowPluginsError(f"remove terminated and rollback failed: {rollback_error}") from None
        raise
    except KeyboardInterrupt:
        try:
            _restore_managed_files(snapshots, expected_current=generated)
        except Exception as rollback_error:
            raise AllowPluginsError(f"remove interrupted and rollback failed: {rollback_error}") from None
        raise
    except Exception as exc:
        try:
            _restore_managed_files(snapshots, expected_current=generated)
        except Exception as rollback_error:
            raise AllowPluginsError(f"remove failed and rollback failed: {rollback_error}") from exc
        raise AllowPluginsError(f"remove failed; managed files were restored: {exc}") from exc
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
            '<button class="btn btn-primary" type="button" data-apply>檢查並套用</button>',
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
            "  root.querySelector('[data-apply]').addEventListener('click', async () => {",
            "    const selected = [...root.querySelectorAll('input[type=checkbox]:checked')].map(input => input.value);",
            "    const status = root.querySelector('[data-status]');",
            "    status.textContent = '正在送出…';",
            "    try {",
            "      await window.openai.sendFollowUpMessage({",
            f"        prompt: '$iysl-allow-plugins 對 Project ' + {_json_string(inventory['project'])} + ' 檢查並套用這份選擇；這則訊息是唯一確認。重新 inventory，僅對可驗證 scope 套用並驗證。\\nselected_plugins = ' + JSON.stringify(selected),",
            "        title: '檢查並套用'",
            "      });",
            "      status.textContent = '已送出；會檢查 scope，必要時才套用並驗證。';",
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


def hook_check(project_raw: str, *, global_config: str | None = None, desktop_codex: str | None = None) -> int:
    """Read-only SessionStart drift sentinel.  It intentionally never starts App Server."""
    try:
        project = _project_path(project_raw)
        saved = _load_allowlist(project)
        if saved is None or saved["schema_version"] != SCHEMA_VERSION:
            raise AllowPluginsError("managed v2 allowlist is unavailable")
        args = argparse.Namespace(
            project=str(project), global_config=global_config, plugin_list_json=None,
            host_plugin=saved["host_plugins"], desktop_codex=desktop_codex,
        )
        inventory = build_inventory(args)
        plan = build_plan(inventory, saved["allowed_plugins"])
        _, _, actual = _read_project_config(project)
        if actual == plan["managed_block"] and plan["fingerprint"] == saved["fingerprint"]:
            return 0
        detail = "Project plugin capability profile changed"
    except Exception as exc:
        detail = f"Project plugin capability drift check failed: {exc}"
    sys.stdout.write(json.dumps({
        "systemMessage": detail + "; rerun $iysl-allow-plugins.",
        "hookSpecificOutput": {
            "hookEventName": "SessionStart",
            "additionalContext": "This SessionStart check is read-only and did not repair project configuration.",
        },
    }, ensure_ascii=False) + "\n")
    return 0


def _add_inventory_args(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--project", required=True)
    parser.add_argument("--global-config")
    parser.add_argument("--plugin-list-json", help="Use captured CLI JSON instead of running codex")
    parser.add_argument("--desktop-codex", help=argparse.SUPPRESS)
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
    hook = subparsers.add_parser("hook-check", help=argparse.SUPPRESS)
    hook.add_argument("--project", required=True)
    hook.add_argument("--global-config")
    hook.add_argument("--desktop-codex", help=argparse.SUPPRESS)
    return parser


def main(argv: list[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    try:
        if args.command == "hook-check":
            return hook_check(args.project, global_config=args.global_config, desktop_codex=args.desktop_codex)
        if args.command in {"inventory", "plan", "apply", "validate"} and platform.system() != "Darwin":
            raise AllowPluginsError("iysl-allow-plugins v2 requires macOS Codex Desktop")
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
                result = apply_plan(plan)
                _write_output(None, result)
                return 0 if result["status"] == "applied_runtime_verified" else 1
            else:
                public_plan = {
                    key: value
                    for key, value in plan.items()
                    if key not in {"base_config", "runtime_targets", "managed_preimage"}
                }
                _write_output(None, public_plan)
        elif args.command == "validate":
            result = validate_state(build_inventory(args))
            _write_output(None, result)
            return 0 if result["status"] in {"valid_runtime_verified", "not_configured"} else 1
        elif args.command == "remove":
            _write_output(None, remove_state(_project_path(args.project), args.confirm_remove))
        return 0
    except AllowPluginsError as exc:
        sys.stderr.write(f"error: {exc}\n")
        return 2
    except TransactionTerminated:
        sys.stderr.write("error: terminated; transaction rollback was attempted\n")
        return 128 + signal.SIGTERM
    except KeyboardInterrupt:
        sys.stderr.write("error: interrupted; transaction rollback was attempted\n")
        return 130


if __name__ == "__main__":
    raise SystemExit(main())
