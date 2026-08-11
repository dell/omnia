# omnia.sh — Setup Script Documentation

The `omnia.sh` script handles initial setup and environment configuration for Omnia.

## Commands

| Command | Description |
|---------|-------------|
| `--setup-venv, -s` | Install env system-wide, create/update Python venv, install deps, run domain-init.sh |
| `--init, -i` | Run all domain-init.sh scripts (stage input files to NFS share) |
| `--run, -r <domain> [--tags <tags>]` | Activate venv and run a domain's playbook |
| `--help, -h` | Show help message |

## Options

| Option | Description |
|--------|-------------|
| `--deps-only` | Install deps only, skip input file staging. Useful in CI or when input files are managed externally. |

## What `--setup-venv` Does

1. **Installs env system-wide** — Copies `omnia.env` → `/etc/omnia/omnia.env`, creates `/etc/profile.d/omnia-env.sh` drop-in, sources vars into current session
2. **Validates environment** — Checks required env vars are set (e.g., `SYSTEM_ADMIN_NIC_IPV4`)
3. **Creates base directories** — Sets up `/opt/omnia/{log,.data}`
4. **Finds Python 3.11+** — Searches for python3.12, python3.11, or python3
5. **Creates or updates venv** — Sets up virtual environment at `$OMNIA_VENV_PATH`
6. **Upgrades pip** — Ensures latest pip, setuptools, wheel
7. **Initializes domains** — Runs each domain's `domain-init.sh` which:
   - Installs pip packages from that domain's `requirements.txt`
   - Installs Galaxy collections from that domain's `requirements.yml`
   - Creates Ansible log directories
   - Stages input files from flat `src/<domain>/input/` to `<OMNIA_DATA_PATH>/<domain>/input/<project>/`
8. **Displays summary** — Shows venv path, Python version, installed Ansible and collections

Use `--deps-only` to skip input file staging in this step (e.g., in CI or if you manage input files externally). Dependencies are still installed.

```bash
./omnia.sh -s                      # Full setup: venv + deps + input copy
./omnia.sh -s --deps-only          # Venv + deps only, skip input staging
./omnia.sh --init                  # Stage input files only
```

## Example Output

```
================================================================================
               Omnia Virtual Environment Setup
================================================================================

  Venv path:   /opt/omnia/venv
  Source dir:  /path/to/omnia/src

Using Python: python3.12 (3.12.1)
Creating venv at /opt/omnia/venv ...
Upgrading pip...
================================================================================
                Omnia Venv Created
================================================================================

  Venv:    /opt/omnia/venv
  Python:  Python 3.12.1

Initializing domains (deps + log dirs + input files) ...
  [build_stream] Installing pip packages ...
  [build_stream] Installing Galaxy collections ...
  [image_build_manager] Installing pip packages ...
  [image_build_manager] Installing Galaxy collections ...
  [repo_manager] Installing pip packages ...
  [telemetry] Installing pip packages ...

Domain init completed for 4 domain(s)

Ansible: ansible [core 2.20.0]
Installed collections:
ansible.posix
community.general
containers.podman
...

Activate in your shell:
  source /opt/omnia/activate-omnia.sh
```

## Domain Discovery

Each domain is self-contained. Its `domain-init.sh` script handles:
- Installing pip packages from `requirements.txt`
- Installing Galaxy collections from `requirements.yml`
- Creating log directories and staging input files

Known domains: `build_stream`, `discovery`, `image_build_manager`, `orchestrator`, `repo_manager`, `telemetry`, `utils`.

**Direct domain-init.sh usage:**
```bash
# Run a single domain's init (full)
bash src/image_build_manager/domain-init.sh

# Run with --deps-only (deps only, no input staging)
bash src/image_build_manager/domain-init.sh --deps-only

# Run with --force (overwrite without prompting)
bash src/image_build_manager/domain-init.sh --force
```

## Troubleshooting

### Python Version Error

```
ERROR: Python >= 3.11 required. Found: 3.10
```

**Solution**: Install Python 3.11 or later:
```bash
dnf install -y python3.12
```

### Required Variable Not Set

```
ERROR: SYSTEM_ADMIN_NIC_IPV4 is not set
```

**Solution**: Source `omnia.env` or export the variable:
```bash
set -a; source src/main/omnia.env; set +a
# or
export SYSTEM_ADMIN_NIC_IPV4=172.16.107.254
```

### Ansible Not Found After Setup

```
ERROR: ansible not found after pip install
```

**Solution**: Check that the venv was created correctly and activate it:
```bash
source /opt/omnia/venv/bin/activate
ansible --version
```

### Domain Init Failed

```
WARNING: domain-init.sh failed for image_build_manager — continuing
```

**Solution**: Check that the domain's `domain-init.sh` exists and is executable. Run it manually to see the error:
```bash
bash src/image_build_manager/domain-init.sh
```

### No domain-init.sh Scripts Found

```
No domain-init.sh scripts found in any domain
```

**Solution**: This means no domain has a `domain-init.sh` script yet. Ansible log directories will not be created automatically, and input files will not be staged to the runtime data path. Run manually:
```bash
sudo mkdir -p /var/log/omnia/<domain>
mkdir -p <OMNIA_DATA_PATH>/<domain>/input/project_default
cp -a src/<domain>/input/*.yml <OMNIA_DATA_PATH>/<domain>/input/project_default/
```
