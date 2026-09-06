# Repo Manager -- Pulp Administration

Copyright 2026 Dell Inc. or its subsidiaries. All Rights Reserved.

## Purpose

This guide explains how Repo Manager names, publishes, inspects and removes
content in its managed Pulp deployment. It is intended for administrators who
need to verify the service, find an exact repository URL or diagnose an
incomplete Pulp object chain.

Use the Repo Manager playbooks for normal add, update, resync and cleanup
operations. The raw Pulp CLI procedures near the end of this guide are for
controlled administrative recovery or deliberately unmanaged content only.
Raw Pulp changes do not update Repo Manager mirror indexes, group status or
catalog execution state.

Repo Manager currently manages these Pulp plugin families:

| Catalog content | Pulp plugin |
|-----------------|-------------|
| RPM packages and repositories | RPM |
| Container images | Container |
| Python packages | Python |
| Tarballs, manifests, Git archives, ISO files, shell files and Ansible Galaxy collections | File |

Other plugins present in the Pulp image are not enabled Repo Manager backends.

## Managed endpoint and CLI

| Item | Current contract |
|------|------------------|
| Pulp image default | `docker.io/pulp/pulp:3.114.2` |
| Service | `pulp.service` |
| Container | `pulp` |
| External protocol | HTTPS only |
| Host endpoint | `https://<pulp_server_ip>:<pulp_server_port>` |
| API root | `/pulp/api/v3/` |
| General content route | `/pulp/content/` |
| Python index route | `/pypi/` |
| Managed CLI | `/usr/local/bin/pulp` |
| CLI configuration | `/etc/pulp/cli.toml` |
| Sample input host port | `2225` |
| Container TLS port | `443` |

`pulp_server_port` and the optional `pulp_server_ip` come from
`repo_manager_endpoint_config.yml`. When the IP is omitted, Repo Manager uses
the validated `SYSTEM_ADMIN_NIC_IPV4` value.

The managed `/usr/local/bin/pulp` launcher supplies the configured endpoint,
administrator credentials and CA verification. A non-empty `OMNIA_VENV_PATH`
selects that virtual environment's Python runtime; an unset or empty value
selects the system Python runtime. Administrators use the same managed CLI in
both cases.

Do not put a Pulp password on a diagnostic command line and do not replace the
managed CLI configuration with an insecure client configuration.

## URL construction

Pulp stores a relative distribution `base_path`. The public URL is derived from
the configured HTTPS origin and the plugin-specific route.

| Pulp family | Relative `base_path` | Administrator-facing location |
|-------------|----------------------|-------------------------------|
| RPM | `offline_repo/cluster/<arch>/<os>/<minor>/rpms/<pulp-name>` | `https://<host>:<port>/pulp/content/<base_path>/` |
| File | `offline_repo/cluster/<arch>/<os>/<minor>/<type>/<artifact>` | `https://<host>:<port>/pulp/content/<base_path>/` |
| Python | `offline_repo/cluster/<arch>/<os>/<minor>/pip_module/<name>==<version>` | `https://<host>:<port>/pypi/<base_path>/` |
| Container | `<image-path-without-registry-host>` | `<host>:<port>/<base_path>:<tag>` |

Important rules:

- A Pulp `--base-path` value is relative. Never include a leading slash,
  `/pulp/content`, `/pypi`, the scheme, host or port.
- The default managed distribution root is `offline_repo/cluster`. Do not
  invent a different root for Repo Manager-owned content.
- RPM, File and Python paths contain OS, minor version and architecture so that
  catalog execution contexts remain isolated.
- Container paths follow the OCI image path and do not use the RPM/File
  distribution root.
- Pulp can return a root-relative RPM/File `base_url` and an internal Python
  origin such as `https://pulp/pypi/...`. `repo_status.yml` normalizes both to
  the configured public HTTPS origin.
- Treat `repo_status.yml` or the container distribution's `registry_path` as
  the consumer source of truth. Do not publish a URL reconstructed from a host
  filesystem path.

For example, these values:

```text
Pulp origin: https://192.0.2.10:2225
Base path:   offline_repo/cluster/x86_64/rhel/10.0/rpms/x86_64_rhel_10.0_baseos
```

produce this RPM repository URL:

