# Omnia Main

Core entry points for the Omnia Infrastructure Manager (OIM).

| File | Description |
|------|-------------|
| `omnia.sh` | Setup script — creates venv, installs deps, copies domain input files |
| `omnia-cli` | Status and diagnostics CLI |
| `omnia.env` | Environment configuration (single source of truth) |
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
./omnia.sh -s

# 3. Install omnia-cli to PATH (optional, one-time)
sudo cp omnia-cli /usr/local/bin/
sudo chmod +x /usr/local/bin/omnia-cli

# 4. Check domain status
omnia-cli status

# 5. Run domain playbooks via omnia.sh
./omnia.sh --run image_build_manager --tags validate
./omnia.sh --run repo_manager --tags build
./omnia.sh -r telemetry --tags validate
```

---

## Setup (`omnia.sh`)

```bash
./omnia.sh -s                      # Full setup: venv + deps + input copy + catalog
./omnia.sh -s --deps-only          # Venv + deps only, skip input staging
./omnia.sh -s --skip-catalog       # Setup without catalog copy
./omnia.sh -s --force-deps         # Force reinstall all deps (bypass cache)
./omnia.sh --init                  # Init all domains (stage input files + deps)
./omnia.sh -i telemetry            # Init single domain
./omnia.sh -i repo_manager,telemetry  # Init specific domains
./omnia.sh -i --force-deps         # Force reinstall deps for all domains
./omnia.sh --check-deps            # Audit dependency version mismatches
./omnia.sh --cleanup               # Remove venv + env (preserve data)
./omnia.sh --cleanup --all         # Full reset (remove everything including data)
./omnia.sh -h                      # Help
```

**What `-s` does:**

1. **Validates env source file** — checks `SYSTEM_ADMIN_NIC_IPV4` is set and valid IPv4 before copying
2. **Installs env system-wide** — copies `omnia.env` to `/etc/omnia/omnia.env` (auto-updates if source differs), creates `/etc/profile.d/omnia-env.sh`
3. Validates full environment (hostname, domain, admin NIC match)
4. Creates `/opt/omnia/{log,.data}` base directories
5. Finds Python 3.11+, creates/updates venv at `$OMNIA_VENV_PATH`
6. Runs each domain's `domain-init.sh` which:
   - Installs pip packages from the domain's `requirements.txt`
   - Installs Ansible Galaxy collections from the domain's `requirements.yml`
   - Creates Ansible log directories
   - Copies input files from flat `input/` to `<OMNIA_DATA_PATH>/<domain>/input/<project>/`
7. Copies catalog files from `src/main/samples/` to `$OMNIA_DATA_PATH/catalog/` (use `--skip-catalog` to suppress)

After setup, all new login shells automatically have the environment variables.
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
```

## Execution (`omnia.sh`)

```bash
./omnia.sh --run <domain> [--tags <tags>]   # Run a domain playbook
./omnia.sh -r image_build_manager --tags build
./omnia.sh -r repo_manager --tags validate  # Validate a domain's config
```

`--run` activates the venv and executes `ansible-playbook` for the given domain.
Use `--tags validate` to run validation only (safe dry-run, no credentials needed).

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
omnia-cli vault edit <domain>             # Edit domain credentials (Vault)
```

### Install to PATH

```bash
sudo cp omnia-cli /usr/local/bin/
sudo chmod +x /usr/local/bin/omnia-cli
# Now use from anywhere:
omnia-cli status
```

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

All domain playbooks support these common tags:

| Tag | Description |
|-----|-------------|
| `precheck` | Environment and connectivity checks (no credentials) |
| `validate` | Schema and runtime validation (no credentials) |
| `prepare` | Deploy prerequisites (containers, services) |
| `execute` | Main domain workflow (alias for domain-specific action) |
| `build` | Main build/execution phase (domain-specific) |
| `cleanup` | Stop services and remove artifacts |
| `upgrade` | Upgrade (placeholder — future) |
| `rollback` | Rollback (placeholder — future) |

Domains may define additional sub-tags (e.g., `x86_64`, `aarch64`, `cleanup_images`, `deploy`, `download`).

Execution order: `precheck` -> `validate` -> `prepare` -> `execute` -> `cleanup`

---

## Multi-Project

```bash
omnia-cli status --project dev
omnia-cli status --project prod
OMNIA_PROJECT_NAME=staging omnia-cli status
```

Each project has its own `input/` and `output/` under each domain.
