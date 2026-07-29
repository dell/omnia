# Test Automation — Design & Architecture

> **Scope**: All Omnia domains | **Last Updated**: Jul 2026

---

## 1. Overview

The test automation framework provides **Functional Verification Testing (FVT)** for all
Omnia domains. Each domain uses this framework to verify that its Ansible playbooks correctly
deploy infrastructure, produce valid output artifacts, and meet contract specifications.

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
  │    .sh       │────>│  pytest hooks │────>│  (OIM / image_build_manager) │
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
                       ├── image_build_manager   → fvt/image_build_manager/
                       ├── validate              → fvt/validate/
                       ├── prepare               → fvt/prepare/
                       ├── build                 → fvt/build/
                       └── cleanup               → fvt/cleanup/
```

### 3.2 Config Mode: `run_validation.sh --config`

Reads `test_run_config.yml` and runs enabled scenarios in order:

```yaml
scenarios:
  image_build_manager:
    order: 1
    run: true
    suite: ""
    marker: "sanity"
```

### 3.3 Playbook ↔ Test Scenario Mapping

| Playbook Tag | Test Scenario | What It Verifies |
|-------------|---------------|------------------|
| `validate` | `validate` | Input config exists, credentials synced |
| `prepare` | `prepare` | Containers running, S3 buckets, ports |
| `build` | `build` | S3 images, registry images, build_status |
| `cleanup` | `cleanup` | Containers removed, artifacts cleaned |
| *(none — default)* | `image_build_manager` | Full end-to-end (deploy + verify) |

---

## 4. Test Phases

### Phase 1: Session Setup (conftest.py)

```
1. Validate test_config.yml (all required fields, dataset exists, paths valid)
   → Fail fast with clear error if invalid (no fallback defaults)
2. Encrypt test_creds.yml (if not already encrypted)
3. Clone/pull repo on target (if remote mode)
4. Sync dataset input/ files to target (sync_image_build_input)
5. Sync config.yml to target clone root
6. Sync repo_manager_output/ to target (sync_output)
7. Initialize TestReport
```

### Phase 2: Deploy (deploy command)

```
1. PlaybookRunner connects to target (SSH or local)
2. Runs: ansible-playbook image_build_manager.yml --tags <tag>
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

### validate (Tag: validate) — 3 Tests

| ID | Test | Markers | Suite |
|----|------|---------|-------|
| TC_VL_001 | Deploy playbook --tags validate | deploy, sanity | *(root)* |
| TC_VL_002 | Verify image_build_config.yml exists on target | sanity | status |
| TC_VL_003 | Verify credentials file present on target | sanity | status |

### prepare (Tag: prepare) — 8 Tests

| ID | Test | Markers | Suite |
|----|------|---------|-------|
| TC_PR_001 | Deploy playbook --tags prepare | deploy, sanity | *(root)* |
| TC_PR_002 | Verify S3 storage backend (MinIO) running | sanity | container |
| TC_PR_003 | Verify registry container running | sanity | container |
| TC_PR_004 | Verify systemd services active | sanity | container |
| TC_PR_005 | Verify firewall ports open | sanity | container |
| TC_PR_006 | Verify s3cmd installed and configured | sanity | container |
| TC_PR_007 | Verify registry reachable | sanity | container |
| TC_PR_008 | Verify S3 buckets created | sanity | s3 |

### build (Tag: build) — 6 Tests

| ID | Test | Markers | Suite |
|----|------|---------|-------|
| TC_BD_001 | Deploy playbook --tags build | deploy, sanity | *(root)* |
| TC_BD_002 | Verify x86_64 images pushed to S3 | x86_64, sanity | s3 |
| TC_BD_003 | Verify aarch64 images pushed to S3 | aarch64, sanity | s3 |
| TC_BD_004 | Verify x86_64 images in registry | x86_64, sanity | registry |
| TC_BD_005 | Verify build_status.yml after build | sanity | registry |
| TC_BD_006 | Verify x86_64 functional groups built | x86_64, sanity | registry |