```text
https://192.0.2.10:2225/pulp/content/offline_repo/cluster/x86_64/rhel/10.0/rpms/x86_64_rhel_10.0_baseos/
```

## Pulp object naming

Repo Manager uses exact, case-sensitive object names.

| Pulp family | Repository/distribution name | Example |
|-------------|------------------------------|---------|
| RPM | `<arch>_<os>_<minor>_<repository>` | `x86_64_rhel_10.0_baseos` |
| File | `<arch>_<os>_<minor>_<type><artifact>` | `x86_64_rhel_10.0_tarballhelm-v3.20.1-amd64` |
| Python | `<arch>_<os>_<minor>_pip_module<name>==<version>` | `x86_64_rhel_10.0_pip_modulecffi==1.17.1` |
| Public container repository/distribution | `container_repo_<registry-and-path>` with `/` and `:` replaced by `_` | `container_repo_docker.io_library_busybox` |
| Public container remote | `remote_<registry-and-path>` with `/` and `:` replaced by `_` | `remote_docker.io_library_busybox` |

For a configured private registry, the stable registry configuration key is
used in the internal repository and remote identity. Changing the registry
endpoint then reconciles the existing Pulp objects instead of creating a
second identity.

The object relationship is:

```text
Remote -> Repository -> Repository Version -> Publication -> Distribution
                    \-> Task
```

RPM repositories use the full chain. Uploaded File and Python content is
published and distributed from its repository. Container content uses a
remote, repository and distribution, with multiple requested tags retained in
the same image repository.

## Safe inspection

These commands do not intentionally change Pulp state:

```bash
/usr/local/bin/pulp --version
/usr/local/bin/pulp status
systemctl status pulp.service
podman ps --filter name=pulp
```

List active work before deciding that an operation is stalled:

```bash
/usr/local/bin/pulp task list \
  --state-in waiting \
  --state-in running \
  --state-in canceling \
  --limit 100
```

List repositories, remotes and public locations:

```bash
/usr/local/bin/pulp rpm repository list --limit 1000
/usr/local/bin/pulp rpm remote list --limit 1000
/usr/local/bin/pulp rpm distribution list \
  --field name,base_path,base_url --limit 1000

/usr/local/bin/pulp file repository list --limit 1000
/usr/local/bin/pulp file distribution list \
  --field name,base_path,base_url --limit 1000

/usr/local/bin/pulp python repository list --limit 1000
/usr/local/bin/pulp python distribution list \
  --field name,base_path,base_url --limit 1000

/usr/local/bin/pulp container repository list --limit 1000
/usr/local/bin/pulp container remote list --limit 1000
/usr/local/bin/pulp container distribution list \
  --field name,base_path,registry_path --limit 1000
```

Inspect one complete RPM serving chain using its exact name:

```bash
RPM_NAME="x86_64_rhel_10.0_baseos"

/usr/local/bin/pulp rpm remote show --name "$RPM_NAME"
/usr/local/bin/pulp rpm repository show --name "$RPM_NAME"
/usr/local/bin/pulp rpm publication list \
  --repository "$RPM_NAME" --limit 1000
/usr/local/bin/pulp rpm distribution show --name "$RPM_NAME"
```

Inspect exact File, Python or container distributions:

```bash
/usr/local/bin/pulp file distribution show \
  --name x86_64_rhel_10.0_tarballhelm-v3.20.1-amd64

/usr/local/bin/pulp python distribution show \
  --name 'x86_64_rhel_10.0_pip_modulecffi==1.17.1'

/usr/local/bin/pulp container distribution show \
  --name container_repo_docker.io_library_busybox
```

Use the generated status file to obtain normalized consumer URLs:

```bash
REPO_MANAGER_ROOT="${REPO_MANAGER_DATA_PATH:-${OMNIA_DATA_PATH:-/opt/omnia}/repo_manager}"
PROJECT_NAME="${OMNIA_PROJECT_NAME:-project_default}"

sed -n '1,260p' \
  "$REPO_MANAGER_ROOT/output/$PROJECT_NAME/repo_status.yml"
```

Validate the served route with the generated CA before giving it to a
downstream system:

