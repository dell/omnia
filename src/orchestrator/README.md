# Omnia Orchestrator Collection

Ansible Galaxy collection for Dell Omnia Orchestrator — OpenCHAMI deployment, PXE boot orchestration, image deployment, and lifecycle management (Kubernetes, Slurm, telemetry) for HPC and AI clusters.

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
| `omnia.orchestrator.orchestrator_setup` | Setup project dirs, upgrade guard, OIM host group |
| `omnia.orchestrator.validate_orchestrator_input` | L1 schema + L2 logic validation |
| `omnia.orchestrator.orchestrator_credentials` | Credential prompting, encryption, vault |
| `omnia.orchestrator.orchestrator_functional_groups` | Generate functional groups from PXE mapping |
| `omnia.orchestrator.orchestrator_validations` | Parameter and environment validation |
| `omnia.orchestrator.orchestrator_common` | Shared task library (S3, auth, vault helpers) |
| `omnia.orchestrator.passwordless_ssh` | SSH key distribution and host list management |
| `omnia.orchestrator.deploy_openchami` | Deploy OpenCHAMI containers on OIM |
| `omnia.orchestrator.configure_ochami` | Configure OpenCHAMI groups, nodes, BSS |
| `omnia.orchestrator.k8s_config` | Kubernetes cluster configuration |
| `omnia.orchestrator.slurm_config` | Slurm workload manager configuration |
| `omnia.orchestrator.mount_config` | NFS/shared filesystem mount configuration |
| `omnia.orchestrator.openldap` | OpenLDAP directory service configuration |
| `omnia.orchestrator.telemetry` | Telemetry and monitoring stack deployment |

### Modules

| Module | Description |
|--------|-------------|
| `omnia.orchestrator.validate_orchestrator_config` | Validate orchestrator configuration (L1+L2) |
| `omnia.orchestrator.validate_credentials` | Validate credential input against rules |
| `omnia.orchestrator.fetch_credential_rule` | Fetch validation rules for a credential field |
| `omnia.orchestrator.generate_functional_groups` | Generate functional groups from PXE mapping CSV |
| `omnia.orchestrator.generate_xname_in_mapping_file` | Generate xnames in mapping file |
| `omnia.orchestrator.slurm_conf` | Parse, merge, and render Slurm configuration |
| `omnia.orchestrator.generate_argon2_password` | Generate Argon2 password hashes |
| `omnia.orchestrator.fetch_telemetry_status` | Fetch telemetry status from config |

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
        omnia_metadata_support: true
        oim_group: true
```

## License

Apache-2.0

## Links

- [Omnia GitHub](https://github.com/dell/omnia)
- [Documentation](https://github.com/dell/omnia/tree/main/docs)
- [Issues](https://github.com/dell/omnia/issues)
