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

# Step 4b — Set domain credentials (S3 + aarch64)
bash setup_env.sh --set-domain-creds  # Interactive prompt for S3 access/secret + aarch64 pw

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

All credentials are stored in `test_creds.yml` and auto-encrypted with Ansible Vault.
SSH credential flags require `oim_server_ip` to be set in `test_config.yml`.
Domain credential flags (`--set-domain-creds` / `--domain-creds`) do **not** require
`oim_server_ip` — they only write to the local `test_creds.yml` file.

#### SSH Credentials (OIM server access)

| Flag | Description |
|------|-------------|
| `--set-password` | Interactive prompt (asks twice). If password exists, asks yes/no to update. |
| `--update-password` | Force-update existing SSH password (no confirmation prompt). |
| `--password PWD` | Non-interactive. Overwrites any existing SSH credentials. |

#### Domain Credentials (S3 / aarch64)

The image build playbook (`image_build_manager.yml`) requires access to S3/MinIO
for image storage and optionally to a remote aarch64 host.  These credentials are
stored alongside the SSH password in `test_creds.yml` (vault-encrypted) and are
read by `collect_build_credentials` during the test deployment step.
These flags do **not** require `oim_server_ip` — they only write to the local file.

| Field | Required | Description |
|-------|----------|-------------|
| `s3_access_id` | Yes | MinIO / S3 access key ID |
| `s3_secret_key` | Yes | MinIO / S3 secret key |
| `aarch64_ssh_password` | No | SSH password for the aarch64 build host. Leave empty for key-based auth or if no aarch64 build is needed. |

| Flag | Description |
|------|-------------|
| `--set-domain-creds` | Interactive prompt for S3 access ID, secret, and aarch64 password. |
| `--domain-creds JSON` | Non-interactive. Pass a JSON string with `s3_access_id`, `s3_secret_key`, `aarch64_ssh_password`. |

> **Note**: `--set-password` and `--set-domain-creds` are independent — run each separately, or combine in one invocation:
> ```bash
> bash setup_env.sh --set-password      # sets oim_password (requires oim_server_ip)
> bash setup_env.sh --set-domain-creds  # sets S3 + aarch64 creds (no oim_server_ip needed)
> ```
> Existing fields not updated by a given flag are **preserved**.

---

## Running Tests

```
./run_validation.sh image_build_manager <command>             # All tags except cleanup
./run_validation.sh image_build_manager <tag> <command>        # Specific tag
./run_validation.sh image_build_manager list                   # List available tags
./run_validation.sh --config                                   # Batch from test_run_config.yml
```

### Commands

| Command | Description |
|---------|-------------|
| `exec` | Run the Ansible playbook only |
| `verify` | Run verification tests only (no playbook) |
| `test` | Full flow: exec + verify |

### Tags

| Tag | Playbook Tag | What It Tests |
|-----|-------------|---------------|
| `precheck` | `--tags precheck` | Env vars, hostname, IP, connectivity, omnia.sh setup |
| `validate` | `--tags validate` | Input config and credentials present |
| `prepare` | `--tags prepare` | MinIO, registry, systemd, S3 buckets |
| `build` | `--tags build` | S3 images, registry images, build_status, **naming convention** |
| `cleanup` | `--tags cleanup` | All artifacts removed |
| `cleanup_images` | `--tags cleanup_images` | Delete S3 + registry images |
| *(none)* | *(no tag)* | Full end-to-end (prepare + build) |

#### Build-type naming convention (within `build` tag)

Both `image-builder` and `image-thrillhouse` produce artifacts with distinct suffixes
(`-imgbld` / `-imgth`) to prevent cross-contamination in the registry and S3 bucket.
The naming tests (`naming/` suite) run automatically within the `build` tag.

```bash
# Run only naming convention tests
./run_validation.sh image_build_manager build verify --suite naming
./run_validation.sh image_build_manager build verify --suite naming --marker x86_64+sanity
```

### NFT

```bash
./run_validation.sh nft test    # Performance thresholds and idempotency
```

### Options

| Option | Description |
|--------|-------------|
| `--suite <name>` | Filter by subfolder (`container`, `s3`, `registry`, `naming`) |
| `--marker <expr>` | Filter by pytest marker expression |
| `-v, --verbose` | Increase pytest verbosity |
| `--debug` | Full debug output (pytest `-vvs`) |

