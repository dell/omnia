# Image Build Manager — Test Automation

Functional, non-functional, and unit-test automation for the
`image_build_manager` domain inside the **omnia monorepo**. It validates
playbook deployment, container infrastructure (MinIO + Registry), S3 storage,
container registry, build output, and image package contents.

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
# On the target server (replace /path/to/omnia with the checkout path):
cd /path/to/omnia/src/main/
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
`/etc/omnia/omnia.env`) to resolve OIM-side input paths and playbook parameters.
The remote aarch64 builder is the intentional exception: its work directory is
`/opt/omnia/image_build_manager`, matching the product role contract because
that node does not run `omnia.sh` and has no `OMNIA_DATA_PATH` environment
variable.

---

## Setup

```bash
# Step 1 — Enter the test directory
cd omnia/test/image_build_manager/

# Step 2 — Select local or remote execution in test_config.yml
vi test_config.yml       # See "Execution Modes" below

# Step 3 — Run setup (choose one install mode)
./setup_env.sh                    # Baremetal (default) or active venv
./setup_env.sh --force            # Force-reinstall every requirement
./setup_env.sh --venv             # Create .venv/ and install there
./setup_env.sh --venv --force     # Recreate .venv/ and reinstall requirements

# Step 4 — Set SSH credentials (optional; for remote mode)
./setup_env.sh --set-creds        # Interactive prompt (2x confirmation)
./setup_env.sh --creds '<password>'  # Non-interactive

# Step 4b — On the execution OIM, set domain credentials (S3 + aarch64)
# For remote mode, run this from test/image_build_manager on the target OIM.
./setup_env.sh --set-domain-creds  # Interactive prompt for S3 access/secret + aarch64

# Step 5 — Activate environment (if using --venv mode)
source .venv/bin/activate            # For --venv mode
# No extra sourcing needed for baremetal

# Step 6 — (Optional) Generate a dataset for custom input
cd datasets/generator/
./generate_dataset.py create my_dataset --profile internet-config
cd ../..
# Set: dataset: "my_dataset" in test_config.yml
# Enable sync_image_build_input/sync_output when the dataset should be copied
# Leave dataset: "" and sync disabled to keep the target's existing input
# (with sync enabled, an empty name uses the canonical src/ examples)

# Step 7 — Run tests
./run_validation.sh fvt_image_build_manager precheck test
```

### Setup Modes

| Mode | Command | Description |
|------|---------|-------------|
| Baremetal | `./setup_env.sh` | Installs via `pip --user` into system Python |
| Active venv | `./setup_env.sh` | Auto-detects active venv, installs there |
| Force reinstall | `./setup_env.sh --force` | Reinstalls every package from `requirements.txt` in the selected environment |
| New venv | `./setup_env.sh --venv` | Creates `.venv/` and installs inside |
| Force recreate | `./setup_env.sh --venv --force` | Recreates `.venv/` and reinstalls every requirement |

### Credential Management

Two separate credential stores are managed by `setup_env.sh`:

| File | Location | Purpose |
|------|----------|---------|
| `test_creds.yml` | Local (this directory) | SSH credentials for remote test execution |
| `.test_creds.key` | Local (this directory) | Vault key for `test_creds.yml` (auto-created) |
| `image_build_credentials.yml` | `$OMNIA_DATA_PATH/image_build_manager/input/$OMNIA_PROJECT_NAME/` on the execution OIM | S3 + aarch64 domain credentials |
| `.image_build_credentials_key` | Same execution-OIM directory as above | Vault key for domain credentials |

The two YAML credential files are encrypted with Ansible Vault. Their private
vault-key files remain mode `0600`. SSH artifacts stay in this gitignored test
directory. Domain artifacts stay under `$OMNIA_DATA_PATH` on the execution OIM.
The framework never copies or syncs the domain credential YAML, its vault key,
or backups.

From `test/image_build_manager` on the execution OIM, run
`./setup_env.sh --set-domain-creds` with that OIM's `OMNIA_DATA_PATH` and
`OMNIA_PROJECT_NAME`. In local mode, the execution OIM is the current machine.
In remote mode, SSH to the target OIM and run the command there.

