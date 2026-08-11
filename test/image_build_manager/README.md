# Image Build Manager — Test Automation

Functional Verification Testing (FVT) for the `image_build_manager` domain
inside the **omnia monorepo**. Validates playbook deployment, container
infrastructure (MinIO + Registry), S3 storage, container registry, build
output, and image package contents.

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
./omnia.sh --setup-venv       # Installs env vars system-wide + creates venv
```

After `omnia.sh --setup-venv`, the following environment variables are available
on every login shell (via `/etc/profile.d/omnia-env.sh`):

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `SYSTEM_ADMIN_NIC_IPV4` | **Yes** | — | Admin NIC IP — must be assigned to a local interface (`hostname -I`) |
| `SYSTEM_HOSTNAME` | **Yes** | `oim` | Short hostname — must match `hostname -s` output |
| `SYSTEM_DOMAIN_NAME` | **Yes** | `omnia.cluster` | Domain name — validated against `hostname -d` |
| `OMNIA_DATA_PATH` | **Yes** | `/opt/omnia` | Root data directory for all Omnia data |
| `OMNIA_PROJECT_NAME` | **Yes** | `project_default` | Project name for input/output paths |
| `OMNIA_VERSION` | **Yes** | — | Omnia release version |

The test framework reads these from the target at runtime (sourcing
`/etc/omnia/omnia.env`) to resolve input sync paths and playbook parameters.

---

## Setup

```bash
# Step 1 — Enter the test directory
cd omnia/test/image_build_manager/

# Step 2 — Configure the target server
vi test_config.yml       # Set oim_server_ip for remote mode

# Step 3 — Run setup (choose one install mode)
bash setup_env.sh                    # Baremetal (default) or active venv
bash setup_env.sh --venv             # Create .venv/ and install there
bash setup_env.sh --venv --force     # Recreate .venv/ from scratch

# Step 4 — Set SSH password (required for remote mode)
bash setup_env.sh --set-password     # Interactive prompt (2× confirmation)
bash setup_env.sh --password 'pass'  # Non-interactive

# Step 5 — Activate environment (if using --venv mode)
source .venv/bin/activate            # For --venv mode
source .run_validation_rc            # For baremetal mode (tab completion)

# Step 6 — (Optional) Generate a dataset for custom input
cd datasets/generator/
python generate_dataset.py my_dataset defaults
cd ../..
# Set: dataset: "my_dataset" in test_config.yml
# Or leave dataset: "" to use input from target's $OMNIA_DATA_PATH

