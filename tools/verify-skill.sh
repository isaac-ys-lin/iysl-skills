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

  # Detection must not depend on a single optional tool (rg): when it is absent
  # or unresolved in the caller's context the old code silently fell back to
  # `unittest discover`, which exits 0 on "Ran 0 tests" and reports false green.
  # Use portable grep, and fail loudly if test files exist but nothing ran.
  if [[ ${#test_files[@]} -gt 0 ]] \
     && grep -lE '^(import|from) pytest' "${test_files[@]}" >/dev/null 2>&1; then
    "$python_bin" -m pytest -q -p no:cacheprovider tests
  else
    if output="$("$python_bin" -m unittest discover -s tests 2>&1)"; then
      printf '%s\n' "$output"
    else
      status=$?
      printf '%s\n' "$output"
      exit "$status"
    fi
    if [[ ${#test_files[@]} -gt 0 ]] && grep -Eq 'Ran 0 tests|NO TESTS RAN' <<<"$output"; then
      echo "verify-skill: tests/test_*.py present but unittest ran 0 tests" \
           "(pytest-style tests need a resolvable pytest)" >&2
      exit 1
    fi
  fi
fi

echo "verified $skill_name"
