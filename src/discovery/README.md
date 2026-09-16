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
| `omnia.discovery.precheck_environment` | Validate the data path and OME HTTPS endpoint readiness |
| `omnia.discovery.validate_discovery_input` | L1 schema + L2 logic validation |
| `omnia.discovery.discovery_credentials` | Credential prompting, encryption, vault |
| `omnia.discovery.discovery_common` | Shared task library (vault and OME endpoint helpers) |
| `omnia.discovery.ome_discovery` | OME-specific discovery, inventory, PXE mapping |
| `omnia.discovery.discovery_cleanup` | Project output and credential cleanup |

### Modules

| Module | Description |
|--------|-------------|
| `omnia.discovery.validate_discovery_config` | Validate discovery configuration (L1+L2) |
| `omnia.discovery.validate_system_environment` | Validate selected OIM environment values and paths; Discovery precheck uses its data-path check |
| `omnia.discovery.validate_credentials` | Validate credential input against rules |
| `omnia.discovery.ome_server_inventory` | Collect server inventory from OME |
| `omnia.discovery.generate_pxe_mapping` | Generate PXE mapping CSV from inventory |
| `omnia.discovery.generate_discovery_report` | Generate BMC discovery report |

### Callback Plugins

| Plugin | Description |
|--------|-------------|
| `omnia.discovery.omnia_default` | Custom stdout callback with clean error formatting |

## Usage

### Environment variables

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

### Playbook flows

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

### Precheck

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

## License

Apache-2.0

## Links

- [Omnia GitHub](https://github.com/dell/omnia)
- [Documentation](https://github.com/dell/omnia/tree/main/docs)
- [Issues](https://github.com/dell/omnia/issues)
