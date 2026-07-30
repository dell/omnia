# Omnia.sh — Test Automation Suite

Automated FVT/NFT validation for `omnia.sh` lifecycle operations (build, install, verify, reinstall, uninstall).

> **Detailed test case list:** See [TEST_CASES.md](TEST_CASES.md)

---

## 1. Prerequisites

| Requirement        | Detail                                                        |
|--------------------|---------------------------------------------------------------|
| OS                 | RHEL 10.x                                                     |
| Python             | 3.9+                                                          |
| Podman             | 4.x+ (container runtime)                                     |
| Network            | SSH access to OIM server, NFS server (if NFS dataset)         |
| Omnia source       | Cloned `omnia` repository                                    |

---

## 2. Setup

```bash
# 1. One-time environment setup
cd test/main
./setup_env.sh

# 2. Activate virtual environment
source .venv/bin/activate

# 3. Configure test parameters
vi test_config.yml           # OIM server IP, storage type, dataset
vi test_creds.yml            # Passwords (auto-encrypted on first run)
```

---

## 3. Directory Structure

```
main/
├── README.md                 # This file
├── TEST_CASES.md             # Detailed test case reference (tabled)
├── setup_env.sh              # Environment setup
├── pytest.ini                # Pytest config + marker definitions
├── conftest.py               # Fixtures, hooks, report capture
├── test_config.yml           # Test configuration (non-sensitive)
├── test_creds.yml            # Credentials (auto-encrypted with vault)
├── library/                  # Test library
│   ├── functions/            # Reusable verification functions
│   ├── vars/                 # Constants, commands, paths
│   ├── messages/             # Test names, log/assert messages
│   └── validation/           # Config validation (fields, datasets, reports)
├── datasets/                 # Storage configuration presets
│   ├── nfs_external/
│   ├── nfs_internal/
│   └── local_storage/
├── fvt/                      # Functional Verification Tests
│   ├── omnia_sh_install/
│   │   ├── container/        # Container lifecycle (deploy, verify)
│   │   └── security/         # SSH connectivity tests
│   ├── omnia_sh_reinstall/
│   │   └── container/        # Reinstall overwrite path
│   └── omnia_sh_uninstall/
│       └── cleanup/          # Uninstall + cleanup verification
└── nft/                      # Non-Functional Tests (parallel to fvt/)
```

---

## 4. Running Tests

### CLI Syntax

```
run_validation <scenario> <command> [--suite <suite>] [--marker <marker>]
run_validation --config [--continue-on-failure] [--restart]
run_validation list
```

> **Both `<scenario>` and `<command>` are mandatory.** If either is missing, the runner will show an error with examples.

### Commands

| Command     | What It Runs                                        |
|-------------|-----------------------------------------------------|
| `deploy`    | `test_deploy.py` only (execution phase)             |
| `verify`    | All tests except deploy (verification phase)        |
| `test`      | Deploy THEN verify (full lifecycle, stops if deploy fails) |

### Quick Start Examples

```bash
run_validation list                                         # show scenarios

run_validation omnia_sh_install deploy                      # build + fresh install
run_validation omnia_sh_install verify                      # verify all
run_validation omnia_sh_install test                        # deploy + verify

run_validation omnia_sh_install verify --suite container    # container tests only
run_validation omnia_sh_install verify --suite security     # SSH tests only
run_validation omnia_sh_install verify --marker smoke       # smoke subset only
run_validation omnia_sh_reinstall deploy                    # reinstall path

run_validation omnia_sh_reinstall verify                    # verify after reinstall

run_validation omnia_sh_uninstall deploy                    # run uninstall
run_validation omnia_sh_uninstall verify --suite cleanup    # verify cleanup
run_validation omnia_sh_uninstall test                      # uninstall + verify
```

### Suite + Marker Combinations

`--suite` filters by **functional area directory**, `--marker` filters by **validation quality**. They can be combined freely:

| Goal                                   | Command                                                                       |
|----------------------------------------|-------------------------------------------------------------------------------|
| All container tests                    | `run_validation omnia_sh_install verify --suite container`                    |
| All security tests                     | `run_validation omnia_sh_install verify --suite security`                     |
| Smoke tests only (all suites)          | `run_validation omnia_sh_install verify --marker smoke`                       |
| Smoke + container only                 | `run_validation omnia_sh_install verify --suite container --marker smoke`     |
| Security sanity subset                 | `run_validation omnia_sh_install verify --suite security --marker sanity`     |
| Functional tests only                  | `run_validation omnia_sh_install verify --marker functional`                  |
| Cleanup sanity checks                  | `run_validation omnia_sh_uninstall verify --suite cleanup --marker sanity`    |
| Reinstall verify (smoke)               | `run_validation omnia_sh_reinstall verify --marker smoke`                     |

> **Tip:** `--suite` is a directory filter, `--marker` is a pytest `-m` filter. Without either, all tests for the command are run.

### Config-Driven Batch Execution

