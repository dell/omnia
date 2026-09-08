# orchestrator_common

Reusable task-library role for the Omnia orchestrator collection.

Include an individual task file with `tasks_from`; do not include the role's
default `main.yml` as a lifecycle role.

Available shared tasks include:

- `configure_s3_access.yml`
- `openchami_auth.yml`
- `decrypt_include_encrypt.yml`
- `check_kube_vip_reachability.yml`
- `normalize_network_spec.yml`

`normalize_network_spec.yml` validates that `Networks` is a non-empty list of
mappings and combines its entries into the `network_data` mapping consumed by
deployment, validation, and provisioning roles.

## Role Variables

See `vars/main.yml` and `defaults/main.yml` for available variables.

## License

Apache-2.0
