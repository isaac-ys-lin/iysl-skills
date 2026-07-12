#!/usr/bin/env bash
set -euo pipefail

if [[ $# -ne 1 ]]; then
  echo "usage: tools/verify-skill.sh <skill-name>" >&2
  exit 2
fi

skill_name="$1"
repo_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
skill_dir="$repo_root/skills/$skill_name"
python_bin="${PYTHON:-python3}"
outdir="$(mktemp -d "${TMPDIR:-/tmp}/codex-skill-verify-$skill_name.XXXXXX")"
trap 'rm -rf "$outdir"' EXIT
export PYTHONDONTWRITEBYTECODE=1

if [[ ! -f "$skill_dir/SKILL.md" ]]; then
  echo "missing skill: $skill_dir/SKILL.md" >&2
  exit 1
fi

cd "$skill_dir"

if [[ -d tests ]]; then
  shopt -s nullglob
  test_files=(tests/test_*.py)
  shopt -u nullglob

  # Pytest collects both pytest functions and unittest.TestCase classes. Always
  # use it when test files exist so a mixed suite cannot be partially skipped.
  if [[ ${#test_files[@]} -gt 0 ]]; then
    "$python_bin" -m pytest -q -p no:cacheprovider tests
  fi
fi

echo "verified $skill_name"
