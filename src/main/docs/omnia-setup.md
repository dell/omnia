# omnia.sh — Setup Script Documentation

The `omnia.sh` script handles initial setup and environment configuration for Omnia.

## Commands

| Command | Description |
|---------|-------------|
| `--setup-venv, -s` | Install env system-wide, create/update Python venv, install deps, run domain-init.sh, copy catalog, install omnia-cli |
| `--init, -i [domain,...]` | Run domain-init.sh scripts (all or comma-separated subset) |
| `--run, -r <domain> [--tags <tags>]` | Activate venv and run a domain's playbook |
| `--prepare-base` | Prepare Repo Manager, Image Build Manager, and Orchestrator in dependency order |
| `--check-deps` | Audit all domains for pip/Galaxy version mismatches |
| `--cleanup` | Remove the venv, system env, omnia-cli, shared Bash completion, activation script, and dependency cache. Runtime data is preserved. |
| `--cleanup --all` | Guarded full reset. Refuses to start while a domain contains uncleared state. Empty `log`/`output` directories and known Build Stream initializer files are allowed, then initializer input/log paths and all remaining Omnia data are removed. |
| `--help, -h` | Show help message |

## Options

| Option | Description |
|--------|-------------|
| `--deps-only` | Install deps only, skip input file staging. Use with `-s` or `-i`. |
| `--force-deps` | Bypass dependency cache and force reinstall. Use with `-s` or `-i`. |
| `--force-env` | With `-s`, explicitly replace `/etc/omnia/omnia.env` from the repository copy. |
| `--skip <domain,...>` | Skip domains with `-s`, `-i`, or `--prepare-base`; only the three base domains are valid with `--prepare-base`. |
| `--dry-run` | Preview domain initialization with `-s`/`-i`, or base-domain phases with `--prepare-base`; no domains are initialized or prepared. Other `-s` setup steps still run. |
| `--skip-catalog` | With `-s`: skip the automatic catalog copy. |
| `--skip-omnia-cli` | With `-s`: skip installing omnia-cli and shared `omnia-cli`/`omnia.sh` Bash completion. |
| `--skip-approval` | With `--cleanup`: skip confirmation for trusted, unattended automation. |

## What `--setup-venv` Does

1. **Configures env system-wide** — Copies `omnia.env` on the first run; later runs preserve the authoritative `/etc/omnia/omnia.env` unless `--force-env` is supplied
2. **Validates environment** — Checks required env vars are set (e.g., `SYSTEM_ADMIN_NIC_IPV4`)
3. **Creates base directories** — Creates `$OMNIA_DATA_PATH` and its `.data` directory
4. **Finds Python 3.11+** — Searches for python3.12, python3.11, or python3
5. **Creates or updates venv** — Sets up virtual environment at `$OMNIA_VENV_PATH`
6. **Upgrades pip** — Ensures latest pip, setuptools, wheel
7. **Initializes domains** — Runs each domain's `domain-init.sh` which:
   - Installs pip packages from that domain's `requirements.txt` (cached — skipped if unchanged)
   - Installs Galaxy collections from that domain's `requirements.yml` (cached — skipped if unchanged)
   - Creates Ansible log directories
   - Stages input files from flat `src/<domain>/input/` to `<OMNIA_DATA_PATH>/<domain>/input/<project>/`
8. **Copies catalog** — Copies catalog files from `src/main/samples/` to `$OMNIA_DATA_PATH/catalog/` (use `--skip-catalog` to suppress)
9. **Installs omnia-cli** — Copies `omnia-cli` to `/usr/local/bin/omnia-cli` and shared completion for `omnia-cli` and `omnia.sh` to `/etc/bash_completion.d/omnia-bash-completion` (use `--skip-omnia-cli` to suppress)
10. **Displays summary** — Shows venv path, Python version, installed Ansible and collections

After copying the default combined Slurm + service_k8s catalog, setup displays
the active `CATALOG_FILE_PATH` and commands for either replacing the catalog at
that path or copying a different catalog and updating the path. For example,
the service_k8s-only sample is
`samples/catalogs/10.0/service_k8s_x86_64.json`.

Use `--deps-only` to skip input file staging in step 7 (e.g., in CI or if you manage input files externally). Dependencies are still installed.

Use `--force-deps` to bypass the dependency cache and force a fresh `pip install` + `ansible-galaxy collection install`.

Bash completion loaders normally pick up the installed file in a fresh shell.
To use it immediately, source `/etc/bash_completion.d/omnia-bash-completion` or source the
generated `${OMNIA_DATA_PATH:-/opt/omnia}/activate-omnia.sh` helper.

```bash
./omnia.sh -s                      # Full setup: venv + deps + input copy + catalog + omnia-cli
./omnia.sh -s --deps-only          # Venv + deps only, skip input staging
./omnia.sh -s --skip-catalog       # Setup without catalog copy
./omnia.sh -s --skip-omnia-cli     # Setup without omnia-cli install
./omnia.sh -s --force-deps         # Force reinstall all deps (bypass cache)
./omnia.sh -s --force-env          # Explicitly replace the installed env from the repo
./omnia.sh --init                  # Install deps and stage inputs for all domains
./omnia.sh -i telemetry            # Init single domain
./omnia.sh -i repo_manager,telemetry  # Init specific domains
./omnia.sh --check-deps            # Audit dependency version mismatches
./omnia.sh --cleanup               # Remove environment + CLI integration; preserve runtime data
./omnia.sh --cleanup --all         # Guarded full reset
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
3. **Removes CLI integration** — `/usr/local/bin/omnia-cli` and `/etc/bash_completion.d/omnia-bash-completion`
4. **Removes activation script and dependency cache** — `activate-omnia.sh` and `$OMNIA_DATA_PATH/.data/deps-cache/`
5. **Preserves runtime data** — input, output, and logs under `$OMNIA_DATA_PATH/` are not removed

With `--all`, cleanup first checks every domain directory. Non-empty `output`
or `log` directories, service storage, and unrecognized paths stop cleanup
before anything is deleted. Empty `output` and `log` roots are allowed. Build
Stream's initializer-staged application files are also allowed because they are
installation content rather than deployed lifecycle state. Once only safe
initializer content remains, each `domain-init.sh --cleanup` removes the domain
input/runtime-log paths and `/var/log/omnia/<domain>`, and the full reset
continues.

```bash
./omnia.sh --cleanup               # Remove environment + CLI integration; preserve runtime data
./omnia.sh --cleanup --all         # Guarded full reset
./omnia.sh --cleanup --skip-approval       # Trusted automation; preserve runtime data
./omnia.sh --cleanup --all --skip-approval # Trusted automation; full reset
```

Both cleanup modes show the exact removal scope and require the operator to type
`yes`. `--skip-approval` is the only supported way to suppress that prompt and
should be used only by automation that has already validated the target host and
`OMNIA_DATA_PATH`. A full cleanup still performs all safety preflight checks when
approval is skipped.

Each domain also exposes `domain-init.sh --cleanup`. This internal helper is
non-interactive and removes only initializer-owned staged `input/`, runtime
`log/`, and `/var/log/omnia/<domain>/` paths. It does not replace the domain's
Ansible `cleanup` tag. `omnia.sh --cleanup --all` calls the helper only after its
preflight confirms that no deployed or generated domain state remains.

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
vi /etc/omnia/omnia.env
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
