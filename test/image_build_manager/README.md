# Image Build Manager — Test Automation

Functional Verification Testing (FVT) for the `image_build_manager` domain
inside the **omnia monorepo**. Validates playbook deployment, container
infrastructure (MinIO + Registry), S3 storage, container registry, build
output, and image package contents.

Uses the **`omnia-auto`** pip package for common test utilities (host
connection, playbook runner, report generation, formatting).

---

## Prerequisites

| Requirement | Minimum | Notes |
|-------------|---------|-------|
| Python | 3.12+ | `python3 --version` |
| `sshpass` | — | `yum install sshpass` (only if password-based SSH) |
| Ansible | 2.15+ | Installed automatically by `setup_env.sh` |

### Target Server Setup

Before running tests, the target server must have the omnia environment
configured. This is done via `omnia.sh` in `src/main/`:

```bash
# On the target server:
cd <omnia_repo>/src/main/
vi omnia.env                  # Set SYSTEM_ADMIN_NIC_IPV4 at minimum
./omnia.sh -s                 # Installs env vars system-wide + creates venv
```

After `omnia.sh -s`, the following environment variables are available on
every login shell (via `/etc/profile.d/omnia-env.sh`):

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `SYSTEM_ADMIN_NIC_IPV4` | **Yes** | — | Admin NIC IP (Pulp, S3, registry endpoint) |
| `OMNIA_DATA_PATH` | No | `/opt/omnia` | Root data directory for all Omnia data |
| `OMNIA_PROJECT_NAME` | No | `project_default` | Project name for input/output paths |
| `SYSTEM_HOSTNAME` | No | `oim` | Short hostname of the OIM host |
| `SYSTEM_DOMAIN_NAME` | No | `omnia.cluster` | Domain name of the OIM host |

The test framework reads these from the target at runtime (sourcing
`/etc/omnia/omnia.env`) to resolve input sync paths and playbook parameters.

---

## Setup

```bash
# Step 1 — Enter the test directory
cd omnia/test/image_build_manager/

# Step 2 — Run setup (creates .venv, installs Python deps + omnia-auto)
bash setup_env.sh

# Step 3 — Activate the virtual environment
source .venv/bin/activate

# Step 4 — Install the omnia-auto package
pip install /path/to/omnia_auto-1.0.0-py3-none-any.whl

# Step 5 — Configure the test
vi test_config.yml       # Set oim_server_ip and clone_path
vi test_creds.yml        # Set oim_password (auto-encrypted on first run)

# Step 6 — Edit dataset input files
vi datasets/data_set_01/input/image_build_config.yml
vi datasets/data_set_01/input/image_build_credentials.yml
```

---

## Running Tests

```
./run_validation.sh <scenario> <command> [options]
./run_validation.sh --config          # Batch run from test_run_config.yml
./run_validation.sh list              # List available scenarios
./run_validation.sh --help            # Full usage
```

### Commands

| Command | Description |
|---------|-------------|
| `deploy` | Run the Ansible playbook only |
| `verify` | Run verification tests only (no playbook) |
| `test` | Full flow: deploy + verify |

### Scenarios

| Scenario | Playbook Tag | What It Tests |
|----------|-------------|---------------|
| `image_build_manager` | *(default: prepare + build)* | Full end-to-end |
| `validate` | `--tags validate` | Input config and credentials present |
| `prepare` | `--tags prepare` | MinIO, registry, systemd, S3 buckets |
| `build` | `--tags build` | S3 images, registry images, build_status |
| `cleanup` | `--tags cleanup` | All artifacts removed |

### Options

| Option | Description |
|--------|-------------|
| `--suite <name>` | Filter by subfolder (`container`, `s3`, `registry`) |
| `--marker <expr>` | Filter by marker (`sanity`, `x86_64`, `x86_64+sanity`) |
| `--debug` | Full debug output (pytest -vvs) |
| `-v, --verbose` | Increase pytest verbosity |

### Typical Workflow

```bash
./run_validation.sh cleanup test                                # 1. Clean previous state
./run_validation.sh validate test                               # 2. Validate inputs
./run_validation.sh prepare test                                # 3. Prepare infrastructure
./run_validation.sh build test --marker x86_64                  # 4. Build images
./run_validation.sh image_build_manager verify --marker sanity  # 5. Full verification
```

---

## Configuration

