# Repo Manager -- Security

## Security Model

Repo Manager runs with elevated local privileges because it manages Podman,
systemd, firewall rules, CA trust, subscription certificates and Pulp content.
Restrict execution and runtime files to trusted administrators.

---

## Pulp HTTPS

| Control | Behavior |
|---------|----------|
| External protocol | HTTPS only |
| Certificate | Generated under `<REPO_MANAGER_DATA_PATH>/pulp_config/settings/certs/` |
| Container TLS port | `443` |
| Host port | User-selected `pulp_server_port` |
| CLI verification | Uses the generated CA through the system and venv managed Pulp CLI paths |
| Host trust | Installs `omnia-pulp.crt` in the RHEL CA trust store |

Users do not configure protocol or certificate paths in the endpoint input. The
managed `pulp` command supplies the CA automatically both inside and outside the
Omnia virtual environment; a persistent shell export of `PULP_CA_BUNDLE` is not
required.

The generated private key is a path in `repo_status.yml`, never the key content.

---

## Credential Protection

### Files

| File | Protection |
|------|------------|
| `repo_manager_config_credentials.yml` | Ansible Vault encrypted, mode `0600` |
| `.repo_manager_config_credentials_key` | Root-owned, mode `0600` |

The credential role writes encrypted canonical state and does not leave the
credential file decrypted after normal processing. A re-encryption failure is a
fatal security error.

### Values Stored

- Pulp administrator username and password.
- Optional Docker Hub username and password/token.
- Private-registry username and password/token keyed by `vault_path`.

Passwords and tokens must not appear in catalog JSON, `repo_manager_config.yml`,
`repo_status.yml`, command output or logs.

### Logging

Credential collection, Vault operations and authenticated Pulp commands use
Ansible `no_log` or redacted command handling. Troubleshooting output should show
only key names, presence, type and file permissions.

---

## Private Registry TLS

```yaml
registries:
  private_registry:
    base_url: "https://harbor.example.com"
    port: 443
    auth:
      type: basic
      credentials:
        vault_path: "registries/harbor-production"
    tls:
      ca_path: "/path/to/harbor-ca.crt"
      client_cert_path: ""
      client_key_path: ""
      insecure: false
```

| Setting | Guidance |
|---------|----------|
| `ca_path` | Use for a private CA |
| `client_cert_path` and `client_key_path` | Use together for mTLS |
| `insecure: true` | Disables verification; use only for controlled testing |
| `base_url: http://...` | Schema-compatible but not recommended for production |

Registry credentials are passed to the Pulp remote for synchronization. They are
not embedded in distribution URLs.

---

## RHEL Subscription Certificates

- Entitlement certificates are copied to
  `<REPO_MANAGER_DATA_PATH>/rhel_repo_certs/`.
- Certificate and key paths are supplied to the matching Pulp RPM remotes.
- SELinux context is set to permit container access.
- User-provided repository URLs and TLS fields take precedence over automatic
  subscription resolution.
- Do not copy subscription keys into catalogs or logs.

---

## Input and Command Safety

| Control | Purpose |
|---------|---------|
| JSON Schema with `additionalProperties: false` | Reject unknown configuration keys |
| Catalog logic validation | Reject unresolved repositories and registries |
| Exact Pulp object names/hrefs | Avoid substring deletion |
| Argument-list subprocess execution | Keep user values out of shell parsing |
| Cleanup path validation | Refuse broad system and parent-directory targets |
| Atomic status/mirror writes | Avoid partially written tracking state |
| Pulp post-delete verification | Update local state only after confirmed deletion |

Digest-based container cleanup is rejected. Tagged cleanup addresses exactly one
tag; untagged cleanup intentionally removes the complete image repository.

---

## File Permissions

| Content | Typical mode |
|---------|--------------|
| Runtime directories | `0755` |
| Public configuration and generated status | `0644` |
| Credentials, Vault key and private keys | `0600` |

Do not relax credential or private-key permissions to solve container access.
Correct SELinux labels and mounts instead.

## Operational Recommendations

1. Keep `tls.insecure` false.
2. Protect `/etc/omnia/omnia.env` and all runtime input directories.
3. Run one Repo Manager instance at a time.
4. Review cleanup scope before using `force=true`.
5. Back up Vault credentials and their matching key together.
6. Rotate Pulp and registry credentials after suspected disclosure.
7. Inspect logs for secrets before sharing them externally.
