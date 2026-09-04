# Repo Manager

**Collection**: `omnia.repo_manager` v3.0.0

Deploys an HTTPS Pulp content server and synchronizes catalog content for
offline Omnia clusters. Supports RPM repositories and packages, container
images, Python packages, files and source artifacts for `x86_64` and `aarch64`.

All playbooks run locally on the Omnia Infrastructure Manager (OIM).

---

## Prerequisites

| Requirement | Minimum | Validated |
|-------------|---------|-----------|
| OIM OS | RHEL 10.x | RHEL 10.0 |
| Python | 3.12+ | 3.12.8 |
| Ansible | ansible-core 2.20+ | 2.20.0 |
| Podman | 5.0+ | 5.3.1 |
| Privileges | Root or equivalent | Root |
| Storage | Sized for retained catalog content | Deployment-specific |

Use the shared Omnia virtual environment:

```bash
./src/main/omnia.sh --setup-venv
source /opt/omnia/venv/bin/activate
```

---

## Quick Start

```bash
# 1. Configure the common environment.
vi src/main/omnia.env
./src/main/omnia.sh --setup-venv
source /opt/omnia/venv/bin/activate
set -a
source /etc/omnia/omnia.env
set +a

# Required values include:
# SYSTEM_ADMIN_NIC_IPV4=<admin_ipv4>
# CATALOG_FILE_PATH=/absolute/path/to/catalog.json

# 2. Edit the flat source inputs.
vi src/repo_manager/input/repo_manager_config.yml
vi src/repo_manager/input/repo_manager_endpoint_config.yml

# 3. Stage inputs into the selected runtime project.
cd src/repo_manager
./domain-init.sh

# 4. Run the standard workflow.
cd playbooks
ansible-playbook repo_manager.yml \
  --tags "prepare,precheck,download,status"
```

Running the playbook without `--tags` executes the standard non-cleanup
workflow. Cleanup and catalog operations use `never` and must be selected
explicitly.

---

## Tags

| Tag | Description | Credentials |
|-----|-------------|-------------|
| `prepare` / `deploy` | Collect/reuse credentials and deploy HTTPS Pulp | Yes |
| `precheck` | Validate environment, input, catalog and subscription sources | No new credentials |
| `download` / `execute` | Resolve and synchronize catalog content | Existing credentials |
| `status` | Generate current `repo_status.yml` | Existing Pulp credentials |
| `cleanup_repos` | Selectively remove Pulp RPM, container, File or Python content | Existing Pulp credentials |
| `cleanup_pulp` / `cleanup` | Remove the Pulp deployment and runtime data | Optional credential deletion |
| `catalog_generate` | Create catalog JSON from text input | No |
| `catalog_add` | Add or update catalog packages | No |
| `catalog_delete` | Delete catalog packages | No |
| `catalog_validate` | Validate catalog JSON | No |

Standard tags can be combined. Their execution order is defined by
`playbooks/repo_manager.yml`, not the order written after `--tags`. Do not mix a
cleanup tag with a standard workflow command.

### Selective Cleanup

```bash
# Remove one RPM repository by its complete Pulp name.
ansible-playbook repo_manager.yml --tags cleanup_repos \
  -e "cleanup_repos=x86_64_rhel_10.0_epel"

# Remove only one image tag. Other tags remain.
ansible-playbook repo_manager.yml --tags cleanup_repos \
  -e "cleanup_containers=registry.example.com/team/image:v1"

# Remove the complete image repository and all its tags.
ansible-playbook repo_manager.yml --tags cleanup_repos \
  -e "cleanup_containers=registry.example.com/team/image"

# Remove selected File/Python artifacts.
ansible-playbook repo_manager.yml --tags cleanup_repos \
  -e "cleanup_files=helm-charts-2.17.0,helm-v3.20.1-amd64"

# Remove all synchronized artifact types but keep the Pulp deployment.
ansible-playbook repo_manager.yml --tags cleanup_repos \
  -e "cleanup_repos=all" -e "cleanup_containers=all" \
  -e "cleanup_files=all" -e "force=true"
```

An exact tag is required when only one tag should be removed. An untagged image
intentionally removes every tag in that Pulp container repository.

### Full Pulp Cleanup

```bash
# Remove Pulp and runtime content; credential deletion is interactive.
ansible-playbook repo_manager.yml --tags cleanup_pulp

# Preserve operational logs and credentials.
ansible-playbook repo_manager.yml --tags cleanup_pulp \
  -e "cleanup_logs=false" -e "cleanup_credentials=false"
```

---

## Input / Output

### Input

`domain-init.sh` copies flat source inputs into the active runtime project:

```text
src/repo_manager/input/
        |
        v
<REPO_MANAGER_DATA_PATH>/input/<OMNIA_PROJECT_NAME>/
```

| Input | Source | Runtime | Required |
|-------|--------|---------|----------|
| `repo_manager_config.yml` | `input/` | `input/<project>/` | Yes |
| `repo_manager_endpoint_config.yml` | `input/` | `input/<project>/` | Yes |
| Catalog JSON | External file | `CATALOG_FILE_PATH` | Yes |
| `repo_manager_config_credentials.yml` | Generated | `input/<project>/` | After `prepare` |
| `.repo_manager_config_credentials_key` | Generated | `input/<project>/` | After `prepare` |

Credential files are Ansible Vault protected, root-owned and mode `0600`.

### Output

