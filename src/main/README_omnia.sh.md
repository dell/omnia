# omnia.sh — Setup Script Documentation

The `omnia.sh` script handles initial setup and environment configuration for Omnia.

## Commands

| Command | Description |
|---------|-------------|
| `--setup-venv, -s` | Create/update the shared Python venv with pip and Galaxy collections |
| `--help, -h` | Show help message |

## What `--setup-venv` Does

1. **Validates `omnia.env`** — Checks required variables are set
2. **Creates base directories** — Sets up `/opt/omnia/{log,.data}`
3. **Finds Python 3.11+** — Searches for python3.12, python3.11, or python3
4. **Creates or updates venv** — Sets up virtual environment at `$OMNIA_VENV_PATH`
5. **Upgrades pip** — Ensures latest pip, setuptools, wheel
6. **Installs per-domain pip packages** — Discovers and installs `requirements.txt` from all domains
7. **Installs Galaxy collections** — Discovers and installs `requirements.yml` from all domains
8. **Displays summary** — Shows venv path, Python version, Ansible version, and installed collections

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

### Missing omnia.env

```
ERROR: omnia.env not found at /path/to/omnia.env
```

**Solution**: Ensure you're in the `src/main` directory and `omnia.env` exists:
```bash
cd src/main
ls -la omnia.env
```

### Variable Not Set

```
ERROR: OMNIA_ADMIN_NIC_IP is not set in omnia.env
```

**Solution**: Edit `omnia.env` and set the required variable:
```bash
vi omnia.env  # Set OMNIA_ADMIN_NIC_IP
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
