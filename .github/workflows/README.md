# CI/CD Workflows — omnia-bsm

All workflows run on pull requests targeting `main`, `staging`, `release_*`, `issue-*`, and `pub/**` branches.

## Workflow Summary

| # | Workflow | File | Jobs | Gate | Description |
|---|---------|------|------|------|-------------|
| 1 | **Ansible Lint** | `ansible-lint.yml` | 1 | Blocking | Runs `ansible-lint` across all playbooks and roles |
| 2 | **Bandit Security Scan** | `bandit.yml` | 1 | Blocking | Python SAST — `bandit -r` to detect security issues in Python code |
| 3 | **Commit Hygiene** | `commit-hygiene.yml` | 3 | Blocking (Job 1) | Validates commit authors, messages, copyright headers, and test co-changes |
| 4 | **Secret Leak Scan** | `gitleaks.yml` | 1 | Blocking | Scans for secrets and credentials using `gitleaks` with custom `.gitleaks.toml` |
| 5 | **Dependency Vulnerability Scan** | `pip-audit.yml` | 1 | Blocking | `pip-audit` scans Python dependencies for known CVEs |
| 6 | **Pylint** | `pylint.yml` | 1 | Blocking | Lint Python code — minimum score threshold enforced |
| 7 | **Unit Tests & Coverage** | `pytest.yml` | 1 | Blocking | Runs `pytest` with coverage reporting |
| 8 | **ShellCheck** | `shellcheck.yml` | 1 | Blocking | Static analysis of shell scripts |

**Total: 8 workflows, 10 jobs**

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
| **Copyright Header** | Check Dell Apache 2.0 copyright header in new/changed source files | WARN (advisory) |
| **Test Co-Change** | Warn when `src/` changes without `test/` updates | WARN (advisory) |

**Note:** `Co-Authored-By` trailers are acceptable. The check validates the primary Author and Committer fields, not trailers.

---

## Security Scanning

| Scanner | Tool | What It Checks |
|---------|------|----------------|
| SAST | `bandit` | Python security anti-patterns (hardcoded passwords, SQL injection, etc.) |
| Secrets | `gitleaks` | Leaked credentials, API keys, tokens in code and history |
| Dependencies | `pip-audit` | Known CVEs in Python package dependencies |

---

## Adding a New Workflow

1. Create the workflow file in `.github/workflows/`
2. Use the standard branch triggers: `main`, `staging`, `release_*`, `issue-*`, `pub/**`
3. Update this README with the new workflow details
4. Ensure the workflow follows the commit format: `ci(workflows): <description>`
