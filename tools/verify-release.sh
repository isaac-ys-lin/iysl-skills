#!/usr/bin/env bash
set -euo pipefail

repo_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$repo_root"
export PYTHONDONTWRITEBYTECODE=1
export PYTHONIOENCODING=utf-8
export PYTHONUTF8=1

python_bin="${PYTHON:-}"
if [[ -z "$python_bin" ]]; then
  if command -v python3 >/dev/null 2>&1; then
    python_bin="python3"
  else
    python_bin="python"
  fi
fi

"$python_bin" -m pytest -q tests
"$python_bin" tools/verify_behavior_evals.py

for skill_dir in skills/*; do
  [[ -d "$skill_dir" ]] || continue
  PYTHON="$python_bin" tools/verify-skill.sh "$(basename "$skill_dir")"
done

echo "portable release gates passed"