#### SSH Credentials (OIM server access)

| Flag | Description |
|------|-------------|
| `--set-creds` | Create SSH password credentials interactively (two entries). If the file exists, asks whether to update it. |
| `--update-creds` | Update an existing SSH password. Skips the overwrite question but still prompts twice; fails if the file does not exist. |
| `--creds PWD` | Non-interactively set `oim_password`; other fields are preserved. Prefer `--set-creds` because command-line secrets may be exposed. |

SSH password credentials are optional when key-based SSH already works. Set
`oim_ssh_user` in `test_config.yml`; `setup_env.sh` does not create or configure
SSH private keys.

#### Domain Credentials (S3 / aarch64)

The image build playbook (`image_build_manager.yml`) requires access to S3/MinIO
for image storage and optionally to a remote aarch64 host. These credentials are
stored in a separate file (`image_build_credentials.yml`) at
`$OMNIA_DATA_PATH/image_build_manager/input/$OMNIA_PROJECT_NAME/`.

| Field | Required | Description |
|-------|----------|-------------|
| `s3_access_id` | PowerScale only | PowerScale S3 access key ID; it may be empty for MinIO. |
| `s3_secret_key` | Yes | MinIO password or PowerScale S3 secret key (minimum 8 characters). |
| `aarch64_ssh_password` | When ARM host is set | Required when `aarch64_inventory_host_ip` is non-empty; otherwise leave it empty. |

| Flag | Description |
|------|-------------|
| `--set-domain-creds` | Interactive prompt for S3 access ID, secret, and aarch64. |
| `--update-domain-creds` | Force-update domain credentials (no "exists" check). |
| `--domain-creds JSON` | Non-interactive. Pass a JSON string with `s3_access_id`, `s3_secret_key`, `aarch64_ssh_password`. |

> **Note**: `--set-creds` and `--set-domain-creds` are independent — run each separately:
> ```bash
> ./setup_env.sh --set-creds          # SSH creds (saved locally)
> ./setup_env.sh --set-domain-creds   # Run on execution OIM; saved to $OMNIA_DATA_PATH
> ```
> Existing fields not updated by a given flag are **preserved**.

---

## Running Tests

Run from inside the `test/image_build_manager/` directory:

```
./run_validation.sh fvt_image_build_manager <command>             # No-tag behavior described below
./run_validation.sh fvt_image_build_manager <tag> <command>        # Specific tag
./run_validation.sh fvt_image_build_manager list                   # List available tags
./run_validation.sh nft_image_build_manager <command>              # NFT tests
./run_validation.sh ut_image_build_manager <command>               # Unit tests
./run_validation.sh --config                                       # Batch from test_run_config.yml
./run_validation.sh --help                                         # Full help
```

### Categories

| Category | Description |
|----------|-------------|
| `fvt_image_build_manager` | Functional Verification Tests (playbook tags) |
| `nft_image_build_manager` | Non-Functional Tests (performance, idempotency) |
| `ut_image_build_manager` | Unit Tests (offline validation) |

### Commands

For FVT runs, use `test` for the normal end-to-end scenario flow:

| Command | Description |
|---------|-------------|
| `exec` | Run the Ansible playbook only |
| `verify` | Run verification tests only (no playbook) |
| `test` | Full flow: exec + verify |

Use `exec` or `verify` separately only when intentionally running one phase.
Marker and suite filters are most useful with `verify` when rerunning focused
checks against an environment that has already been deployed.

NFT and UT accept the same command names for CLI consistency, but all three
names run their complete pytest suite; use `test` as the conventional form.

For FVT with no tag, `verify` runs verification for precheck, validate,
prepare, and build (excluding both cleanup flows). No-tag `exec` runs the
playbook's default full-stack flow, and no-tag `test` runs that deployment
followed by the same non-cleanup verification set.

### FVT Tags

