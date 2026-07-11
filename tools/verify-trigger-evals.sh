#!/usr/bin/env bash
set -euo pipefail

repo_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
yao_root="${YAO_META_SKILL_DIR:-${AGENTS_HOME:-$HOME/.agents}/skills/yao-meta-skill}"
evaluator="$yao_root/scripts/trigger_eval.py"

if [[ ! -f "$evaluator" ]]; then
  echo "missing Yao trigger evaluator: $evaluator" >&2
  exit 1
fi

evaluated=0
for skill_dir in "$repo_root"/skills/*; do
  cases="$skill_dir/evals/trigger_cases.json"
  config="$skill_dir/evals/semantic_config.json"
  if [[ ! -f "$cases" || ! -f "$config" ]]; then
    continue
  fi

  python3 "$evaluator" \
    --description-file "$skill_dir/SKILL.md" \
    --cases "$cases" \
    --semantic-config "$config" >/dev/null
  evaluated=$((evaluated + 1))
done

if [[ $evaluated -eq 0 ]]; then
  echo "no trigger eval packages found" >&2
  exit 1
fi

echo "trigger evals verified for $evaluated skills"
