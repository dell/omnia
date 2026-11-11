# deploy_openldap

Deploys the optional `omnia_auth` OpenLDAP container as a Podman Quadlet
service on the OIM. An already-running healthy container is left in place.

## What It Does

1. Stops early when OpenLDAP support is disabled.
2. Loads and validates project-scoped OpenLDAP credentials.
3. Creates persistent configuration, certificate, data, and initialization
   directories.
4. Generates TLS material, `slapd.conf`, and the bootstrap LDIF.
5. Pulls the configured `omnia_auth` image and renders its Quadlet.
6. Starts the systemd-managed service and waits for the container to run.

## Requirements

- `openldap_support: true` resolved from the active cluster configuration.
- Valid OpenLDAP username and password in the Orchestrator credential vault.
- Podman Quadlet and systemd on the OIM.
- Resolved OIM address and domain name.

## Role Variables

See `vars/main.yml`; this role has no `defaults/main.yml`. Key values include
`omnia_auth_image`, `omnia_auth_tag`, persistent paths, LDAP/LDAPS ports, TLS
settings, and readiness retries.

## Dependencies

No automatic dependency is declared in `meta/main.yml`. The caller must run
`orchestrator_setup` and credential collection first.

## Example

```yaml
- hosts: oim
  become: true
  roles:
    - deploy_openldap
```

Container build and runtime details are documented in
`containers/omnia_auth/README.md`.

## License

Apache-2.0
