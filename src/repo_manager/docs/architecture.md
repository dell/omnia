# Repo Manager -- Architecture

## System Context

```text
 catalog JSON                  Repo Manager                         downstream consumers
 repo_manager_config.yml       +-------------------------------+    +-------------------+
 endpoint config              | validate -> prepare -> sync    |    | image_build_manager|
 Vault credentials ---------->|          -> status             |--->| cluster workflows  |
 RHEL subscription            |                               |    | administrators     |
                               +---------------+---------------+    +-------------------+
                                               |
                                    HTTPS Pulp content server
                              RPM | OCI images | File | Python
```

Repo Manager validates catalog sources, deploys a local Pulp server, synchronizes
content and generates `repo_status.yml` for downstream Omnia components.

## Execution Mode

**Bare-metal only.** Repo Manager runs on the OIM host with
`connection: local`. It does not SSH to cluster nodes.

Runtime paths are derived from `OMNIA_DATA_PATH` and can be overridden with
`REPO_MANAGER_DATA_PATH`. `/opt/omnia` is only the default data root.

---

## Tag Reference

Run from `src/repo_manager/playbooks`:

```bash
ansible-playbook repo_manager.yml                                  # standard workflow
ansible-playbook repo_manager.yml --tags precheck                  # validate inputs
ansible-playbook repo_manager.yml --tags prepare                   # credentials + Pulp
ansible-playbook repo_manager.yml --tags download                  # synchronize content
ansible-playbook repo_manager.yml --tags status                    # write repo_status.yml
ansible-playbook repo_manager.yml --tags cleanup_repos             # selective cleanup
ansible-playbook repo_manager.yml --tags cleanup_pulp              # remove Pulp deployment
ansible-playbook repo_manager.yml --tags catalog_validate          # validate catalog
```

Standard tags can be combined. Plays still execute in their order in
`repo_manager.yml`:

```bash
ansible-playbook repo_manager.yml --tags "prepare,precheck,download,status"
```

### Tag Behavior Matrix

| Tag | Main action | Credentials | Running Pulp required | Destructive |
|-----|-------------|-------------|-----------------------|-------------|
| *(none)* | prepare, validate, download and status | Yes | Created by workflow | No |
| `precheck` | Environment, schema and catalog validation | No | No | No |
| `prepare` / `deploy` | Collect credentials and deploy Pulp | Yes | No | No |
| `download` / `execute` | Resolve catalog and synchronize content | Yes | Yes | No |
| `status` | Generate `repo_status.yml` from Pulp | No prompt | Yes | No |
| `cleanup_repos` | Remove selected Pulp content | No | Yes | Yes |
| `cleanup_pulp` / `cleanup` | Remove Pulp service and runtime data | No | No | Yes |
| `catalog_generate` | Generate a catalog | No | No | Writes catalog |
| `catalog_add` | Add entries to a catalog | No | No | Writes catalog |
| `catalog_delete` | Delete catalog entries | No | No | Writes catalog |
| `catalog_validate` | Validate a catalog | No | No | No |

Cleanup, catalog, upgrade and rollback plays use the `never` tag. They run only
when explicitly selected. Do not combine cleanup tags with the standard workflow.

---

## Execution Flow

### Step 0: Environment setup (tag: always)

- Load the Omnia environment.
- Resolve `OMNIA_DATA_PATH`, project name, runtime, input, output and log paths.
- Require `SYSTEM_ADMIN_NIC_IPV4` and `CATALOG_FILE_PATH`.
- Load `repo_manager_config.yml` and endpoint configuration.

### Step 1: Precheck (tag: precheck)

- Validate the host environment and required files.
- Validate YAML syntax and JSON schemas.
- Validate catalog-to-repository and catalog-to-registry mappings.
- Validate lowercase configuration keys, repository policies and registry TLS.
- Detect missing URLs when RHEL subscription content is unavailable.

### Step 2: Prepare (tag: prepare)

- Collect or reuse Pulp, Docker Hub and configured-registry credentials.
- Store credentials with Ansible Vault and mode `0600`.
- Generate a self-signed Pulp HTTPS certificate when needed.
- Deploy Pulp as a Podman Quadlet and enable `pulp.service`.
- Publish the configured host port to container port `443`.
- Configure the Pulp CLI and host CA trust.
- Verify the container and Pulp status endpoint.

### Step 3: Download (tag: download)

1. Load and reconcile credentials.
2. Detect the RHEL subscription state.
3. Populate empty BaseOS, AppStream and CodeReady Builder entries from the
   subscription when available.
