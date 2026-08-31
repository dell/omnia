# Repo Manager -- Output Contract

**Domain**: `repo_manager` | **Collection**: `omnia.repo_manager`

---

## 1. repo_status.yml

**Purpose**: Publishes synchronized Pulp repository URLs and certificate paths
to downstream Omnia components.

**Location**: `<REPO_MANAGER_DATA_PATH>/output/<project>/repo_status.yml`

**Producer**: `generate_local_repo_access` module (`status` tag).

**Consumers**: Image Build Manager and cluster provisioning workflows.

### Structure

```yaml
overall_status: "success"
cluster_os_type: "rhel"
repo_config: "partial"

repo_manager:
  port: 2225
  certificates:
    server_crt: "<REPO_MANAGER_DATA_PATH>/pulp_config/settings/certs/pulp_webserver.crt"
    server_key: "<REPO_MANAGER_DATA_PATH>/pulp_config/settings/certs/pulp_webserver.key"
    certs_dir: "<REPO_MANAGER_DATA_PATH>/pulp_config/settings/certs"

repositories:
  "10.0":
    x86_64:
      baseos:
        url: "https://192.0.2.10:2225/pulp/content/.../baseos/"
      slurm_custom:
        url: "https://192.0.2.10:2225/pulp/content/.../slurm_custom/"
        priority: 100
    aarch64: {}

file_repos:
  x86_64:
    tarball:
      helm-v3_20_1-amd64: "https://192.0.2.10:2225/pulp/content/.../"
    pip_module:
      cffi_1_17_1: "https://192.0.2.10:2225/pypi/.../"
  aarch64: {}

offline_tarball_path: "https://192.0.2.10:2225/pulp/content/.../tarball/"
offline_pip_module_path: "https://192.0.2.10:2225/pypi/.../pip_module/"
```

### Fields

| Field | Type | Description |
|-------|------|-------------|
| `overall_status` | string | Generation result, normally `success` |
| `cluster_os_type` | string | Catalog OS type, normally `rhel` |
| `repo_config` | string | Repository policy reported by the generator |
| `repo_manager.port` | integer | Pulp HTTPS host port |
| `repo_manager.certificates.*` | string | Pulp certificate and certificate-directory paths |
| `repositories.<version>.<arch>.<repo>.url` | string | RPM distribution URL |
| `repositories.<version>.<arch>.<repo>.priority` | integer | Optional DNF priority copied from the repository input (1-100; lower values have higher precedence) |
| `file_repos.<arch>.<type>.<artifact>` | string | File or Python distribution URL |
| `*_base_url` | string | Base URL for a content type when available |
| `offline_*_path` | string | Backward-compatible type URL |

Repository URLs are generated from actual Pulp distributions. Empty architecture
maps are valid when the catalog did not select content for that architecture.

### Generation Rules

| Rule | Behavior |
|------|----------|
| Pulp unavailable | Status generation fails |
| Distribution exists | URL is included |
| Repository has explicit `priority` | Priority is included; otherwise consumers retain their default of 99 |
| `additional_repos` | One aggregate priority is emitted; conflicting effective priorities fail validation |
| No distribution for an architecture/type | Corresponding map is empty |
| Custom `OMNIA_DATA_PATH` | Certificate and output paths use the custom root |
| Selective cleanup completed | Run `--tags status` again to refresh this file |

`repo_status.yml` is not automatically regenerated during selective cleanup.

---

## 2. Pulp Services and Content

Services created by the `prepare` tag:

| Output | Location or name | Description |
|--------|------------------|-------------|
| Systemd service | `pulp.service` | Enabled Pulp Podman Quadlet service |
| Quadlet | `/etc/containers/systemd/pulp.container` | Container definition |
| HTTPS endpoint | `https://<pulp_server_ip>:<pulp_server_port>` | API, content and OCI registry endpoint |
| CA certificate | `<REPO_MANAGER_DATA_PATH>/pulp_config/settings/certs/pulp_webserver.crt` | Client trust certificate |
| Pulp CLI launcher | `/usr/local/bin/pulp` | CLI configured for HTTPS access |
| Host trust anchor | `/etc/pki/ca-trust/source/anchors/omnia-pulp.crt` | System CA trust |

Content stored in Pulp is the authoritative downloadable output. Local files
under `offline_repo` are staging content, not the downstream contract.

---

## 3. Download and Mirror State

**Location**: `<REPO_MANAGER_DATA_PATH>/log/<os>/<version>/`

| File | Purpose |
|------|---------|
| `<arch>/<group>/status.csv` | Exact package/artifact status for one catalog group |
| `<arch>/groups_status.csv` | Overall state for every resolved group |
| `<arch>/<group>_task_results.log` | Final worker results for a group |
| `mirror_status/global_package_index.json` | Catalog package identities and ownership |
| `mirror_status/pulp_mirror_index.json` | Mirrored, failed and pending Pulp identities |
| `standard.log` | Download execution and progress heartbeat |

### status.csv Fields

| Field | Description |
|-------|-------------|
| `name` | Exact package, artifact or tagged image identity |
| `type` | Catalog package type |
| `repo_name` | RPM source repository when applicable |
| `status` | `Success` or failure state |
| `catalog_name` | Catalog identity when recorded |

Status and mirror files use atomic replacement. They are operational state used
for idempotent reruns; downstream components should consume `repo_status.yml`.

---

## 4. Cleanup Results

Selective cleanup writes:

| File | Path |
|------|------|
| Detailed cleanup log | `<REPO_MANAGER_DATA_PATH>/log/<os>/<version>/cleanup/standard.log` |
| Result table | `<REPO_MANAGER_DATA_PATH>/log/<os>/<version>/cleanup/cleanup_status.csv` |

`cleanup_status.csv` contains one result per requested Pulp object with its type,
status and message. Successful cleanup also removes matching package rows from
download state and marks affected groups partial.

Full Pulp cleanup removes `<REPO_MANAGER_DATA_PATH>/log` by default. Set
`cleanup_logs=false` to preserve existing runtime logs.

---

## 5. Ansible Logs

| Invocation | Log path |
|------------|----------|
| Top-level `repo_manager.yml` | `/var/log/omnia/repo_manager/repo_manager.log` |
| Direct cleanup playbook from `playbooks/cleanup` | `/var/log/omnia/repo_manager/cleanup.log` |
| Direct deploy playbook from `playbooks/deploy` | `/var/log/omnia/repo_manager/deploy.log` |
| Direct repository operation | `/var/log/omnia/repo_manager/repo_operations.log` |

---

## 6. Consumption by Image Build Manager

Image Build Manager reads:

- `overall_status`
- `cluster_os_type`
- `repositories.<version>.<architecture>`
- Pulp certificate paths
- backward-compatible repository keys when required by older consumers

The consumer must trust the Pulp CA certificate and must reject a non-successful
`overall_status`.

## Security and Permissions

| Output | Expected protection |
|--------|---------------------|
| `repo_status.yml` | Contains URLs and paths, not credential values |
| Pulp private key | Root-only file under Pulp settings |
| Operational logs | Must not contain passwords or tokens |
| Credential Vault | Root-owned mode `0600`; separate from outputs |
