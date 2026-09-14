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
| `omnia.discovery.discovery_cleanup` | Project output and credential cleanup |

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

### Cleanup

Full cleanup does not remove or create the current project's Discovery output
directory. When the directory exists, cleanup removes every entry inside it
and leaves the empty directory in place. It also removes the encrypted
credential file and vault key:

```bash
ansible-playbook playbooks/discovery.yml --tags cleanup
```

Preserve the credential file and vault key while still removing all generated
output contents:

```bash
ansible-playbook playbooks/discovery.yml --tags cleanup \
  -e cleanup_credentials=false
```

Other files under the Discovery input project directory are never removed.
To remove only the encrypted credential file and vault key, use:

```bash
ansible-playbook playbooks/discovery.yml --tags cleanup_credentials
```

The explicit `cleanup_credentials` tag always removes the credential artifacts,
even when it is combined with `cleanup` and
`-e cleanup_credentials=false`. Cleanup is limited to the project selected by
`OMNIA_PROJECT_NAME`; Discovery log files are preserved.

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

## License

Apache-2.0

## Links

- [Omnia GitHub](https://github.com/dell/omnia)
- [Documentation](https://github.com/dell/omnia/tree/main/docs)
- [Issues](https://github.com/dell/omnia/issues)
