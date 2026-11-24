# CI/CD Workflows -- omnia-bsm

All workflows run on pull requests targeting `main`, `release_*`, `issue-*`, `pub/**`, and `feature/**` branches.

## Workflow Summary

| # | Workflow | File | Jobs | Gate | Description |
|---|---------|------|------|------|-------------|
| 1 | **Ansible Lint** | `ansible-lint.yml` | 1 | Blocking | Runs `ansible-lint` with production profile (FQCN, named tasks, module-vs-shell) |
| 2 | **Bandit Security Scan** | `bandit.yml` | 1 | Blocking | Python SAST -- `bandit -r` to detect security issues in Python code |
| 3 | **Commit Hygiene** | `commit-hygiene.yml` | 3 | Blocking (Job 1) | Validates commit authors, messages, copyright headers, and test co-changes |
| 4 | **HPC Compliance Scanner** | `hpc-compliance.yml` | 1 | Mixed | HPC anti-patterns + Checkmarx pre-scan (see below) |
| 5 | **PR Hygiene** | `pr-hygiene.yml` | 1 | Blocking | Validates PR title format, branch naming, and spec/code separation |
| 6 | **PR Issue and Network Policy** | `pr-policy.yml` | 1 | Blocking | Requires a linked issue and rejects added `100.x.x.x` IPv4 addresses |
| 7 | **PR Effective Size** | `line-length.yml` | 1 | Blocking | Measures effective added lines (comments/blank lines stripped); fails above 1000 lines |
| 8 | **Secret Leak Scan** | `gitleaks.yml` | 1 | Blocking | Scans for secrets and credentials using `gitleaks` with custom `.gitleaks.toml` |
| 9 | **Dependency Vulnerability Scan** | `pip-audit.yml` | 1 | Blocking | `pip-audit` scans Python dependencies for known CVEs |
| 10 | **Pylint** | `pylint.yml` | 1 | Blocking | Lint Python code -- minimum score >= 8.0 per file |
| 11 | **Unit Tests & Coverage** | `pytest.yml` | 1 | Blocking | Runs `pytest` with coverage reporting |
| 12 | **ShellCheck** | `shellcheck.yml` | 1 | Blocking | Static analysis of shell scripts |
| 13 | **Secure Code Review** | `secure-code-review.yml` | 1 | Advisory | Scans added lines against secure-coding rules from past security fixes; posts a pass/fail checklist PR comment, never blocks |

**Total: 13 workflows, 15 jobs**

> **Note:** YAML linting is handled by `ansible-lint` (production profile). A separate `yamllint` workflow is not required.

---

## HPC Compliance Scanner Details

The `hpc-compliance.yml` workflow enforces Omnia-specific HPC rules that `ansible-lint` does not cover.

### Ansible Checks (Advisory)

| Check | What It Detects | Style Guide Reference |
|-------|----------------|----------------------|
| `loop:` + `delegate_to:` | Potential serial fan-out across 1000 nodes -- manual review required | `ansible.md` §13.1 |
| `with_items:` + `delegate_to:` | Potential legacy serial fan-out pattern -- manual review required | `ansible.md` §13.1 |

### Python Checks -- Blocking (Errors)

| Check | What It Detects | Style Guide Reference |
|-------|----------------|----------------------|
| `shell=True` | OS Command Injection risk in subprocess | `python.md` §8.3 |
| `os.system()` | OS Command Injection | `python.md` §8.3 |
| `eval()` | Code Injection | `python.md` §8.3 |
| `exec()` | Dynamic code execution | `python.md` §8.3 |
| `yaml.load()` | Insecure YAML deserialization | `python.md` §8.3 |
| `yaml.full_load()` | Unsafe YAML loader | `python.md` §8.3 |
| `yaml.UnsafeLoader` / `yaml.FullLoader` | Unsafe YAML loader classes | `python.md` §8.3 |

### Python Checks -- Advisory (Warnings)

| Check | What It Detects | Note |
|-------|----------------|------|
| `pickle.loads()` | Potentially unsafe deserialization | May have valid internal uses |
| Hardcoded credentials | `password`, `secret`, `api_key`, `token`, `access_token`, `auth_token` patterns | Excludes `test/`, `examples/`, `docs/`, `build/` |

**Design principle:** This workflow only checks rules that `ansible-lint` cannot detect. All FQCN, module-vs-shell, named-task, and bare-variable checks are handled by `ansible-lint` with the production profile.

---

## Quality Gate Summary

### Code Quality

| Gate | Tool | Threshold | Reference |
|------|------|-----------|-----------|
| Ansible Lint | `ansible-lint` | Zero errors (production profile) | `ansible.md` §14.1 |
| Pylint | `pylint` | Score >= 8.0 per file | `python.md` §7.1 |
| ShellCheck | `shellcheck` | Zero errors | `ansible.md` §14 |
| PR Hygiene | `pr-hygiene.yml` | Valid PR title format, branch naming, spec/code separation | `general.md` §11 |
| PR Policy | `pr-policy.yml` | Linked issue and no added `100.x.x.x` IPv4 addresses | Repository policy |
| PR Effective Size | `line-length.yml` | Effective added lines <= 1000 | Repository policy |

### Security

| Gate | Tool | Threshold | Reference |
|------|------|-----------|-----------|
| Python SAST | `bandit` | Zero High/Critical | `python.md` §7 |
| Secret Leak | `gitleaks` | Zero findings | `ansible.md` §14.4 |
| Dependency CVE | `pip-audit` | Zero known vulnerabilities | `python.md` §7 |
| Checkmarx Pre-scan | HPC Compliance Scanner | No `shell=True`, `os.system()`, `eval()`, `exec()`, unsafe `yaml.load()` | `python.md` §8.3 |
| PR Hygiene | `pr-hygiene.yml` | Valid PR title format, branch naming, spec/code separation | `general.md` §11 |

