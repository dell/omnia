# Omnia Discovery Collection

Ansible Galaxy collection for Dell Omnia Discovery — BMC discovery via OME, PXE mapping generation, and inventory reporting for HPC and AI clusters.

## Requirements

- Ansible >= 2.14
- Python >= 3.9
- `community.general` collection >= 5.0.0

## Installation

```bash
ansible-galaxy collection install omnia.discovery
```

## Included Content

### Roles

| Role | Description |
|------|-------------|
| `omnia.discovery.discovery_setup` | Setup project dirs, config loading, tag validation |
| `omnia.discovery.validate_discovery_input` | L1 schema + L2 logic validation |
| `omnia.discovery.discovery_credentials` | Credential prompting, encryption, vault |
| `omnia.discovery.discovery_common` | Shared task library (vault helpers) |
| `omnia.discovery.ome_discovery` | OME-specific discovery, inventory, PXE mapping |

### Modules

| Module | Description |
|--------|-------------|
| `omnia.discovery.validate_discovery_config` | Validate discovery configuration (L1+L2) |
| `omnia.discovery.validate_credentials` | Validate credential input against rules |
| `omnia.discovery.ome_server_inventory` | Collect server inventory from OME |
| `omnia.discovery.generate_pxe_mapping` | Generate PXE mapping CSV from inventory |
| `omnia.discovery.generate_discovery_report` | Generate BMC discovery report |

### Callback Plugins

| Plugin | Description |
|--------|-------------|
| `omnia.discovery.omnia_default` | Custom stdout callback with clean error formatting |

## Usage

```yaml
- name: Run discovery
  hosts: localhost
  connection: local
  roles:
    - omnia.discovery.discovery_setup
```

## License

Apache-2.0

## Links

- [Omnia GitHub](https://github.com/dell/omnia)
- [Documentation](https://github.com/dell/omnia/tree/main/docs)
- [Issues](https://github.com/dell/omnia/issues)
