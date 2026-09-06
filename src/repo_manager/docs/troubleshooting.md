# Repo Manager -- Troubleshooting

## Common Issues

### 1. Required environment variable is missing

```text
SYSTEM_ADMIN_NIC_IPV4 or CATALOG_FILE_PATH is not set
```

**Cause**: Repo Manager validates both values before running an operation.

**Fix**:

```bash
export SYSTEM_ADMIN_NIC_IPV4=<admin_ipv4>
export CATALOG_FILE_PATH=/path/to/catalog.json
```

`CATALOG_FILE_PATH` may use any file name, but it must identify an existing
regular file whose extension is `.json`.

If context resolution reports `invalid artifact URL`, verify that catalog
artifact URLs use HTTP(S), do not contain embedded credentials or fragments,
and do not place passwords or tokens in query parameters. Public selectors
such as `?version=1.7.7` are supported.

---

### 2. Runtime input file is missing

```text
repo_manager_config.yml not found
```

**Cause**: The source inputs were not staged, the project name differs, or a
custom data path was selected.

**Fix**:

```bash
cd src/repo_manager
./domain-init.sh
ls "${REPO_MANAGER_DATA_PATH:-${OMNIA_DATA_PATH:-/opt/omnia}/repo_manager}/input/${OMNIA_PROJECT_NAME:-project_default}"
```

Edit source files under `src/repo_manager/input/`, then run `domain-init.sh`
again to stage them.

---

### 3. Input validation rejects a field

```text
Additional properties are not allowed
```

**Cause**: An unknown key, an uppercase key, an invalid policy, a priority
outside `1-100`, or an invalid port was supplied.

**Fix**: Use lowercase configuration keys and compare the file with
`input/repo_manager_config.yml` or the [input contract](contracts/input-contract.md).
Registry and repository values such as URLs and usernames may contain their
normal case-sensitive values.

---

### 4. Pulp is not running or its endpoint is unavailable

```text
PULP VALIDATION FAILED
```

**Verify**:

```bash
systemctl status pulp.service
podman ps --filter name=pulp
pulp status
```

**Fix**:

```bash
cd src/repo_manager/playbooks
ansible-playbook repo_manager.yml --tags prepare
```

Repo Manager deploys HTTPS only. The configured host port forwards to port
`443` inside the Pulp container.

---

### 5. `pulp status` reports a self-signed certificate error

**Cause**: An unmanaged Pulp CLI or direct HTTPS client is not using the Repo
Manager CA. Older deployments also allowed the virtual environment's native
`pulp` entry point to shadow the managed `/usr/local/bin/pulp` launcher.

**Fix**: Run `prepare` again. If `OMNIA_VENV_PATH` is non-empty, Repo Manager
uses that virtual environment and links its `bin/pulp` entry point to the
managed `/usr/local/bin/pulp` launcher. If `OMNIA_VENV_PATH` is unset or empty,
Repo Manager uses the system Python runtime. The generated CA is supplied
automatically in both modes.

```bash
cd <OMNIA_SOURCE_PATH>/repo_manager/playbooks
ansible-playbook repo_manager.yml --tags prepare
```

For a separate diagnostic client, use this CA explicitly:

```text
<REPO_MANAGER_DATA_PATH>/pulp_config/settings/certs/pulp_webserver.crt
```

A persistent `PULP_CA_BUNDLE` shell export is not required for normal Repo
Manager or managed Pulp CLI use.

Full Pulp cleanup removes the server, CLI configuration, and CA trust while
preserving the managed launcher and backend. The Omnia venv link is preserved
only when `OMNIA_VENV_PATH` is configured and available. Consequently,
`pulp --version` remains available, but server commands such as `pulp status`
remain unavailable until `prepare` redeploys and reconfigures Pulp.

---

### 6. Credential or Vault validation fails

**Verify metadata without printing secrets**:

```bash
ls -l \
  "${REPO_MANAGER_DATA_PATH:-${OMNIA_DATA_PATH:-/opt/omnia}/repo_manager}/input/${OMNIA_PROJECT_NAME:-project_default}/repo_manager_config_credentials.yml" \
  "${REPO_MANAGER_DATA_PATH:-${OMNIA_DATA_PATH:-/opt/omnia}/repo_manager}/input/${OMNIA_PROJECT_NAME:-project_default}/.repo_manager_config_credentials_key"
```