4. Resolve functional layers, groups and packages from the catalog.
5. Match RPM sources by OS version, architecture and `reponame`.
6. Match container sources by `registry`.
7. Synchronize RPM, OCI image, File and Python content to Pulp.
8. Update group status CSVs and the mirror index.

General catalog workers, RPM-repository workers and DNF command concurrency are
separate controls. DNF command concurrency defaults to one to protect its shared
metadata cache.

### Step 4: Status (tag: status)

- Verify the Pulp endpoint.
- Read actual Pulp distributions.
- Generate `<REPO_MANAGER_DATA_PATH>/output/<project>/repo_status.yml`.
- Include HTTPS repository URLs, file-content URLs and certificate paths.

The status file is generated only when the `status` tag runs. Run it again after
selective cleanup if downstream consumers need an updated view.

### Step 5: Selective cleanup (tag: cleanup_repos)

- `cleanup_repos`: RPM repositories.
- `cleanup_files`: File and Python artifacts.
- Tagged `cleanup_containers`: only the exact OCI tag.
- Untagged `cleanup_containers`: the repository, all tags, distribution and remote.
- `all`: every Pulp object in that cleanup category.
- Update status rows, group state and the mirror index only after verified deletion.
- Run Pulp orphan cleanup after successful changes.

### Step 6: Full cleanup (tag: cleanup_pulp)

- Disable and remove `pulp.service` and its Quadlet.
- Remove the Pulp container, image, configuration and data.
- Remove Pulp CLI configuration and host integration.
- Optionally preserve credentials and Repo Manager runtime logs.

---

## Pulp Deployment

| Item | Behavior |
|------|----------|
| Protocol | HTTPS only |
| Host endpoint | `https://<pulp_server_ip>:<pulp_server_port>` |
| Container endpoint | nginx on port `443` |
| Service | `pulp.service` generated from a Podman Quadlet |
| Persistence | `<REPO_MANAGER_DATA_PATH>/pulp_config/` |
| Certificate | Generated under `pulp_config/settings/certs/` |
| CLI trust | `PULP_CA_BUNDLE` plus an installed host CA anchor |

The user selects the host port in `repo_manager_endpoint_config.yml`. The
container port remains `443`.

## Content Model

| Catalog type | Resolution | Pulp content |
|--------------|------------|--------------|
| `rpm` | Package name and mapped `reponame` | RPM repository |
| `rpm_repo` | DNF resolves package and dependencies | RPM repository |
| `rpm_file` | Direct RPM file | RPM repository |
| `image` | Image name, tag and mapped registry | Container repository |
| `pip_module` | Package and version | Python repository |
| `tarball`, `manifest`, `git`, `iso`, `shell`, `ansible_galaxy_collection` | Type-specific source | File repository |

See [Content Configuration Guide](content-configuration-guide.md) for catalog
mapping and policy behavior.

## Runtime Paths

| Purpose | Path |
|---------|------|
| Input | `<REPO_MANAGER_DATA_PATH>/input/<project>/` |
| Output | `<REPO_MANAGER_DATA_PATH>/output/<project>/` |
| Operational logs | `<REPO_MANAGER_DATA_PATH>/log/` |
| Pulp settings and data | `<REPO_MANAGER_DATA_PATH>/pulp_config/` |
| RHEL entitlement copy | `<REPO_MANAGER_DATA_PATH>/rhel_repo_certs/` |
| Local content staging | `<REPO_MANAGER_DATA_PATH>/offline_repo/` |
| Top-level Ansible log | `/var/log/omnia/repo_manager/repo_manager.log` |

`REPO_MANAGER_DATA_PATH` defaults to `<OMNIA_DATA_PATH>/repo_manager`.

---

## Validation

### Schema Validation

| Schema | Purpose |
|--------|---------|
| `repo_manager_config.json` | Repository, registry and policy structure |
| `repo_manager_endpoint_config.json` | Pulp IP and host port |
| Catalog schema | Functional layers, groups, packages and sources |

### Logic and Runtime Validation

| Check | Failure behavior |
|-------|------------------|
| Required environment and files | Fail before deployment or download |
| Catalog source mappings | Report exact missing repository or registry |
| Repository policy combinations | Reject unsupported or unsafe combinations |
| Subscription repository resolution | Require URLs when subscription content is unavailable |
| Private-registry credentials | Require matching Vault entry for basic auth |
| Pulp health | Stop download, status or cleanup operations immediately |
| Cleanup verification | Update local tracking only after Pulp confirms deletion |

## Related Documentation

- [Input Contract](contracts/input-contract.md)
- [Output Contract](contracts/output-contract.md)
- [Content Configuration Guide](content-configuration-guide.md)
- [Catalog Operations](catalog_operations.md)
- [Security](security.md)
- [Troubleshooting](troubleshooting.md)