| File | Purpose |
|------|---------|
| `test_config.yml` | Target server IP, sync settings, dataset, report options |
| `test_creds.yml` | SSH password (auto-encrypted with Ansible Vault) |
| `test_run_config.yml` | Batch execution: scenario order, markers, suites |

### Execution Modes

- **Local mode** (`oim_server_ip: ""`): Tests run on the current machine.
- **Remote mode** (`oim_server_ip: "<IP>"`): Tests run against a remote server via SSH.

### How Sync Works (Remote Mode)

On session startup the framework performs:

1. **Project sync** — rsyncs the local omnia monorepo to `clone_path` on the target
2. **Input sync** — reads `OMNIA_DATA_PATH` and `OMNIA_PROJECT_NAME` from the target's `/etc/omnia/omnia.env`, creates the target directory if needed, then syncs `datasets/<dataset>/input/` → `<OMNIA_DATA_PATH>/image_build_manager/input/<project>/`
3. **Repo manager output sync** (optional) — syncs `datasets/<dataset>/repo_manager_output/` to the target's repo_manager output directory

### Datasets

Input files live in `datasets/data_set_01/`:

```
datasets/data_set_01/
├── input/
│   ├── image_build_config.yml        # Image build domain configuration
│   └── image_build_credentials.yml   # S3 credentials (Vault-encrypted)
└── repo_manager_output/
    ├── repo_status.yml               # RPM repo URLs, cert paths
    ├── functional_group_packages.yml # Package lists per functional group
    └── certs/                        # Pulp TLS certificates
```

See [`datasets/data_set_01/README.md`](datasets/data_set_01/README.md) for field details.

---

## Reports

Generated in the configured `report_path` (default `/opt/omnia/reports`):

| File | Format |
|------|--------|
| `image_test_report.json` | Machine-readable results |
| `image_test_report.html` | Interactive browser report |

---

## Test Cases

See [`fvt/TEST_CASES.md`](fvt/TEST_CASES.md) for the complete test case registry.

| Scenario | Prefix | Count |
|----------|--------|-------|
| image_build_manager | TC_IB_ | 12 |
| validate | TC_VL_ | 3 |
| prepare | TC_PR_ | 8 |
| build | TC_BD_ | 6 |
| cleanup | TC_CL_ | 8 |

---

## Directory Structure

```
test/image_build_manager/
├── setup_env.sh                 # Environment setup (--force, --debug)
├── run_validation.sh            # CLI runner
├── conftest.py                  # Pytest hooks, fixtures, report generation
├── test_config.yml              # Target server and sync settings
├── test_creds.yml               # SSH credentials (Ansible Vault)
├── test_run_config.yml          # Batch execution config
├── requirements.txt             # Python dependencies
│
├── docs/                        # Configuration documentation
│   ├── test_config.md
│   ├── test_creds.md
│   └── test_run_config.md
│
├── datasets/                    # Test input datasets
│   └── data_set_01/
│       ├── input/               # image_build_config, credentials
│       └── repo_manager_output/ # repo_status, packages, certs
│
├── library/                     # Reusable automation library
│   ├── functions/               # host_func, build_image_func, validation_func
│   ├── vars/                    # Constants, paths, commands (common_vars)
│   └── messages/                # Test names, log/assert messages
│
└── fvt/                         # Functional Verification Tests
    ├── TEST_CASES.md
    ├── image_build_manager/     # Full end-to-end
    │   ├── container/
    │   ├── s3/
    │   ├── registry/
    │   └── image_verification/
    ├── validate/                # Validate tag
    │   └── status/
    ├── prepare/                 # Prepare tag
    │   ├── container/
    │   └── s3/
    ├── build/                   # Build tag
    │   ├── s3/
    │   └── registry/
    └── cleanup/                 # Cleanup tag
        └── cleanup/
```

---

## Key Architecture Decisions (Monorepo)

| Area | Old (multi-repo) | New (monorepo) |
|------|-------------------|----------------|
| **Code delivery** | `git clone` on target | `rsync` project to target |
| **Config source** | `config.yml` in dataset | Environment variables on target (`omnia.env`) |
| **Env var setup** | N/A | `omnia.sh -s` installs to `/etc/omnia/omnia.env` |
| **Input sync dest** | `<clone_path>/src/input/<project>/` | `<OMNIA_DATA_PATH>/image_build_manager/input/<project>/` |
| **Playbook workdir** | `src/` | `src/image_build_manager/playbooks/` |
| **Common utilities** | Inline library | `omnia-auto` pip package |
| **Dir creation** | Manual | Auto-created by framework before sync |
