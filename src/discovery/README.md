# Omnia Discovery

Discovery (`omnia.discovery`) finds bare-metal nodes through Dell OpenManage Enterprise (OME) and produces a PXE mapping and a discovery report for operator hand-off. It does not provision or register nodes; that is Orchestrator's role.

## Overview

Discovery automates hardware inventory discovery for HPC and AI clusters by:

- Connecting to Dell OpenManage Enterprise (OME) to query BMC endpoints
- Collecting server inventory including hardware specifications and network information
- Generating PXE mapping files that map physical nodes to functional groups and network configurations
- Creating discovery reports for operator review and validation
- Assigning functional group names based on OME static groups or default patterns

### What Discovery does

Discovery only queries OME and writes local artifacts. It:
- Discovers BMC endpoints through OME API
- Generates `bmc_pxe_mapping_file_<timestamp>.csv` (with a `bmc_pxe_mapping_file.csv` symlink to the latest) for operator review and hand-off to Orchestrator
- Produces discovery reports with inventory details
- Validates OME connectivity and data path readiness

Discovery does **not**:
- Provision nodes
- Register nodes in OpenCHAMI
- Configure network settings
- Install operating systems

### Related modules

| Direction | Module | Interaction |
|-----------|--------|-------------|
| Upstream | OpenManage Enterprise | Source of server inventory (HTTPS, port 443) |
| Downstream | Orchestrator | The operator reviews the generated mapping and copies it to `pxe_mapping_file.csv` |

Discovery is optional when a PXE mapping is supplied manually.

## Architecture

### Roles

Roles are invoked as `omnia.discovery.<role>`.

| Role | Description |
|------|-------------|
| [`discovery_cleanup`](roles/discovery_cleanup/README.md) | Remove Discovery-owned outputs, logs, and optional credential artifacts |
| [`discovery_common`](roles/discovery_common/README.md) | Shared task library (Vault and OME endpoint helpers); included with `tasks_from`, not run standalone |
| [`discovery_credentials`](roles/discovery_credentials/README.md) | Prompt for, validate, encrypt, and Vault-store OME credentials |
| [`discovery_setup`](roles/discovery_setup/README.md) | Set up project directories, load configuration, and validate tags |
| [`ome_discovery`](roles/ome_discovery/README.md) | Collect inventory from OME and generate the PXE mapping and discovery report |
| [`precheck_environment`](roles/precheck_environment/README.md) | Validate the Discovery data path and OME endpoint readiness |
| [`validate_discovery_input`](roles/validate_discovery_input/README.md) | L1 schema and L2 logic validation of `discovery_config.yml` |

### Modules

Modules are invoked as `omnia.discovery.<module>`.

| Module | Description |
|--------|-------------|
| `generate_discovery_report` | Generate BMC discovery report from server inventory |
| `generate_pxe_mapping` | Generate PXE mapping file from server inventory |
| `ome_server_inventory` | Collect server inventory from Dell OME |
| `validate_credentials` | Validate credential input against rules |
| `validate_discovery_config` | Validate discovery configuration files |
| `validate_system_environment` | Validate the Discovery system environment |

### Plugins

| Plugin | Type | Description |
|--------|------|-------------|
| `omnia_default` | Callback | Custom Ansible stdout callback plugin for Omnia |

## Prerequisites

| Requirement | Minimum | Notes |
|-------------|---------|-------|
| OS | RHEL 10.x, Rocky 10.x | Runs on the OIM |
| Python | 3.12+ | Shared Omnia virtual environment |
| Ansible | ansible-core 2.20+ | Pinned in `requirements.txt` |
| Collection | `community.general` >= 5.0.0 |  |
| OME | Reachable from the OIM | HTTPS port 443 |

## Installation

Run the shared setup once from the repository root. It creates the Omnia virtual environment, runs every domain's `domain-init.sh` (dependencies, log directories, input staging) and installs the default catalog if none is active.

```bash
cd src/main
vi omnia.env                       # first run only; afterwards edit /etc/omnia/omnia.env
sudo ./omnia.sh --setup-venv
source /etc/profile.d/omnia-env.sh
```

To re-run only this module's initializer (for example after editing source inputs):

```bash
sudo ./omnia.sh --init discovery
```

## Configuration