| Tag | Playbook Tag | What It Tests |
|-----|-------------|---------------|
| `precheck` | `--tags precheck` | Env vars, hostname, IP, connectivity, omnia.sh setup |
| `validate` | `--tags validate` | Input/credentials presence, effective `repo_ssl_verify`, and template wiring |
| `prepare` | `--tags prepare` | MinIO, registry, systemd, S3 buckets |
| `build` | `--tags build` | S3 images, registry images, build_status, **naming convention** |
| `cleanup` | `--tags cleanup` | Remove local MinIO/registry data and services, build output/logs, MinIO s3cmd config, and domain credentials; external PowerScale storage and s3cmd config are retained |
| `cleanup_images` | `--tags cleanup_images` | Delete S3 + registry images |
| *(none)* | *(no tag)* | Full end-to-end (prepare + build) |

#### Build-type naming convention (within `build` tag)

Both `image-builder` and `image-thrillhouse` produce artifacts with distinct
suffixes (`-imgbld` / `-imgth`). The naming tests confirm that at least one
artifact for the configured build type carries the expected suffix. Artifacts
from another build type are allowed to coexist and are reported, not rejected.

```bash
# Run only naming convention tests
./run_validation.sh fvt_image_build_manager build verify --suite naming
./run_validation.sh fvt_image_build_manager build verify --suite naming --marker x86_64+sanity
```

### Options

| Option | Description |
|--------|-------------|
| `--suite <name>` | FVT only: filter by an existing tag subfolder (`connectivity`, `status`, `container`, `s3`, `registry`, `naming`, `aarch64`, `image_verification`, `cleanup`, or `cleanup_images`) |
| `--marker <expr>` | Filter by pytest marker expression |
| `-v, --verbose` | Increase pytest verbosity |
| `--debug` | Full debug output (pytest `-vvs`) |

Use only a suite that belongs to the selected tag. The current runner falls
back to the entire tag when the suite directory does not exist.

### Marker Expressions

| Syntax | Example | Meaning |
|--------|---------|---------|
| Single | `--marker x86_64` | Tests with `@pytest.mark.x86_64` |
| OR (`,`) | `--marker x86_64,aarch64` | Tests with EITHER marker |
| AND (`+`) | `--marker x86_64+sanity` | Tests with BOTH markers |
| Standard | `--marker sanity` | Tests with `@pytest.mark.sanity` |

Available markers: `sanity`, `x86_64`, `aarch64`, `functional`, `deploy`

Use either AND or OR in one expression; do not mix `+` and `,`.

### Examples

```bash
# FVT: recommended full build flow (deploy + verify)
./run_validation.sh fvt_image_build_manager build test

# Optional focused verification reruns against the deployed build
./run_validation.sh fvt_image_build_manager build verify --marker x86_64+sanity
./run_validation.sh fvt_image_build_manager build verify --suite registry
./run_validation.sh fvt_image_build_manager build verify --suite naming
./run_validation.sh fvt_image_build_manager list

# NFT
./run_validation.sh nft_image_build_manager test

# UT
./run_validation.sh ut_image_build_manager test

# Config-driven batch
./run_validation.sh --config
```

### Recommended Functional Workflow (default MinIO backend)

```bash
./run_validation.sh fvt_image_build_manager precheck test               # 0. Run precheck + verify environment
./run_validation.sh fvt_image_build_manager validate test               # 1. Validate inputs
./run_validation.sh fvt_image_build_manager prepare test                # 2. Prepare infrastructure
./run_validation.sh fvt_image_build_manager build test                  # 3. Build + verify
./run_validation.sh fvt_image_build_manager verify --marker sanity      # 4. Full sanity verification
./run_validation.sh fvt_image_build_manager cleanup_images test         # 5. Delete images; keep infrastructure
./run_validation.sh fvt_image_build_manager cleanup test                # 6. Remove infrastructure + verify cleanup
```

`cleanup_images` and `cleanup` are separate FVT tags. When validating both,
run `cleanup_images` first: it removes built S3 and registry images while the
storage services remain available. Run `cleanup` last to remove the local
MinIO/registry deployment, build output, configuration, and domain credentials.