| Output | Location | Purpose |
|--------|----------|---------|
| `repo_status.yml` | `output/<project>/` | Pulp URLs, repositories, file content and certificate paths for consumers |
| Package/group state | `log/<os>/<version>/<arch>/` | Per-group CSV and worker results |
| Mirror indexes | `log/<os>/<version>/mirror_status/` | Composite catalog and Pulp mirror state |

Selective cleanup removes the now-stale `repo_status.yml`. Run `download,status`
to restore cleaned catalog content and regenerate the consumer output, or run
`status` alone to describe the intentionally incomplete current Pulp state.

---

## Configuration

### Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `SYSTEM_ADMIN_NIC_IPV4` | **required** | OIM admin-network IPv4 used by Pulp |
| `CATALOG_FILE_PATH` | **required** | Existing catalog file with a `.json` extension |
| `OMNIA_DATA_PATH` | `/opt/omnia` | Root Omnia runtime data directory |
| `REPO_MANAGER_DATA_PATH` | `<OMNIA_DATA_PATH>/repo_manager` | Optional Repo Manager runtime override |
| `OMNIA_PROJECT_NAME` | `project_default` | Active input/output project |

### Endpoint

Pulp uses HTTPS only. The user controls the host port; certificate paths and
container TLS port are internal:

```yaml
pulp_server_port: 2225
```

The host port maps to Pulp container port `443`. The systemd-enabled
`pulp.service` starts after reboot. The managed Pulp CLI automatically uses the
generated CA.

### Repository Policies

```yaml
repo_config: "partial"   # always | partial
caching_policy: true     # true | false
```

Per-repository `policy` and `caching` fields override the global values.

| Policy | Caching | Pulp policy |
|--------|---------|-------------|
| `always` | `false` | `immediate` |
| `always` | `true` | `on_demand` |
| `partial` | `false` | `streamed` |
| `partial` | `true` | `on_demand` |
| `never` | either | `streamed` |

Container synchronization uses its independent configured policy and defaults
to `immediate`. A catalog `rpm_repo` item must use retained content and cannot
resolve to `streamed`.

### RHEL Subscription Repositories

```yaml
baseos: {}
appstream: {}
codeready-builder: {}
```

Empty mappings use the matching subscription/EUS repository and entitlement
certificates. Without a valid subscription, provide explicit URLs. Explicit
user fields always take precedence over subscription-derived values.

### Private Registry

```yaml
registries:
  harbor.example.com:
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

The catalog source `registry` must match this configuration key. During
`prepare`, Repo Manager collects credentials under the referenced `vault_path`
and passes them to the Pulp remote. Known public registries work without a
configuration entry.

### Concurrency

| Setting | Default | Scope |
|---------|---------|-------|
| `parallel_config.default_nthreads` | `3` | General catalog worker processes |
| `rpm_repo_config.thread_pool_size` | `3` | RPM repository synchronization |
| `dnf_config.max_concurrent_commands` | `1` | DNF commands and shared metadata cache |

Keep DNF concurrency at one. Reduce either parallel setting when Pulp, network,
CPU, memory, or storage capacity cannot sustain the default concurrency.

---

## Runtime Paths

### Data Path (`$REPO_MANAGER_DATA_PATH`)

```text
/opt/omnia/repo_manager/
+-- input/<project>/                 Staged inputs and Vault credentials
+-- output/<project>/repo_status.yml Consumer output
+-- log/<os>/<version>/              Progress, group and mirror state
+-- pulp_config/                     Pulp settings, certificates and data
+-- rhel_repo_certs/                 Subscription certificates
+-- offline_repo/                    Retained offline artifacts
```

`/opt/omnia/repo_manager` is the default only. Setting `OMNIA_DATA_PATH` or
`REPO_MANAGER_DATA_PATH` moves domain runtime paths consistently.

### Ansible Logs

| Log | Location |
|-----|----------|
| Top-level playbook | `/var/log/omnia/repo_manager/repo_manager.log` |
| Direct cleanup playbook | `/var/log/omnia/repo_manager/cleanup.log` |
| Selective cleanup details | `<REPO_MANAGER_DATA_PATH>/log/<os>/<version>/cleanup/standard.log` |
| Selective cleanup results | `<REPO_MANAGER_DATA_PATH>/log/<os>/<version>/cleanup/cleanup_status.csv` |
| Multi-version/shared cleanup details | `<REPO_MANAGER_DATA_PATH>/log/<os>/cleanup/standard.log` |
| Multi-version/shared cleanup results | `<REPO_MANAGER_DATA_PATH>/log/<os>/cleanup/cleanup_status.csv` |

Full Pulp cleanup removes runtime logs by default. Use
`-e "cleanup_logs=false"` to preserve them.

---

## Documentation

| Document | Description |
|----------|-------------|
| [Architecture](docs/architecture.md) | Execution flow, tags, Pulp and runtime paths |
| [Content Configuration](docs/content-configuration-guide.md) | Catalog, RPM, registry and policy mapping |
| [Catalog Operations](docs/catalog_operations.md) | Generate, add, delete and validate catalog JSON |
| [Troubleshooting](docs/troubleshooting.md) | Common failures, logs and safe diagnostics |
| [Security](docs/security.md) | HTTPS, Vault, registry TLS and cleanup controls |
| [Input Contract](docs/contracts/input-contract.md) | Environment and input schemas |
| [Output Contract](docs/contracts/output-contract.md) | `repo_status.yml`, state and logs |
| [Design](docs/design/repo-manager-design.md) | Developer implementation boundaries and invariants |

---

## License

Apache License, Version 2.0
