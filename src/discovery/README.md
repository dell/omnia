# Omnia Discovery

**Collection**: `omnia.discovery` v2.3.0

Discovery is an Ansible Galaxy collection that discovers bare-metal nodes via
Dell OpenManage Enterprise (OME) and produces mapping and report artifacts for
cluster provisioning. It does not provision or register nodes itself -- those
responsibilities belong to the Orchestrator domain.

## Overview

The sections below use the common Omnia domain README structure. The detailed
reference preserves the complete Discovery-specific operational information.

## Architecture and Dependencies

Discovery runs on the OIM, queries Dell OME, and produces operator-reviewed
mapping artifacts consumed explicitly by Orchestrator.

## Prerequisites

Complete Main setup, configure OME connectivity, and stage the project inputs
before running Discovery.

## Installation and Initialization

```bash
cd <OMNIA_SOURCE_PATH>/src/main
./omnia.sh --setup-venv
source /etc/profile.d/omnia-env.sh
```

## Configuration and Credentials

Configure `discovery_config.yml` and `network_spec.yml`. OME credentials are
stored in the project-scoped encrypted Discovery credential file.

## Run with omnia.sh

Use `omnia.sh` for the supported customer-facing workflow. It activates the
shared Omnia virtual environment, selects the Discovery entry playbook, applies
the installed environment, and forwards tags and extra Ansible arguments.

### Complete Discovery workflow with omnia.sh

```bash
cd <OMNIA_SOURCE_PATH>/src/main
./omnia.sh --run discovery
```

The untagged command runs setup, validation, credential handling, and OME
inventory discovery. Run one lifecycle tag at a time for a scoped operation:

```bash
# Check the OIM data path and OME TCP/443 reachability without credentials.
./omnia.sh --run discovery --tags precheck

# Validate discovery_config.yml and network_spec.yml without contacting OME.
./omnia.sh --run discovery --tags validate

# Create or update the encrypted OME credential file.
./omnia.sh --run discovery --tags credentials

# Run the reserved preparation phase.
./omnia.sh --run discovery --tags prepare

# Validate, load credentials, query OME, and generate Discovery outputs.
./omnia.sh --run discovery --tags execute

# Remove generated output, logs, and credentials using the default policy.
./omnia.sh --run discovery --tags cleanup

# Remove only the encrypted credential file and Vault key.
./omnia.sh --run discovery --tags cleanup_credentials
```

Pass supported extra variables after the domain and tag arguments:

```bash
# Preserve encrypted credentials during full Discovery cleanup.
./omnia.sh --run discovery --tags cleanup -e cleanup_credentials=false

# Preserve runtime and Ansible execution logs during cleanup.
./omnia.sh --run discovery --tags cleanup -e cleanup_logs=false
```

## Run with ansible-playbook

Use the direct Ansible method for development, debugging, or component-level
operation. Initialize Omnia first, load the installed environment, activate the
shared virtual environment, and select the domain Ansible configuration.

### Prepare the direct Ansible environment

```bash
source /etc/profile.d/omnia-env.sh
source "$OMNIA_VENV_PATH/bin/activate"
cd <OMNIA_SOURCE_PATH>/src/discovery/playbooks
export ANSIBLE_CONFIG=../ansible.cfg
```

### Complete Discovery workflow with ansible-playbook

```bash
ansible-playbook discovery.yml
```

Run the same scoped lifecycle operations directly:

```bash
# Check the OIM data path and OME TCP/443 reachability without credentials.
ansible-playbook discovery.yml --tags precheck

# Validate Discovery configuration without contacting OME.
ansible-playbook discovery.yml --tags validate

# Create or update encrypted OME credentials.
ansible-playbook discovery.yml --tags credentials

# Run the reserved preparation phase.
ansible-playbook discovery.yml --tags prepare

# Query OME and generate the mapping, report, and status artifacts.
ansible-playbook discovery.yml --tags execute

# Remove generated output, logs, and credentials using the default policy.
ansible-playbook discovery.yml --tags cleanup

# Remove only the Discovery credential file and Vault key.
ansible-playbook discovery.yml --tags cleanup_credentials
```

