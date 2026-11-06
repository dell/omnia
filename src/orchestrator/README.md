# Omnia Orchestrator

Orchestrator (`omnia.orchestrator`) turns built images, repository information, and a PXE mapping into provisioned cluster nodes. It deploys OpenCHAMI (and optional OpenLDAP) on the OIM, reconciles node identity and metadata, configures Slurm and service Kubernetes nodes, and optionally PXE boots physical nodes through iDRAC.

## Overview

Orchestrator provides:

- OpenCHAMI deployment and validation on the OIM (Boot Service, Metadata Service, SMD)
- Optional OpenLDAP deployment for cluster authentication
- Functional-group generation from the PXE mapping, and Metadata Service reconciliation per node
- Persistent Service Tag-to-XNAME identity resolution through SMD Hardware Inventory
- Slurm, Kubernetes, shared-mount, and passwordless-SSH configuration for provisioned nodes
- iDRAC PXE boot, with fresh-boot and cloud-init verification (`node_registration_*` controls)
- Provisioning, lifecycle, and PXE failure reports (`provisioning_report.yml`, `orchestrator_status.yml`, `failed_nodes.json`)

### Related modules

| Direction | Module | Contract |
|-----------|--------|----------|
| Upstream | Image Build Manager | `build_status.yml` (kernel, initrd, rootfs locations) |
| Upstream | Repository Manager | `repo_status.yml` (repository endpoints and certificates) |
| Upstream | Discovery or operator | `pxe_mapping_file.csv` |
| Downstream | Telemetry | Provisioned service Kubernetes cluster |

Orchestrator does not build images, discover hardware, synchronize repositories, or deploy telemetry; those belong to the modules above.

## Architecture

### Directory layout

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

### Roles

| Role | Description |
|------|-------------|
| `omnia.orchestrator.cleanup` | Select and coordinate Orchestrator cleanup components |
| `omnia.orchestrator.orchestrator_setup` | Setup project dirs, OIM host group |
| `omnia.orchestrator.validate_orchestrator_input` | L1 schema + L2 logic validation |
| `omnia.orchestrator.orchestrator_credentials` | Credential prompting, encryption, vault |
| `omnia.orchestrator.orchestrator_functional_groups` | Generate functional groups from PXE mapping |
| `omnia.orchestrator.orchestrator_validations` | Parameter and environment validation |
| `omnia.orchestrator.orchestrator_common` | Shared task library (S3, auth, vault helpers) |
| `omnia.orchestrator.passwordless_ssh` | SSH key distribution and host list management |
| `omnia.orchestrator.deploy_openchami` | Deploy OpenCHAMI containers on OIM |
| `omnia.orchestrator.deploy_openldap` | Deploy the OpenLDAP container on OIM |
| `omnia.orchestrator.generate_inventories` | Generate downstream Ansible and BMC inventories |
| `omnia.orchestrator.k8s_config` | Kubernetes cluster configuration |
| `omnia.orchestrator.slurm_config` | Slurm workload manager configuration |
| `omnia.orchestrator.mount_config` | NFS/shared filesystem mount configuration |
| `omnia.orchestrator.openldap` | OpenLDAP directory service configuration |
| `omnia.orchestrator.idrac_pxe_boot` | Configure Dell iDRAC PXE boot via Redfish API |
| `omnia.orchestrator.precheck_environment` | Validate OIM environment prerequisites |
| `omnia.orchestrator.provision_common` | Prepare common provisioning data and Metadata Service content |
| `omnia.orchestrator.orchestrator_node_topology` | Publish shared node and functional-group topology facts |
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
| `omnia.orchestrator.validate_system_environment` | Validate the OIM system environment |

### Action plugins

| Plugin | Description |
|--------|-------------|
| `omnia.orchestrator.node_boot_status` | Convert transient SSH transport failures into structured retryable results before invoking the node-local module |

### Callback plugins

| Plugin | Description |
|--------|-------------|
| `omnia.orchestrator.omnia_default` | Custom stdout callback with clean error formatting |

## Prerequisites

| Requirement | Minimum | Notes |
|-------------|---------|-------|
| OS | RHEL 10.x, Rocky 10.x | Omnia platform support matrix |
| Python | 3.12+ | Shared Omnia virtual environment |
| Ansible | ansible-core 2.20+ | `requirements.txt` |
| Podman | 5.0+ | OpenCHAMI and OpenLDAP service deployment |
| `ansible.posix` | 2.0.0 | `requirements.yml` |
| `ansible.utils` | 5.1.1 | `requirements.yml` |
| `community.general` | 10.3.0 | `requirements.yml` |
| `dellemc.openmanage` | 10.0.3+ | `requirements.yml` |