### Marker Expressions

| Syntax | Example | Meaning |
|--------|---------|---------|
| Single | `--marker sanity` | Tests with `@pytest.mark.sanity` |
| AND (`+`) | `--marker x86_64+sanity` | Tests with BOTH markers |
| OR (`,`) | `--marker x86_64,aarch64` | Tests with EITHER marker |

Available markers: `sanity`, `x86_64`, `aarch64`, `functional`, `deploy`

### More Examples

```bash
# Marker expressions
./run_validation.sh image_build_manager build test --marker x86_64+sanity    # x86_64 AND sanity
./run_validation.sh image_build_manager build test --marker x86_64,aarch64   # x86_64 OR aarch64
./run_validation.sh image_build_manager build verify --suite registry        # Registry tests only
./run_validation.sh image_build_manager build verify --suite naming          # Naming tests only

# Config-driven execution
./run_validation.sh --config                                                 # Run test_run_config.yml

# List tags and test counts
./run_validation.sh image_build_manager list
```

### Typical Workflow

```bash
./run_validation.sh image_build_manager precheck verify                 # 0. Precheck environment
./run_validation.sh image_build_manager cleanup test                    # 1. Clean previous state
./run_validation.sh image_build_manager validate test                   # 2. Validate inputs
./run_validation.sh image_build_manager prepare test                    # 3. Prepare infrastructure
./run_validation.sh image_build_manager build test --marker x86_64      # 4. Build images
./run_validation.sh image_build_manager build verify --suite naming     # 4b. Naming convention
./run_validation.sh image_build_manager verify --marker sanity          # 5. Full verification
./run_validation.sh nft test                                            # 6. Performance
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

See [`fvt/README.md`](fvt/README.md) for the complete test case registry.

| Tag | Prefix | Count | Notes |
|-----|--------|-------|-------|
| precheck | TC_PC_ | 6 | 001–006 |
| validate | TC_VL_ | 4 | 001–004 (includes repo_ssl_verify_config) |
| prepare | TC_PR_ | 8 | 001–008 |
| build | TC_BD_ | 16 | 001–016 (007–011 naming, 012–015 aarch64+packages, 016 repo_ssl_verify) |
| cleanup | TC_CL_ | 8 | 001–008 |
| cleanup_images | TC_CI_ | 3 | 001–003 |
| nft | NFT_ | 4 | |
| **Total** | | **50** | Plus TC_IB_001 (full-stack deploy) |

### Build-type naming convention tests (TC_BD_007 – TC_BD_011)

| Test | Build type | Checks |
|------|-----------|--------|
| TC_BD_007 | image-builder | x86_64 registry images end with `-imgbld`; no `-imgth` leakage |
| TC_BD_008 | image-builder | x86_64 S3 paths include `-imgbld`; no `-imgth` leakage |
| TC_BD_009 | image-thrillhouse | x86_64 registry images end with `-imgth`; no `-imgbld` leakage |
| TC_BD_010 | image-thrillhouse | x86_64 S3 paths include `-imgth`; no `-imgbld` leakage |
| TC_BD_011 | both | `-imgbld` and `-imgth` base names never collide (isolation check) |

---

## Directory Structure

```
test/image_build_manager/
├── setup_env.sh                 # Environment setup (--venv, --set-password, etc.)
├── run_validation.sh            # CLI runner (FVT + NFT)
├── conftest.py                  # Pytest hooks, fixtures, report generation
├── test_config.yml              # Target server and sync settings
├── test_creds.yml               # All credentials: SSH + S3 + aarch64 (Ansible Vault, gitignored)
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
│   ├── README.md                # Test case registry (authoritative)
│   ├── precheck/                # Precheck tag (env + connectivity)
│   │   └── connectivity/
│   ├── validate/                # Validate tag
│   │   └── status/
│   ├── prepare/                 # Prepare tag
│   │   ├── container/
│   │   └── s3/
│   ├── build/                   # Build tag
│   │   ├── s3/
│   │   ├── registry/
│   │   ├── naming/              # Naming convention tests (TC_BD_007-011)
│   │   └── image_verification/  # Package verification (TC_BD_014-015)
│   ├── cleanup/                 # Cleanup tag
│   │   └── cleanup/
│   └── cleanup_images/          # Cleanup images tag
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