Pass cleanup controls with Ansible extra variables:

```bash
ansible-playbook discovery.yml --tags cleanup \
  -e cleanup_credentials=false

ansible-playbook discovery.yml --tags cleanup \
  -e cleanup_logs=false
```

Do not combine lifecycle tags except for the explicitly supported
`cleanup,cleanup_credentials` combination. The Discovery setup role rejects
unsupported tags and conflicting combinations before execution.

## Tags and Workflows

Discovery supports `precheck`, `validate`, `credentials`, `prepare`, `execute`,
`cleanup`, and `cleanup_credentials`, subject to entry-playbook validation.

## Roles, Modules, and Plugins

Discovery includes setup, precheck, validation, credential, OME execution,
report-generation, mapping-generation, cleanup, and callback components.

## Inputs, Outputs, and Runtime Paths

Inputs, generated mappings, reports, status, credentials, and logs are scoped
by `DISCOVERY_DATA_PATH` and `OMNIA_PROJECT_NAME`.

## Cleanup

Use the scoped cleanup tags before guarded global cleanup. Preservation options
for credentials and logs are documented in the detailed reference.

## Security

Credentials remain encrypted with Ansible Vault, sensitive callback output is
redacted, and generated mapping data requires operator review.

## Troubleshooting and Verification

Verify OME reachability, generated server counts, mapping fields, report data,
and `discovery_status.yml` before passing data to Orchestrator.

## Documentation and Support

Read the domain documentation table and linked contracts near the end of this
README for field-level and architectural details.

## Detailed Domain Reference

### Overview

Discovery automates hardware inventory discovery for HPC and AI clusters by:

- Connecting to Dell OpenManage Enterprise (OME) to query BMC endpoints
- Collecting server inventory including hardware specifications and network information
- Generating PXE mapping files that map physical nodes to functional groups and network configurations
- Creating discovery reports for operator review and validation
- Assigning functional group names based on OME static groups or default patterns

#### What Discovery Does

Discovery is a **read-only** domain that:
- Discovers BMC endpoints through the OME API
- Generates `pxe_mapping_file.csv` for downstream consumption by Orchestrator
- Produces discovery reports with inventory details
- Validates OME connectivity and data path readiness

Discovery does **not**:
- Provision nodes
- Register nodes in OpenCHAMI
- Configure network settings
- Install operating systems

---

### Requirements

- Ansible >= 2.14
- Python >= 3.9
- `community.general` collection >= 5.0.0

### Installation

```bash
ansible-galaxy collection install omnia.discovery
```

---

### Included Content

#### Roles

| Role | Description |
|------|-------------|
| `omnia.discovery.discovery_setup` | Setup project dirs, config loading, tag validation |
| `omnia.discovery.precheck_environment` | Validate the data path and OME HTTPS endpoint readiness |
| `omnia.discovery.validate_discovery_input` | L1 schema + L2 logic validation |
| `omnia.discovery.discovery_credentials` | Credential prompting, encryption, vault |
| `omnia.discovery.discovery_common` | Shared task library (vault and OME endpoint helpers) |
| `omnia.discovery.ome_discovery` | OME-specific discovery, inventory, PXE mapping |
| `omnia.discovery.discovery_cleanup` | Project output, runtime-log, and credential cleanup |

#### Modules

| Module | Description |
|--------|-------------|
| `omnia.discovery.validate_discovery_config` | Validate discovery configuration (L1+L2) |
| `omnia.discovery.validate_system_environment` | Validate selected OIM environment values and paths; Discovery precheck uses its data-path check |
| `omnia.discovery.validate_credentials` | Validate credential input against rules |
| `omnia.discovery.ome_server_inventory` | Collect server inventory from OME |
| `omnia.discovery.generate_pxe_mapping` | Generate PXE mapping CSV from inventory |
| `omnia.discovery.generate_discovery_report` | Generate BMC discovery report |

