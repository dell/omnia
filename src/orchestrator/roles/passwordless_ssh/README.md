# passwordless_ssh

Builds category-specific cluster host lists and configures OIM SSH access used
by provisioning and node-to-node automation.

## What It Does

- Reads the PXE mapping on localhost and derives Kubernetes and Slurm hostname
  lists plus network wildcard patterns.
- Generates the OIM SSH key pair when absent.
- Adds managed cluster host entries to the OIM hosts file.
- Writes SSH host matching rules using the derived names and networks.
- Can rebuild patterns from per-category OpenCHAMI `nodes_*.yaml` files, with a
  consolidated `nodes.yaml` fallback.

The caller invokes the same role on localhost to build facts and on the OIM to
apply SSH configuration.

## Requirements

- Resolved PXE mapping file with hostnames and admin IP addresses.
- Root access to the OIM SSH configuration and managed hosts file.
- OIM and localhost facts established by the provisioning preamble.

## Role Variables

| Variable | Purpose |
|----------|---------|
| `k8s_fg_pattern` | Select Kubernetes functional groups |
| `slurm_fg_pattern` | Select Slurm and login functional groups |
| `oim_ssh_config_path` | Managed SSH client configuration path |

See `vars/main.yml` for required and optional group definitions.

## Dependencies

No automatic dependency is declared in `meta/main.yml`.

## Example

```yaml
- hosts: localhost
  roles:
    - passwordless_ssh

- hosts: oim
  roles:
    - passwordless_ssh
```

## License

Apache-2.0