Both files must be root-owned and mode `0600`. Run `--tags prepare` to collect
missing Pulp, Docker Hub, or private-registry credentials. Never paste Vault
contents or passwords into logs or issue reports.

---

### 7. Private registry image synchronization fails

**Cause**: The catalog registry name, registry configuration key, credential
`vault_path`, or TLS settings do not form one complete mapping.

**Check this chain**:

```text
catalog source.registry
  -> repo_manager_config.yml registries.<registry>
  -> auth.credentials.vault_path
  -> encrypted registry_credentials.<vault_path>
  -> Pulp container remote
```

Public registries do not require a `registries` entry unless custom
authentication or TLS is needed. For basic authentication, rerun `prepare` to
collect the mapped username and password.

---

### 8. Empty BaseOS, AppStream, or CodeReady Builder entry fails

```yaml
baseos: {}
appstream: {}
codeready-builder: {}
```

**Cause**: Only catalog-referenced `baseos`, `appstream` and
`codeready-builder` entries may omit their URLs, and only when the Repo Manager
host has usable RHEL subscription access. Every referenced repository requires
an explicit URL when subscription access is disabled.

**Verify the host subscription without displaying certificate content**:

```bash
subscription-manager identity
subscription-manager status
subscription-manager release --list
subscription-manager repos --list-enabled
```

Then run the Repo Manager precheck from its playbook directory:

```bash
ansible-playbook repo_manager.yml --tags precheck -vv
```

Use the failure summary to check the active catalog minor version and every
selected architecture. The repository key must exactly match the catalog
`reponame`; accepted mappings can be flat or nested under `user_repos` or
`additional_repos`.

| Condition | Resolution |
|-----------|------------|
| Subscription is valid and a referenced subscription repository is empty | Ensure the repository is available for the active RHEL version; Repo Manager prefers EUS and then tries standard |
| Subscription is valid but a custom repository is empty | Add its explicit URL; subscriptions do not supply custom repositories |
| Subscription is unavailable | Add an explicit URL for every referenced repository, including BaseOS, AppStream and CodeReady Builder |
| An explicit URL is configured | Repo Manager uses it instead of subscription discovery |
| An unused repository is empty or missing | No action is required for the current catalog execution |

For an explicit repository URL that does not require client authentication,
verify its metadata endpoint without downloading repository content:

```bash
REPO_URL="https://mirror.example/rhel/10.2/x86_64/baseos/"
curl --fail --silent --show-error --output /dev/null \
  "${REPO_URL%/}/repodata/repomd.xml"
```

Do not place repository credentials directly in this command. For mTLS URLs,
use the configured CA, client certificate and client key through a protected
configuration and rely on Repo Manager precheck for the authoritative result.

For mixed `x86_64` and `aarch64` catalogs, each architecture needs its own
matching repository entry or subscription source. An x86_64 URL cannot satisfy
an aarch64 repository. When several repositories are missing, Repo Manager
reports them together by architecture.

---

### 9. RPM package or repository synchronization fails

**Check**:

1. The catalog `reponame` exactly matches the configured repository key.
2. The catalog version and architecture exist under `repositories`.
3. The repository URL and GPG key are reachable.
4. A catalog item with `packagetype: rpm_repo` does not resolve to `streamed`.
5. The detailed group log contains the failing package and repository.

`rpm` downloads selected packages and dependencies. `rpm_repo` synchronizes the
mapped repository as retained Pulp content.

---

### 10. Download appears to be hung

**Cause**: A subgroup is processed inside one Ansible module invocation. Large
container or RPM operations can take several minutes before the task returns.

**Verify progress**:

```bash
tail -F "${REPO_MANAGER_DATA_PATH:-${OMNIA_DATA_PATH:-/opt/omnia}/repo_manager}/log/rhel/10.0/standard.log"

find "${REPO_MANAGER_DATA_PATH:-${OMNIA_DATA_PATH:-/opt/omnia}/repo_manager}/log" \
  -path '*/logs/package_status_*.log' -type f -printf '%T@ %p\n' \
  | sort -nr | head
```

The standard log emits a heartbeat approximately every 60 seconds. It reports
finished tasks, remaining tasks, elapsed time, worker count, and the detailed-log
directory. Unchanged counts can still mean one long Pulp operation is active.
Do not start a second Repo Manager instance.

---

### 11. DNF lock or metadata-cache error

