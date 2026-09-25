# orchestrator_common

Reusable task-library role for operations shared by Orchestrator lifecycle
playbooks. Call a specific task file with `tasks_from`; the default `main.yml`
only reports the supported usage pattern.

## Task Library

| Task file | Purpose |
|-----------|---------|
| `configure_s3_access.yml` | Load and publish Image Build Manager S3 settings |
| `openchami_auth.yml` | Generate and protect a TokenSmith access token |
| `decrypt_include_encrypt.yml` | Temporarily decrypt, load, and re-encrypt a Vault file |
| `check_kube_vip_reachability.yml` | Check Kubernetes virtual-IP SSH reachability |
| `normalize_network_spec.yml` | Validate and merge the `Networks` list |
| `normalize_pxe_functional_groups.yml` | Normalize primary Kubernetes control-plane membership |

## Requirements

- Facts required by the selected task file must already exist.
- Credential task callers must protect values with `no_log`.
- OpenCHAMI authentication requires a deployed TokenSmith service and cluster
  certificate configuration.

## Role Variables

`vars/main.yml` contains shared mapping error messages. Individual task files
also consume caller-provided paths, credentials, and host facts.

## Dependencies

No role dependency is declared in `meta/main.yml`.

## Example

```yaml
- name: Authenticate with OpenCHAMI
  ansible.builtin.include_role:
    name: orchestrator_common
    tasks_from: openchami_auth.yml
```

## License

Apache-2.0
