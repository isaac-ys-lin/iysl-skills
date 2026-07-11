#!/usr/bin/env bash
set -euo pipefail

repo_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
source_ref="${1:-$repo_root}"
skills_cli_version="${SKILLS_CLI_VERSION:-1.5.16}"
tmp_home="$(mktemp -d "${TMPDIR:-/tmp}/iysl-skills-npx-home.XXXXXX")"
trap 'rm -rf "$tmp_home"' EXIT

HOME="$tmp_home" npx --yes "skills@$skills_cli_version" add "$source_ref" \
  --agent codex \
  --global \
  --yes

python3 "$repo_root/tools/compare-installed-skills.py" \
  "$repo_root/skills" \
  "$tmp_home/.agents/skills"

echo "isolated npx install verified with skills@$skills_cli_version from $source_ref"