Repo Manager separates general artifact workers from DNF command concurrency.
Keep the DNF limit at one even if image/file parallelism is increased:

```yaml
dnf_config:
  max_concurrent_commands: 1
```

`parallel_config.default_nthreads` may be increased only after validating Pulp,
network, CPU, memory and disk capacity. It does not raise the DNF concurrency
limit.

---

### 12. One image has multiple tags

Repo Manager stores same-name images in one Pulp container repository while
tracking each tag as a distinct catalog identity.

- `registry.example.com/team/image:v1` cleanup removes only `v1`.
- `registry.example.com/team/image:v2` remains available.
- An untagged `registry.example.com/team/image` cleanup removes the complete
  repository and every tag.

Use an exact tag whenever only one version should be deleted.

---

### 13. Cleanup log is missing

| Operation | Log or result |
|-----------|---------------|
| Top-level execution | `/var/log/omnia/repo_manager/repo_manager.log` |
| Direct cleanup playbook | `/var/log/omnia/repo_manager/cleanup.log` |
| Selective cleanup details | `<REPO_MANAGER_DATA_PATH>/log/<os>/<version>/cleanup/standard.log` |
| Selective cleanup results | `<REPO_MANAGER_DATA_PATH>/log/<os>/<version>/cleanup/cleanup_status.csv` |
| Multi-version/shared cleanup details | `<REPO_MANAGER_DATA_PATH>/log/<os>/cleanup/standard.log` |
| Multi-version/shared cleanup results | `<REPO_MANAGER_DATA_PATH>/log/<os>/cleanup/cleanup_status.csv` |

Full Pulp cleanup removes the Repo Manager runtime log directory by default.
Use `-e "cleanup_logs=false"` when the logs must be retained.

---

### 14. `repo_status.yml` is absent after selective cleanup

**Cause**: This is intentional. Selective cleanup invalidates the previous
consumer output so it cannot advertise deleted content.

**Fix**:

```bash
ansible-playbook repo_manager.yml --tags "download,status"
```

Using `--tags status` alone after cleanup writes the current incomplete Pulp
state with `overall_status: failed` and lists the missing RPM repositories. The
status play then fails so that the incomplete output cannot be mistaken for a
ready repository service.

---

### 15. Disk space is low or a Pulp task failed

**Verify**:

```bash
df -h
podman logs --tail 200 pulp
pulp task list --state running --state failed
```

Resolve the storage, registry, certificate, or source-repository failure before
rerunning `download`. Successful composite mirror identities are reused, so a
rerun does not intentionally download every completed artifact again.

---

## Log Locations

| Content | Path |
|---------|------|
| Main Ansible log | `/var/log/omnia/repo_manager/repo_manager.log` |
| Version summary and heartbeat | `<REPO_MANAGER_DATA_PATH>/log/<os>/<version>/standard.log` |
| Group summary | `<REPO_MANAGER_DATA_PATH>/log/<os>/<version>/<arch>/groups_status.csv` |
| Package status | `<REPO_MANAGER_DATA_PATH>/log/<os>/<version>/<arch>/<group>/status.csv` |
| Worker details | `<REPO_MANAGER_DATA_PATH>/log/<os>/<version>/<arch>/<group>/logs/` |
| Mirror state | `<REPO_MANAGER_DATA_PATH>/log/<os>/<version>/mirror_status/` |
| Catalog operations | `<REPO_MANAGER_DATA_PATH>/log/catalog/catalog_manager.log` |
| Pulp container logs | `<REPO_MANAGER_DATA_PATH>/log/pulp/` and `podman logs pulp` |

`REPO_MANAGER_DATA_PATH` defaults to
`${OMNIA_DATA_PATH:-/opt/omnia}/repo_manager`.

---

## Safe Diagnostic Commands

```bash
# Validate environment, input, catalog and subscription sources.
ansible-playbook repo_manager.yml --tags precheck -vv

# Check deployed service and container.
systemctl status pulp.service
podman inspect pulp
pulp status

# List current Pulp objects without changing them.
pulp rpm repository list --limit 1000
pulp container repository list --limit 1000
pulp file repository list --limit 1000
pulp python repository list --limit 1000

# Generate current consumer output after a successful synchronization.
ansible-playbook repo_manager.yml --tags status
```

For field definitions, use the [input contract](contracts/input-contract.md).
For cleanup scope and tag ordering, use the [architecture guide](architecture.md).
