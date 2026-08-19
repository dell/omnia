# CI/CD Workflows -- omnia-bsm

All workflows run on pull requests targeting `main`, `staging`, `release_*`, `issue-*`, and `pub/**` branches.

## Workflow Summary

| # | Workflow | File | Jobs | Gate | Description |
|---|---------|------|------|------|-------------|
| 1 | **Ansible Lint** | `ansible-lint.yml` | 1 | Blocking | Runs `ansible-lint` with production profile (FQCN, named tasks, module-vs-shell) |
| 2 | **Bandit Security Scan** | `bandit.yml` | 1 | Blocking | Python SAST -- `bandit -r` to detect security issues in Python code |
| 3 | **Commit Hygiene** | `commit-hygiene.yml` | 3 | Blocking (Job 1) | Validates commit authors, messages, copyright headers, and test co-changes |
| 4 | **HPC Compliance Scanner** | `ansible-module-lint.yml` | 1 | Mixed | HPC anti-patterns + Checkmarx pre-scan (see below) |
| 5 | **Secret Leak Scan** | `gitleaks.yml` | 1 | Blocking | Scans for secrets and credentials using `gitleaks` with custom `.gitleaks.toml` |
| 6 | **Dependency Vulnerability Scan** | `pip-audit.yml` | 1 | Blocking | `pip-audit` scans Python dependencies for known CVEs |
| 7 | **Pylint** | `pylint.yml` | 1 | Blocking | Lint Python code -- minimum score >= 8.0 per file |
| 8 | **Unit Tests & Coverage** | `pytest.yml` | 1 | Blocking | Runs `pytest` with coverage reporting |
| 9 | **ShellCheck** | `shellcheck.yml` | 1 | Blocking | Static analysis of shell scripts |

**Total: 9 workflows, 11 jobs**

> **Note:** YAML linting is handled by `ansible-lint` (production profile). A separate `yamllint` workflow is not required.

---

## HPC Compliance Scanner Details

The `ansible-module-lint.yml` workflow enforces Omnia-specific HPC rules that `ansible-lint` does not cover.

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

### Security

| Gate | Tool | Threshold | Reference |
|------|------|-----------|-----------|
| Python SAST | `bandit` | Zero High/Critical | `python.md` §7 |
| Secret Leak | `gitleaks` | Zero findings | `ansible.md` §14.4 |
| Dependency CVE | `pip-audit` | Zero known vulnerabilities | `python.md` §7 |
| Checkmarx Pre-scan | HPC Compliance Scanner | No `shell=True`, `os.system()`, `eval()`, `exec()`, unsafe `yaml.load()` | `python.md` §8.3 |

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
| Checkmarx Pre-scan | HPC Compliance Scanner | `shell=True`, `os.system()`, `eval()`, `exec()`, `yaml.load()`, hardcoded credentials |
| Secrets | `gitleaks` | Leaked credentials, API keys, tokens in code and history |
| Dependencies | `pip-audit` | Known CVEs in Python package dependencies |

---

## Adding a New Workflow

1. Create the workflow file in `.github/workflows/`
2. Use the standard branch triggers: `main`, `staging`, `release_*`, `issue-*`, `pub/**`
3. Update this README with the new workflow details
4. Ensure the workflow follows the commit format: `ci(workflows): <description>`
