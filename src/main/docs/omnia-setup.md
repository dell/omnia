# omnia.sh — Setup Script Documentation

The `omnia.sh` script handles initial setup and environment configuration for Omnia.

## Commands

| Command | Description |
|---------|-------------|
| `--setup-venv, -s` | Install env system-wide, create/update Python venv, install deps, run domain-init.sh, copy catalog, install omnia-cli |
| `--init, -i [domain,...]` | Run domain-init.sh scripts (all or comma-separated subset) |
| `--run, -r <domain> [--tags <tags>]` | Activate venv and run a domain's playbook |
| `--check-deps` | Audit all domains for pip/Galaxy version mismatches |
| `--cleanup` | Remove venv, system env files, and activation script. Data is preserved. |
| `--cleanup --all` | Remove everything: venv, system env, AND all data at `$OMNIA_DATA_PATH/` (full reset) |
| `--help, -h` | Show help message |

## Options

| Option | Description |
|--------|-------------|
| `--deps-only` | Install deps only, skip input file staging. Use with `-s` or `-i`. |
| `--force-deps` | Bypass dependency cache and force reinstall. Use with `-s` or `-i`. |
| `--skip-catalog` | With `-s`: skip the automatic catalog copy. |
| `--skip-omnia-cli` | With `-s`: skip installing omnia-cli and bash completion. |

## What `--setup-venv` Does

1. **Installs env system-wide** — Copies `omnia.env` → `/etc/omnia/omnia.env`, creates `/etc/profile.d/omnia-env.sh` drop-in, sources vars into current session
2. **Validates environment** — Checks required env vars are set (e.g., `SYSTEM_ADMIN_NIC_IPV4`)
3. **Creates base directories** — Sets up `/opt/omnia/{log,.data}`
4. **Finds Python 3.11+** — Searches for python3.12, python3.11, or python3
5. **Creates or updates venv** — Sets up virtual environment at `$OMNIA_VENV_PATH`
6. **Upgrades pip** — Ensures latest pip, setuptools, wheel
7. **Initializes domains** — Runs each domain's `domain-init.sh` which:
   - Installs pip packages from that domain's `requirements.txt` (cached — skipped if unchanged)
   - Installs Galaxy collections from that domain's `requirements.yml` (cached — skipped if unchanged)
   - Creates Ansible log directories
   - Stages input files from flat `src/<domain>/input/` to `<OMNIA_DATA_PATH>/<domain>/input/<project>/`
8. **Copies catalog** — Copies catalog files from `src/main/samples/` to `$OMNIA_DATA_PATH/catalog/` (use `--skip-catalog` to suppress)
9. **Installs omnia-cli** — Copies `omnia-cli` to `/usr/local/bin/omnia-cli` and bash completion to `/etc/bash_completion.d/omnia-cli` (use `--skip-omnia-cli` to suppress)
10. **Displays summary** — Shows venv path, Python version, installed Ansible and collections

Use `--deps-only` to skip input file staging in step 7 (e.g., in CI or if you manage input files externally). Dependencies are still installed.

Use `--force-deps` to bypass the dependency cache and force a fresh `pip install` + `ansible-galaxy collection install`.

```bash
./omnia.sh -s                      # Full setup: venv + deps + input copy + catalog + omnia-cli
./omnia.sh -s --deps-only          # Venv + deps only, skip input staging
./omnia.sh -s --skip-catalog       # Setup without catalog copy
./omnia.sh -s --skip-omnia-cli     # Setup without omnia-cli install
./omnia.sh -s --force-deps         # Force reinstall all deps (bypass cache)
./omnia.sh --init                  # Stage input files only (all domains)
./omnia.sh -i telemetry            # Init single domain
./omnia.sh -i repo_manager,telemetry  # Init specific domains
./omnia.sh --check-deps            # Audit dependency version mismatches
./omnia.sh --cleanup               # Remove venv + env (preserve data)
./omnia.sh --cleanup --all         # Full reset (remove everything)
```

## What `--check-deps` Does

Scans all domain `requirements.txt` and `requirements.yml` files for the same
package/collection pinned at different versions across domains. Exits non-zero
if any mismatch is found.

```bash
./omnia.sh --check-deps
```

## Dependency Caching

On first run, each domain's `requirements.txt` and `requirements.yml` are
hashed (MD5). On subsequent runs, if the file hasn't changed, the install
step is skipped entirely — saving 10-30 seconds per domain. Cache files
live at `$OMNIA_DATA_PATH/.data/deps-cache/`.

Use `--force-deps` to bypass the cache and force a fresh install.

## What `--cleanup` Does

Removes the Omnia environment without touching runtime data:

1. **Removes the Python venv** at `$OMNIA_VENV_PATH`
2. **Removes system env files** — `/etc/omnia/omnia.env`, `/etc/profile.d/omnia-env.sh`
3. **Removes activation script** — `activate-omnia.sh`
4. **Preserves data** — `$OMNIA_DATA_PATH/` is NOT removed

With `--all`, also removes all data at `$OMNIA_DATA_PATH/` (prompts for confirmation).

```bash
./omnia.sh --cleanup               # Venv + env only
./omnia.sh --cleanup --all         # Full reset (prompts for confirmation)
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

# Run with --force-deps (force reinstall even if cached)
bash src/image_build_manager/domain-init.sh --force-deps

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