Run all scenarios in sequence from `test_run_config.yml`:

```bash
run_validation --config                        # run all enabled scenarios in order
run_validation --config --continue-on-failure   # don't stop on first failure
run_validation --config --restart               # discard resume state, start fresh
```

**Config file:** `test_run_config.yml` (in the `main/` directory)

```yaml
scenarios:
  omnia_sh_install:
    order: 1          # execution order (ascending, must be unique)
    run: true         # true = execute, false = skip
    command: "test"   # deploy / verify / test
    suite: ""         # folder filter (empty = all)
    marker: ""        # pytest marker filter (empty = all)

  omnia_sh_reinstall:
    order: 2
    run: true
    command: "test"
    suite: ""
    marker: ""

  omnia_sh_uninstall:
    order: 3
    run: true
    command: "test"
    suite: ""
    marker: ""
```

**Validation rules:**
- `order` must be a unique integer across all scenarios
- `command` must be one of: `deploy`, `verify`, `test`
- Duplicate order values are a config error — batch aborts before running
- When `command: test`, deploy runs first; if it fails, verify is skipped
- Resume support: re-run `--config` to resume from the last failure; use `--restart` to start over

---

## 5. Validation Markers (IEEE 829 / SDD)

Markers are **test quality categories** — they classify the validation purpose. Actions like `deploy`, `verify`, `reinstall` are **CLI commands**, not markers.

| Marker        | Purpose                                           | Typical Use                     |
|---------------|---------------------------------------------------|---------------------------------|
| `sanity`      | Baseline verification — must pass after deploy    | Default gate for all deploys    |
| `smoke`       | Minimal critical-path subset (< 2 min)            | CI pipeline, quick health check |
| `regression`  | Full regression coverage                          | Nightly builds, release gate    |
| `functional`  | Feature-level functional verification             | Feature-specific validation     |
| `negative`    | Invalid input, error handling, boundary tests     | Robustness validation           |
| `security`    | Auth, SSH, credentials, access control            | Security audits                 |
| `performance` | Timing, throughput, resource benchmarks           | NFT baselines                   |
| `stress`      | Sustained load, concurrency, exhaustion           | NFT soak testing                |
| `integration` | Cross-component interaction                       | Multi-service tests             |
| `acceptance`  | End-to-end user acceptance                        | UAT sign-off                    |

---

## 6. Datasets (Storage Configurations)

Datasets control **what storage configuration** the tests use. They are NOT markers.

| Dataset          | `share_option` | `nfs_type` | Key Config                               |
|------------------|----------------|------------|------------------------------------------|
| `nfs_external`   | NFS            | external   | `nfs_server_ip`, `nfs_share_path`        |
| `nfs_internal`   | NFS            | internal   | `nfs_server_share_path`                  |
| `local_storage`  | Local          | —          | `omnia_shared_path`                      |

Enable via `test_config.yml`:

```yaml
use_dataset: true
dataset: nfs_external
```

---

## 7. Reports

Generated in `reports/` after each run:

| File                  | Format | Contents                                        |
|-----------------------|--------|-------------------------------------------------|
| `main_report.json`   | JSON   | Machine-readable results with TC IDs            |
| `main_report.html`   | HTML   | Interactive report with deploy/verify sections  |

---

## 8. Adding New Tests

1. Create test file in `fvt/<scenario>/<functional_area>/test_<name>.py`
2. Assign a TC ID: `TC_<AREA>_<SEQ>` (see [TEST_CASES.md](TEST_CASES.md))
3. Add proper markers (`@pytest.mark.sanity`, `@pytest.mark.smoke`, etc.)
4. Use `TestLogger` for structured output
5. Import functions/vars/messages from `main.library`
6. Update [TEST_CASES.md](TEST_CASES.md) with the new entry

```python
import pytest
from main.library import TestLogger, check_container_running

@pytest.mark.sanity
@pytest.mark.smoke
@pytest.mark.order(1)
def test_container_running(host):
    """TC_IT_003: Verify omnia_core container is running."""
    log = TestLogger("[TC_IT_003] Verify container running")
    result = check_container_running(host)
    if result["success"]:
        log.passed("Container is running")
    else:
        log.failed("Container not running", result["error"])
    assert result["success"], result["error"]
```

---

## 9. Troubleshooting

| Problem                           | Solution                                                                    |
|-----------------------------------|-----------------------------------------------------------------------------|
| Container already running         | `run_validation omnia_sh_uninstall deploy` first, or use `omnia_sh_reinstall` |
| NFS server not reachable          | `ping <nfs_ip>` and `showmount -e <nfs_ip>`                                |
| Vault encryption error            | `rm .test_creds.key` then re-edit `test_creds.yml`                          |
| Tests not collected               | Check `pytest.ini` testpaths, verify `__init__.py` in all directories       |

---

## License

Copyright 2026 Dell Inc. or its subsidiaries. All Rights Reserved.
Licensed under the Apache License, Version 2.0.
