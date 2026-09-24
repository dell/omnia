# openldap

Derives the OpenLDAP client facts used while generating Slurm and Kubernetes
node configuration. This role does not deploy the LDAP server; that belongs to
`deploy_openldap`.

## What It Does

- Converts the configured DNS domain into an LDAP search base.
- Uses the OIM admin address as the LDAP server address.
- Normalizes the LDAP or LDAPS connection type.
- Builds the administrator bind DN.
- Publishes the password as a protected fact for downstream template tasks.

The role performs no work when `openldap_support` is false.

## Requirements

- `orchestrator_setup` has resolved the domain, admin address, and feature flag.
- OpenLDAP credentials have been loaded into protected localhost facts.

## Role Variables

| Variable | Source | Purpose |
|----------|--------|---------|
| `openldap_support` | `hostvars['localhost']` | Enable LDAP fact preparation |
| `ldap_connection_type` | `hostvars['localhost']` | Select LDAP or LDAPS behavior |
| `openldap_db_username` | Credential facts | Build the administrator bind DN |
| `openldap_db_password` | Credential facts | Protected bind password |

`vars/main.yml` contains the role failure message.

## Dependencies

No automatic dependency is declared in `meta/main.yml`.

## Example

```yaml
- hosts: oim
  roles:
    - openldap
```

## License

Apache-2.0
