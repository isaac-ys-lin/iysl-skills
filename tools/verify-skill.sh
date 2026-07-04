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
outdir="${TMPDIR:-/tmp}/codex-skill-verify-$skill_name"

if [[ ! -f "$skill_dir/SKILL.md" ]]; then
  echo "missing skill: $skill_dir/SKILL.md" >&2
  exit 1
fi

cd "$skill_dir"

if [[ -d tests ]]; then
  "$python_bin" -m unittest discover -s tests
fi

rm -rf "$outdir"
mkdir -p "$outdir"

if [[ -f scripts/render_animated_diagram.py ]] && compgen -G "assets/*-spec.json" >/dev/null; then
  for spec in assets/*-spec.json; do
    base="$(basename "$spec" .json)"
    "$python_bin" scripts/render_animated_diagram.py \
      --spec "$spec" \
      --outdir "$outdir/$base" \
      --basename "$base" \
      --verify \
      --check >/dev/null
  done
fi

if [[ -f scripts/render_animated_diagram.py ]] && [[ -d examples/gallery ]]; then
  gallery_spec_list="$outdir/gallery-specs-list"

  if ! find examples/gallery -name spec.json -print0 | sort -z > "$gallery_spec_list"; then
    echo "failed to enumerate gallery specs in examples/gallery" >&2
    exit 1
  fi

  while IFS= read -r -d '' spec; do
    rel="${spec#./}"
    base="${rel%/spec.json}"
    base="${base//\//-}"
    if ! render_output="$("$python_bin" scripts/render_animated_diagram.py \
      --spec "$spec" \
      --outdir "$outdir/gallery-$base" \
      --basename "$base" \
      --verify \
      --check 2>&1)"; then
      echo "failed to render gallery spec: $spec" >&2
      echo "$render_output" >&2
      exit 1
    fi
  done < "$gallery_spec_list"
fi

codex debug prompt-input "\$$skill_name verify prompt visibility" | grep -E "$skill_name|ani-diagram|animated explanatory diagrams" >/dev/null

echo "verified $skill_name"
