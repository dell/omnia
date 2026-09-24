# Omnia Orchestrator Collection

Ansible Galaxy collection for Dell Omnia Orchestrator — OpenCHAMI deployment,
PXE boot orchestration, image deployment, and Kubernetes and Slurm lifecycle
management for HPC and AI clusters.

## Requirements

- Ansible >= 2.14
- Python >= 3.9
- `community.general` collection >= 5.0.0

## Installation

```bash
ansible-galaxy collection install omnia.orchestrator
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
| `omnia.orchestrator.openchami_reconcile` | Resolve persistent SMD identities and reconcile OpenCHAMI state through verified APIs |
| `omnia.orchestrator.slurm_conf` | Parse, merge, and render Slurm configuration |
| `omnia.orchestrator.generate_argon2_password` | Generate Argon2 password hashes |
| `omnia.orchestrator.validate_system_environment` | Validate the OIM system environment |

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

## License

Apache-2.0

## Links

- [Omnia GitHub](https://github.com/dell/omnia)
- [Documentation](https://github.com/dell/omnia/tree/main/docs)
- [Issues](https://github.com/dell/omnia/issues)
