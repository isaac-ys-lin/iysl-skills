#!/usr/bin/env bash
set -euo pipefail

if [[ $# -ne 1 ]]; then
  echo "usage: tools/install-skill.sh <skill-name>" >&2
  exit 2
fi

skill_name="$1"
repo_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
source_dir="$repo_root/skills/$skill_name"
target_dir="${CODEX_HOME:-$HOME/.codex}/skills/$skill_name"

if [[ ! -f "$source_dir/SKILL.md" ]]; then
  echo "missing skill: $source_dir/SKILL.md" >&2
  exit 1
fi

mkdir -p "$(dirname "$target_dir")"
rsync -a --delete \
  --exclude='__pycache__/' \
  --exclude='.pytest_cache/' \
  --exclude='.venv/' \
  --exclude='outputs/' \
  "$source_dir/" "$target_dir/"

echo "installed $skill_name -> $target_dir"