#### Callback Plugins

| Plugin | Description |
|--------|-------------|
| `omnia.discovery.omnia_default` | Custom stdout callback with clean error formatting |

---

### Usage

#### Environment Variables

Discovery follows the Image Build Manager component-path pattern:

| Variable | Default | Description |
|----------|---------|-------------|
| `OMNIA_DATA_PATH` | `/opt/omnia` | Root for shared Omnia data and the default Discovery path |
| `OMNIA_PROJECT_NAME` | `project_default` | Active input/output project name |
| `DISCOVERY_DATA_PATH` | `${OMNIA_DATA_PATH}/discovery` | Optional Discovery component data-path override |

The resolved component root contains `input/<project>`, `output/<project>`, and
`log/<project>`. `domain-init.sh`, playbook setup, validation, credential
lookup, output generation, and Discovery cleanup all use the same resolved
root.

#### Playbook Flows

Discovery uses OME as its only backend. No discovery-mechanism extra variable
is required.

```bash
# Validate the Discovery input only; do not load credentials.
ansible-playbook playbooks/discovery.yml --tags validate

# Load stored credentials or collect any missing OME username/password.
ansible-playbook playbooks/discovery.yml --tags credentials

# Validate input, collect missing credentials, and run OME discovery.
ansible-playbook playbooks/discovery.yml --tags execute
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

#### Precheck

Run the prerequisite checks without loading OME credentials or calling the OME
API:

```bash
ansible-playbook playbooks/discovery.yml --tags precheck
```

The precheck validates the resolved `DISCOVERY_DATA_PATH` and verifies TCP
connectivity from the OIM host to `ome_ip` on the standard OME HTTPS port,
443. The same endpoint check runs again before every OME discovery execution.

Discovery reads project data from `DISCOVERY_DATA_PATH`. When that variable is
unset or empty, it defaults to `$OMNIA_DATA_PATH/discovery`.

#### Cleanup

Full cleanup does not remove or create the current project's Discovery output
directory. When the directory exists, cleanup removes every entry inside it
and leaves the empty directory in place. It also resets the current project's
runtime log directory to an empty directory, removes the Discovery Ansible
execution-log directory, and removes the encrypted credential file and vault
key:

```bash
ansible-playbook playbooks/discovery.yml --tags cleanup
```

Preserve the credential file and vault key while still removing all generated
output and runtime-log contents:

```bash
ansible-playbook playbooks/discovery.yml --tags cleanup \
  -e cleanup_credentials=false
```

Preserve the current project's runtime and Ansible execution logs while still
cleaning generated outputs and credentials:

```bash
ansible-playbook playbooks/discovery.yml --tags cleanup \
  -e cleanup_logs=false
```

Other files under the Discovery input project directory are never removed.
To remove only the encrypted credential file and vault key, use:

```bash
ansible-playbook playbooks/discovery.yml --tags cleanup_credentials
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

---

#### Functional Groups

Discovery assigns `FUNCTIONAL_GROUP_NAME` based on OME static groups:

| Scenario | Result |
|----------|--------|
| Valid OME static group | Uses OME group name |
| Invalid OME static group | Default: `slurm_node_rhel_10_0_aarch64` |
| No OME static group | Default: `slurm_node_rhel_10_0_aarch64` |

**Valid pattern:** `<prefix>_rhel_<major>_<minor>_(x86_64|aarch64)`

Examples:
- `slurm_node_rhel_10_0_x86_64`
- `login_node_rhel_10_2_aarch64`
- `login_node` (missing `_rhel_<version>_<arch>`) -- invalid

> **Note:** Discovery does not read from catalog. The default functional group
> is a fixed value with no external dependencies.

---

#### Discovery Execution Flow

A full Discovery run performs the following ordered operations:

1. Resolve `OMNIA_DATA_PATH`, `DISCOVERY_DATA_PATH`, and
   `OMNIA_PROJECT_NAME`.
