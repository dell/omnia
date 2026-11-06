# Repository Manager

Repository Manager (`omnia.repo_manager`) deploys an HTTPS Pulp content server on the OIM and synchronizes catalog-selected content (RPMs, container images, Python packages, files and source artifacts for `x86_64` and `aarch64`) so Omnia clusters can run offline.

## Overview

All playbooks run locally on the Omnia Infrastructure Manager (OIM).

### Related modules

| Direction | Module | Contract |
|-----------|--------|----------|
| Upstream | None | Reads the catalog JSON at `CATALOG_FILE_PATH` |
| Downstream | Image Build Manager, Orchestrator | `repo_status.yml` (repository endpoints and certificates) |
| Automation | Build Stream | Its build pipeline invokes this module |

## Architecture

Repository Manager runs Pulp as a container on the OIM with a systemd-enabled `pulp.service` that starts after reboot. Pulp serves HTTPS only; the host port maps to Pulp container port `443`, and the managed Pulp CLI uses the generated CA.

Execution order and runtime layout are described in [docs/architecture.md](docs/architecture.md); developer boundaries are in [docs/design/repo-manager-design.md](docs/design/repo-manager-design.md).

### Roles

Roles are invoked as `omnia.repo_manager.<role>`.

| Role | Description |
|------|-------------|
| [`catalog`](roles/catalog/README.md) | Catalog management operations for repo_manager |
| [`collect_repo_credentials`](roles/collect_repo_credentials/README.md) | Collects and manages repository manager credentials with encryption support |
| [`common`](roles/common/README.md) | Common tasks and utilities shared across repo_manager playbooks |
| [`deploy_pulp`](roles/deploy_pulp/README.md) | Deploy and configure Pulp container for repository management |
| [`parse_and_download`](roles/parse_and_download/README.md) | Parse configuration and download packages to Pulp |
| [`precheck_environment`](roles/precheck_environment/README.md) | Validates system environment before repo_manager operations |
| [`pulp_validation`](roles/pulp_validation/README.md) | Validate Pulp server connectivity and configuration |
| [`repo_manager_execution`](roles/repo_manager_execution/README.md) | Execute resolved Repo Manager catalog contexts sequentially |
| [`repo_manager_setup`](roles/repo_manager_setup/README.md) | Initial setup and configuration for repo_manager |
| [`repository_access`](roles/repository_access/README.md) | Resolve platform-specific repository access |
| [`validate_input`](roles/validate_input/README.md) | Validate input configuration files |
| [`validation`](roles/validation/README.md) | General validation tasks for repo_manager |

### Modules

Modules are invoked as `omnia.repo_manager.<module>`.

| Module | Description |
|--------|-------------|
| `cert_vault_handler` | Handle certificate vault operations |
| `check_user_registry` | Validate user container registry configuration |
| `generate_local_repo_access` | Generate repo_status.yml with repository URLs |
| `load_validated_yaml` | Load literal runtime YAML without Jinja evaluation |
| `parallel_tasks` | Execute tasks in parallel with thread pool |
| `prepare_tasklist` | Prepare task list for parallel execution |
| `process_rpm_config` | Process RPM repository configuration |
| `pulp_cleanup` | Clean up Pulp repositories and distributions |
| `pulp_repo_name_migration` | Migrate legacy Pulp repository names |
| `resolve_catalog_context` | Resolve Repo Manager catalog execution contexts |
| `resolve_rhel_subscription_repositories` | Resolve RHEL subscription repositories for Pulp |
| `validate_input` | Validate input configuration files |
| `validate_system_environment` | Validate Omnia environment variables against system state |
| `validate_user_repo` | Validate user repository configuration |
| `vault_handler` | Encrypt, decrypt, or view Ansible Vault files |

### Plugins

| Plugin | Type | Description |
|--------|------|-------------|
| `omnia_default` | Callback | Custom Ansible stdout callback plugin for Omnia |

## Prerequisites

