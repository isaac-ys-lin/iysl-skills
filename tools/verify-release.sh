#!/usr/bin/env bash
set -euo pipefail

repo_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$repo_root"
export PYTHONDONTWRITEBYTECODE=1

python3 -m unittest tests.test_skill_inventory tests.test_package_contract

for skill_dir in skills/*; do
  [[ -d "$skill_dir" ]] || continue
  tools/verify-skill.sh "$(basename "$skill_dir")"
done

echo "portable release gates passed"
