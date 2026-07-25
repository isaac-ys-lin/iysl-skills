#!/usr/bin/env bash
set -euo pipefail

repo_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
source_ref="${1:-$repo_root}"
skills_cli_version="${SKILLS_CLI_VERSION:-1.5.16}"
tmp_home="$(mktemp -d "${TMPDIR:-/tmp}/iysl-skills-npx-home.XXXXXX")"
trap 'rm -rf "$tmp_home"' EXIT
python_bin="${PYTHON:-}"
if [[ -z "$python_bin" ]]; then
  if command -v python3 >/dev/null 2>&1; then
    python_bin="python3"
  else
    python_bin="python"
  fi
fi

HOME="$tmp_home" \
USERPROFILE="$tmp_home" \
AGENTS_HOME="$tmp_home/.agents" \
CODEX_HOME="$tmp_home/.codex" \
npx --yes "skills@$skills_cli_version" add "$source_ref" \
  --agent codex \
  --global \
  --yes

"$python_bin" "$repo_root/tools/compare-installed-skills.py" \
  "$repo_root/skills" \
  "$tmp_home/.agents/skills"

echo "isolated npx install verified with skills@$skills_cli_version from $source_ref"