```bash
PULP_CA="$REPO_MANAGER_ROOT/pulp_config/settings/certs/pulp_webserver.crt"
RPM_URL="https://<host>:<port>/pulp/content/<rpm-base-path>"
PYTHON_URL="https://<host>:<port>/pypi/<python-base-path>"

curl --head --cacert "$PULP_CA" \
  "$RPM_URL/repodata/repomd.xml"
curl --head --cacert "$PULP_CA" \
  "$PYTHON_URL/simple/"
```

An HTTP redirect is acceptable only when its `Location` retains the configured
public host and port. A redirect to an internal name such as `https://pulp/...`
is not externally consumable. Reconcile the deployment with `--tags prepare`
and verify the route again before publishing it. Do not work around the problem
by disabling certificate or hostname verification.

## Supported administrative operations

Run these commands from `src/repo_manager/playbooks`. They preserve Pulp and
Repo Manager state together.

| Goal | Command |
|------|---------|
| Deploy or reconcile Pulp | `ansible-playbook repo_manager.yml --tags prepare` |
| Validate inputs and catalog mappings | `ansible-playbook repo_manager.yml --tags precheck` |
| Add or restore catalog-selected content | `ansible-playbook repo_manager.yml --tags download` |
| Force all required RPM remotes to check upstream | `ansible-playbook repo_manager.yml --tags download -e "resync_repos=all"` |
| Force one exact RPM repository | `ansible-playbook repo_manager.yml --tags download -e "resync_repos=x86_64_rhel_10.0_baseos"` |
| Generate normalized consumer URLs | `ansible-playbook repo_manager.yml --tags status` |
| Remove one exact RPM repository | `ansible-playbook repo_manager.yml --tags cleanup_repos -e "cleanup_repos=x86_64_rhel_10.0_epel"` |
| Remove one container tag | `ansible-playbook repo_manager.yml --tags cleanup_repos -e "cleanup_containers=docker.io/library/busybox:1.36"` |
| Remove a complete container image and all tags | `ansible-playbook repo_manager.yml --tags cleanup_repos -e "cleanup_containers=docker.io/library/busybox"` |
| Remove one File or Python catalog artifact | `ansible-playbook repo_manager.yml --tags cleanup_repos -e "cleanup_files=cffi==1.17.1"` |
| Remove all Pulp content of selected categories | Use the matching `cleanup_repos=all`, `cleanup_containers=all` or `cleanup_files=all` value with `-e "force=true"` |
| Remove the complete Pulp deployment | `ansible-playbook repo_manager.yml --tags cleanup_pulp` |

To add permanent content, update the catalog and Repo Manager input mapping,
then run:

```bash
ansible-playbook repo_manager.yml --tags "precheck,download,status"
```

To remove catalog-managed content permanently, remove its catalog reference,
run the matching selective cleanup command, and regenerate status after the
remaining catalog is synchronized. Selective cleanup invalidates the old
`repo_status.yml`; use `download,status` to restore any still-required content
and publish a new status file.

## Advanced manual Pulp operations

### Before using raw Pulp commands

Raw create, sync, upload, publish, distribute and destroy commands bypass:

- `pulp_mirror_index.json` and `global_package_index.json`;
- package and group status CSV files;
- `catalog_execution_summary.yml`;
- catalog reference and shared-ownership checks;
- automatic `repo_status.yml` invalidation; and
- Repo Manager's interrupted-run reconciliation and cleanup verification.

Do not modify an existing Repo Manager-owned object with raw Pulp commands.
For deliberately unmanaged content, use a unique object name and a unique final
base-path segment while retaining the same OS/version/architecture hierarchy.

The following examples use `manual-` names for that reason. Replace every
example value only after verifying that neither the object name nor base path
already exists.

### Manually synchronize an RPM repository

```bash
RPM_NAME="x86_64_rhel_10.0_manual-tools"
RPM_URL="https://mirror.example/rhel/10.0/x86_64/manual-tools/"
RPM_BASE_PATH="offline_repo/cluster/x86_64/rhel/10.0/rpms/$RPM_NAME"

/usr/local/bin/pulp rpm remote create \
  --name "$RPM_NAME" --url "$RPM_URL" --policy on_demand
/usr/local/bin/pulp rpm repository create --name "$RPM_NAME"
/usr/local/bin/pulp rpm repository sync \
  --name "$RPM_NAME" --remote "$RPM_NAME"
/usr/local/bin/pulp rpm publication create --repository "$RPM_NAME"
/usr/local/bin/pulp rpm publication list \
  --repository "$RPM_NAME" --field pulp_href,pulp_created --limit 1000
```