# Step 7 — Run tests
./run_validation.sh prepare verify --marker sanity
```

### Setup Modes

| Mode | Command | Description |
|------|---------|-------------|
| Baremetal | `bash setup_env.sh` | Installs via `pip --user` into system Python |
| Active venv | `bash setup_env.sh` | Auto-detects active venv, installs there |
| New venv | `bash setup_env.sh --venv` | Creates `.venv/` and installs inside |
| Force recreate | `bash setup_env.sh --venv --force` | Deletes existing `.venv/` first |

### Credential Management

Credentials are required for remote mode (`oim_server_ip` set in `test_config.yml`).
The SSH password is saved to `test_creds.yml` and auto-encrypted with Ansible Vault.

| Flag | Description |
|------|-------------|
| `--set-password` | Interactive prompt (asks twice). If password exists, asks yes/no to update. |
| `--update-password` | Force-update existing password (no confirmation prompt). |
| `--password PWD` | Non-interactive. Overwrites any existing credentials. |

> **Note**: All credential flags require `oim_server_ip` to be set in `test_config.yml`.

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

### FVT Scenarios

| Scenario | Playbook Tag | What It Tests |
|----------|-------------|---------------|
| `precheck` | `--tags precheck` | Env vars, hostname, IP, connectivity, omnia.sh setup |
| `image_build_manager` | *(default: prepare + build)* | Full end-to-end |
| `validate` | `--tags validate` | Input config and credentials present |
| `prepare` | `--tags prepare` | MinIO, registry, systemd, S3 buckets |
| `build` | `--tags build` | S3 images, registry images, build_status |
| `cleanup` | `--tags cleanup` | All artifacts removed |

### NFT Scenario

| Scenario | Marker | What It Tests |
|----------|--------|---------------|
| `nft` | `@pytest.mark.nft` | Performance thresholds and idempotency |

### Options

| Option | Description |
|--------|-------------|
| `--suite <name>` | Filter by subfolder (`container`, `s3`, `registry`) |
| `--marker <expr>` | Filter by marker (`sanity`, `x86_64`, `x86_64+sanity`) |
| `--debug` | Full debug output (pytest -vvs) |
| `-v, --verbose` | Increase pytest verbosity |

### Typical Workflow

```bash
./run_validation.sh precheck verify --marker sanity             # 0. Precheck environment
./run_validation.sh cleanup test                                # 1. Clean previous state
./run_validation.sh validate test                               # 2. Validate inputs
./run_validation.sh prepare test                                # 3. Prepare infrastructure
./run_validation.sh build test --marker x86_64                  # 4. Build images
./run_validation.sh image_build_manager verify --marker sanity  # 5. Full verification
./run_validation.sh nft test                                    # 6. Performance + idempotency
```

---

## Configuration

| File | Purpose | Git Status |
|------|---------|------------|
| `test_config.yml` | Target server IP, sync settings, dataset, report options | Tracked |
| `test_creds.yml` | SSH password (auto-encrypted with Ansible Vault) | **Gitignored** |
| `.test_creds.key` | Vault encryption key (auto-generated) | **Gitignored** |
| `test_run_config.yml` | Batch execution: scenario order, markers, suites | Tracked |

### Key Settings in `test_config.yml`

| Setting | Required | Default | Description |
|---------|----------|---------|-------------|
| `oim_server_ip` | No | `""` (local) | Target server IP. Leave empty for local mode. |
| `clone_path` | Remote only | `/omnia` | Path on the **target server** where project code is synced. In local mode, the playbook path is resolved automatically from the source tree. |
| `venv_path` | No | `""` | Python venv path on target. If set, activated before `ansible-playbook`. Leave empty to use system-wide ansible. |
| `dataset` | No | `""` | Empty = input from target's `$OMNIA_DATA_PATH/image_build_manager/input/<project>/`. Set to a generated dataset name for custom inputs. |
| `project_name` | No | `project_default` | Project name for input/output paths on target. |

### Execution Modes

- **Local mode** (`oim_server_ip: ""`): Tests run on the current machine.
- **Remote mode** (`oim_server_ip: "<IP>"`): Tests run against a remote server via SSH.

### How Sync Works (Remote Mode)

On session startup the framework performs:

1. **Project sync** — rsyncs the local omnia monorepo to `clone_path` on the target
2. **Input sync** — reads `OMNIA_DATA_PATH` and `OMNIA_PROJECT_NAME` from the target's `/etc/omnia/omnia.env`, creates the target directory if needed, then syncs input files to `<OMNIA_DATA_PATH>/image_build_manager/input/<project>/`
3. **Repo manager output sync** (optional) — syncs repo_manager_output to the target's repo_manager output directory

### Input Files

#### Option A: Empty dataset (`dataset: ""`) — Target server input

When `dataset` is empty, the playbook reads input files from the **target server** at:

```
$OMNIA_DATA_PATH/image_build_manager/input/<project_name>/
```

No input files are synced from the local machine. Files must already exist on the
target (placed by `omnia.sh` setup or a prior deployment). This is the **production behavior**.

When `sync_image_build_input: true` AND `dataset: ""`, the framework syncs from
`src/image_build_manager/input/` to the target path as a development convenience.

#### Option B: Generated dataset (`dataset: "<name>"`)

Create a dataset using the [dataset generator](datasets/generator/README.md),
then set `dataset: "<name>"` in `test_config.yml`:

```bash
cd datasets/generator/

# Generate from a profile
python generate_dataset.py my_dataset defaults

# Generate with overrides
python generate_dataset.py my_dataset defaults --var s3_provider=powerscale

# Copy directly from src/ (quick bootstrap)
python generate_dataset.py my_dataset --from-src