| Requirement | Minimum | Notes |
|-------------|---------|-------|
| OS | RHEL 10.0, 10.2 | Runs on the OIM; see the [support matrix](https://omnia.readthedocs.io/en/latest/Reference/SupportMatrix/index.html) |
| Python | 3.12+ | Shared Omnia virtual environment |
| Ansible | ansible-core 2.20+ | Pinned in `requirements.txt` |
| Podman | 5.0+ | Runs the Pulp container |
| Privileges | Root or equivalent |  |
| Storage | Sized for retained catalog content | Deployment-specific |

Use the shared Omnia virtual environment:

```bash
./src/main/omnia.sh --setup-venv
source /opt/omnia/venv/bin/activate
```

## Installation

Run the shared setup once from the repository root. It creates the Omnia virtual environment, runs every domain's `domain-init.sh` (dependencies, log directories, input staging) and installs the default catalog if none is active.

```bash
cd src/main
vi omnia.env                       # first run only; afterwards edit /etc/omnia/omnia.env
sudo ./omnia.sh --setup-venv
source /etc/profile.d/omnia-env.sh
```

To re-run only this module's initializer (for example after editing source inputs):

```bash
sudo ./omnia.sh --init repo_manager
```

## Configuration

### Environment variables

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
to `immediate`. An `rpm_repo` item may not explicitly declare `policy: never`.
When another policy/caching combination maps to `streamed`, Repo Manager uses
validation-only handling for that item.

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
| `parallel_config.default_nthreads` | `4` | General catalog worker processes |
| `rpm_repo_config.thread_pool_size` | `2` | RPM repository synchronization |
| `dnf_config.max_concurrent_commands` | `1` | DNF commands and shared metadata cache |

Keep DNF concurrency at one. Reduce either parallel setting when Pulp, network,
CPU, memory, or storage capacity cannot sustain the default concurrency.

Edit the flat source inputs, then stage them with `sudo ./omnia.sh --init repo_manager`:

```bash
vi src/repo_manager/input/repo_manager_config.yml
vi src/repo_manager/input/repo_manager_endpoint_config.yml
```

## Usage

Run this module through `omnia.sh`; it activates the virtual environment and runs `src/repo_manager/playbooks/repo_manager.yml`. All `./omnia.sh` commands in this document are run from `src/main` on the OIM. See [Tags](#tags) for the supported tags and combinations.

```bash
cd src/main
./omnia.sh --run repo_manager --tags <tag> [-e <extra_var>=<value>]
```

To run the playbook directly, activate `$OMNIA_VENV_PATH/bin/activate`, source `/etc/profile.d/omnia-env.sh`, and run from the module root so its `ansible.cfg` is loaded:

```bash
cd src/repo_manager
ansible-playbook playbooks/repo_manager.yml --tags <tag>
```

Typical flow:

```bash
cd src/main
./omnia.sh --run repo_manager --tags prepare    # deploy HTTPS Pulp
./omnia.sh --run repo_manager --tags precheck
./omnia.sh --run repo_manager --tags download   # synchronize catalog content
./omnia.sh --run repo_manager --tags status     # write repo_status.yml
```

Running without `--tags` executes the standard non-cleanup workflow. Cleanup and catalog operations use the `never` tag and must be selected explicitly.

### Exact RPM repository reconciliation

Use the standalone playbook only after the normal download workflow has created
the catalog-selected RPM repositories, remotes, publications and distributions:

```bash
cd src/repo_manager
ansible-playbook playbooks/repo_operations/repo_sync.yml
```

This maintenance operation processes the catalog's RHEL minor-version contexts
sequentially. It preflights every context before changing Pulp, synchronizes
each referenced RPM repository with `mirror_content_only`, validates the new
HTTPS `repomd.xml`, switches the stable distribution, updates the repository
checkpoint and affected package states atomically, and only then prunes
superseded publications and repository versions. Non-RPM artifacts are not
processed. Do not run it concurrently with download or cleanup operations.

The result is written to `output/<project>/repo_resync_status.yml`. The normal
consumer contract in `repo_status.yml`, the standard playbook tags and the
fresh-download/rerun behavior are unchanged.

## Tags

| Tag | Description | Credentials |
|-----|-------------|-------------|
| `credentials` | Collect or update credentials without deploying Pulp | Yes |
| `prepare` / `deploy` | Collect/reuse credentials and deploy HTTPS Pulp | Yes |
| `precheck` | Validate environment, input, catalog and subscription sources | No new credentials |
| `download` / `execute` | Resolve and synchronize catalog content | Existing credentials |
| `status` | Generate current `repo_status.yml` | Existing Pulp credentials |
| `cleanup_repos` | Selectively remove Pulp RPM, container, File or Python content | Existing Pulp credentials |
| `cleanup_pulp` / `cleanup` | Remove the Pulp deployment, runtime data, and credentials by default | `cleanup_credentials=false` preserves credentials |
| `catalog_generate` | Create catalog JSON from text input | No |
| `catalog_add` | Add or update catalog packages | No |
| `catalog_delete` | Delete catalog packages | No |
| `catalog_validate` | Validate catalog JSON | No |

Standard tags can be combined. Their execution order is defined by
`playbooks/repo_manager.yml`, not the order written after `--tags`. Do not mix a
cleanup tag with a standard workflow command.

## Inputs and Outputs

### Inputs

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

### Outputs

| Output | Location | Purpose |
|--------|----------|---------|
| `repo_status.yml` | `output/<project>/` | Version-qualified Pulp RPM, artifact and content-base URLs plus certificate paths for consumers |
| `repo_resync_status.yml` | `output/<project>/` | Administrative result for the latest standalone exact RPM reconciliation |
| Package/group state | `log/<os>/<version>/<arch>/` | Per-group CSV and worker results |
| Mirror indexes | `log/<os>/<version>/mirror_status/` | Composite catalog and Pulp mirror state |

Selective cleanup removes the now-stale `repo_status.yml`. Run `download,status`
to restore cleaned catalog content and regenerate the consumer output, or run
`status` alone to describe the intentionally incomplete current Pulp state.

## Runtime Paths

### Data path (`$REPO_MANAGER_DATA_PATH`)

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

### Ansible logs

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

## Cleanup

### Selective cleanup

```bash
# Remove one RPM repository by its complete Pulp name.
./omnia.sh --run repo_manager --tags cleanup_repos \
  -e "cleanup_repos=x86_64_rhel_10.0_epel"

# Remove only one image tag. Other tags remain.
./omnia.sh --run repo_manager --tags cleanup_repos \
  -e "cleanup_containers=registry.example.com/team/image:v1"

# Remove the complete image repository and all its tags.
./omnia.sh --run repo_manager --tags cleanup_repos \
  -e "cleanup_containers=registry.example.com/team/image"

# Remove selected File/Python artifacts.
./omnia.sh --run repo_manager --tags cleanup_repos \
  -e "cleanup_files=helm-charts-2.17.0,helm-v3.20.1-amd64"

# Remove all synchronized artifact types but keep the Pulp deployment.
./omnia.sh --run repo_manager --tags cleanup_repos \
  -e "cleanup_repos=all" -e "cleanup_containers=all" \
  -e "cleanup_files=all" -e "force=true"
```

An exact tag is required when only one tag should be removed. An untagged image
intentionally removes every tag in that Pulp container repository.

### Full Pulp cleanup

```bash
# Remove Pulp, runtime content, and Repo Manager credentials.
./omnia.sh --run repo_manager --tags cleanup_pulp

# Preserve operational logs and credentials.
./omnia.sh --run repo_manager --tags cleanup_pulp \
  -e "cleanup_logs=false" -e "cleanup_credentials=false"
```

Credential deletion is enabled by default and does not add a separate prompt;
the explicit cleanup tag is the operator's request. `cleanup_repos` is selective
content cleanup and retains credentials because the Pulp deployment remains.

For a complete Omnia reset, run `sudo ./omnia.sh --run repo_manager --tags
cleanup` from `src/main`, resolve any retained paths it reports, and then run
`sudo ./omnia.sh --cleanup --all`. `src/repo_manager/domain-init.sh --cleanup`
is a non-interactive helper that removes only initializer-owned staged input and
domain log paths. Both global cleanup modes prompt for `yes`; trusted automation
can add `--skip-approval`.

## Troubleshooting

- Ansible log: `/var/log/omnia/repo_manager/repo_manager.log` (top-level playbook execution).
- Selective-cleanup details and results are under `<REPO_MANAGER_DATA_PATH>/log/<os>/<version>/cleanup/` (see [Runtime Paths](#runtime-paths)).
- Re-run `sudo ./omnia.sh --init repo_manager` if inputs or dependencies were not staged.
- [docs/troubleshooting.md](docs/troubleshooting.md), [docs/failure-modes.md](docs/failure-modes.md), and [docs/pulp-administration.md](docs/pulp-administration.md) cover failures, recovery, and Pulp health.

## Security

- Pulp is HTTPS only. Credential files are Ansible Vault protected, root-owned, and mode `0600`; `cleanup_pulp` deletes them by default (`-e cleanup_credentials=false` keeps them).
- See [docs/security.md](docs/security.md) for HTTPS, Vault, registry TLS, and cleanup controls.

## Documentation

- [Read the Docs: Repo Manager guides](https://omnia.readthedocs.io/en/latest/HowTo/repo_manager/index.html)
- [Architecture](docs/architecture.md)
- [Content configuration](docs/content-configuration-guide.md)
- [Catalog operations](docs/catalog_operations.md)
- [Troubleshooting](docs/troubleshooting.md)
- [Failure modes](docs/failure-modes.md)
- [Pulp administration](docs/pulp-administration.md)
- [Security](docs/security.md)
- [Design](docs/design/repo-manager-design.md)
- [Input contract](docs/contracts/input-contract.md)
- [Output contract](docs/contracts/output-contract.md)
- [Samples](samples/README.md)
- [Omnia on GitHub](https://github.com/dell/omnia)
- [Report an issue](https://github.com/dell/omnia/issues)

## License

Apache License, Version 2.0
