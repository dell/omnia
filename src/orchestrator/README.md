# Omnia Orchestrator Collection

Ansible Galaxy collection for Dell Omnia Orchestrator — OpenCHAMI deployment,
PXE boot orchestration, image deployment, and Kubernetes and Slurm lifecycle
management for HPC and AI clusters.

**Collection**: `omnia.orchestrator` v2.3.0

## Prerequisites

| Requirement | Supported version | Source |
|-------------|-------------------|--------|
| OIM operating system | RHEL 10.x or Rocky Linux 10.x | Omnia platform support matrix |
| Python | 3.12+ | Omnia virtual environment |
| Ansible | `ansible-core` 2.20+ | `requirements.txt` |
| Podman | 5.0+ | OpenCHAMI and OpenLDAP service deployment |
| `ansible.posix` | 2.0.0 | `requirements.yml` |
| `ansible.utils` | 5.1.1 | `requirements.yml` |
| `community.general` | 10.3.0 | `requirements.yml` |
| `dellemc.openmanage` | 10.0.3+ | `requirements.yml` |

Install through `src/main/omnia.sh --setup-venv` for the supported dependency
set. The collection metadata permits Ansible 2.15 or newer, while the supported
v2.3 runtime dependency file installs Ansible 2.20 or newer.

## Installation

```bash
ansible-galaxy collection install omnia.orchestrator
```

## Quick Start

```bash
# From the repository root
cd src/main

# Configure the host, create the shared virtual environment, and stage inputs.
vi omnia.env
sudo ./omnia.sh -s
source /etc/profile.d/omnia-env.sh

# Edit the staged project inputs.
vi "$ORCHESTRATOR_DATA_PATH/input/$OMNIA_PROJECT_NAME/orchestrator_config.yml"
vi "$ORCHESTRATOR_DATA_PATH/input/$OMNIA_PROJECT_NAME/pxe_mapping_file.csv"

# Validate, prepare services, and provision nodes.
./omnia.sh --run orchestrator --tags validate
./omnia.sh --run orchestrator --tags prepare
./omnia.sh --run orchestrator --tags provision
```

For direct playbook execution, source `/etc/profile.d/omnia-env.sh`, activate
`$OMNIA_VENV_PATH/bin/activate`, and run commands from
`src/orchestrator/playbooks/`.

## Tags

| Tag | Description |
|-----|-------------|
| `precheck` | Generate functional groups and validate inputs, parameters, and boot images |
| `validate` | Validate project input files without contacting deployed services |
| `credentials` | Collect or reuse encrypted Orchestrator credentials |
| `prepare` | Collect credentials, deploy services, and validate readiness |
| `deploy` | Deploy OpenCHAMI and enabled OpenLDAP services and validate them |
| `provision` | Reconcile OpenCHAMI data, configure nodes, and validate provisioning |
| `execute` | Run provisioning and conditional PXE boot |
| `validate-deployment` | Validate deployed OpenCHAMI and OpenLDAP services |
| `pxeboot` | Run iDRAC PXE boot and optional node/cloud-init verification |
| `cleanup` | Remove enabled components and credentials by default |
| `cleanup_credentials` | Remove only the Orchestrator credential file and vault key |
| `upgrade` | Run the opt-in OpenCHAMI and OpenLDAP upgrade workflows |
| `rollback` | Reserved entry point; fails explicitly because rollback is not supported in v2.3 |

With no tag, the playbook runs the default lifecycle through conditional PXE
boot. Cleanup, credential cleanup, upgrade, and rollback are opt-in. The
rollback route is intentionally non-operational in v2.3 because the OpenCHAMI
upgrade is one-way. Unsupported and conflicting tag combinations fail
during setup.

## Input / Output

### Input

