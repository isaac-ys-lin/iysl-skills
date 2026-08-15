#!/usr/bin/env bash
set -euo pipefail
export PYTHONIOENCODING=utf-8
export PYTHONUTF8=1

repo_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
yao_root="${YAO_META_SKILL_DIR:-${AGENTS_HOME:-$HOME/.agents}/skills/yao-meta-skill}"
evaluator="$yao_root/scripts/trigger_eval.py"
python_bin="${PYTHON:-}"
if [[ -z "$python_bin" ]]; then
  if command -v python3 >/dev/null 2>&1; then
    python_bin="python3"
  else
    python_bin="python"
  fi
fi

if [[ ! -f "$evaluator" ]]; then
  echo "missing Yao trigger evaluator: $evaluator" >&2
  exit 1
fi

trigger_skills="$("$python_bin" - "$repo_root" <<'PY' | tr -d '\r'
import sys
from pathlib import Path

root = Path(sys.argv[1])
sys.path.insert(0, str(root))
from tools.skill_manifest import load_manifest

manifest = load_manifest(root)
for name, entry in sorted(manifest["skills"].items()):
    if "trigger" in entry.get("required_gates", []):
        print(name)
PY
)"

if [[ -z "$trigger_skills" ]]; then
  echo "no manifest skills require trigger evals" >&2
  exit 1
fi

evaluated=0
while IFS= read -r skill_name; do
  [[ -n "$skill_name" ]] || continue
  skill_dir="$repo_root/skills/$skill_name"
  cases="$skill_dir/evals/trigger_cases.json"
  config="$skill_dir/evals/semantic_config.json"
  if [[ ! -f "$cases" ]]; then
    echo "$skill_name: missing required trigger cases: $cases" >&2
    exit 1
  fi
  if [[ ! -f "$config" ]]; then
    echo "$skill_name: missing required semantic config: $config" >&2
    exit 1
  fi

  "$python_bin" "$evaluator" \
    --description-file "$skill_dir/SKILL.md" \
    --cases "$cases" \
    --semantic-config "$config" >/dev/null
  evaluated=$((evaluated + 1))
done <<< "$trigger_skills"

expected=$(printf '%s\n' "$trigger_skills" | sed '/^$/d' | wc -l | tr -d ' ')
if [[ $evaluated -ne $expected ]]; then
  echo "trigger eval coverage mismatch: expected=$expected evaluated=$evaluated" >&2
  exit 1
fi

echo "trigger evals verified for $evaluated skills"
