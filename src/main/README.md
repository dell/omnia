# Omnia Main

Core entry points for the Omnia Infrastructure Manager (OIM).

| File | Description |
|------|-------------|
| `omnia.sh` | Setup script — creates venv, installs deps, copies domain input files |
| `omnia-cli` | Status and diagnostics CLI |
| `omnia-bash-completion` | Shared Bash completion for `omnia-cli` and `omnia.sh` |
| `omnia.env` | Bootstrap template for the installed environment configuration |
| `samples/` | Reference files (catalog JSON, etc.) for documentation and testing |

---

## Documentation

| File | Description |
|------|-------------|
| `docs/omnia-env.md` | Environment variable reference |
| `docs/omnia-setup.md` | Setup script (`omnia.sh`) documentation |
| `docs/omnia-cli.md` | CLI (`omnia-cli`) documentation |

---

## Quick Start

```bash
# 1. Configure environment
vi omnia.env                         # Set SYSTEM_ADMIN_NIC_IPV4 at minimum

# 2. Set up env + venv + copy input files (one-time)
#    Installs env to /etc/omnia/omnia.env (system-wide)
#    Creates /etc/profile.d/omnia-env.sh (auto-loaded on login)
#    Installs omnia-cli + shared omnia-cli/omnia.sh bash completion
./omnia.sh -s

# 3. (Optional) Skip omnia-cli install during setup
./omnia.sh -s --skip-omnia-cli

# 4. Check domain status
omnia-cli status

# 5. Run domain playbooks via omnia.sh
./omnia.sh --run image_build_manager --tags validate
./omnia.sh --run repo_manager --tags prepare
./omnia.sh -r telemetry --tags validate
```

---

## Setup (`omnia.sh`)

```bash
./omnia.sh -s                      # Full setup: venv + deps + input copy + catalog + omnia-cli
./omnia.sh -s --deps-only          # Venv + deps only, skip input staging
./omnia.sh -s --skip-catalog       # Setup without catalog copy
./omnia.sh -s --skip-omnia-cli     # Setup without omnia-cli install
./omnia.sh -s --force-deps         # Force reinstall all deps (bypass cache)
./omnia.sh -s --force-env          # Explicitly replace /etc config from repo omnia.env
./omnia.sh --init                  # Init all domains (stage input files + deps)
./omnia.sh -i telemetry            # Init single domain
./omnia.sh -i repo_manager,telemetry  # Init specific domains
./omnia.sh -i --force-deps         # Force reinstall deps for all domains
./omnia.sh -i --skip telemetry     # Init all domains except telemetry
./omnia.sh -i --skip telemetry,utils  # Skip multiple domains
./omnia.sh -i --dry-run            # Preview which domains would be initialized
./omnia.sh -i --dry-run --skip telemetry  # Preview with skip filter
./omnia.sh --check-deps            # Audit dependency version mismatches
./omnia.sh --cleanup               # Remove environment + CLI integration; preserve runtime data
./omnia.sh --cleanup --all         # Guarded full reset; blocks on uncleared domain state
./omnia.sh --cleanup --skip-approval       # Standard cleanup for trusted automation
./omnia.sh --cleanup --all --skip-approval # Full cleanup for trusted automation
./omnia.sh -h                      # Help
```

Both `--cleanup` and `--cleanup --all` display their removal scope and require
the operator to type `yes`. Add `--skip-approval` only for trusted unattended
automation. The `--all` safety preflight still runs when confirmation is
skipped and stops before deletion if a domain contains anything other than its
initializer-owned `input/` directory.

**What `-s` does:**

1. **Selects the environment config** — installs repository `omnia.env` on the first run; otherwise preserves and uses `/etc/omnia/omnia.env`
2. **Validates the active env file** — checks `SYSTEM_ADMIN_NIC_IPV4` is set and valid before loading it; `--force-env` explicitly replaces the installed file from the repository
3. Validates full environment (hostname, domain, admin NIC match)
4. Creates `$OMNIA_DATA_PATH` and its `.data` directory
5. Finds Python 3.11+, creates/updates venv at `$OMNIA_VENV_PATH`
6. Runs each domain's `domain-init.sh` which:
   - Installs pip packages from the domain's `requirements.txt`
   - Installs Ansible Galaxy collections from the domain's `requirements.yml`
   - Creates Ansible log directories
   - Copies input files from flat `input/` to `<OMNIA_DATA_PATH>/<domain>/input/<project>/`
7. Copies catalog files from `src/main/samples/` to `$OMNIA_DATA_PATH/catalog/` (use `--skip-catalog` to suppress)
8. Installs `omnia-cli` to `/usr/local/bin/omnia-cli` and shared completion for `omnia-cli` and `omnia.sh` to `/etc/bash_completion.d/omnia-bash-completion` (use `--skip-omnia-cli` to suppress)