For PowerScale, see the [full cleanup](#full-cleanup) caveat before using
`cleanup test`.

NFT is an independent destructive flow, not the cleanup phase of the FVT
workflow. A full NFT run measures prepare, build, and cleanup performance and
checks repeated prepare execution. Its final timed cleanup removes the deployed
environment and domain credentials, so restore credentials before any later
playbook run by rerunning `./setup_env.sh --set-domain-creds` on the execution
OIM.

### Complete Commands by Flow

#### Complete FVT Lifecycle (both cleanup tags, default MinIO backend)

```bash
./run_validation.sh fvt_image_build_manager precheck test       # Precheck tag + environment verification
./run_validation.sh fvt_image_build_manager validate test        # Validate + verify
./run_validation.sh fvt_image_build_manager prepare test         # Prepare + verify
./run_validation.sh fvt_image_build_manager build test           # Build + verify (all configured architectures)
./run_validation.sh fvt_image_build_manager cleanup_images test  # Delete S3/registry images + verify
./run_validation.sh fvt_image_build_manager cleanup test         # Full cleanup + verify
```

#### Non-Functional Flow (includes timed cleanup)

```bash
./run_validation.sh fvt_image_build_manager precheck verify      # Check target prerequisites
./run_validation.sh fvt_image_build_manager validate verify      # Check existing inputs and credentials
./run_validation.sh nft_image_build_manager test                 # Prepare/build timing, repeated prepare, cleanup timing
```

The NFT suite performs its own prepare, build, and cleanup playbook runs. It
does not run the FVT cleanup verification cases. Run
`./run_validation.sh fvt_image_build_manager cleanup verify` immediately
after NFT when those assertions are required; the cleanup playbook has already
run.

#### Build and x86_64 Verification

The build deployment uses `--tags build` and therefore targets every configured
architecture. Run the complete build flow first, then optionally rerun only the
x86_64 sanity checks.

```bash
./run_validation.sh fvt_image_build_manager build test
./run_validation.sh fvt_image_build_manager build verify --marker x86_64+sanity
```

#### Build and AArch64 Verification

The complete build flow builds every configured architecture. The second
command is an optional focused verification rerun.

```bash
./run_validation.sh fvt_image_build_manager build test
./run_validation.sh fvt_image_build_manager build verify --marker aarch64+sanity
```

#### Naming Convention Tests

```bash
./run_validation.sh fvt_image_build_manager build verify --suite naming
```

#### Cleanup Images (delete all)

```bash
./run_validation.sh fvt_image_build_manager cleanup_images test
```

The runner supplies `skip_approval=true` and uses the playbook's default `*`
pattern, so this command deletes all built S3 and registry images. It retains
the MinIO/registry infrastructure and the S3 buckets.

#### Full Cleanup

```bash
./run_validation.sh fvt_image_build_manager cleanup test
```

This runs the `cleanup` playbook tag, which also removes build logs and domain
credentials. The post-cleanup FVT cases verify local MinIO/registry services
and data, listening ports, S3 state, s3cmd configuration, build output, and
registry state.

With PowerScale, the product intentionally retains the external buckets and
`/root/.s3cfg`. The current `TC_CL_005` and `TC_CL_006` assertions are
MinIO-oriented and expect those resources to be absent, so a PowerScale
`cleanup test` can fail after a successful cleanup. Use
`./run_validation.sh fvt_image_build_manager cleanup exec` for the PowerScale
cleanup playbook, then verify the applicable local container, service, port,
build-output, and registry state separately.

#### Unit Tests

```bash
./run_validation.sh ut_image_build_manager test                  # Recommended form
./run_validation.sh ut_image_build_manager verify                # Equivalent UT alias
```

#### Verify Only (no playbook execution)

```bash
./run_validation.sh fvt_image_build_manager precheck verify
./run_validation.sh fvt_image_build_manager prepare verify
./run_validation.sh fvt_image_build_manager build verify
./run_validation.sh fvt_image_build_manager cleanup_images verify
./run_validation.sh fvt_image_build_manager cleanup verify
```

The cleanup `verify` commands only inspect the current target state; they do
not delete anything. Use the corresponding `test` command to execute the
cleanup tag before verification.

#### Config-Driven Batch Run

```bash
./run_validation.sh --config                                     # Runs enabled flows from test_run_config.yml
```

---

## Configuration

| File | Purpose | Git Status |
|------|---------|------------|
| `test_config.yml` | Target server IP, sync settings, dataset, report options | Tracked |
| `test_creds.yml` | SSH creds (created by `--set-creds`, auto-encrypted) | **Gitignored** |
| `.test_creds.key` | Vault key for `test_creds.yml` (auto-created) | **Gitignored** |
| `test_run_config.yml` | Batch execution: enabled flows, commands, markers, suites, and sync overrides | Tracked |

### Key Settings in `test_config.yml`

| Setting | Required | Default | Description |
|---------|----------|---------|-------------|
| `oim_server_ip` | No | `""` (local) | Target server IP. Leave empty for local mode. |
| `clone_path` | Remote only | `/omnia` | Non-empty absolute path on the target where project code is synced. Ignored in local mode. |
| `dataset` | No | `""` | Selects local sync sources. Empty uses `src/image_build_manager/input/` and `src/image_build_manager/samples/repo_manager_output/`; a name uses only `datasets/<name>/input/` and `datasets/<name>/repo_manager_output/`. Nothing is copied unless its sync flag is enabled. |

### Batch Runs with `test_run_config.yml`

Use `./run_validation.sh --config` to run the entries enabled in
`test_run_config.yml`. See [the complete batch configuration
reference](docs/test_run_config.md) for the schema and examples.

The top-level sections are `fvt_image_build_manager`,
`nft_image_build_manager`, and `ut_image_build_manager`. FVT tags run in their
YAML mapping order; NFT runs after all FVT entries, followed by UT. The tracked
sequence is `precheck`, `validate`, `prepare`, `build`, `cleanup_images`, then
`cleanup`, which keeps image-only cleanup ahead of full infrastructure cleanup.

Each FVT tag supports these fields:

| Field | Meaning |
|-------|---------|
| `run` | Enable or skip the tag. All tracked entries default to `false`. |
| `command` | `exec`, `verify`, or `test`; use `test` for deploy + verify. |
| `suite` | Verification subfolder; empty runs the complete tag. |
| `marker` | Single, AND (`+`), or OR (`,`) expression applied to the selected pytest phase(s). |
| `dataset` | Non-empty per-tag dataset override; empty inherits `test_config.yml`. |
| `sync_input` | Explicit per-tag override for `sync_image_build_input`. |
| `sync_output` | Explicit per-tag override for `sync_output`. |

For `command: "test"`, the marker applies to both playbook execution and
verification. Use `marker: ""` to run every applicable case, or
`marker: "sanity"` for the sanity lifecycle; an architecture-only marker such
as `x86_64` does not select the deploy test.
Suite filtering affects verification only. If a named suite directory is not
present under the selected tag, the current runner falls back to the complete
tag, so verify suite names with `./run_validation.sh fvt_image_build_manager
list` before a destructive run.

The optional top-level `dataset_override`, `sync_input_override`, and
`sync_output_override` values take precedence over per-FVT settings. These
overrides apply to FVT entries only; NFT and UT use `test_config.yml` directly.

The batch runner attempts every enabled entry even when an earlier entry fails,
then returns non-zero if any entry failed. The image build manager batch file
does not define a skip-after-failure setting.

Run NFT separately from a complete FVT cleanup batch. FVT `cleanup` removes the
domain credentials that the later NFT build would require.

### Execution Modes

#### Local mode

Use local mode when the tests and playbook run from the current Omnia checkout:

```yaml
oim_server_ip: ""
```

`clone_path` is not required or read in local mode. The framework resolves the
repository root from `test/image_build_manager/` and uses the current source
tree for playbook execution and source-template verification.

#### Remote mode

Use remote mode when verification commands and the playbook run on another
server:

```yaml
oim_server_ip: "<target-ip>"
oim_ssh_user: root
clone_path: "/omnia"
```

In remote mode, `clone_path` is required and must be a non-empty absolute path
on the target server. The framework syncs the local Omnia checkout there and
runs the playbook from
`<clone_path>/src/image_build_manager/playbooks/`.

### How Sync Works (Remote Mode)

Project sync runs only for remote execution. In local mode, no project sync
occurs; tests and source-template checks use the current Omnia checkout, and
`clone_path` is ignored.

Input and repo-manager-output sync are independent of project sync. When their
respective flags are enabled, those optional sync operations also run in local
mode, copying into paths resolved on the current machine.

In remote mode, session startup performs:

1. **Project sync** — stages and rsyncs the local Omnia working tree to the
   target's absolute `clone_path`; local credentials, vault keys, VCS metadata,
   virtual environments, and caches are excluded
2. **Input sync** (only when `sync_image_build_input: true`) — reads
   `OMNIA_DATA_PATH` and `OMNIA_PROJECT_NAME` from the target's
   `/etc/omnia/omnia.env` and creates the target directory if needed. A
   non-empty `dataset` syncs only `datasets/<name>/input/`; an empty name syncs
   canonical `src/image_build_manager/input/`. Credential files, keys, and
   backups are excluded.
3. **Repo manager output sync** (only when `sync_output: true`) — uses
   `datasets/<name>/repo_manager_output/` for a named dataset or
   `src/image_build_manager/samples/repo_manager_output/` when the name is
   empty, then syncs it to the target Repo Manager output directory.

Domain credentials are never part of session sync. Configure them directly on
the execution OIM with `./setup_env.sh --set-domain-creds`.

### Input Files

#### Option A: Empty dataset (`dataset: ""`) — Target server input

When `dataset` is empty, the playbook reads input files from the **target server** at:

```
$OMNIA_DATA_PATH/image_build_manager/input/<project_name>/
```

With `sync_image_build_input: false`, no input files are synced from the local
machine. Files must already exist on the target (placed by `omnia.sh` setup or a
prior deployment). This is the **production behavior**.

When `sync_image_build_input: true` AND `dataset: ""`, the framework syncs from
`src/image_build_manager/input/` to the target path as a development convenience.

#### Option B: Generated dataset (`dataset: "<name>"`)

Create a dataset using the [dataset generator](datasets/generator/README.md),
then set `dataset: "<name>"` in `test_config.yml`:

```bash
cd datasets/generator/

# Inspect profiles and generate the recommended independent dataset
./generate_dataset.py profiles
./generate_dataset.py create my_dataset --profile internet-config

# Generate an offline dataset with one real host applied to every repo URL
./generate_dataset.py create my_offline --profile offline-config \
  --repo-host repo.company.internal

# Preview without publishing
./generate_dataset.py create my_dataset --profile internet-config --dry-run

# Use canonical source values without a profile patch
./generate_dataset.py create my_snapshot --from-src

# Inspect all inline customer-edit markers after generation
grep -R -n 'REPLACE WITH REAL VALUE' \
  ../my_dataset/input/ ../my_dataset/repo_manager_output/
```

Replace `repo.company.internal` with the real Repo Manager hostname or IP
reachable from the execution environment.

The generator publishes these five files:

| File | Location |
|------|----------|
| `image_build_config.yml` | `datasets/<name>/input/` |
| `package_groups.yml` | `datasets/<name>/input/` |
| `repo_status.yml` | `datasets/<name>/repo_manager_output/` |
| `dataset_manifest.yml` | `datasets/<name>/` |
| `README.md` | `datasets/<name>/` |

Credentials are never generated in a dataset or synced by the framework. From
`test/image_build_manager` on the execution OIM, configure the separate
encrypted runtime pair with `./setup_env.sh --set-domain-creds`.

---

## Reports

Generated in the configured `report_path` (tracked default
`/opt/omnia/reports`):

| File | Format |
|------|--------|
| `image_test_report.json` | Machine-readable results |
| `image_test_report.html` | Interactive browser report |

---

## Test Cases

See [`fvt/README.md`](fvt/README.md) for the complete test case registry.

| ID area | Prefix | ID count | Notes |
|---------|--------|----------|-------|
| precheck | TC_PC_ | 6 | 001–006 |
| validate | TC_VL_ | 4 | 001–004 (includes repo_ssl_verify_config) |
| prepare | TC_PR_ | 8 | 001–008 |
| build | TC_BD_ | 21 | 001–021; TC_BD_016 physically runs under `validate/status` |
| cleanup | TC_CL_ | 8 | 001–008 |
| cleanup_images | TC_CI_ | 3 | 001–003 |
| nft | NFT_ | 4 | |
| **Reportable IDs** | | **55** | 50 tagged FVT IDs + TC_IB_001 + 4 NFT IDs |

There are 54 physical FVT/NFT test functions (50 FVT and 4 NFT).
`TC_IB_001` is the alternate full-stack ID emitted by the same build deploy
function that reports `TC_BD_001` for a tagged build.

### Build-type suffix checks (TC_BD_007 – TC_BD_011)

| Test | Build type | Checks |
|------|-----------|--------|
| TC_BD_007 | image-builder | At least one x86_64 registry repository ends with `-imgbld` |
| TC_BD_008 | image-builder | At least one x86_64 S3 path includes `-imgbld` |
| TC_BD_009 | image-thrillhouse | At least one x86_64 registry repository ends with `-imgth` |
| TC_BD_010 | image-thrillhouse | At least one x86_64 S3 path includes `-imgth` |
| TC_BD_011 | both | At least one registry or S3 artifact carries the configured build type's suffix; suffix populations are reported |

---

## Directory Structure

```
test/image_build_manager/
├── setup_env.sh                 # Environment setup (--venv, --force, credentials)
├── run_validation.sh            # Shell entry point (delegates to _run.py)
├── _run.py                      # Python entry point (loads domain vars, creates runner)
├── conftest.py                  # Pytest hooks, fixtures, report generation
├── test_config.yml              # Target server and sync settings
├── test_creds.yml               # SSH credentials (auto-encrypted, gitignored)
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
│   ├── vars/                    # Constants, paths, commands (common_vars, domain_vars)
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
│   │   ├── aarch64/             # AArch64 infrastructure checks (TC_BD_017–021)
│   │   └── image_verification/  # Package verification (TC_BD_014-015)
│   ├── cleanup/                 # Cleanup tag
│   │   └── cleanup/
│   └── cleanup_images/          # Cleanup images tag
│       └── cleanup_images/
│
├── nft/                         # Non-Functional Tests
│   ├── README.md                # NFT documentation (thresholds, execution)
│   ├── test_performance.py      # Performance threshold tests (NFT_001–NFT_003)
│   └── test_idempotency.py      # Idempotency tests (NFT_004)
│
└── ut/                          # Unit Tests
    ├── conftest.py
    ├── test_catalog_validation.py
    ├── test_functional_group_packages.py
    ├── test_standalone_independence.py
    └── test_validate_image_build_config.py
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
| **Sync** | `sync_files()` |
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

**Step 3 — Test files** call the wrapper with the explicit playbook constant.
Test metadata and messages remain centralized as required by
[`test_automation.md`](../../docs/code-style/test_automation.md):

```python
from library.functions import run_playbook
from library.vars.common_vars import PLAYBOOK_ENTRY_POINT

result = run_playbook(
    playbook=PLAYBOOK_ENTRY_POINT,
    tag="prepare",
    timeout=1800,
)
```

For the full `omnia-auto` API reference, see the package's
[USAGE.md](../plugins/USAGE.md) and [docs/](../plugins/docs/).

---

## Key Architecture Decisions (Monorepo)

| Area | Old (multi-repo) | New (monorepo) |
|------|-------------------|----------------|
| **Code delivery** | `git clone` on target | Current checkout locally; `rsync` to `clone_path` remotely |
| **Config source** | `config.yml` in dataset | Environment variables on target (`omnia.env`) |
| **Env var setup** | N/A | `omnia.sh -s` installs to `/etc/omnia/omnia.env` |
| **Input sync dest** | `<clone_path>/src/input/<project>/` | `<OMNIA_DATA_PATH>/image_build_manager/input/<project>/` |
| **Playbook workdir** | `src/` | `src/image_build_manager/playbooks/` |
| **Common utilities** | Inline library | `omnia-auto` pip package |
| **Dir creation** | Manual | Auto-created by framework before sync |
