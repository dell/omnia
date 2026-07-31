---
name: domain-completion-checker
description: "Validates Omnia domain Galaxy compliance, structure, input validation, independence, and code quality/security gates. Use when assessing domain migration readiness or scoring domain completion."
---

# domain-completion-checker

## When to Use

Activate when assessing an Omnia domain's compliance with the Galaxy collection structure, coding standards, code quality/security gates, and domain independence rules defined in `docs/design/omnia-domain-repo-design.md` and `docs/design/domain-integration.md`.

## Instructions

### Input

The user provides a domain path relative to `src/` (e.g., `repo_manager`, `image_build_manager`, `discovery`).

### Step 1 — Load Reference Documents

Read these files before scanning:

1. `docs/design/omnia-domain-repo-design.md` — Domain structure, roles, modules, tags, contracts
2. `docs/design/domain-integration.md` — copy-input.sh, status files, env vars, execution order
3. `docs/code-style/python.md` — Galaxy doc blocks (§5), input validation structure (§6), security gates (§7)
4. `docs/code-style/ansible.md` — Galaxy role requirements (§10), security gates (§11)

### Step 2 — Scan Domain Directory

Run the checks from the checklist in [Scoring Rubric](#scoring-rubric) against `src/<domain>/`.

For each category, collect:
- **PASS**: Requirement fully met
- **PARTIAL**: Partially met (explain what's missing)
- **FAIL**: Not met at all

### Step 3 — Generate Report

Output the report in this format:

```markdown
# Domain Completion Report: <domain_name>

**Date**: YYYY-MM-DD
**Score**: XX/100
**Status**: NOT_STARTED | IN_PROGRESS | COMPLIANT

## Score Breakdown

| # | Category | Weight | Score | Max | Status |
|---|----------|--------|-------|-----|--------|
| 1 | Galaxy Structure | 15 | X | 15 | PASS/PARTIAL/FAIL |
| 2 | Module Documentation | 10 | X | 10 | PASS/PARTIAL/FAIL |
| 3 | Role Metadata | 10 | X | 10 | PASS/PARTIAL/FAIL |
| 4 | Input Validation Structure | 10 | X | 10 | PASS/PARTIAL/FAIL |
| 5 | Entry Point & Tags | 10 | X | 10 | PASS/PARTIAL/FAIL |
| 6 | Domain Integration | 10 | X | 10 | PASS/PARTIAL/FAIL |
| 7 | FQCN Usage | 5 | X | 5 | PASS/PARTIAL/FAIL |
| 8 | ansible.cfg Compliance | 5 | X | 5 | PASS/PARTIAL/FAIL |
| 9 | Documentation | 5 | X | 5 | PASS/PARTIAL/FAIL |
| 10 | Domain Independence | 5 | X | 5 | PASS/PARTIAL/FAIL |
| 11 | Code Quality & Security | 15 | X | 15 | PASS/PARTIAL/FAIL |
| | **Total** | | **XX** | **100** | |

## Galaxy Change Summary (if applicable)

Include this section only if the domain has a `CHANGELOG.md`. List:
- Current version from `galaxy.yml`
- Last changelog entry summary
- Whether the changelog covers recent code changes

## Detailed Findings

### 1. Galaxy Structure (X/15)
[Details of what passed/failed]

### 2. Module Documentation (X/10)
[Table of modules with DOCUMENTATION/EXAMPLES/RETURN status]

... (repeat for all 11 categories)

## Priority Action Items

1. [Highest priority fix]
2. [Next fix]
...
```

## Scoring Rubric

### 1. Galaxy Structure (15 points)

| Check | Points | How to Verify |
|-------|--------|---------------|
| `galaxy.yml` exists with valid namespace, name, version | 4 | `find <domain> -name galaxy.yml` |
| `meta/runtime.yml` exists | 2 | `find <domain> -name runtime.yml -path "*/meta/*"` |
| `plugins/modules/` directory (not `library/modules/`) | 3 | Check dir exists under `plugins/` |
| `plugins/module_utils/` directory (not `library/module_utils/`) | 3 | Check dir exists under `plugins/` |
| `plugins/callback/` directory (not `callback_plugins/`) | 1 | Check dir exists under `plugins/` |
| `requirements.txt` exists | 1 | `find <domain> -maxdepth 1 -name requirements.txt` |
| `requirements.yml` exists | 1 | `find <domain> -maxdepth 1 -name requirements.yml` |

### 2. Module Documentation (10 points)

For each Python module under `plugins/modules/*.py` (or `library/modules/*.py`):

| Check | Points | How to Verify |
|-------|--------|---------------|
| `DOCUMENTATION` block present | 4 | `grep -l "^DOCUMENTATION" <module>` |
| `EXAMPLES` block present | 3 | `grep -l "^EXAMPLES" <module>` |
| `RETURN` block present | 3 | `grep -l "^RETURN" <module>` |

Score = (modules_with_all_3_blocks / total_modules) × 10. If no modules exist, score 10/10.

### 3. Role Metadata (10 points)

For each role under `roles/*/`:

| Check | Points | How to Verify |
|-------|--------|---------------|
| `README.md` exists in every role | 5 | `find roles -mindepth 2 -maxdepth 2 -name README.md` |
| `meta/main.yml` exists in every role | 5 | `find roles -path "*/meta/main.yml"` |

Score = ((roles_with_readme + roles_with_meta) / (total_roles × 2)) × 10.

### 4. Input Validation Structure (10 points)

Check if `plugins/module_utils/input_validation/` (or `library/module_utils/input_validation/`) follows the four-directory pattern:

| Check | Points | How to Verify |
|-------|--------|---------------|
| `core/` directory exists with `validation_engine.py` | 3 | Directory and file check |
| `messages/` directory exists with message constants | 3 | Directory exists; messages use `UPPER_SNAKE_CASE` |
| `schema/` directory exists with `.json` files | 2 | Directory and JSON file check |
| `validators/` directory exists with per-config validators | 2 | Directory exists; each exposes `validate()` |

**Additional deductions**:
- −2 if error messages are inline in validator code (not in `messages/`)
- −2 if using `common/library/` imports instead of domain-local
- −1 if `core/config.py` contains constants for other domains

If the domain has no input validation (no config files to validate), score 10/10.

### 5. Entry Point & Tags (10 points)

| Check | Points | How to Verify |
|-------|--------|---------------|
| Top-level playbook exists (e.g., `playbooks/<domain>.yml`) | 3 | File exists |
| Uses only `import_playbook:` or `import_role:` (no inline tasks) | 2 | Grep for `tasks:` in entry point |
| Uses common tags (precheck, validate, prepare, execute, build, cleanup) | 3 | Grep tags in entry point |
| No duplicate flat playbooks (all in subdirectories) | 2 | Compare root vs subdirectory playbooks |

### 6. Domain Integration (10 points)

| Check | Points | How to Verify |
|-------|--------|---------------|
| `domain-init.sh` exists (domain init script) | 3 | `find <domain> -name domain-init.sh` |
| Status file writer (writes `<domain>_status.yml`) | 3 | Grep for `_status.yml` in tasks |
| Setup role exists (`<domain>_setup` or equivalent) | 2 | Check `roles/` |
| Input/output contract docs exist (`docs/contracts/`) | 2 | Check `docs/contracts/` |

### 7. FQCN Usage (5 points)

| Check | Points | How to Verify |
|-------|--------|---------------|
| All tasks use `ansible.builtin.*` for builtin modules | 3 | Grep for bare module names without FQCN |
| Custom modules referenced by FQCN (`omnia.<collection>.*`) | 2 | Grep for short-name custom module calls |

Score 5/5 if >95% FQCN usage; 3/5 if >80%; 0/5 if <80%.

### 8. ansible.cfg Compliance (5 points)

| Check | Points | How to Verify |
|-------|--------|---------------|
| `log_path` uses `/var/log/omnia/<domain>/<name>.log` (flat, no subfolders) | 2 | Grep ansible.cfg for `log_path`; must use `/var/log/omnia/` with no subdirectories — reject `/opt/omnia/` or relative paths |
| Uses `collections_path` (not `collections_paths`) | 1 | Grep ansible.cfg |
| Points to `plugins/` not `library/` | 2 | Check `library` and `module_utils` settings |

**Two-tier log convention**:
- **`ansible.cfg` `log_path`** → `/var/log/omnia/<domain>/<name>.log` — flat directory, no subfolders. Ansible playbook execution logs go here (OS-standard location).
- **Domain runtime logs** (validation, build, application) → `<OMNIA_DATA_PATH>/<domain>/log/` (under the data path, managed by roles)

Only the `ansible.cfg` `log_path` is checked in this category. Runtime logs under `omnia_data_path` are acceptable and expected.

**Directory setup**: The `/var/log/omnia/<domain>/` directory must be created before playbook execution. Domains provide a `domain-init.sh` script that handles this. If the user does not run the script, they must manually run: `sudo mkdir -p /var/log/omnia/<domain>`

### 9. Documentation (5 points)

| Check | Points | How to Verify |
|-------|--------|---------------|
| Domain-level `README.md` exists | 3 | `find <domain> -maxdepth 1 -name README.md` |
| `docs/` directory exists with at least one doc | 2 | Check `docs/` |

### 10. Domain Independence (5 points)

| Check | Points | How to Verify |
|-------|--------|---------------|
| No imports from `common/library/` or other domains | 3 | Grep for cross-domain imports |
| Communicates with other domains only via YAML contracts | 2 | Check for direct file/code imports from other `src/` domains |

## Status Thresholds

| Score | Status |
|-------|--------|
| 0–30 | NOT_STARTED |
| 31–70 | IN_PROGRESS |
| 71–100 | COMPLIANT |

## Gotchas

- **Legacy `library/` vs `plugins/`**: Many domains still use `library/`. This is a structural FAIL but the code inside may be fine — note it as a migration task, not a rewrite.
- **No input validation needed**: Some small domains (e.g., `utils`) may not have user-facing config files. In that case, score category 4 as 10/10.
- **Duplicate playbooks**: Check for flat playbooks at `playbooks/` root that also exist in subdirectories — the flat copies are dead code.
- **common/ dependency**: The `common/` directory is a shared legacy library. New domains MUST NOT depend on it. If a domain still imports from `common/`, flag it but don't penalize if it's the only source of shared utilities during migration.
- **CHANGELOG.md**: The Galaxy Change Summary section is only included in the report if a `CHANGELOG.md` exists. If absent, skip the section entirely.

### 11. Code Quality & Security (15 points)

| Check | Points | How to Verify |
|-------|--------|---------------|
| All `.py` files score ≥ 8.0 with `pylint` | 5 | Run `pylint <file>` on each `.py` under `plugins/` |
| All playbooks/roles pass `ansible-lint` (production profile) | 3 | Run `ansible-lint -p production` on domain |
| Zero `gitleaks` findings (no hardcoded secrets) | 3 | Run `gitleaks detect --source <domain>` |
| Zero Checkmarx High/Critical findings | 2 | Check Checkmarx project scan results |
| All `.sh` files pass `shellcheck` with zero errors | 2 | Run `shellcheck <file>` on each `.sh` |

**Scoring guidance**:
- If a tool is not available in the scan environment, note it as SKIPPED and do not deduct points.
- For pylint: score = (files_passing / total_py_files) × 5. If no `.py` files exist, score 5/5.
- For ansible-lint: 3/3 if zero errors; 1/3 if only warnings; 0/3 if errors present.
- For gitleaks: 3/3 if zero findings; 0/3 if any finding.
- For Checkmarx: 2/2 if zero High/Critical; 1/2 if only Medium; 0/2 if High/Critical present. If no scan results available, score as SKIPPED.
- For shellcheck: 2/2 if all `.sh` pass; 1/2 if only warnings; 0/2 if errors. If no `.sh` files, score 2/2.

## Examples

### Example Input

```
Check domain completion for: src/repo_manager
```

### Example Output

```markdown
# Domain Completion Report: repo_manager

**Date**: 2026-07-30
**Score**: 25/100
**Status**: NOT_STARTED

## Score Breakdown

| # | Category | Weight | Score | Max | Status |
|---|----------|--------|-------|-----|--------|
| 1 | Galaxy Structure | 15 | 2 | 15 | FAIL |
| 2 | Module Documentation | 10 | 1 | 10 | FAIL |
| 3 | Role Metadata | 10 | 0 | 10 | FAIL |
| 4 | Input Validation Structure | 10 | 8 | 10 | PARTIAL |
| 5 | Entry Point & Tags | 10 | 5 | 10 | PARTIAL |
| 6 | Domain Integration | 10 | 0 | 10 | FAIL |
| 7 | FQCN Usage | 5 | 5 | 5 | PASS |
| 8 | ansible.cfg Compliance | 5 | 0 | 5 | FAIL |
| 9 | Documentation | 5 | 0 | 5 | FAIL |
| 10 | Domain Independence | 5 | 0 | 5 | FAIL |
| 11 | Code Quality & Security | 15 | 0 | 15 | FAIL |
| | **Total** | | **21** | **100** | |

## Priority Action Items

1. Rename `library/` → `plugins/` (modules, module_utils, callback)
2. Create `galaxy.yml` (namespace: omnia, name: repo_manager)
3. Add DOCUMENTATION/EXAMPLES/RETURN to all 14 modules
4. Create README.md + meta/main.yml for all 9 roles
5. Create domain README.md
6. Create copy-input.sh
7. Remove duplicate flat playbooks
8. Fix ansible.cfg hardcoded paths
```