| File | Source | Purpose |
|------|--------|---------|
| `orchestrator_config.yml` | Project input | Orchestrator lifecycle and PXE settings |
| `pxe_mapping_file.csv` | Discovery or user | Physical-node, network, and functional-group mapping |
| `omnia_config.yml` | Main domain input | Cluster, service, Slurm, Kubernetes, and storage configuration |
| `network_spec.yml` | Project input | Admin, BMC, InfiniBand, DNS, and DHCP network data |
| `build_status.yml` | Image Build Manager | Kernel, initrd, and rootfs artifact locations |
| `repo_status.yml` | Repository Manager | Repository endpoints, certificates, and staged artifacts |
| Catalog JSON | Catalog workflow | OS metadata and feature resolution |

### Output

| File | Purpose |
|------|---------|
| `.data/functional_groups_config.yml` | Generated functional-group model |
| `orchestrator_state.yml` | Persisted domain state used by standalone phases |
| `provisioning_report.yml` | SMD, Boot Service, and Metadata Service validation result |
| `pxeboot_status.yml` | Per-node PXE and cloud-init verification result |
| `orchestrator_status.yml` | Aggregate provisioning and PXE lifecycle state |
| `failed_nodes.json` | Failure-only PXE report |

See the input and output contracts for field-level specifications.

## Runtime Paths

`ORCHESTRATOR_DATA_PATH` defaults to `$OMNIA_DATA_PATH/orchestrator`.

```text
<ORCHESTRATOR_DATA_PATH>/
+-- input/<project>/       Project inputs and encrypted credentials
+-- output/<project>/      State files, reports, and generated data
+-- log/                   Component lifecycle logs
```

Top-level Ansible logs are written under `/var/log/omnia/orchestrator/`.

## Directory Layout

```text
src/orchestrator/
+-- playbooks/              Lifecycle entry points by phase
+-- roles/                  Domain roles and role documentation
+-- plugins/modules/        Ansible modules
+-- plugins/module_utils/   Shared validation and OpenCHAMI clients
+-- plugins/action/         Controller-side action plugins
+-- input/                  Project input templates
+-- samples/                Upstream contract examples
+-- containers/             Orchestrator-owned container sources
+-- docs/                   Architecture, contracts, and troubleshooting
```

## Included Content

### Roles

| Role | Description |
|------|-------------|
| `omnia.orchestrator.cleanup` | Select and coordinate Orchestrator cleanup components |
| `omnia.orchestrator.orchestrator_setup` | Setup project dirs, upgrade guard, OIM host group |
| `omnia.orchestrator.validate_orchestrator_input` | L1 schema + L2 logic validation |
| `omnia.orchestrator.orchestrator_credentials` | Credential prompting, encryption, vault |
| `omnia.orchestrator.orchestrator_functional_groups` | Generate functional groups from PXE mapping |
| `omnia.orchestrator.orchestrator_validations` | Parameter and environment validation |
| `omnia.orchestrator.orchestrator_common` | Shared task library (S3, auth, vault helpers) |
| `omnia.orchestrator.passwordless_ssh` | SSH key distribution and host list management |
| `omnia.orchestrator.deploy_openchami` | Deploy OpenCHAMI containers on OIM |
| `omnia.orchestrator.deploy_openldap` | Deploy the OpenLDAP container on OIM |
| `omnia.orchestrator.configure_ochami` | Configure OpenCHAMI groups, nodes, Boot Service, and Metadata Service |
| `omnia.orchestrator.generate_inventories` | Generate downstream Ansible and BMC inventories |
| `omnia.orchestrator.k8s_config` | Kubernetes cluster configuration |
| `omnia.orchestrator.slurm_config` | Slurm workload manager configuration |
| `omnia.orchestrator.mount_config` | NFS/shared filesystem mount configuration |
| `omnia.orchestrator.openldap` | OpenLDAP directory service configuration |
| `omnia.orchestrator.idrac_pxe_boot` | Configure Dell iDRAC PXE boot via Redfish API |
| `omnia.orchestrator.precheck_environment` | Validate OIM environment prerequisites |
| `omnia.orchestrator.provision_common` | Prepare common provisioning data and Metadata Service content |
| `omnia.orchestrator.validate_openchami` | Validate OpenCHAMI service and artifact readiness |
| `omnia.orchestrator.validate_preamble` | Prepare shared facts for deployment validation |
| `omnia.orchestrator.validate_provisioning` | Validate provisioned node and service state |
| `omnia.orchestrator.verify_node_registration` | Fresh-boot and cloud-init verification after PXE boot |