Copy the newest publication HREF returned by the last command, then complete
the distribution:

```bash
RPM_PUBLICATION_HREF="/pulp/api/v3/publications/rpm/rpm/<uuid>/"

/usr/local/bin/pulp rpm distribution create \
  --name "$RPM_NAME" --base-path "$RPM_BASE_PATH" \
  --repository "$RPM_NAME"
/usr/local/bin/pulp rpm distribution update \
  --name "$RPM_NAME" --publication "$RPM_PUBLICATION_HREF"
/usr/local/bin/pulp rpm distribution show --name "$RPM_NAME"
```

Use `immediate`, `on_demand` or `streamed` only after deciding whether Pulp
must retain all payloads, fetch and retain requested payloads, or stream them.
Do not use `streamed` for content that must remain fully retained offline.

### Manually upload a File artifact

```bash
FILE_NAME="x86_64_rhel_10.0_tarballmanual-tool-1.0"
FILE_PATH="/absolute/path/manual-tool-1.0.tar.gz"
FILE_RELATIVE_PATH="manual-tool-1.0.tar.gz"
FILE_BASE_PATH="offline_repo/cluster/x86_64/rhel/10.0/tarball/manual-tool-1.0"

/usr/local/bin/pulp file repository create --name "$FILE_NAME"
/usr/local/bin/pulp file content upload \
  --repository "$FILE_NAME" --file "$FILE_PATH" \
  --relative-path "$FILE_RELATIVE_PATH"
/usr/local/bin/pulp file publication create --repository "$FILE_NAME"
/usr/local/bin/pulp file distribution create \
  --name "$FILE_NAME" --base-path "$FILE_BASE_PATH" \
  --repository "$FILE_NAME"
/usr/local/bin/pulp file distribution show --name "$FILE_NAME"
```

The local file path must be absolute and readable. Quoted paths containing
spaces remain one CLI argument.

### Manually upload a Python package

```bash
PYTHON_NAME='x86_64_rhel_10.0_pip_moduleexample_pkg==1.0.0'
PYTHON_FILE="/absolute/path/example_pkg-1.0.0-py3-none-any.whl"
PYTHON_RELATIVE_PATH="example_pkg-1.0.0-py3-none-any.whl"
PYTHON_BASE_PATH="offline_repo/cluster/x86_64/rhel/10.0/pip_module/example_pkg==1.0.0"

/usr/local/bin/pulp python repository create --name "$PYTHON_NAME"
/usr/local/bin/pulp python content upload \
  --repository "$PYTHON_NAME" --file "$PYTHON_FILE" \
  --relative-path "$PYTHON_RELATIVE_PATH"
/usr/local/bin/pulp python publication create --repository "$PYTHON_NAME"
/usr/local/bin/pulp python distribution create \
  --name "$PYTHON_NAME" --repository "$PYTHON_NAME" \
  --base-path "$PYTHON_BASE_PATH"
/usr/local/bin/pulp python distribution show --name "$PYTHON_NAME"
```

The Python consumer base is
`https://<host>:<port>/pypi/<PYTHON_BASE_PATH>/`. A Python simple-index client
uses the corresponding `simple/` child route.

### Manually synchronize a public container image

```bash
CONTAINER_REPOSITORY="container_repo_manual_docker.io_library_busybox"
CONTAINER_REMOTE="remote_manual_docker.io_library_busybox"
CONTAINER_UPSTREAM="https://registry-1.docker.io"
CONTAINER_UPSTREAM_NAME="library/busybox"
CONTAINER_TAG="1.36"
CONTAINER_BASE_PATH="manual/library/busybox"

/usr/local/bin/pulp container repository create \
  --name "$CONTAINER_REPOSITORY"
/usr/local/bin/pulp container remote create \
  --name "$CONTAINER_REMOTE" --url "$CONTAINER_UPSTREAM" \
  --upstream-name "$CONTAINER_UPSTREAM_NAME" --policy on_demand \
  --include-tags "[\"$CONTAINER_TAG\"]" \
  --exclude-tags '["*sha256*.sig"]'
/usr/local/bin/pulp container repository sync \
  --name "$CONTAINER_REPOSITORY" --remote "$CONTAINER_REMOTE"
/usr/local/bin/pulp container distribution create \
  --name "$CONTAINER_REPOSITORY" \
  --repository "$CONTAINER_REPOSITORY" \
  --base-path "$CONTAINER_BASE_PATH"
/usr/local/bin/pulp container distribution show \
  --name "$CONTAINER_REPOSITORY"
```

