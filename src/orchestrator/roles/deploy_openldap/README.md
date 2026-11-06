# deploy_openldap

Deploys the optional `omnia_auth` OpenLDAP container as a Podman Quadlet
service on the OIM. When the container is already running the desired image
(`omnia_auth_image:omnia_auth_tag`), only `slapd.conf` is reconciled: a changed
rendering is validated with `slaptest`, installed, and applied by restarting the
service, with the previous file restored if the restarted service does not
answer. An unchanged rendering leaves the running container untouched. When the
running container uses a different image, the role replaces it. Bump
`omnia_auth_tag` whenever the image content changes, so that existing
deployments pick the change up.

## What It Does

1. Stops early when OpenLDAP support is disabled.
2. Loads and validates project-scoped OpenLDAP credentials.
3. Creates the `auth_ldap_group` group (gid `auth_ldap_gid`) and the persistent
   configuration, certificate, data, and initialization directories.
4. Generates TLS material, `slapd.conf`, and the bootstrap LDIF.
5. Pulls the configured `omnia_auth` image and renders its Quadlet.
6. Starts the systemd-managed service and waits for the container to run.

## Requirements

- `openldap_support: true` resolved from the active cluster configuration.
- Valid OpenLDAP username and password in the Orchestrator credential vault.
- Podman Quadlet and systemd on the OIM.
- Resolved OIM address and domain name.

## File Ownership

`slapd` runs as the unprivileged `ldap` user (uid/gid `auth_ldap_uid` and
`auth_ldap_gid`, default 55, matching the image). The container is rootful, so
numeric ids are shared with the OIM and the host group must stay empty:

| Path | Owner:group | Mode |
|------|-------------|------|
| `auth/config/slapd.conf` | `root:ldap` | `0640` |
| `auth/tls_certs/` | `root:ldap` | `0750` |
| `auth/tls_certs/ldapserver.key` | `root:ldap` | `0640` |
| `auth/tls_certs/ldapserver.crt` | `root:root` | `0644` |
| `auth/data/` | `ldap uid:gid` | `0700` |

## TLS Trust

The generated `ldapserver.crt` is self-signed and is its own trust anchor. For a
certificate issued by a separate CA, place the CA certificate in `auth/tls_certs`
and set `ldap_tls_ca_file` to its file name; the entrypoint then verifies the
certificate against that CA and `slapd.conf` uses it as `TLSCACertificateFile`.
`ldap_tls_cert_sha256` optionally pins the certificate fingerprint. Both default
to unset. Node-side distribution of a separate CA is not covered by this role.

## Role Variables

See `vars/main.yml`; this role has no `defaults/main.yml`. Key values include
`omnia_auth_image`, `omnia_auth_tag`, `auth_ldap_uid`/`auth_ldap_gid`,
`ldap_tls_ca_file`, `ldap_tls_cert_sha256`, persistent paths, LDAP/LDAPS ports,
TLS settings, and readiness retries.

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
