# Test Automation — Design & Architecture

> **Scope**: All Omnia domains | **Last Updated**: Jul 2026

---

## 1. Overview

The test automation framework provides **Functional Verification Testing (FVT)** for all
Omnia domains. Each domain uses this shared framework to verify that its Ansible playbooks
correctly deploy infrastructure, produce valid output artifacts, and meet contract specifications.

### Design Goals

- **Zero hardcoded values** — all IPs, paths, and credentials read from config
- **Centralized messages** — no inline strings in test files
- **Graceful skipping** — optional features skip cleanly (no false failures)
- **Structured output** — TestLogger produces consistent ✓/✗ formatted results
- **HTML reports** — consolidated report across multiple scenario runs
- **Remote + local** — tests run against a remote OIM server or locally

---

## 2. Architecture

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                        TEST AUTOMATION ARCHITECTURE                         │
└─────────────────────────────────────────────────────────────────────────────┘

  ┌──────────────┐     ┌──────────────┐     ┌──────────────────────────────┐
  │ run_validation│     │  conftest.py  │     │       Target Server          │
  │    .sh       │────>│  pytest hooks │────>│    (OIM / <domain>)          │
  │              │     │  + fixtures   │     │                              │
  └──────┬───────┘     └──────┬───────┘     └──────────────────────────────┘
         │                    │                          ▲
         │                    │                          │ SSH / testinfra
         │                    ▼                          │
         │             ┌──────────────┐           ┌─────┴──────┐
         │             │  fvt/        │           │  library/   │
         │             │  test files  │──────────>│  functions/ │
         │             │              │           │  vars/      │
         │             └──────────────┘           │  messages/  │
         │                                        └────────────┘
         │
         ▼
  ┌──────────────┐     ┌──────────────┐
  │ test_config  │     │ test_run     │
  │   .yml       │     │  _config.yml │
  │ (connection) │     │ (scenarios)  │
  └──────────────┘     └──────────────┘
```

---

## 3. Execution Flow

### 3.1 Entry Point: `run_validation.sh`

```
run_validation.sh <scenario> <command> [--marker <expr>]
                       │          │
                       │          ├── deploy  → run playbook + verify
                       │          ├── verify  → verify only (no deploy)
                       │          └── test    → deploy + verify (combined)
                       │
                       ├── <domain>              → fvt/<domain>/
                       ├── validate              → fvt/validate/
                       ├── prepare               → fvt/prepare/
                       ├── build                 → fvt/build/
                       └── cleanup               → fvt/cleanup/
```

### 3.2 Config Mode: `run_validation.sh --config`

Reads `test_run_config.yml` and runs enabled scenarios in order:

```yaml
scenarios:
  <domain>:
    order: 1
    run: true
    suite: ""
    marker: "sanity"
```

### 3.3 Playbook ↔ Test Scenario Mapping

| Playbook Tag | Test Scenario | What It Verifies |
|-------------|---------------|------------------|
| `validate` | `validate` | Input config exists, credentials synced |
| `prepare` | `prepare` | Containers running, services, ports |
| `build` | `build` | Output artifacts, status files |
| `cleanup` | `cleanup` | Containers removed, artifacts cleaned |
| *(none — default)* | `<domain>` | Full end-to-end (deploy + verify) |

---

## 4. Test Phases

### Phase 1: Session Setup (conftest.py)

```
1. Validate test_config.yml (all required fields, dataset exists, paths valid)
   → Fail fast with clear error if invalid (no fallback defaults)
2. Encrypt test_creds.yml (if not already encrypted)
3. Clone/pull repo on target (if remote mode)
4. Sync dataset input/ files to target (sync_domain_input)
5. Sync config.yml to target clone root
6. Sync upstream output/ to target (sync_output)
7. Initialize TestReport
```

### Phase 2: Deploy (deploy command)

```
1. PlaybookRunner connects to target (SSH or local)
2. Runs: ansible-playbook <domain>.yml --tags <tag>
3. Streams live output with | prefix
4. Returns success/failure dict
```

### Phase 3: Verify (verify command)

```
1. Testinfra connects to target
2. Runs verification functions (check_*, verify_*)
3. TestLogger produces structured output
4. Results collected by TestReport
```

### Phase 4: Report Generation

```
1. conftest.py pytest_sessionfinish hook
2. TestReport.save() → JSON + HTML
3. Multiple runs merge into single report
```

---

## 5. Test Case Registry

Each domain defines its own test cases following the ID convention below. The actual
test case tables live in the domain’s own `test/` directory documentation.

### Test Case ID Convention

| Area | Prefix | Applies To |
|------|--------|------------|
| Validate | `TC_VL_` | All domains |
| Prepare | `TC_PR_` | Domains with infrastructure setup |
| Build | `TC_BD_` | Domains with build/execute phase |
| Cleanup | `TC_CL_` | All domains |
| End-to-End | `TC_E2E_` | Full domain verification |

### Generic Scenario Structure

| Playbook Tag | Test Scenario | What It Verifies |
|-------------|---------------|------------------|
| `validate` | `validate` | Input config present, prerequisites met |
| `prepare` | `prepare` | Infrastructure deployed, services running, ports open |
| `build` | `build` | Output artifacts created, status file reports success |
| `cleanup` | `cleanup` | Services stopped, artifacts removed |
| *(no tag)* | `<domain>` | Full end-to-end (deploy + verify all of the above) |

---

## 6. Data Flow

### 6.1 Input Flow

```
test/datasets/<dataset>/input/           (local — automation runner)
        │
        │  rsync via conftest.py (when sync_domain_input: true)
        ▼
