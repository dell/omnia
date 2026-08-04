# Build Stream — Test Automation

Functional Verification Testing (FVT) for the `build_stream` domain
inside the **omnia monorepo**. Validates playbook deployment, container
infrastructure (BuildStream API, PostgreSQL, GitLab), database tables,
and service health.

Uses the **`omnia-auto`** package (from `test/plugins/`) for common test
utilities (host connection, playbook runner, report generation, formatting).

---

## Prerequisites

| Requirement | Minimum | Notes |
|-------------|---------|-------|
| Python | 3.12+ | `python3 --version` |
| `sshpass` | — | `yum install sshpass` (only if password-based SSH) |
| Ansible | 2.15+ | Installed automatically by `setup_env.sh` |

### Target Server Setup

Before running tests, the target server must have the omnia environment
configured via `omnia.sh` in `src/main/`.

---

## Setup

```bash
# Step 1 — Enter the test directory
cd omnia/test/build_stream/

# Step 2 — Run setup (creates .venv, installs Python deps + omnia-auto)
bash ../image_build_manager/setup_env.sh

# Step 3 — Activate the virtual environment
source .venv/bin/activate

# Step 4 — Configure the test
vi test_config.yml       # Set oim_server_ip and clone_path
vi test_creds.yml        # Set oim_password (auto-encrypted on first run)

# Step 5 — Edit dataset input files
vi datasets/data_set_01/input/build_stream_config.yml
```

---

## Running Tests

```bash
# Run all build_stream sanity tests
pytest fvt/build_stream/ --marker sanity -v

# Run prepare scenario (deploy + verify)
pytest fvt/prepare/ -v

# Run cleanup scenario
pytest fvt/cleanup/ -v

# Run only infrastructure checks (no deploy)
pytest fvt/build_stream/infrastructure/ --marker infrastructure -v

# Run specific test case
pytest fvt/build_stream/infrastructure/test_infrastructure.py::test_build_stream_health -v
```

---

## Scenarios

| Scenario | Playbook Tag | What It Tests |
|----------|-------------|---------------|
| `build_stream` | *(default: prepare + build)* | Full end-to-end |
| `prepare` | `--tags prepare` | BSM, Postgres, GitLab containers + API |
| `cleanup` | `--tags cleanup` | All resources removed |

---

## Configuration

| File | Purpose |
|------|---------|
| `test_config.yml` | Target server IP, sync settings, dataset, report options |
| `test_creds.yml` | SSH password (auto-encrypted with Ansible Vault) |

### Execution Modes

- **Local mode** (`oim_server_ip: ""`): Tests run on the current machine.
- **Remote mode** (`oim_server_ip: "<IP>"`): Tests run against a remote server via SSH.

---

## Test Cases

See [`fvt/TEST_CASES.md`](fvt/TEST_CASES.md) for the complete test case registry.

| Scenario | Prefix | Count |
|----------|--------|-------|
| build_stream | TC_BS_ | 6 |
| prepare | TC_PR_ | 7 |
| cleanup | TC_CL_ | 4 |

---

## Directory Structure

```
test/build_stream/
├── conftest.py                  # Pytest hooks, fixtures, report generation
├── test_config.yml              # Target server and sync settings
├── test_creds.yml               # SSH credentials (Ansible Vault)
├── requirements.txt             # Python dependencies
│
├── datasets/                    # Test input datasets
│   └── data_set_01/
│       └── input/               # build_stream_config.yml
│
├── library/                     # Reusable automation library
│   ├── functions/               # build_stream_func, host_func, validation_func
│   ├── vars/                    # Constants, paths, commands (common_vars)
│   └── messages/                # Test names, log/assert messages
│
└── fvt/                         # Functional Verification Tests
    ├── TEST_CASES.md
    ├── build_stream/            # Full end-to-end
    │   └── infrastructure/      # Container, API, DB, GitLab checks
    ├── prepare/                 # Prepare tag
    │   └── infrastructure/      # Post-prepare infrastructure checks
    └── cleanup/                 # Cleanup tag
        └── cleanup/             # Post-cleanup verification
```

---

## Molecule Test Migration

This FVT structure replaces the molecule-based tests from
`automation_v22/molecule/build_stream/`. The mapping is documented in
[`fvt/TEST_CASES.md`](fvt/TEST_CASES.md#molecule-test-coverage-mapping).

### Covered (minimum working set)
- Infrastructure checks (enabled, API health, Postgres, GitLab)
- Playbook deploy + verify for prepare/cleanup scenarios
- Container and port verification

### Future (not yet covered)
- Pipeline trigger tests (auto-trigger, manual trigger)
- Pipeline stage monitoring and DB verification
- Cleanup pipeline (image group cleanup)
- Generated input verification
- Stress tests