After setup, all new login shells automatically have the environment variables.
The installed `/etc/omnia/omnia.env` is authoritative after the first setup;
edit it directly for later configuration changes.
Step 6 ensures each domain's dependencies are installed and Ansible roles read
input from a stable runtime location (`/opt/omnia/<domain>/input/<project>/`)
rather than the git checkout. Use `--deps-only` to skip input file staging in this step (e.g., in CI
or if you manage input files externally). Dependencies are still installed.

**Dependency caching:** On first run, each domain's `requirements.txt` and
`requirements.yml` are hashed (MD5). On subsequent runs, if the file hasn't
changed the install step is skipped entirely — saving 10-30s per domain.
Use `--force-deps` to bypass the cache. Cache files live at
`$OMNIA_DATA_PATH/.data/deps-cache/`.

Each domain provides a `domain-init.sh` script that handles the copy. Input files
live flat in the source `input/` directory (no project subdirectory); the project
subdirectory is created only at the runtime destination.

**Direct domain-init.sh usage:**
```bash
# Run a single domain's init (full)
bash src/image_build_manager/domain-init.sh

# Run with --deps-only (deps only, no input staging)
bash src/image_build_manager/domain-init.sh --deps-only

# Run with --force-deps (force reinstall even if cached)
bash src/image_build_manager/domain-init.sh --force-deps

# Run with --force (overwrite without prompting)
bash src/image_build_manager/domain-init.sh --force

# Non-interactively remove only this initializer's staged input and log paths
bash src/image_build_manager/domain-init.sh --cleanup
```

`domain-init.sh --cleanup` deliberately has no confirmation prompt because it
is an internal, narrowly scoped helper. It removes the domain's staged `input/`,
runtime `log/`, and `/var/log/omnia/<domain>/` paths; it does not remove domain
outputs, deployed services, or persistent application data.

### Domain Skip (`--skip`)

Exclude specific domains during init instead of listing all the ones you want:

```bash
./omnia.sh -i --skip telemetry              # All domains except telemetry
./omnia.sh -i --skip telemetry,utils        # Skip multiple domains
./omnia.sh -s --skip build_stream           # Full setup, skip build_stream init
./omnia.sh -i --skip telemetry --deps-only  # Combine with other flags
```

`--skip` is mutually exclusive with an explicit domain list:
```bash
./omnia.sh -i telemetry --skip utils   # ERROR: can't combine include + skip
./omnia.sh --run repo_manager --skip utils  # ERROR: --skip requires -s or -i
```

### Dry Run (`--dry-run`)

Preview which domains would be initialized without executing:

```bash
./omnia.sh -i --dry-run                      # Show all domains
./omnia.sh -i --dry-run --skip telemetry     # Show filtered list
```

Output shows each domain and whether it has a `domain-init.sh` script:
```
DRY RUN — would initialize these domains:
  build_stream
  discovery
  image_build_manager
  orchestrator
  repo_manager
  utils
  Skipped: telemetry
```

## Prepare Base (`omnia.sh --prepare-base`)

Prepares the three base infrastructure domains in dependency order:
**repo_manager** → **image_build_manager** → **orchestrator**

For each domain, runs lifecycle phases: validation → `credentials` → `prepare`.
The validation phase uses `precheck` for Repo Manager and `validate` for Image
Build Manager and Orchestrator.
If any domain fails, execution stops immediately.

```bash
./omnia.sh --prepare-base                     # Prepare all three base domains
./omnia.sh --prepare-base --skip orchestrator # Skip orchestrator
./omnia.sh --prepare-base --skip orchestrator,repo_manager  # Skip multiple
./omnia.sh --prepare-base --dry-run           # Preview what would be prepared
```

**What it prepares:**

| Domain | What Gets Deployed |
|--------|--------------------|
| `repo_manager` | Pulp server for package repos |
| `image_build_manager` | MinIO S3 storage + container registry |
| `orchestrator` | OpenLDAP (if enabled), functional groups |

---

## Execution (`omnia.sh`)

```bash
./omnia.sh --run <domain> [--tags <tags>]   # Run a domain playbook
./omnia.sh -r image_build_manager --tags build
./omnia.sh -r repo_manager --tags precheck  # Validate Repo Manager inputs
```

`--run` activates the venv and executes `ansible-playbook` for the given domain.
Use the tag documented by each domain to select a lifecycle stage. For example,
Repo Manager uses `precheck` for input validation, while Image Build Manager uses
`validate`.

---

## Diagnostics (`omnia-cli`)

```bash
omnia-cli status                          # All domains
omnia-cli repo-manager                    # Repo manager details
omnia-cli image-build                     # Image build details
omnia-cli status --project prod           # Specific project
omnia-cli version                         # Version info
omnia-cli help                            # Full help
omnia-cli logs <domain>                   # Browse & tail domain logs
omnia-cli edit <domain>                   # Select and edit domain input files
```

### Install to PATH