# List available profiles
python generate_dataset.py --list-profiles
```

The generated dataset contains all required input files:

| File | Location |
|------|----------|
| `image_build_config.yml` | `datasets/<name>/input/` |
| `image_build_credentials.yml` | `datasets/<name>/input/` |
| `repo_status.yml` | `datasets/<name>/repo_manager_output/` |

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
| image_build_manager | TC_IB_ | 13 |
| precheck | TC_PC_ | 3 |
| validate | TC_VL_ | 3 |
| prepare | TC_PR_ | 8 |
| build | TC_BD_ | 6 |
| cleanup | TC_CL_ | 8 |
| nft | NFT_ | 4 |

---

## Directory Structure

```
test/image_build_manager/
├── setup_env.sh                 # Environment setup (--venv, --set-password, etc.)
├── run_validation.sh            # CLI runner (FVT + NFT)
├── conftest.py                  # Pytest hooks, fixtures, report generation
├── test_config.yml              # Target server and sync settings
├── test_creds.yml               # SSH credentials (Ansible Vault, gitignored)
├── test_run_config.yml          # Batch execution config
├── requirements.txt             # Python dependencies
│
├── docs/                        # Configuration documentation
│   ├── test_config.md
│   ├── test_creds.md
│   └── test_run_config.md
│
├── datasets/                    # Test datasets (generated via generator tool)
│   └── generator/               # Dataset generator tool
│       ├── generate_dataset.py
│       ├── profiles/            # Variable profiles (YAML)
│       └── templates/           # Jinja2 templates
│
├── library/                     # Reusable automation library
│   ├── functions/               # host_func, build_image_func, validation_func
│   ├── vars/                    # Constants, paths, commands (common_vars)
│   └── messages/                # Test names, log/assert messages
│
├── fvt/                         # Functional Verification Tests
│   ├── TEST_CASES.md
│   ├── image_build_manager/     # Full end-to-end
│   │   ├── container/
│   │   ├── s3/
│   │   ├── registry/
│   │   └── image_verification/
│   ├── precheck/                # Precheck tag (env + connectivity)
│   │   └── connectivity/
│   ├── validate/                # Validate tag
│   │   └── status/
│   ├── prepare/                 # Prepare tag
│   │   ├── container/
│   │   └── s3/
│   ├── build/                   # Build tag
│   │   ├── s3/
│   │   └── registry/
│   └── cleanup/                 # Cleanup tag
│       └── cleanup/
│
├── nft/                         # Non-Functional Tests
│   ├── README.md                # NFT documentation (thresholds, execution)
│   ├── test_performance.py      # Performance threshold tests (NFT_001–NFT_003)
│   └── test_idempotency.py      # Idempotency tests (NFT_004)
│
└── ut/                          # Unit Tests
    └── conftest.py
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

### How this module integrates with `omnia-auto`

**Step 1 — `conftest.py`** calls `omnia_auto.configure()` to register the test directory and config files.

**Step 2 — `library/functions/__init__.py`** imports from `omnia_auto` and wraps `run_playbook()` with module-specific defaults:

```python
from omnia_auto import run_playbook as _run_playbook
from ..vars.common_vars import PLAYBOOK_ENTRY_POINT, PLAYBOOK_WORKDIR

def run_playbook(tag=None, **kwargs):
    return _run_playbook(
        playbook=kwargs.pop("playbook", PLAYBOOK_ENTRY_POINT),
        playbook_workdir=kwargs.pop("playbook_workdir", PLAYBOOK_WORKDIR),
        tag=tag, **kwargs,
    )
```

**Step 3 — Test files** call the wrapper without needing to know the playbook details:

```python
from library.functions import run_playbook, TestLogger

def test_prepare_phase():
    tl = TestLogger("Verify prepare phase", "TC_PR_001")
    result = run_playbook(tag="prepare", timeout=1800)
    assert result["success"], result["error"]
```

For the full `omnia-auto` API reference, see the package's
[USAGE.md](../plugins/USAGE.md) and [docs/](../plugins/docs/).

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
