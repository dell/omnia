# omnia.sh — Setup Script Documentation

The `omnia.sh` script handles initial setup and environment configuration for Omnia.

## Commands

| Command | Description |
|---------|-------------|
| `--setup-venv, -s` | Install env system-wide, create/update Python venv, install deps, run domain-init.sh |
| `--init, -i` | Run all domain-init.sh scripts (stage input files to NFS share) |
| `--run, -r <domain> [--tags <tags>]` | Activate venv and run a domain's playbook |
| `--validate <domain>` | Validate a domain's configuration (shortcut for --run with validate tag) |
| `--help, -h` | Show help message |

## Options

| Option | Description |
|--------|-------------|
| `--skip-init` | Skip running domain-init.sh scripts during `--setup-venv` (useful in CI or when input files are managed externally) |

## What `--setup-venv` Does

1. **Installs env system-wide** — Copies `omnia.env` → `/etc/omnia/omnia.env`, creates `/etc/profile.d/omnia-env.sh` drop-in, sources vars into current session
2. **Validates environment** — Checks required env vars are set (e.g., `SYSTEM_ADMIN_NIC_IPV4`)
3. **Creates base directories** — Sets up `/opt/omnia/{log,.data}`
4. **Finds Python 3.11+** — Searches for python3.12, python3.11, or python3
5. **Creates or updates venv** — Sets up virtual environment at `$OMNIA_VENV_PATH`
6. **Upgrades pip** — Ensures latest pip, setuptools, wheel
7. **Installs per-domain pip packages** — Discovers and installs `requirements.txt` from all domains
8. **Installs Galaxy collections** — Discovers and installs `requirements.yml` from all domains
9. **Initializes domains** — Runs each domain's `domain-init.sh` to create Ansible log directories and stage input files from flat `src/<domain>/input/` to `<OMNIA_DATA_PATH>/<domain>/input/<project>/`
10. **Displays summary** — Shows venv path, Python version, Ansible version, and installed collections

Use `--skip-init` to skip step 9 (e.g., in CI pipelines or when input files are managed externally).

```bash
./omnia.sh -s                      # Full setup: venv + input copy
./omnia.sh -s --skip-init          # Venv only, skip input file staging
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
Installing pip packages for image_build_manager ...
Installing pip packages for telemetry ...
Installing Galaxy collections for repo_manager ...
Installing Galaxy collections for discovery ...

================================================================================
                Omnia Venv Setup Complete
================================================================================

  Venv:    /opt/omnia/venv
  Python:  Python 3.12.1
  Ansible:  ansible [core 2.17.0]

Installed collections:
ansible.builtin
ansible.posix
community.general
kubernetes.core
...

Activate in your shell:
  source /opt/omnia/venv/bin/activate
```

## Domain Discovery

The script automatically discovers and installs dependencies from all known domains:

- `build_stream`
- `discovery`
- `image_build_manager`
- `orchestrator`
- `repo_manager`
- `telemetry`
- `utils`

For each domain, it looks for:
- `requirements.txt` — Python pip packages
- `requirements.yml` — Ansible Galaxy collections

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

### No requirements.txt Found

```
WARNING: No requirements.txt found in any domain
```

**Solution**: This is a warning, not an error. It means no domains have Python dependencies. If you expect dependencies, check that domain directories exist under `src/`.

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
