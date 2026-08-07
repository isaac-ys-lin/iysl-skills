#!/usr/bin/env bash
set -euo pipefail

if [[ $# -ne 1 ]]; then
  echo "usage: tools/verify-live-install.sh <skill-name>" >&2
  exit 2
fi

skill_name="$1"
repo_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
skill_dir="$repo_root/skills/$skill_name"
live_dir="${AGENTS_HOME:-$HOME/.agents}/skills/$skill_name"

if [[ ! -f "$skill_dir/SKILL.md" ]]; then
  echo "missing source skill: $skill_dir/SKILL.md" >&2
  exit 1
fi

if [[ ! -f "$live_dir/SKILL.md" ]]; then
  echo "missing live skill: $live_dir/SKILL.md" >&2
  exit 1
fi

source_resolved="$(cd "$skill_dir" && pwd -P)"
live_resolved="$(cd "$live_dir" && pwd -P)"
if [[ "$live_resolved" != "$source_resolved" ]]; then
  echo "live source mismatch: expected=$source_resolved actual=$live_resolved" >&2
  exit 1
fi

description="$(sed -n 's/^description:[[:space:]]*//p' "$skill_dir/SKILL.md" | head -1)"
if [[ -z "$description" ]]; then
  echo "missing frontmatter description: $skill_dir/SKILL.md" >&2
  exit 1
fi

disable_model_invocation="$(
  sed -n 's/^disable-model-invocation:[[:space:]]*//p' "$skill_dir/SKILL.md" \
    | head -1
)"
if [[ "$disable_model_invocation" == "true" ]]; then
  if ! grep -F "allow_implicit_invocation: false" \
    "$skill_dir/agents/openai.yaml" >/dev/null; then
    echo "explicit-only metadata mismatch: $skill_dir" >&2
    exit 1
  fi

  echo "live install metadata parity only (explicit-only; verify invocation in a fresh task): $skill_name -> $live_dir"
  exit 0
fi

codex debug prompt-input 'verify installed skill catalog visibility' \
  | grep -F "$description" >/dev/null

echo "live install visible: $skill_name -> $live_dir"
