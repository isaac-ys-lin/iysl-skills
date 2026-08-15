# Skills update: Oracle parity

Status: Complete
Last updated: 2026-08-08

## Final contract

- Update the explicitly requested Oracle stack only; do not install recommended plugins or add Oracle to the iysl-skills inventory.
- Keep the iysl-managed skills sourced from `/Users/isaacyslin/Code/iysl-skills`; their live entries remain symlinks to that repository.
- Keep API consults consent-gated; maintenance verification uses local help, dry-run, and structural checks only.

## Outcome

- Updated global `@steipete/oracle` from `0.16.1` to `0.17.1`.
- Updated `/Users/isaacyslin/.codex/skills/oracle/SKILL.md` to match the current upstream skill, including GPT-5.6 Extra High browser guidance and API Pro reasoning-mode guidance.
- Confirmed the local iysl-skills `main` matched `origin/main` before the task; no iysl skill source content required an upstream update.

## Verification

- `oracle --version`: `0.17.1`.
- Oracle help exposes `--reasoning-mode`, `--reasoning-effort`, browser follow-up, Project Sources, archive, and remote-browser controls.
- Browser GPT-5.6 `extra-high` dry-run and API GPT-5.6 Pro dry-run passed without model calls.
- Upstream raw `skills/oracle/SKILL.md` parity check passed; `quick_validate.py` passed via `uv run --with pyyaml`.
- iysl repository contract: `21 passed, 6 subtests passed`; all seven portable skill verifiers passed; all seven live-install checks returned success, with `writing-great-skills` correctly verified as explicit-only metadata parity.
- Generated Python caches and duplicate test processes were cleaned up; no skills-repo residue remained.

## Limits and preserved state

- No paid API call or live browser consult was made; model/account access remains unverified at runtime.
- Desktop remote-plugin catalog visibility was not inferred from CLI checks.
- The unrelated in-flight modification to `skills/equity-data/templates/collected-data-matrix.md` was preserved and not included in this task.