| Variable | Default | Description |
|----------|---------|-------------|
| `OMNIA_DATA_PATH` | `/opt/omnia` | Root for shared Omnia data and the default Discovery path |
| `OMNIA_PROJECT_NAME` | `project_default` | Active input/output project name |
| `DISCOVERY_DATA_PATH` | `${OMNIA_DATA_PATH}/discovery` | Optional Discovery component data-path override |

The resolved component root contains `input/<project>`, `output/<project>`, and
`log/<project>`. `domain-init.sh`, playbook setup, validation, credential
lookup, output generation, and Discovery cleanup all use the same resolved
root.

Edit the staged `discovery_config.yml` under `$DISCOVERY_DATA_PATH/input/$OMNIA_PROJECT_NAME/` (source template: `src/discovery/input/discovery_config.yml`) before running.

## Usage

Run this module through `omnia.sh`; it activates the virtual environment and runs `src/discovery/playbooks/discovery.yml`. All `./omnia.sh` commands in this document are run from `src/main` on the OIM. See [Tags](#tags) for the supported tags and combinations.

```bash
cd src/main
./omnia.sh --run discovery --tags <tag> [-e <extra_var>=<value>]
```

To run the playbook directly, activate `$OMNIA_VENV_PATH/bin/activate`, source `/etc/profile.d/omnia-env.sh`, and run from the module root so its `ansible.cfg` is loaded:

```bash
cd src/discovery
ansible-playbook playbooks/discovery.yml --tags <tag>
```

### Playbook flows

Discovery uses OME as its only backend. No discovery-mechanism extra variable
is required.

```bash
# Validate the Discovery input only; do not load credentials.
./omnia.sh --run discovery --tags validate

# Load stored credentials or collect any missing OME username/password.
./omnia.sh --run discovery --tags credentials

# Validate input, collect missing credentials, and run OME discovery.
./omnia.sh --run discovery --tags execute
```

Running the playbook without a tag performs the same full flow as `execute`.
The supported prerequisite-only tag is `precheck`; `discovery` is not an
execution-tag alias.

```yaml
- name: Run discovery
  hosts: localhost
  connection: local
  roles:
    - omnia.discovery.discovery_setup
```

### Precheck

Run the prerequisite checks without loading OME credentials or calling the OME
API:

```bash
./omnia.sh --run discovery --tags precheck
```

The precheck validates the resolved `DISCOVERY_DATA_PATH` and verifies TCP
connectivity from the OIM host to `ome_ip` on the standard OME HTTPS port,
443. The same endpoint check runs again before every OME discovery execution.

Discovery reads project data from `DISCOVERY_DATA_PATH`. When that variable is
unset or empty, it defaults to `$OMNIA_DATA_PATH/discovery`.

## Tags

Run one tag at a time; `cleanup` plus `cleanup_credentials` is the only supported pair (from the `discovery.yml` header).

| Tag | Description | Credentials |
|-----|-------------|-------------|
| _(none)_ | Default flow: validate, credentials, execute | Yes |
| `precheck` | Validate the data path and OME TCP/443 reachability | No |
| `validate` | Validate `discovery_config.yml` | No |
| `credentials` | Load or collect missing OME credentials only | Yes |
| `prepare` | Placeholder for a future release | No |
| `execute` | Run BMC discovery through OME | Yes |
| `cleanup` | Remove outputs, runtime logs, and credentials | No |
| `cleanup_credentials` | Remove only the credential file and vault key | No |

## Inputs and Outputs

### Inputs

| File | Description |
|------|-------------|
| `discovery_config.yml` | Discovery configuration, including `ome_ip` (validated by the `validate` tag) |
| `discovery_credentials.yml` | OME credentials, collected by the `credentials` tag and Vault-encrypted |

### Outputs

Written to `$DISCOVERY_DATA_PATH/output/<project>/` (see the [output contract](docs/contracts/output-contract.md)):

| File | Description |
|------|-------------|
| `bmc_pxe_mapping_file_<timestamp>.csv` | PXE mapping; `bmc_pxe_mapping_file.csv` is a symlink to the latest |
| `bmc_discovery_report_<timestamp>.csv` | BMC discovery report |
| `discovery_status.yml` | Discovery status |

Copy the reviewed mapping to Orchestrator's input as `pxe_mapping_file.csv`.

### Functional groups

Discovery assigns `FUNCTIONAL_GROUP_NAME` based on OME static groups:

| Scenario | Result |
|----------|--------|
| Valid OME static group | Uses OME group name |
| Invalid OME static group | Default: `slurm_node_rhel_10_0_aarch64` |
| No OME static group | Default: `slurm_node_rhel_10_0_aarch64` |

**Valid pattern:** `<prefix>_rhel_<major>_<minor>_(x86_64|aarch64)`

Examples:
- ✅ `slurm_node_rhel_10_0_x86_64`
- ✅ `login_node_rhel_10_2_aarch64`
- ❌ `login_node` (missing `_rhel_<version>_<arch>`)

> **Note:** Discovery does not read from catalog. The default functional group
> is a fixed value with no external dependencies.

## Runtime Paths

The resolved component root contains `input/<project>`, `output/<project>`, and `log/<project>`. `domain-init.sh`, setup, validation, credential lookup, output generation, and cleanup all use this root.

### Logs

Discovery keeps execution and runtime logs separate:

- Ansible execution logs: `/var/log/omnia/discovery/*.log`; the main entrypoint
  uses `discovery.log`, while supported direct sub-playbooks use their own log
  files.
- Validation/runtime logs:
  `<DISCOVERY_DATA_PATH>/log/<project>/`

The validation log is named `discovery_validation_<project>.log`. When the
validation module is invoked directly without `log_dir`, it falls back to
`${DISCOVERY_DATA_PATH:-${OMNIA_DATA_PATH:-/opt/omnia}/discovery}/log/`.

## Cleanup

Full cleanup does not remove or create the current project's Discovery output
directory. When the directory exists, cleanup removes every entry inside it
and leaves the empty directory in place. It also resets the current project's
runtime log directory to an empty directory, removes the Discovery Ansible
execution-log directory, and removes the encrypted credential file and vault
key:

```bash
./omnia.sh --run discovery --tags cleanup
```

Preserve the credential file and vault key while still removing all generated
output and runtime-log contents:

```bash
./omnia.sh --run discovery --tags cleanup \
  -e cleanup_credentials=false
```

Preserve the current project's runtime and Ansible execution logs while still
cleaning generated outputs and credentials:

```bash
./omnia.sh --run discovery --tags cleanup \
  -e cleanup_logs=false
```

Other files under the Discovery input project directory are never removed.
To remove only the encrypted credential file and vault key, use:

```bash
./omnia.sh --run discovery --tags cleanup_credentials
```

The explicit `cleanup_credentials` tag always removes the credential artifacts,
even when it is combined with `cleanup` and
`-e cleanup_credentials=false`. Cleanup is limited to the project selected by
`OMNIA_PROJECT_NAME`. Runtime logs are removed by default; preserving them can
block guarded global cleanup until they are removed.

For a complete Omnia reset, run the Discovery cleanup tag first, then run the
guarded global cleanup from `src/main`:

```bash
sudo ./omnia.sh --run discovery --tags cleanup
sudo ./omnia.sh --cleanup --all
```

`src/discovery/domain-init.sh --cleanup` is non-interactive and removes only the
initializer-owned staged input and domain log paths. It does not replace the
Ansible cleanup tag. Both global cleanup modes prompt for `yes`; trusted
automation can add `--skip-approval`.

## Troubleshooting

- Ansible log: `/var/log/omnia/discovery/discovery.log` (top-level playbook execution).
- Validation and runtime logs: `<DISCOVERY_DATA_PATH>/log/<project>/discovery_validation_<project>.log`.
- Run `--tags precheck` to confirm the data path and OME reachability.
- Re-run `sudo ./omnia.sh --init discovery` if inputs or dependencies were not staged.

## Security

- OME credentials are collected by the `credentials` tag and stored Vault-encrypted with a separate vault key; `cleanup` removes both unless `-e cleanup_credentials=false` is passed.
- Cleanup is limited to the project selected by `OMNIA_PROJECT_NAME`.

## Documentation

- [Read the Docs: Discovery guides](https://omnia.readthedocs.io/en/latest/HowTo/discovery/index.html)
- [Architecture](docs/architecture.md)
- [Design](docs/design/discovery-design.md)
- [Input contract](docs/contracts/input-contract.md)
- [Output contract](docs/contracts/output-contract.md)
- [Omnia on GitHub](https://github.com/dell/omnia)
- [Report an issue](https://github.com/dell/omnia/issues)

## License

Apache-2.0