<clone_path>/src/input/<project>/       (target server)
        │
        │  ansible-playbook <domain>.yml
        ▼
/opt/omnia/<domain>/output/             (target server — runtime output)
```

### 6.2 Dataset Structure

```
datasets/<dataset>/
├── input/                              # Synced to <clone_path>/src/input/<project>/
│   ├── config.yml                      # Project config (also -> <clone_path>/config.yml)
│   ├── <domain>_config.yml             # Domain-specific input config
│   └── <domain>_credentials.yml        # Vault-encrypted credentials (if needed)
└── upstream_output/                    # Synced to upstream output dir (sync_output: true)
    ├── <upstream>_status.yml            # Upstream domain status/contract
    └── ...                             # Additional upstream artifacts
```

---

## 7. Report Architecture

### 7.1 Report Generation

```
pytest_sessionstart  → TestReport.__init__()
pytest_runtest_makereport → TestReport.add_result()
pytest_sessionfinish → TestReport.save() → JSON + HTML
```

### 7.2 HTML Report Sections

1. **Header** — server info, suite, marker, duration
2. **Summary** — pass/fail/skip counts
3. **Folder Breakdown** — results grouped by test folder + suite/marker info
4. **Test Details** — expandable per-test results with details

### 7.3 Report Merging

Multiple scenario runs with the same `report_id` merge into one report.
Each run appears as a separate section under the same server.

---

## 8. Connection Architecture

### 8.1 Remote Mode (`oim_server_ip` set)

```
Automation Runner → SSH → Target Server (OIM)
                                │
                                ├── testinfra host = ssh://<ip>
                                ├── PlaybookRunner = sshpass + ssh
                                └── rsync for file sync
```

### 8.2 Local Mode (`oim_server_ip` empty)

```
Same Machine
    ├── testinfra host = local://
    ├── PlaybookRunner = subprocess
    └── cp/rsync for file sync
```

---

## 9. Security

- **Credentials**: `test_creds.yml` encrypted with Ansible Vault on first use
- **Dataset credentials**: `<domain>_credentials.yml` vault-encrypted
- **No secrets in code**: All credentials from config files
- **No secrets in git**: `.gitignore` excludes vault key files
- **SSH**: Uses `StrictHostKeyChecking=no` for automation only

---

## 10. Configuration Validation

### 10.1 No Fallback Defaults

All required fields in `test_config.yml` must be explicitly set. The framework
never silently substitutes a default value. If a field is missing or `null`,
session startup fails immediately with a clear error listing every missing field.

**Required fields:** `oim_server_ip`, `dataset`, `project_name`, `clone_path`,
`shared_path`, `report_path`, `report_name`.

### 10.2 Dataset Validation

Before tests run, the validator checks:
- Dataset directory exists: `datasets/<dataset>/`
- Required files present: `input/config.yml`, `input/<domain>_config.yml`

### 10.3 Report Path

`report_path` supports both relative (to `test/`) and absolute paths.
Directories are created automatically if they do not exist.

### 10.4 Tab Completion

```bash
eval "$(./run_validation.sh --completion)"
```

Enables bash tab completion for scenarios, commands, `--suite`, and `--marker`.

---

## 11. Extensibility

### Adding a New Test Scenario

1. Create `fvt/<scenario_name>/` directory
2. Add `test_playbook.py` at scenario root for playbook execution
3. Add `<component>/test_<component>.py` for verification
4. Add test names/messages to `<domain>_msgs.py`
5. Add scenario to `test_run_config.yml`
6. Update this design document

### Adding a New Verification Check

1. Add function to `<domain>_func.py` (return dict pattern)
2. Add command to `CMDS` in `common_vars.py` (if new shell command)
3. Add messages to `<domain>_msgs.py`
4. Create test in appropriate `fvt/` folder
5. Run pylint and verify score ≥ 8.7
