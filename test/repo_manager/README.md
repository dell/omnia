# Repo Manager — Test Automation

Functional Verification Testing (FVT) for the `repo_manager` domain
inside the **omnia monorepo**. Validates playbook deployment, Pulp
container infrastructure (port 2225), RPM repository sync, software
configuration, and endpoint settings.

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
| `SYSTEM_ADMIN_NIC_IPV4` | **Yes** | — | Admin NIC IP (Pulp endpoint) |
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
cd omnia/test/repo_manager/

# Step 2 — Run setup (creates .venv, installs Python deps + omnia-auto)
bash setup_env.sh

# Step 3 — Activate the virtual environment
source .venv/bin/activate

# Step 4 — omnia-auto is installed automatically from test/plugins/dist/
# (via requirements.txt → ../plugins/dist/omnia_auto-1.0.0-py3-none-any.whl)

# Step 5 — Configure the test
vi test_config.yml       # Set oim_server_ip and clone_path
vi test_creds.yml        # Set oim_password (auto-encrypted on first run)

# Step 6 — Edit dataset input files
vi datasets/data_set_01/input/repo_manager_config.yml
vi datasets/data_set_01/input/repo_manager_config_credentials.yml
vi datasets/data_set_01/input/repo_manager_endpoint_config.yml
vi datasets/data_set_01/input/software_config.json
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
| `repo_manager` | *(default: deploy + download)* | Full end-to-end |
| `validate` | `--tags validate` | Input config, credentials, endpoint settings |
| `deploy` | `--tags deploy` | Pulp container (port 2225), systemd services |
| `download` | `--tags download` | RPM repo sync, package availability |
| `cleanup` | `--tags cleanup` | All artifacts removed |

### Options

| Option | Description |
|--------|-------------|
| `--suite <name>` | Filter by subfolder (`pulp`, `repos`, etc.) |
| `--marker <expr>` | Filter by marker (`sanity`, `x86_64`, `x86_64+sanity`) |
| `--debug` | Full debug output (pytest -vvs) |
| `-v, --verbose` | Increase pytest verbosity |

### Typical Workflow

```bash
./run_validation.sh cleanup test                             # 1. Clean previous state
./run_validation.sh validate test                            # 2. Validate inputs
./run_validation.sh deploy test                              # 3. Deploy Pulp container
./run_validation.sh download test --marker x86_64            # 4. Download repos
./run_validation.sh repo_manager verify --marker sanity      # 5. Full verification
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
2. **Input sync** — reads `OMNIA_DATA_PATH` and `OMNIA_PROJECT_NAME` from the target's `/etc/omnia/omnia.env`, creates the target directory if needed, then syncs `datasets/<dataset>/input/` → `<OMNIA_DATA_PATH>/repo_manager/input/<project>/`

### Datasets

Input files live in `datasets/data_set_01/`:

```
datasets/data_set_01/
└── input/
    ├── repo_manager_config.yml                 # Repository URL configuration
    ├── repo_manager_config_credentials.yml     # Pulp and Docker credentials
    ├── repo_manager_endpoint_config.yml        # Pulp server endpoint settings
    └── software_config.json                    # Software and OS configuration
```

See [`datasets/data_set_01/README.md`](datasets/data_set_01/README.md) for field details.

---

## Reports

Generated in the configured `report_path` (default `/opt/omnia/reports`):

| File | Format |
|------|--------|
| `repo_manager_test_report.json` | Machine-readable results |
| `repo_manager_test_report.html` | Interactive browser report |

---

## Test Cases

### Unit Tests (ut/)

| Test File | Tests |
|-----------|-------|
| `test_software_config.py` | 8 tests — software_config.json structure and content |
| `test_validate_repo_manager_config.py` | 5 tests — repo_manager_config.yml schema |
| `test_endpoint_config.py` | 5 tests — endpoint config structure |

### Functional Tests (fvt/)

| Scenario | Prefix | Description |
|----------|--------|-------------|
| repo_manager | TC_RM_ | Full end-to-end verification |
| validate | TC_VL_ | Input configuration validation |
| deploy | TC_DP_ | Pulp container deployment |
| download | TC_DL_ | Repository sync verification |
| cleanup | TC_CL_ | Resource cleanup verification |

---

## Directory Structure

```
test/repo_manager/
├── setup_env.sh                 # Environment setup (--force, --debug)
├── run_validation.sh            # CLI runner
├── README.md                    # This file
│
├── docs/                        # Configuration documentation
│   ├── test_config.md
│   ├── test_creds.md
│   └── test_run_config.md
│
├── datasets/                    # Test input datasets
│   └── data_set_01/
│       └── input/               # repo_manager_config, credentials, endpoint, software
│
├── ut/                          # Unit Tests
│   ├── __init__.py
│   ├── conftest.py              # Pytest fixtures (config loaders)
│   ├── test_software_config.py
│   ├── test_validate_repo_manager_config.py
│   └── test_endpoint_config.py
│
├── nft/                         # Non-functional Tests (placeholder)
│   └── .gitkeep
│
└── fvt/                         # Functional Verification Tests
```

---

## Using the `omnia-auto` Pip Package

This module uses the **[omnia-auto](../plugins/)** package (installed from
`test/plugins/dist/omnia_auto-1.0.0-py3-none-any.whl`) for all common test
automation utilities.  The package provides:

| Category | Functions used |
|----------|---------------|
| **Config** | `configure()`, `load_test_config()`, `load_test_credentials()`, `get_setting()` |
| **Host** | `get_testinfra_host()`, `is_local_execution()`, `run_on_host()`, `connection_params()` |
| **Remote utils** | `read_remote_env()`, `ensure_remote_dir()`, `resolve_domain_input_path()` |
| **Sync** | `sync_files()`, `clone_repo()` |
| **Runner** | `run_playbook()` — wrapped with module-specific playbook/workdir |
| **Formatting** | `TestLogger`, `Colors`, `Symbols`, `log()`, `add_session_result()`, `print_summary_table()` |
| **Report** | `TestReport`, `set_current_report()`, `get_current_report()` |

---

## Key Architecture Decisions (Monorepo)

| Area | Old (multi-repo) | New (monorepo) |
|------|-------------------|----------------|
| **Code delivery** | `git clone` on target | `rsync` project to target |
| **Config source** | `config.yml` in dataset | Environment variables on target (`omnia.env`) |
| **Env var setup** | N/A | `omnia.sh -s` installs to `/etc/omnia/omnia.env` |
| **Input sync dest** | `<clone_path>/src/input/<project>/` | `<OMNIA_DATA_PATH>/repo_manager/input/<project>/` |
| **Playbook workdir** | `src/` | `src/repo_manager/playbooks/` |
| **Common utilities** | Inline library | `omnia-auto` pip package |
| **Dir creation** | Manual | Auto-created by framework before sync |