2. Create the project-scoped input, output, and runtime-log directories.
3. Validate the requested lifecycle tag and reject unsupported combinations.
4. Load `discovery_config.yml` and `network_spec.yml` from the active project.
5. Run schema validation followed by cross-field semantic validation.
6. Load the encrypted credential file or prompt for missing OME credentials.
7. Verify that the configured OME endpoint is reachable over HTTPS.
8. Query OME for managed server and network-interface inventory.
9. Resolve OME static-group membership into functional-group assignments.
10. Select the administration, BMC, and InfiniBand interface data.
11. Generate the timestamped PXE mapping and stable latest-file link.
12. Generate the timestamped BMC discovery report for operator review.
13. Write `discovery_status.yml` with the execution result and artifact paths.

Discovery does not automatically copy its mapping into Orchestrator. The
operator must review the generated data and copy the accepted mapping into the
active Orchestrator project. This review boundary prevents unverified hardware
or network data from directly entering a provisioning workflow.

#### Generated Artifacts

Discovery writes artifacts below
`$DISCOVERY_DATA_PATH/output/$OMNIA_PROJECT_NAME/`:

| Artifact | Description |
|----------|-------------|
| `bmc_pxe_mapping_file_<timestamp>.csv` | Immutable mapping produced by one OME query |
| `bmc_pxe_mapping_file.csv` | Link to the newest timestamped mapping |
| `bmc_discovery_report_<timestamp>.csv` | Point-in-time BMC and NIC inventory report |
| `discovery_status.yml` | Machine-readable result, counts, paths, timestamp, and failure details |

The PXE mapping contains the functional group, OME group, service tag, parent
service tag, hostname, administration MAC and IP, BMC MAC and IP, and
InfiniBand interface and IP. Fields that cannot be resolved remain visible for
operator correction; Discovery does not invent provisioning identities.

Before using the mapping, verify at minimum:

- Every intended server appears exactly once.
- Service tags and hostnames match the physical inventory.
- `ADMIN_MAC` identifies the interface connected to the PXE network.
- Administration and BMC addresses belong to the expected subnets.
- Functional-group names use the required OS/version/architecture suffix.
- InfiniBand interface data is present when the target workload requires it.
- OME static-group assignments match the intended cluster role.

Copy an accepted mapping into the Orchestrator project explicitly:

```bash
cp "$DISCOVERY_DATA_PATH/output/$OMNIA_PROJECT_NAME/bmc_pxe_mapping_file.csv" \
  "$ORCHESTRATOR_DATA_PATH/input/$OMNIA_PROJECT_NAME/pxe_mapping_file.csv"
```

#### Logs

Discovery keeps execution and runtime logs separate:

- Ansible execution logs: `/var/log/omnia/discovery/*.log`; the main entrypoint
  uses `discovery.log`, while supported direct sub-playbooks use their own log
  files.
- Validation/runtime logs:
  `<DISCOVERY_DATA_PATH>/log/<project>/`

The validation log is named `discovery_validation_<project>.log`. When the
validation module is invoked directly without `log_dir`, it falls back to
`${DISCOVERY_DATA_PATH:-${OMNIA_DATA_PATH:-/opt/omnia}/discovery}/log/`.

---

### Documentation

| Document | Description |
|----------|-------------|
| [Discovery Documentation](https://omnia.readthedocs.io/en/latest/HowTo/discovery/index.html) | Read the Docs user guide |
| [Architecture](docs/architecture.md) | Discovery architecture |
| [Input Contract](docs/contracts/input-contract.md) | Input file specifications |
| [Output Contract](docs/contracts/output-contract.md) | Output file specifications |

### License

Apache-2.0

### Links

- [Omnia GitHub](https://github.com/dell/omnia)
- [Documentation](https://omnia.readthedocs.io/en/latest/HowTo/discovery/index.html)
- [Issues](https://github.com/dell/omnia/issues)
