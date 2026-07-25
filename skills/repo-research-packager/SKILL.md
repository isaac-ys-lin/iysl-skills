---
name: repo-research-packager
description: Curate a software repository into a focused, self-contained Markdown research pack for another AI, using Taiwan Traditional Chinese by default. Use for product research, architecture review, planning, debugging, security analysis, or feature ideation when the receiving AI cannot access the repository.
---

# Repo Research Packager

Create one evidence-dense Markdown handoff. Let the model decide what matters;
use the bundled assembler for deterministic formatting, safety, and budget
enforcement.

## Contract

- Make the pack self-contained and trace major claims to embedded source.
- Separate repository facts, external facts, hypotheses, proposals, and open
  questions.
- Select the smallest evidence set that still explains the relevant
  architecture, flows, contracts, state, failure behavior, and tests.
- Preserve repository-relative paths and line ranges. Keep code, identifiers,
  and commands verbatim.
- Exclude secrets, personal or user data, binaries, generated outputs,
  dependencies, and irrelevant implementation detail.
- Keep packaging read-only. Do not confuse the working tree with a shipped or
  deployed baseline.
- Default to natural Taiwan Traditional Chinese and one `.md` file. Use another
  language or ZIP only when explicitly requested.

## Method

1. Read repository instructions and authoritative project, architecture,
   release, build, and Git context.
2. Map the research-relevant system before choosing full files or focused line
   slices. Give every selection a one-sentence reason.
3. Print the manifest template and replace its placeholders with the objective,
   verified context, constraints, open questions, and repository-relative
   evidence:

```bash
skill_dir="${AGENTS_HOME:-$HOME/.agents}/skills/repo-research-packager"
python3 "$skill_dir/scripts/assemble_research_pack.py" --print-template > manifest.json
```

4. Assemble the pack:

```bash
python3 "$skill_dir/scripts/assemble_research_pack.py" \
  --repo /absolute/path/to/repository \
  --manifest /absolute/path/to/manifest.json \
  --output /absolute/path/to/research-pack.md
```

Use `--force` only to replace a previously verified generated pack. If the
budget fails, improve evidence density or split independent research questions;
do not silently remove load-bearing evidence.

## Quality gate

Before delivery, verify that:

- The receiving AI can explain the product, relevant architecture, primary
  flow, research objective, and evidence gaps without repository access.
- Current behavior and proposals remain distinguishable.
- Claims are traceable to selected evidence and line ranges remain current.
- The output is valid UTF-8 Markdown within budget and contains no secrets,
  personal data, or absolute home-directory paths.
- Temporary manifests and other packaging residue are removed.

Unless the user specifies otherwise, write the result to:

```text
<repo>/output/research-packs/<repository>-<topic>-YYYYMMDD.md
```

Report the output path, source commit, estimated size, exclusions, and known
evidence gaps.