---

## Commit Hygiene Details

The `commit-hygiene.yml` workflow enforces the AI Agent Usage Policy from `docs/code-style/general.md`:

| Job | Check | Severity |
|-----|-------|----------|
| **Commit Validation** | Block commits authored by AI bots (Devin, Codex, Copilot, etc.) | ERROR |
| | Block commits from root user | ERROR |
| | Validate `<type>(<scope>): <description>` format | WARN |
| | Block trivially short commit messages (<10 chars) | ERROR |
| | Detect LLM-style language in commit messages | WARN |
| **Copyright Header** | Audit every added/modified `.yml`, `.yaml`, and `.py` file for the Dell header; copyright year is not validated | WARN (advisory) |
| **Test Co-Change** | Warn when `src/` changes without `test/` updates | WARN (advisory) |

**Note:** `Co-Authored-By` trailers are acceptable. The check validates the primary Author and Committer fields, not trailers.

---

## PR Hygiene Details

The `pr-hygiene.yml` workflow enforces PR-level validation rules:

| Check | Description | Severity |
|-------|-------------|----------|
| **PR Title Format** | Validates Conventional Commit format: `<type>(<scope>): <description>` | ERROR |
| **Branch Naming** | Enforces `pub/<name>` prefix for protected branches | ERROR |
| **Spec/Code Separation** | Warns when `specs/` and `src/`/`test/` changes are mixed in the same PR | WARN |

**Protected branches**: Branches matching `pub/*` pattern require PR reviews and status checks before merge.

---

## PR Effective Size Details

The `line-length.yml` workflow measures the effective size of a PR by counting added code lines only (removed lines are reported but never counted toward the limit). Comments and blank lines are stripped before counting.

| Check | Description | Threshold | Severity |
|-------|-------------|-----------|----------|
| **Effective Added Lines** | Counts added lines after stripping comments and blank lines | 1000 lines | ERROR |

**Excluded files:**
- Markdown (`.md`)
- JSON (`.json`)
- Binary files (`.png`, `.jpg`, `.jpeg`, `.gif`, `.svg`, `.ico`, `.pdf`, `.gz`, `.tar`, `.zip`, `.rpm`, `.iso`)
- `.github/workflows/` directory

**Report output:**
- Effective added lines (limit: 1000)
- Effective removed lines
- Net change
- Files touched
- Average effective line length
- Top 10 files by added lines

**Bypass options:**
- Add the `skip-size-check` label to make the check report-only (no failure)
- PRs with `sync` prefix in title are automatically skipped (e.g., `sync(main): merge main into feature/*`)

**Rationale for 1000 line threshold:**
Based on analysis of 100 merged PRs (excluding giant sync PRs):
- Median: 177 lines
- 75th percentile: 796 lines
- 90th percentile: 1,899 lines
- 84% of normal PRs pass the 1000 line threshold
- Encourages smaller, focused changes while allowing flexibility for legitimate large PRs

---

## Security Scanning

| Scanner | Tool | What It Checks |
|---------|------|----------------|
| SAST | `bandit` | Python security anti-patterns (hardcoded passwords, SQL injection, etc.) |
| Checkmarx Pre-scan | HPC Compliance Scanner | `shell=True`, `os.system()`, `eval()`, `exec()`, `yaml.load()`, hardcoded credentials |
| Secrets | `gitleaks` | Leaked credentials, API keys, tokens in code and history |
| Dependencies | `pip-audit` | Known CVEs in Python package dependencies |

## PR-Level Validation

| Workflow | What It Checks |
|----------|----------------|
| **Commit Hygiene** | Commit author validation, message format, copyright headers, test co-changes |
| **PR Hygiene** | PR title format, branch naming (`pub/*`), spec/code separation |
| **PR Issue and Network Policy** | Required issue reference and blocked `100.x.x.x` IPv4 addresses in PR metadata or added lines |
| **PR Effective Size** | Effective added lines (comments/blank lines stripped); fails above 1000 lines |

Configure **Validate linked issue and IP policy** as a required status check in the
repository branch ruleset so a failing result prevents merge.

### Sync PR Exemption

The following workflows automatically skip PRs with `sync` prefix in the title (e.g., `sync(main): merge main into feature/*`):
- Commit Hygiene (all 3 jobs)
- PR Hygiene
- PR Issue and Network Policy
- HPC Compliance Scanner
- PR Effective Size

This allows feature branch sync PRs to bypass hygiene checks since they are mechanical merges rather than real code changes.

### Bypass Labels

For special cases where hygiene checks need to be bypassed, the following labels can be added to the PR:

| Label | Purpose | Workflow |
|-------|---------|----------|
| `skip-size-check` | Skip PR effective size check enforcement (report-only mode) | PR Effective Size |
| `skip-policy-check` | Skip PR policy check (issue-linking requirement) | PR Issue and Network Policy |

Use these labels sparingly and only for legitimate cases:
- `skip-size-check`: Large but justified PRs (e.g., major feature completions, test infrastructure)
- `skip-policy-check`: PRs without linked issues (e.g., CI/CD improvements, documentation, refactoring)

---

## Adding a New Workflow

1. Create the workflow file in `.github/workflows/`
2. Use the standard branch triggers: `main`, `release_*`, `issue-*`, `pub/**`, `feature/**`
3. Update this README with the new workflow details
4. Ensure the workflow follows the commit format: `ci(workflows): <description>`