### cleanup (Tag: cleanup) — 8 Tests

| ID | Test | Markers | Suite |
|----|------|---------|-------|
| TC_CL_001 | Deploy playbook --tags cleanup | deploy, sanity | *(root)* |
| TC_CL_002 | Verify containers removed | sanity | cleanup |
| TC_CL_003 | Verify systemd services stopped | sanity | cleanup |
| TC_CL_004 | Verify firewall ports closed | sanity | cleanup |
| TC_CL_005 | Verify S3 buckets removed | sanity | cleanup |
| TC_CL_006 | Verify s3cmd configuration removed | sanity | cleanup |
| TC_CL_007 | Verify build_status.yml removed | sanity | cleanup |
| TC_CL_008 | Verify registry has no images | sanity | cleanup |

### image_build_manager (Full End-to-End) — 13 Tests

| ID | Test | Markers | Suite |
|----|------|---------|-------|
| TC_IB_000 | Deploy image_build_manager.yml (no tags) | deploy, sanity | *(root)* |
| TC_IB_001 | Verify S3 storage backend (MinIO) | x86_64, aarch64, sanity | container |
| TC_IB_002 | Verify registry container running | x86_64, aarch64, sanity | container |
| TC_IB_003 | Verify required S3 buckets exist | x86_64, aarch64, sanity | s3 |
| TC_IB_004 | Verify x86_64 images pushed to S3 | x86_64, sanity | s3 |
| TC_IB_005 | Verify aarch64 images pushed to S3 | aarch64, sanity | s3 |
| TC_IB_006 | Verify x86_64 images in registry | x86_64, sanity | registry |
| TC_IB_007 | Verify aarch64 images in registry | aarch64, sanity | registry |
| TC_IB_008 | Verify build_status.yml reports success | x86_64, aarch64, sanity | registry |
| TC_IB_009 | Verify x86_64 functional groups built | x86_64, sanity | registry |
| TC_IB_010 | Verify aarch64 functional groups built | aarch64, sanity | registry |
| TC_IB_011 | Verify packages in x86_64 S3 images | x86_64, sanity | image_verification |
| TC_IB_012 | Verify packages in aarch64 S3 images | aarch64, sanity | image_verification |

**Total: 38 test cases across 5 scenarios.**

---

## 6. Data Flow

### 6.1 Input Flow

```
test/datasets/data_set_01/input/         (local — automation runner)
        │
        │  rsync via conftest.py (when sync_image_build_input: true)
        ▼
<clone_path>/src/input/project_default/ (target server)
        │
        │  ansible-playbook image_build_manager.yml
        ▼
/opt/omnia/image_build_manager/output/  (target server — runtime output)
```

### 6.2 Dataset Structure

```
datasets/data_set_01/
├── input/                              # Synced to <clone_path>/src/input/<project>/
│   ├── config.yml                      # Project config (also -> <clone_path>/config.yml)
│   ├── image_build_config.yml          # Domain input config
│   └── image_build_credentials.yml     # Vault-encrypted credentials
└── repo_manager_output/                # Synced to repo_manager_output_dir (sync_output: true)
    ├── repo_status.yml                 # RPM repo URLs, certs
    ├── functional_group_packages.yml
    └── certs/
        ├── pulp_webserver.crt
        └── pulp_webserver.key
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
- **Dataset credentials**: `image_build_credentials.yml` vault-encrypted
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
- Required files present: `input/config.yml`, `input/image_build_config.yml`,
  `input/image_build_credentials.yml`

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
4. Add test names/messages to `build_image_msgs.py`
5. Add scenario to `test_run_config.yml`
6. Update this design document

### Adding a New Verification Check

1. Add function to `build_image_func.py` (return dict pattern)
2. Add command to `CMDS` in `common_vars.py` (if new shell command)
3. Add messages to `build_image_msgs.py`
4. Create test in appropriate `fvt/` folder
5. Run pylint and verify score ≥ 8.7
