# Runbook

## Baseline checks

- Repository state:
  - `git status --short --branch`
- Protocol baseline present:
  - `test -f protocols/AGENT_INTEROP_V1.md && echo ok`

## Search hygiene

- Prefer repo-local scoped searches.
- Use `.rgignore` and `.ignore` to avoid scanning heavy paths.