Install through `src/main/omnia.sh --setup-venv` for the supported dependency
set. The collection metadata permits Ansible 2.15 or newer, while the supported
v2.3 runtime dependency file installs Ansible 2.20 or newer.

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
sudo ./omnia.sh --init orchestrator
```

## Configuration

| Variable | Default | Description |
|----------|---------|-------------|
| `OMNIA_DATA_PATH` | `/opt/omnia` | Root Omnia data directory |
| `OMNIA_PROJECT_NAME` | `project_default` | Active input/output project |
| `ORCHESTRATOR_DATA_PATH` | `$OMNIA_DATA_PATH/orchestrator` | Optional module data-path override |

Edit the staged project inputs before running (see [Inputs and Outputs](#inputs-and-outputs)):

```bash
vi "$ORCHESTRATOR_DATA_PATH/input/$OMNIA_PROJECT_NAME/orchestrator_config.yml"
vi "$ORCHESTRATOR_DATA_PATH/input/$OMNIA_PROJECT_NAME/pxe_mapping_file.csv"
```

## Usage

Run this module through `omnia.sh`; it activates the virtual environment and runs `src/orchestrator/playbooks/orchestrator.yml`. All `./omnia.sh` commands in this document are run from `src/main` on the OIM. See [Tags](#tags) for the supported tags and combinations.

```bash
cd src/main
./omnia.sh --run orchestrator --tags <tag> [-e <extra_var>=<value>]
```

To run the playbook directly, activate `$OMNIA_VENV_PATH/bin/activate`, source `/etc/profile.d/omnia-env.sh`, and run from the module root so its `ansible.cfg` is loaded:

```bash
cd src/orchestrator
ansible-playbook playbooks/orchestrator.yml --tags <tag>
```

Typical flow:

```bash
cd src/main
./omnia.sh --run orchestrator --tags validate
./omnia.sh --run orchestrator --tags prepare
./omnia.sh --run orchestrator --tags provision
```

Running without a tag runs the default lifecycle through conditional PXE boot.

### Ansible role usage

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

### Upgrading from Omnia 2.2

For deployments moving from Omnia 2.2:

- Service Tag is now persisted against a permanent XNAME in SMD Hardware
  Inventory; CSV row order no longer controls node identity.
- Metadata Service resources are reconciled in place with project ownership,
  and changed nodes remain `reprovision_required` until a verified fresh boot.
- PXE completion uses the `node_registration_*` controls and verifies SSH boot
  freshness plus structured cloud-init state.
- Lifecycle automation should consume `provisioning_report.yml`, the aggregate
  `orchestrator_status.yml`, and `failed_nodes.json` for PXE failures.

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
| `verify_node_registration` | Verify pending manually or hypervisor-booted nodes over SSH without iDRAC |
| `cleanup` | Remove enabled components and credentials by default |
| `cleanup_credentials` | Remove only the Orchestrator credential file and vault key |

With no tag, the playbook runs the default lifecycle through conditional PXE
boot. Cleanup and credential cleanup are opt-in. Unsupported and conflicting
tag combinations fail during setup.

After an operator or hypervisor boots pending nodes, verify and record their
fresh boot and cloud-init completion with:

```bash
./omnia.sh --run orchestrator --tags verify_node_registration
```

For a node whose Orchestrator-triggered PXE attempt failed, first allow the
`pxeboot` workflow to finish and write `orchestrator_status.yml`. Then boot the
node manually or through the hypervisor and run the verification tag. The
external verifier requires a boot newer than the persisted lifecycle status;
a boot started before the failed PXE workflow finishes is treated as stale.

## Inputs and Outputs

### Inputs

| File | Source | Purpose |
|------|--------|---------|
| `orchestrator_config.yml` | Project input | Orchestrator lifecycle and PXE settings |
| `pxe_mapping_file.csv` | Discovery or user | Physical-node, network, and functional-group mapping |
| `omnia_config.yml` | Main domain input | Cluster, service, Slurm, Kubernetes, and storage configuration |
| `network_spec.yml` | Project input | Admin, BMC, InfiniBand, DNS, and DHCP network data |
| `build_status.yml` | Image Build Manager | Kernel, initrd, and rootfs artifact locations |
| `repo_status.yml` | Repository Manager | Repository endpoints, certificates, and staged artifacts |
| Catalog JSON | Catalog workflow | OS metadata and feature resolution |

### Outputs

| File | Purpose |
|------|---------|
| `.data/functional_groups_config.yml` | Generated functional-group model |
| `orchestrator_state.yml` | Persisted domain state used by standalone phases |
| `provisioning_report.yml` | SMD, Boot Service, and Metadata Service validation result |
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

## Cleanup

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

## Troubleshooting

- Ansible log: `/var/log/omnia/orchestrator/orchestrator.log` (top-level playbook execution).
- Aggregate state: `orchestrator_status.yml`, `provisioning_report.yml`, and `failed_nodes.json` in the project output directory.
- Re-run `sudo ./omnia.sh --init orchestrator` if inputs or dependencies were not staged.
- [docs/troubleshooting.md](docs/troubleshooting.md) lists common failures, recovery guidance, and diagnostic commands.

## Security

- Orchestrator credentials are collected by the `credentials` tag and stored Vault-encrypted; `cleanup` removes the file and vault key unless `-e cleanup_credentials=false` is passed.
- Provisioning-password hashes use a stable project-and-cluster salt, and plaintext is passed to OpenSSL over standard input rather than as a process argument.

## Documentation

- [Read the Docs: Orchestrator guides](https://omnia.readthedocs.io/en/latest/HowTo/orchestrator/index.html)
- [Architecture](docs/architecture.md)
- [Hardware identity mapping](docs/hardware-identity-mapping.md)
- [Troubleshooting](docs/troubleshooting.md)
- [Input contract](docs/contracts/input-contract.md)
- [Output contract](docs/contracts/output-contract.md)
- [Cleanup playbooks](playbooks/cleanup/README.md)
- [OpenLDAP authentication container](containers/omnia_auth/README.md)
- [Omnia on GitHub](https://github.com/dell/omnia)
- [Report an issue](https://github.com/dell/omnia/issues)

## License

Apache-2.0