`omnia-cli` is installed automatically during `./omnia.sh -s` to `/usr/local/bin/omnia-cli`. The completion file installed at `/etc/bash_completion.d/omnia-bash-completion` supports both `omnia-cli` and `omnia.sh` (including `./omnia.sh`).

To skip the install:
```bash
./omnia.sh -s --skip-omnia-cli
```

Manual install (if needed):
```bash
sudo cp omnia-cli /usr/local/bin/
sudo chmod +x /usr/local/bin/omnia-cli
sudo mkdir -p /etc/bash_completion.d
sudo cp omnia-bash-completion /etc/bash_completion.d/omnia-bash-completion
source /etc/bash_completion.d/omnia-bash-completion
```

After loading it, use Tab completion with either interface, for example
`omnia-cli st<Tab>` or `./omnia.sh --run image_<Tab>`. The `omnia.sh`
completion covers command-specific options, comma-separated domain lists, and
only the tags supported by the selected domain. If the system's Bash completion
loader has not picked up the new file in a fresh shell, source the installed
completion file or run
`source "${OMNIA_DATA_PATH:-/opt/omnia}/activate-omnia.sh"` to load newly
installed completions into the current shell.

---

## Runtime Directory Structure

After `./omnia.sh -s`, the following structure is created at `$OMNIA_DATA_PATH`:

```
/opt/omnia/
├── venv/                              # Shared Python venv
├── .data/                             # Internal metadata
├── catalog/                           # Catalog JSON files (from repo_manager)
│   └── catalog_rhel.json              # RHEL services catalog
└── <domain>/                          # One per domain (repeats for each)
    ├── input/<project>/                # Staged input files (copied from src/)
    │   └── <domain>_config.yml         # Domain-specific config
    ├── output/<project>/               # Domain output (status files, artifacts)
    └── log/<project>/                 # Domain logs
```

Domains: `repo_manager`, `image_build_manager`, `discovery`, `orchestrator`, `telemetry`, `build_stream`, `utils`.

---

## Input File Flow

```
Source (git repo)                        Runtime (NFS share / data path)
─────────────────                        ─────────────────────────────
src/<domain>/input/*.yml        ──copy──>  /opt/omnia/<domain>/input/<project>/
  (flat — no project subdir)                     │
                                              ▼
                                     Ansible playbooks read from here
```

- **Source** input files are flat in `src/<domain>/input/` (no project subdirectory)
- **domain-init.sh** copies them into a project-specific directory at the runtime path
- **Run** `./omnia.sh --init` or `./omnia.sh -s` to stage them
- **Playbooks** read from the runtime location only

---

## Tags

Supported tags differ by domain. These are the public tags suggested by Bash
completion and accepted by the top-level playbooks:

| Domain | Supported tags |
|--------|----------------|
| `build_stream` | `precheck`, `validate`, `credentials`, `prepare`, `execute`, `build`, `cleanup`, `upgrade`, `rollback` |
| `discovery` | `precheck`, `validate`, `credentials`, `prepare`, `execute`, `discovery`, `cleanup`, `cleanup_credentials`, `upgrade`, `rollback` |
| `image_build_manager` | `precheck`, `validate`, `credentials`, `prepare`, `execute`, `build`, `cleanup`, `cleanup_images`, `upgrade`, `rollback` |
| `orchestrator` | `precheck`, `validate`, `credentials`, `prepare`, `deploy`, `provision`, `execute`, `validate-deployment`, `pxeboot`, `cleanup`, `cleanup_credentials`, `upgrade`, `rollback` |
| `repo_manager` | `precheck`, `credentials`, `prepare`, `deploy`, `execute`, `download`, `status`, `cleanup`, `cleanup_pulp`, `cleanup_repos`, `upgrade`, `rollback`, `catalog_generate`, `catalog_add`, `catalog_delete`, `catalog_validate` |
| `telemetry` | `precheck`, `validate`, `validation`, `prepare`, `credentials`, `execute`, `deploy`, `cleanup`, `cleanup_kafka`, `cleanup_victoria_metrics`, `cleanup_victoria_logs`, `cleanup_idrac`, `cleanup_ldms`, `cleanup_ome`, `cleanup_powerscale`, `cleanup_ufm`, `cleanup_vast`, `upgrade`, `rollback`, `external_kafka`, `external_victoria` |
| `utils` | `precheck`, `setup`, `collect`, `install_os`, `backup_oim_logs`, `cleanup`, `cleanup_logs`, `cleanup_install_os`, `cleanup_backup_oim_logs`, `upgrade`, `rollback` |

Without `--tags`, a playbook runs its full default flow. Some tag combinations
are intentionally rejected; follow the selected domain's validation message.

---

## Multi-Project

```bash
omnia-cli status --project dev
omnia-cli status --project prod
OMNIA_PROJECT_NAME=staging omnia-cli status
```

Each project has its own `input/` and `output/` under each domain.