Use the returned `registry_path` plus `:$CONTAINER_TAG` as the pull reference.
Configure authenticated or private-CA registries through Repo Manager and its
Vault-backed credential flow; do not place registry passwords in shell history.

### Delete deliberately unmanaged manual content

Review each exact name first. Deletion is dependency-ordered and irreversible
unless the source content remains available for another synchronization.

For RPM content, delete the distribution, every publication HREF, the remote
and then the repository:

```bash
/usr/local/bin/pulp rpm distribution destroy --name "$RPM_NAME"
/usr/local/bin/pulp rpm publication list \
  --repository "$RPM_NAME" --field pulp_href --limit 1000
/usr/local/bin/pulp rpm publication destroy --href "$RPM_PUBLICATION_HREF"
/usr/local/bin/pulp rpm remote destroy --name "$RPM_NAME"
/usr/local/bin/pulp rpm repository destroy --name "$RPM_NAME"
```

Repeat the publication destroy command for every HREF returned by the list.

For an uploaded File or Python repository, delete the distribution, every
publication HREF and then the repository:

```bash
/usr/local/bin/pulp file distribution destroy --name "$FILE_NAME"
/usr/local/bin/pulp file publication list \
  --repository "$FILE_NAME" --field pulp_href --limit 1000
/usr/local/bin/pulp file publication destroy --href "<file-publication-href>"
/usr/local/bin/pulp file repository destroy --name "$FILE_NAME"

/usr/local/bin/pulp python distribution destroy --name "$PYTHON_NAME"
/usr/local/bin/pulp python publication list \
  --repository "$PYTHON_NAME" --field pulp_href --limit 1000
/usr/local/bin/pulp python publication destroy \
  --href "<python-publication-href>"
/usr/local/bin/pulp python repository destroy --name "$PYTHON_NAME"
```

For a manual container, delete the distribution, remote and repository:

```bash
/usr/local/bin/pulp container distribution destroy \
  --name "$CONTAINER_REPOSITORY"
/usr/local/bin/pulp container remote destroy --name "$CONTAINER_REMOTE"
/usr/local/bin/pulp container repository destroy \
  --name "$CONTAINER_REPOSITORY"
```

Do not run global orphan cleanup as a routine diagnostic command. Repo Manager
runs it after verified selective content changes. A global manual orphan cleanup
can reclaim content referenced only by unmanaged workflows.

## State and recovery after manual intervention

| State | Location | Raw Pulp command updates it? |
|-------|----------|------------------------------|
| Pulp object state | Pulp database and content storage | Yes |
| Package mirror state | `<REPO_MANAGER_DATA_PATH>/log/<os>/<minor>/mirror_status/pulp_mirror_index.json` | No |
| Expected catalog identities | `<REPO_MANAGER_DATA_PATH>/log/<os>/<minor>/mirror_status/global_package_index.json` | No |
| Package/group results | `<REPO_MANAGER_DATA_PATH>/log/<os>/<minor>/<arch>/...` | No |
| Context execution summary | `<REPO_MANAGER_DATA_PATH>/log/<os>/catalog_execution_summary.yml` | No |
| Consumer output | `<REPO_MANAGER_DATA_PATH>/output/<project>/repo_status.yml` | No |

If a raw command changed a Repo Manager-owned object, stop making manual
changes and run the normal reconciliation flow:

```bash
ansible-playbook repo_manager.yml --tags "precheck,download,status"
```

Repo Manager will inspect the external Pulp state and repair missing remote,
repository, publication or distribution stages where supported. If raw
deletion removed required content, it will download that content again. Do not
edit mirror indexes or status CSV files by hand to make a rerun skip work.

## Related documentation

- [Architecture and supported tags](architecture.md)
- [Content configuration](content-configuration-guide.md)
- [Input contract](contracts/input-contract.md)
- [Output contract](contracts/output-contract.md)
- [Security](security.md)
- [Troubleshooting](troubleshooting.md)