### Modules

| Module | Description |
|--------|-------------|
| `omnia.orchestrator.additional_images_collector` | Collect additional container images from the catalog |
| `omnia.orchestrator.bulk_discover_node_specs` | Discover hardware specifications for multiple nodes |
| `omnia.orchestrator.bulk_update_hosts` | Update managed `/etc/hosts` entries across multiple hosts |
| `omnia.orchestrator.validate_orchestrator_config` | Validate orchestrator configuration (L1+L2) |
| `omnia.orchestrator.validate_credentials` | Validate credential input against rules |
| `omnia.orchestrator.fetch_credential_rule` | Fetch validation rules for a credential field |
| `omnia.orchestrator.generate_functional_groups` | Generate functional groups from PXE mapping CSV |
| `omnia.orchestrator.node_boot_status` | Verify fresh boot and cloud-init completion on a provisioned node |
| `omnia.orchestrator.openchami_reconcile` | Resolve persistent SMD identities and reconcile OpenCHAMI state through verified APIs |
| `omnia.orchestrator.slurm_conf` | Parse, merge, and render Slurm configuration |
| `omnia.orchestrator.generate_argon2_password` | Generate Argon2 password hashes |
| `omnia.orchestrator.validate_system_environment` | Validate the OIM system environment |

### Action Plugins

| Plugin | Description |
|--------|-------------|
| `omnia.orchestrator.node_boot_status` | Convert transient SSH transport failures into structured retryable results before invoking the node-local module |

### Callback Plugins

| Plugin | Description |
|--------|-------------|
| `omnia.orchestrator.omnia_default` | Custom stdout callback with clean error formatting |

## Usage

```yaml
- name: Run orchestrator
  hosts: localhost
  connection: local
  roles:
    - role: omnia.orchestrator.orchestrator_setup
      vars:
        openchami_vars_support: true
        oim_group: true
```

## Cleanup and Reset

Full Orchestrator cleanup removes all enabled components and the encrypted
Orchestrator credential file and vault key by default. Set
`cleanup_credentials=false` only when those credentials must be retained:

```bash
cd src/main
sudo ./omnia.sh --run orchestrator --tags cleanup
sudo ./omnia.sh --run orchestrator --tags cleanup \
  -e cleanup_credentials=false
```

`src/orchestrator/domain-init.sh --cleanup` is non-interactive and removes only
initializer-owned staged input and log paths; it does not clean deployed
components. Run the domain cleanup tag first, then use
`sudo ./omnia.sh --cleanup --all` for a guarded global reset. Both global cleanup
modes prompt for `yes`; trusted automation can add `--skip-approval`. Detailed
component cleanup behavior is documented in
[`playbooks/cleanup/README.md`](playbooks/cleanup/README.md).

## Documentation

| Document | Description |
|----------|-------------|
| [`docs/architecture.md`](docs/architecture.md) | System context, lifecycle phases, tag behavior, and service interactions |
| [`docs/hardware-identity-mapping.md`](docs/hardware-identity-mapping.md) | Persistent Service Tag-to-XNAME identity and reconciliation behavior |
| [`docs/troubleshooting.md`](docs/troubleshooting.md) | Common failures, recovery guidance, logs, and diagnostic commands |
| [`docs/contracts/input-contract.md`](docs/contracts/input-contract.md) | Input file and upstream dependency specifications |
| [`docs/contracts/output-contract.md`](docs/contracts/output-contract.md) | Output artifact and lifecycle-status specifications |
| [`containers/omnia_auth/README.md`](containers/omnia_auth/README.md) | OpenLDAP authentication container contents, build, and runtime behavior |

## License

Apache-2.0

## Links

- [Omnia GitHub](https://github.com/dell/omnia)
- [Documentation](https://github.com/dell/omnia/tree/main/docs)
- [Issues](https://github.com/dell/omnia/issues)
