# Dataset: data_set_01

Default dataset for `repo_manager` test automation.
Contains input files synced to the target server.

In monorepo mode, host settings (hostname, IP, domain) come from
**environment variables** on the target (set via `omnia.env` / `omnia.sh -s`),
not from a `config.yml`.

---

## Structure

```
data_set_01/
└── input/                                      # Synced to: <OMNIA_DATA_PATH>/repo_manager/input/<project>/
    ├── repo_manager_config.yml                 # Repository URL configuration
    ├── repo_manager_config_credentials.yml     # Pulp and Docker credentials
    ├── repo_manager_endpoint_config.yml        # Pulp server endpoint settings
    └── software_config.json                    # Software and OS configuration
```

---

## input/repo_manager_config.yml

Repository URL configuration. Controls which RPM repos are synced to Pulp.

| Section | Key Fields | Description |
|---------|------------|-------------|
| `user_registry` | `host`, `cert_path`, `key_path` | User container registry configuration |
| `user_repo_url_x86_64` | `url`, `gpgkey`, `name`, `policy`, `caching` | Custom x86_64 repos (e.g., slurm_custom) |
| `user_repo_url_aarch64` | `url`, `gpgkey`, `name`, `policy`, `caching` | Custom aarch64 repos |
| `rhel_os_url_x86_64` | `url`, `gpgkey`, `name`, `policy`, `caching` | RHEL OS repos for x86_64 (baseos, appstream, codeready-builder) |
| `rhel_os_url_aarch64` | `url`, `gpgkey`, `name`, `policy`, `caching` | RHEL OS repos for aarch64 |
| `rhel_subscription_repo_config_x86_64` | `url`, `name`, `policy`, `caching` | RHEL subscription repo overrides for x86_64 |
| `rhel_subscription_repo_config_aarch64` | `url`, `name`, `policy`, `caching` | RHEL subscription repo overrides for aarch64 |
| `omnia_repo_url_rhel_x86_64` | `url`, `gpgkey`, `name` | Omnia feature repos for x86_64 (docker-ce, epel, kubernetes, cri-o, doca, cuda, nvidia-hpc-sdk) |
| `omnia_repo_url_rhel_aarch64` | `url`, `gpgkey`, `name` | Omnia feature repos for aarch64 (docker-ce, epel, doca, cuda, nvidia-hpc-sdk) |
| `additional_repos_x86_64` | `url`, `gpgkey`, `name` | Additional aggregated repos for x86_64 |
| `additional_repos_aarch64` | `url`, `gpgkey`, `name` | Additional aggregated repos for aarch64 |

---

## input/repo_manager_config_credentials.yml

Credentials for Pulp and Docker registries. **Reset to empty before committing.**

| Field | Description |
|-------|-------------|
| `pulp_username` | Pulp server admin username |
| `pulp_password` | Pulp server admin password |
| `docker_username` | Docker Hub registry username |
| `docker_password` | Docker Hub registry password |
| `user_registry_credentials` | List of private registry credentials (`host`, `username`, `password`) |

---

## input/repo_manager_endpoint_config.yml

Pulp server endpoint configuration.

| Field | Description |
|-------|-------------|
| `pulp_server_ip` | Pulp server IP address |
| `pulp_server_port` | Pulp server port (default: 2225) |
| `pulp_protocol` | Protocol (`https`) |
| `pulp_https_enabled` | Enable HTTPS (`true`) |
| `ssl_certificates` | SSL cert/key/dir paths (`server_crt`, `server_key`, `certs_dir`) |

---

## input/software_config.json

Software and OS configuration for repo sync.

| Field | Description |
|-------|-------------|
| `cluster_os_type` | OS type (`rhel`) |
| `cluster_os_version` | OS version (`10.0`) |
| `repo_config` | Sync policy (`partial` or `always`) |
| `softwares` | List of software packages to sync |

---

## Sync behavior

| Config | Target Path |
|--------|-------------|
| `sync_repo_manager_input: true` | `input/` → `<OMNIA_DATA_PATH>/repo_manager/input/<project>/` |

> **Note:** If the target server already has repo_manager input configured,
> set `sync_repo_manager_input: false` in `test_config.yml`.
