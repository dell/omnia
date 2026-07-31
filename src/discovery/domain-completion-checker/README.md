# domain-completion-checker

Validates Omnia domain Galaxy compliance, structure, input validation patterns, and domain independence. Generates a scored report with actionable items.

## When to Use

- Assessing a domain's readiness for Galaxy packaging
- Reviewing domain structure during migration from legacy to mono-repo
- CI/CD quality gate for domain PRs
- Sprint planning to identify remaining domain compliance work

## Quick Start

Invoke: `@domain-completion-checker` then provide the domain path (e.g., `src/repo_manager`).

## Output

A scored report (0-100) with per-category breakdown and a prioritized list of pending items.

## Reference Documents

- `docs/design/omnia-domain-repo-design.md` — Domain structure rules
- `docs/design/domain-integration.md` — Integration contract rules
- `docs/code-style/python.md` §5 (Galaxy doc blocks), §6 (input validation structure)
- `docs/code-style/ansible.md` §10 (Galaxy role requirements)
