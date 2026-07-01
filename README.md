# iysl-skills

Personal Codex skill source repository.

## Structure

```text
skills/
  <skill-name>/
    SKILL.md
    assets/
    references/
    reports/
    scripts/
    tests/
tools/
  install-skill.sh
  verify-skill.sh
```

## Source Of Truth

- This repo is the source of truth for personal skills.
- Installed live skills live under `~/.codex/skills/<skill-name>`.
- Generated outputs, caches, virtual environments, and local render artifacts do not belong in this repo.

## Included Skills

- `iysl-anidiagram`
- `iysl-deck-ab`

## Install A Skill Locally

```bash
tools/install-skill.sh iysl-anidiagram
```

## Verify A Skill

```bash
tools/verify-skill.sh iysl-anidiagram
```

Verification runs the skill tests, renders representative specs with `--verify --check`, and checks that the skill is prompt-visible to Codex.
