<!-- Copyright 2026 Dell Inc. or its subsidiaries. All Rights Reserved.

Licensed under the Apache License, Version 2.0 (the "License");
you may not use this file except in compliance with the License.
You may obtain a copy of the License at

    http://www.apache.org/licenses/LICENSE-2.0

Unless required by applicable law or agreed to in writing, software
distributed under the License is distributed on an "AS IS" BASIS,
WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
See the License for the specific language governing permissions and
limitations under the License. -->

# Omnia Automation Framework

End-to-end automation and testing for **Omnia Infrastructure Manager (OIM)** deployments using pytest and testinfra.

## Table of Contents

- [Overview](#overview)
- [Quick Start](#quick-start)
- [Configuration](#configuration)
- [Execution](#execution)
- [Scenarios](#scenarios)
- [Project Structure](#project-structure)
- [Detailed References](#detailed-references)
- [License](#license)

---

## Overview

This framework automates testing of Omnia Infrastructure Manager (OIM) deployments. It provides:

- **Prerequisite validation** of the OIM server (hardware, OS, network, NFS, Podman)
- **Pytest validation scenarios** that execute Ansible playbooks inside the `omnia_core` container and verify results with pytest-testinfra
- **Interactive HTML and JSON reports** for every test run

### How It Works

1. **`omnia_test_config.yml`** drives all automation — it defines the OIM server connection, hardware thresholds, deployment options, and dataset selection.
2. **`omnia_test_credentials.yml`** stores sensitive credentials (passwords) separately — automatically encrypted with Ansible Vault on first run.
3. **`setup_env.sh`** creates a Python virtual environment, installs dependencies, and registers the `oim-prereq-test` CLI and `run_validation` shell function.
4. **Validation scenarios** follow a `deploy → verify` lifecycle:
   - **deploy** — Executes the target Ansible playbook inside `omnia_core` via `podman exec` with live streaming output using the `playbook_runner` module.
   - **verify** — Runs pytest-testinfra tests that use `automation_library` functions to validate deployment state.
5. **`automation_library/core/`** provides shared utilities for host connections, config loading, container command execution, PXE mapping parsing, credential decryption, and report generation.
6. **`automation_library/playbook_runner/`** provides the `PlaybookRunner` class for executing Ansible playbooks and shell commands with real-time output streaming, responsive Ctrl+C handling, and structured result reporting.

### Container Path Layout

The `omnia_core` container image copies the repository source code to `/omnia/src/`. Playbook paths inside the container follow this structure:

| Host path (repo) | Container path |
|---|---|
| `src/playbooks/<playbook>/` | `/omnia/src/playbooks/<playbook>/` |
| `src/input/` | `/omnia/src/input/` |
| `src/examples/` | `/omnia/src/examples/` |
| Deployed input files | `/opt/omnia/input/project_default/` |

### Local Mode vs Remote Mode

| Mode | When | How |
|------|------|-----|
| **Local mode** | `oim_server_ip` is empty, `""`, `localhost`, or `127.0.0.1` | All commands run directly on the local machine — no SSH required. Assumes the automation is running on the OIM server itself. |
| **Remote mode** | `oim_server_ip` is set to a remote IP address | All commands are executed over SSH using the provided `oim_ssh_user` and `oim_ssh_password`. |

> **Important:** If `oim_server_ip` is not set, every scenario (including `omnia_sh_install`) runs in local mode on the current host.

---

## Quick Start

```bash
# 1. Clone the omnia repository
git clone https://github.com/dell/omnia.git
cd omnia/test/fvt

# 2. Run the environment setup script
./setup_env.sh

# 3. Activate the virtual environment
source .venv/bin/activate

# 4. Configure your OIM server
vi omnia_test_config.yml

# 5. Configure credentials (passwords)
vi omnia_test_credentials.yml

# 6. (Optional) Fill dataset files — required only for deploy/test runs
vi datasets/project_default/network_spec.yml
vi datasets/project_default/software_config.json

# 7. Run prerequisite checks
oim-prereq-test

# 8. Run validation tests
./run_validation.sh telemetry verify --suite sanity   # Single scenario
./run_validation.sh prepare_oim test                  # Full lifecycle (deploy + verify)
./run_validation.sh list                              # List available scenarios
```

> **Note:** For `verify`-only runs (validating an already-deployed environment), filling the dataset files is not required. The validation framework uses the input files already present inside the `omnia_core` container.

---

## Configuration

### omnia\_test\_config.yml

This is the central configuration file for non-sensitive settings. Every automation script reads from it. Edit this file before running any tests.

> **Full parameter reference:** [docs/input_reference.md](docs/input_reference.md)

Key parameters:

| Parameter | Description |
|-----------|-------------|
| `oim_server_ip` | OIM server IP. Leave empty for local mode. |
| `oim_ssh_user` | SSH username for remote mode. |
| `dataset` | Dataset folder name under `datasets/` (default: `project_default`). |
| `sync_dataset_to_core` | When `true`, syncs dataset files into the container before playbook execution. |
| `report_id` | Custom report ID string. When set, replaces the auto-generated timestamp. Reusing the same ID appends results to the existing report. Default: `""` (auto-generate). |
| `reconfigure_images` | When `true`, runs `omnia.sh --build` before install. Default: `false`. |
| `share_option` | Storage backend for omnia.sh: `NFS` or `Local`. |

### omnia\_test\_credentials.yml

This file stores all sensitive credentials (passwords). It is **automatically encrypted** with Ansible Vault on first run.

| Parameter | Description |
|-----------|-------------|
| `oim_ssh_password` | SSH password for remote OIM server (remote mode only). |
| `omnia_core_password` | Root password for `omnia_core` container SSH (port 2222). |
| `ldap_credentials` | LDAP user credentials for cluster login tests (format: `user:pass` or `user1:pass1,user2:pass2`). |
| `external_ldap_bind_username` | External LDAP bind username for slapd.conf configuration. |
| `external_ldap_bind_password` | External LDAP bind password for slapd.conf configuration. |

> **Security:** The credentials file is automatically encrypted using Ansible Vault. The vault key is stored in `.omnia_test_credentials.key` (gitignored). On each test run, the file is decrypted, used, and re-encrypted.

### Datasets

The `datasets/project_default/` folder contains Omnia deployment input files that mirror `/opt/omnia/input/project_default/` inside the `omnia_core` container.

> **Full dataset reference:** [docs/dataset_reference.md](docs/dataset_reference.md)

Key files:

| File | Purpose |
|------|---------|
| `software_config.json` | Central control — defines OS type, version, and software stack to deploy |
| `network_spec.yml` | Admin network, InfiniBand network, DHCP, DNS, NTP |
| `telemetry_config.yml` | Telemetry sources — iDRAC, LDMS, DCGM, PowerScale |
| `omnia_config.yml` | Slurm and Kubernetes cluster definitions |
| `pxe_mapping_file.csv` | Node-to-network mapping for PXE provisioning |
| `additional_cloud_init.yml` | Custom cloud-init for stateless node provisioning |

---

## Execution

### Installation

```bash
./setup_env.sh                # Creates .venv, installs deps, registers CLI
source .venv/bin/activate     # Activates the virtual environment
```

| Flag | Description |
|------|-------------|
| `--force` | Remove existing `.venv` and recreate from scratch |
| `--debug` | Verbose output — show every package installed |

### Prerequisite Checks

Validates the OIM server before deployment. See [docs/prereq_check_reference.md](docs/prereq_check_reference.md) for details.

```bash
oim-prereq-test                       # Run all checks
oim-prereq-test --debug               # Verbose output
oim-prereq-test --stop-on-failure     # Stop on first failure
oim-prereq-test --continue-on-failure # Continue even if a check fails
oim-prereq-test --no-report           # Skip HTML report generation
```

### Running Validation Tests

```bash
# Basic commands
./run_validation.sh <scenario> deploy              # Run playbook with live output
./run_validation.sh <scenario> verify              # Run ALL verification tests
./run_validation.sh <scenario> test                # Deploy + verify (full flow)
./run_validation.sh list                           # List available scenarios
```

Invalid scenarios, commands, or suites are validated and rejected with supported values listed.

### Suite and Marker Filtering

Tests can be filtered by **suite** (folder-based), **marker** (decorator-based), or **both combined**:

| Option | Mechanism | What it does |
|--------|-----------|----------|
| `--suite` | Folder-based | Runs tests from `tests/<suite>/` directory only |
| `--marker` | Decorator-based | Runs tests decorated with `@pytest.mark.<marker>` |
| Both | Combined | Runs tests in `tests/<suite>/` that also have `@pytest.mark.<marker>` |

```bash
# Suite only — run all tests in a specific suite folder
./run_validation.sh provision verify --suite sanity           # tests/sanity/*.py
./run_validation.sh provision verify --suite negative         # tests/negative/*.py
./run_validation.sh provision verify --suite regression       # tests/regression/*.py

# Marker only — run tests with a specific @pytest.mark across ALL suites
./run_validation.sh provision verify --marker smoke           # all @pytest.mark.smoke tests
./run_validation.sh provision verify --marker build_stream    # all @pytest.mark.build_stream tests
./run_validation.sh provision verify --marker deploy          # all @pytest.mark.deploy tests

# Suite + Marker combined — narrowest filter
./run_validation.sh provision verify --suite sanity --marker smoke          # sanity tests with @smoke
./run_validation.sh provision verify --suite sanity --marker build_stream   # sanity tests with @build_stream
./run_validation.sh provision test --suite sanity --marker smoke            # deploy + sanity @smoke tests
```

**Available markers** (registered in `pytest.ini`):

| Marker | Purpose |
|--------|---------|
| `sanity` | Core verification tests |
| `negative` | Negative / failure-path tests (e.g., reboot scenarios) |
| `regression` | Full regression tests |
| `stress` | Stress tests |
| `deploy` | Playbook deployment tests (used by `test_deploy.py`) |
| `build_stream` | Tests dependent on build stream pipeline |
| `build_auto` | Build pipeline auto-trigger tests |
| `build_manual` | Build pipeline manual trigger tests |
| `deploy_auto` | Deploy pipeline auto-trigger tests |
| `deploy_manual` | Deploy pipeline manual trigger tests |
| `cleanup_manual` | Cleanup pipeline tests (manual trigger only) |
| `ldap` | LDAP user authentication and PAM tests |
| `sanityib` | InfiniBand sanity tests |
| `sanitygpu` | GPU sanity tests |
| `minimal_os` | Minimal OS provisioning tests |
| `compatibility` | Compatibility tests |
| `vast_telemetry` | VAST storage telemetry tests |
| `ufm_telemetry` | UFM telemetry tests |

### Batch Execution

```bash
./run_validation.sh --config                                        # Batch from config (stop on failure)
./run_validation.sh --config --continue-on-failure                   # Continue despite failures
./run_validation.sh --config --restart                               # Discard progress, start fresh
./run_validation.sh --config --restart --continue-on-failure         # Fresh start + continue on failure
./run_validation.sh all test                                         # Run ALL scenarios (deploy + verify)
./run_validation.sh all verify --suite sanity                        # Verify all with sanity suite
./run_validation.sh all verify --marker smoke                        # Verify all with smoke marker
./run_validation.sh all verify --suite sanity --marker smoke         # Verify all: sanity + smoke
```

Batch mode generates a **single unified report** across all scenarios using a shared report ID.

**Batch behavior (`--config`):**

- **Upfront validation** — before any scenario runs, the config is validated: duplicate/missing `order` values and invalid `command` values (must be `deploy`, `verify`, or `test`) are caught immediately with a clear error.
- **Stop on failure** — by default, if a scenario fails the batch stops immediately. Fix the issue and re-run `--config` to **resume** from where it left off.
- **`--continue-on-failure`** — continues executing remaining scenarios even if one fails. The final exit code still reflects whether any scenario failed.
- **`--restart`** — discards any saved progress and starts the batch from the first scenario.
- **Resume** — batch progress is tracked in `.batch_track`. On re-run, completed steps are automatically skipped. The report ID from the previous run is reused so results append to the same report. When all scenarios pass, the track file is cleaned up.
- **Deploy / verify split tracking** — for `command: test` scenarios, deploy and verify are tracked independently. If deploy passed but verify failed, resume skips deploy and retries only verify. If deploy failed, both phases are re-run.
- **Prerequisite tracking** — `oim-prereq-test` is also tracked; once it passes, resume skips it on subsequent runs.
- **Ordering** — scenarios run in ascending `order` value. Duplicate or missing `order` values are a configuration error and abort the batch.
- **Dataset sync** — when `sync_dataset_to_core: true` in `omnia_test_config.yml`, playbook deploy steps sync the selected dataset (including the vault-encrypted `omnia_config_credentials.yml`) into the container before execution. The `omnia_sh_install` scenario is exempt — it builds the container and does not receive synced project inputs.
- **Custom report ID** — set `report_id` in `omnia_test_config.yml` to use a fixed string instead of the auto-generated timestamp. Reusing the same report ID across runs appends results to the existing report entry.

### Test Reports

Reports are generated in `reports/` after execution:

| Format | File | Description |
|--------|------|-------------|
| HTML | `test_report.html` | Interactive report with charts, Deploy/Verify sections, theme toggle |
| JSON | `test_report.json` | Machine-readable format for CI/CD integration |

Report features:

- **Dark / Light theme toggle** — switch between themes in the header
- **Donut chart** per test run showing pass rate (excludes skipped from calculation)
- **Scenario bar chart** with hover tooltips showing mini donut + suite/marker info
- **Scenario Trends panel** — per-scenario pass-rate sparklines across historical runs on the same server, with up/down/flat trend deltas so flaky or regressing scenarios stand out
- **Slowest Scenarios duration bars** — per-run horizontal bars ranking scenarios by execution time to surface performance hot-spots
- **Deploy / Verify sections** — each scenario splits results into Deploy (playbook logs + deploy tests) and Verify (verification tests)
- **Suite & marker badges** — shows which `--suite` and `--marker` were used per scenario
- **Server Setup panel** — separate graphical status panel for server-setup checks when present (not counted in test totals)
- **KPI cards** — Total, Passed, Failed, Skipped, Pass Rate, Runs, and Duration with hover effects
- **ANSI-clean output** — color codes from playbook logs are stripped automatically
- **Collapsible sections** — runs, modules, tests, and playbook logs are expandable
- **Self-contained** — all CSS/JS inline, shareable as a single HTML file
- **Pass rate formula** — `passed / (passed + failed)` — skipped tests are excluded since they were not executed

---

## Scenarios

Scenarios are defined in `test_run_config.yml`. Each scenario has an
`order` value that controls execution sequence in batch mode — orders must
be **unique** (duplicate orders abort the batch) but need not be contiguous.
The `#` column below matches the default `order` values shipped in
`test_run_config.yml`.

The prerequisite tool (`oim-prereq-test`) is **not** a scenario. It is a gate
controlled by the top-level `oim_prereq_test: true/false` flag in
`test_run_config.yml`. When enabled, it validates and configures the OIM
server first; if it fails, the batch aborts before any scenario runs.

| # | Scenario | Omnia Playbook (inside container) | Description |
|---|----------|----------------------------------|-------------|
| 1 | `omnia_sh_install` | `omnia.sh --build` + `omnia.sh --install` | Builds container image and installs `omnia_core` (live streaming) |
| 2 | `prepare_oim` | `/omnia/src/playbooks/prepare_oim/prepare_oim.yml` | Prepares OIM — OpenCHAMI, firewall, NTP, NFS |
| 3 | `gitlab_install` | `/omnia/src/playbooks/gitlab/gitlab.yml` | Deploys GitLab for BuildStream CI/CD |
| 4 | `local_repo` | `/omnia/src/playbooks/local_repo/local_repo.yml` | Syncs packages to Pulp repository |
| 5 | `build_image_x86_64` | `/omnia/src/playbooks/build_image_x86_64/build_image_x86_64.yml` | Builds x86_64 OS images |
| 6 | `build_image_aarch64` | `/omnia/src/playbooks/build_image_aarch64/build_image_aarch64.yml` | Builds aarch64 OS images |
| 7 | `discovery` | `/omnia/src/playbooks/discovery/discovery.yml` | Discovers cluster nodes via BMC/OME |
| 8 | `provision` | `/omnia/src/playbooks/provision/provision.yml` | Provisions nodes with OS and software |
| 9 | `telemetry` | `/omnia/src/playbooks/telemetry/telemetry.yml` | Deploys telemetry stack |
| 10 | `apptainer` | — (verify only) | Verifies Apptainer runtime on Slurm nodes |
| 11 | `kubernetes` | — (verify only) | Verifies Kubernetes cluster health |
| 12 | `slurm` | — (verify only) | Verifies Slurm workload manager |
| 13 | `dcgm` | — (verify only) | Verifies NVIDIA DCGM GPU monitoring |
| 14 | `hpc_benchmarks` | — (verify only) | Verifies HPC benchmark results |
| 15 | `vast_storage` | — (verify only) | Verifies VAST storage mounts |
| 16 | `build_stream` | — (verify only) | Verifies BuildStream CI/CD pipeline |
| 17 | `additional_cloud_init` | — (verify only) | Verifies custom cloud-init configuration |
| 18 | `one_shot_log_extraction` | — (deploy + verify) | Extracts combined logs from cluster nodes |
| 19 | `upgrade_omnia_sh` | `omnia.sh --upgrade` | Upgrades the `omnia_core` container to newer version (live streaming) |
| 20 | `rollback_omnia_sh` | `omnia.sh --rollback` | Rolls back the `omnia_core` container to previous version (live streaming) |
| 21 | `gitlab_cleanup` | `/omnia/src/playbooks/gitlab/cleanup_gitlab.yml` | Removes GitLab deployment |
| 22 | `oim_cleanup` | `/omnia/src/playbooks/utils/oim_cleanup.yml` | Cleans up OIM environment |
| 23 | `omnia_sh_uninstall` | `omnia.sh --uninstall` | Uninstalls the `omnia_core` container (live streaming) |

---

## Project Structure

```
omnia/test/fvt/
├── omnia_test_config.yml              # Central config — OIM server, settings, dataset
├── omnia_test_credentials.yml         # Sensitive credentials (auto-encrypted with Vault)
├── .omnia_test_credentials.key        # Vault encryption key (gitignored)
├── test_run_config.yml                # Batch scenario runner config
├── requirements.txt                   # Python dependencies
├── setup.py                           # Package setup (omnia-automation)
├── setup_env.sh                       # Environment setup script
├── run_validation.sh                  # Validation test runner
├── run_prereq_test.py                # Prerequisite check entry point
├── pytest.ini                         # Pytest configuration and custom markers
│
├── datasets/                          # Deployment input datasets
│   └── project_default/               # Default dataset
│       ├── software_config.json
│       ├── network_spec.yml
│       ├── additional_cloud_init.yml
│       ├── ...                        # See docs/dataset_reference.md
│       └── config/                    # Per-architecture package lists
│
├── automation_library/                # Python automation library
│   ├── core/                          # Shared infrastructure & single source of truth
│   │   ├── functions/                 # SSH, config loading, container exec, PXE, reports
│   │   ├── vars/                      # Shared constants (paths, container, SSH, groups)
│   │   └── messages/                  # Shared log/assertion messages
│   ├── checks/                        # Prerequisite checks (oim-prereq-test CLI)
│   ├── playbook_runner/               # Playbook execution engine (PlaybookRunner)
│   └── <module>/                      # Per-scenario modules — telemetry, slurm, kubernetes,
│       ├── __init__.py                #   dcgm, discovery, provision, vast_storage, etc.
│       ├── functions/                 # Verification logic ONLY (component_func.py, common_func.py)
│       ├── vars/                      # Module constants — reuse core vars, no duplication
│       └── messages/                  # Test names, log messages, assertion messages
│
├── validations/                       # Validation test scenarios (pytest-native)
│   ├── conftest.py                    # Global pytest fixtures, markers, report hooks
│   └── <scenario>/tests/              # Per-scenario test directories
│       ├── sanity/                    # Sanity suite tests (call functions, assert only)
│       ├── negative/                  # Negative / failure-path tests
│       └── test_deploy.py             # Playbook deployment test (@pytest.mark.deploy)
│
├── docs/                              # Detailed reference documentation
│   ├── input_reference.md             # omnia_test_config.yml parameter reference
│   ├── dataset_reference.md           # Dataset files reference
│   └── prereq_check_reference.md      # Prerequisite checks reference
│
└── reports/                           # Generated test reports (gitignored)
```

---

## Detailed References

| Document | Description |
|----------|-------------|
| [docs/input_reference.md](docs/input_reference.md) | Complete `omnia_test_config.yml` parameter reference with types, defaults, and usage |
| [docs/dataset_reference.md](docs/dataset_reference.md) | All dataset files, which Omnia playbooks consume them, and how input files flow into the container |
| [docs/prereq_check_reference.md](docs/prereq_check_reference.md) | Detailed prerequisite check descriptions and `oim-prereq-test` usage |
| [docs/migration_molecule_to_pytest.md](docs/migration_molecule_to_pytest.md) | Migration guide from Molecule to the new validation framework |

---

## License

Copyright 2026 Dell Inc. or its subsidiaries. All Rights Reserved.

Licensed under the Apache License, Version 2.0 (the "License"); you may not use this file except in compliance with the License. You may obtain a copy of the License at

http://www.apache.org/licenses/LICENSE-2.0

Unless required by applicable law or agreed to in writing, software distributed under the License is distributed on an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the License for the specific language governing permissions and limitations under the License.
