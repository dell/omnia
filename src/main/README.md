# Omnia Main

Core entry points for the Omnia Infrastructure Manager (OIM).

| File | Description |
|------|-------------|
| `omnia.sh` | Setup script — creates venv, installs deps, copies domain input files |
| `omnia-cli` | Status and diagnostics CLI |
| `omnia.env` | Environment configuration (single source of truth) |

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

# 5. Run domain playbooks
source /opt/omnia/venv/bin/activate
cd ../src/<domain>/playbooks
ansible-playbook <domain>.yml --tags validate
```

---

## Setup (`omnia.sh`)

```bash
./omnia.sh -s                      # Full setup: venv + input copy
./omnia.sh -s --skip-input-copy    # Venv only, skip input file staging
./omnia.sh -h                      # Help
```

**What `-s` does:**

1. **Installs env system-wide** — copies `omnia.env` to `/etc/omnia/omnia.env`, creates `/etc/profile.d/omnia-env.sh`
2. Validates environment (required variables like `SYSTEM_ADMIN_NIC_IPV4`)
3. Creates `/opt/omnia/{log,.data}` base directories
4. Finds Python 3.11+, creates/updates venv at `$OMNIA_VENV_PATH`
5. Installs pip packages from each domain's `requirements.txt`
6. Installs Ansible Galaxy collections from each domain's `requirements.yml`
7. **Copies input files** from each domain's `input/<project>/` to `<OMNIA_DATA_PATH>/<domain>/input/<project>/`

After setup, all new login shells automatically have the environment variables.
Step 7 ensures Ansible roles read input from a stable runtime location
(`/opt/omnia/<domain>/input/<project>/`) rather than the git checkout. Use
`--skip-input-copy` to skip this step (e.g., in CI or if you manage input files
externally).

Each domain provides a `copy-input.sh` script that handles the copy. The script
is idempotent and only overwrites files that differ.

---

## Diagnostics (`omnia-cli`)

```bash
omnia-cli status                          # All domains
omnia-cli repo-manager                    # Repo manager details
omnia-cli image-build                     # Image build details
omnia-cli status --project prod           # Specific project
omnia-cli version                         # Version info
omnia-cli help                            # Full help
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
└── <domain>/                          # One per domain (repeats for each)
    ├── input/<project>/                # Staged input files (copied from src/)
    │   └── <domain>_config.yml         # Domain-specific config
    ├── output/<project>/               # Domain output (status files, artifacts)
    └── log/<project>/                 # Domain logs
```

Domains: `repo_manager`, `image_build_manager`, `discovery`, `orchestrator`, `telemetry`, `build_stream`.

---

## Input File Flow

```
Source (git repo)                        Runtime (data path)
─────────────────                        ───────────────────
src/<domain>/input/<project>/   ──copy──>  /opt/omnia/<domain>/input/<project>/
                                              │
                                              ▼
                                     Ansible playbooks read from here
```

- **Edit** input files in the source tree (`src/<domain>/input/<project>/`)
- **Run** `./omnia.sh -s` or manually invoke `src/<domain>/copy-input.sh` to stage them
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

Domains may define additional sub-tags (e.g., `x86_64`, `aarch64`, `deploy`, `download`).

---

## Multi-Project

```bash
omnia-cli status --project dev
omnia-cli status --project prod
OMNIA_PROJECT_NAME=staging omnia-cli status
```

Each project has its own `input/` and `output/` under each domain.
