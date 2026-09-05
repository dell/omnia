# Content Configuration Guide

## Overview

The catalog is the source of truth for content selection. Each catalog package
declares its type and one or more sources. Repo Manager maps those sources to
RPM repositories or container registries in `repo_manager_config.yml`.

**Catalog location**: Exact `.json` file from `CATALOG_FILE_PATH`

**Repository configuration**:
`<REPO_MANAGER_DATA_PATH>/input/<project>/repo_manager_config.yml`

---

## Resolution Flow

```text
functional layer -> group -> package -> source
                                      |      |
                                      |      +--> registry -> public/configured registry
                                      +---------> reponame -> version + arch repository
                                                     |
                                                     +--> Pulp content
```

Only packages reachable from selected functional layers and groups are processed.
The source's OS version and architecture determine which repository definition is
used.

## Catalog Package Structure

### RPM Example

```json
{
  "bash": {
    "name": "bash",
    "packagetype": "rpm",
    "sources": [
      {
        "architecture": "x86_64",
        "name": "rhel",
        "version": ["10.0"],
        "reponame": "baseos"
      }
    ]
  }
}
```

This resolves to:

```yaml
repositories:
  "10.0":
    x86_64:
      baseos: {}
```

### Container Image Example

```json
{
  "registry_k8s_io/kube_controller_manager": {
    "name": "registry.k8s.io/kube-controller-manager",
    "packagetype": "image",
    "tag": "v1.35.1",
    "sources": [
      {
        "architecture": "x86_64",
        "registry": "registry.k8s.io",
        "name": "rhel",
        "version": ["10.0"]
      }
    ]
  }
}
```

`registry.k8s.io` is a known public registry, so a `registries` entry is not
required unless custom authentication or TLS settings are needed.

---

## Supported Content Types

| `packagetype` | Required package fields | Source mapping | Pulp plugin |
|---------------|-------------------------|----------------|-------------|
| `rpm` | `name` | `reponame` | RPM |
| `rpm_repo` | `name` | `reponame` | RPM |
| `rpm_file` | `name` and direct source | `reponame` when applicable | RPM |
| `image` | `name`, `tag` | `registry` | Container |
| `pip_module` | `name` with optional exact `==version`, or separate `version` | package source | Python |
| `tarball` | `name`, `version` | URL/source metadata | File |
| `manifest` | `name`, `version` | URL/source metadata | File |
| `git` | `name`, version/ref | URL/source metadata | File |
| `iso` | `name`, `version` | URL/source metadata | File |
| `shell` | `name`, `version` | URL/source metadata | File |
| `ansible_galaxy_collection` | collection name, version | Galaxy source | File |

Python packages may use either `name: "cffi==1.17.1"` or the equivalent
`name: "cffi"` with `version: "1.17.1"`. Repo Manager canonicalizes both to
`cffi==1.17.1` for download, Pulp identity, status tracking and selective
cleanup. When both forms provide a version, the values must match.

### rpm and rpm_repo

| Type | Behavior |
|------|----------|
| `rpm` | Validate or synchronize the named RPM according to repository policy |
| `rpm_repo` | Use DNF to download the named package plus dependencies, then make them available through Pulp |

`rpm_repo` requires retained Pulp content. Its mapped repository must not resolve
to the `streamed` policy.

### Multiple Tags for One Image

The same image name can appear with multiple tags:

```text
docker.io/victoriametrics/operator:v0.68.3
docker.io/victoriametrics/operator:config-reloader-v0.68.3
```

Both tags use one Pulp container repository but remain separate catalog, status
and mirror identities. Synchronizing or cleaning one tag does not remove its
sibling tag.

---

## RPM Repository Mapping

The lookup key is:

```text
catalog source version + architecture + reponame
```

Example:

```yaml
repositories:
  "10.0":
    x86_64:
      epel:
        url: "https://download.example.com/epel/10/Everything/x86_64/"
        gpgkey: "https://download.example.com/keys/RPM-GPG-KEY-EPEL-10"
        policy: partial
        caching: true
        priority: 99
```

### Subscription Repositories

BaseOS, AppStream and CodeReady Builder support two modes:

```yaml
# Subscription-provided content
baseos: {}
appstream: {}
codeready-builder: {}
```

When a matching RHEL subscription repository is available, Repo Manager fills
the URL and entitlement certificate paths. If a user supplies a URL and related
settings, those user values take precedence. Without subscription content, empty
entries fail validation and the user must provide URLs.

### Additional and User Repositories

```yaml
repositories:
  "10.0":
    x86_64:
      additional_repos:
        internal-tools:
          url: "https://repo.example.com/internal-tools/"
          priority: 99
      user_repos:
        slurm_custom:
          url: "https://repo.example.com/slurm/"
          priority: 100
```

The catalog must use the same `reponame` value.

`additional_repos` are published as one aggregated Pulp repository per
architecture. All entries in that section must therefore have the same effective
priority. An omitted priority has the DNF default value of 99; mixing that default
with another value fails precheck rather than publishing an ambiguous priority.

---

## Container Registry Mapping

### Public Registry

Known public registries are resolved directly:

```yaml
registries:
```

Docker Hub credentials remain optional and are collected using the existing
Docker credential prompts.

### Private Registry with Basic Authentication

Configuration:

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
      ca_path: ""
      client_cert_path: ""
      client_key_path: ""
      insecure: false
```

Encrypted credential mapping:

```yaml
registry_credentials:
  registries/harbor-production:
    registry: "private_registry"
    username: "omnia-pull-user"
    password: "<secret>"
```

Catalog package and source:

```json
{
  "name": "harbor.example.com:443/library/nginx",
  "packagetype": "image",
  "sources": [{
    "architecture": "x86_64",
    "registry": "private_registry",
    "version": ["10.0"]
  }],
  "tag": "1.25.2"
}
```

Repo Manager passes the resolved username and password to the Pulp container
remote. Credentials are not placed in the catalog, main configuration or logs.
The image name must use the exact configured endpoint. Names such as
`private_registry/library/nginx` are rejected; no alias-prefix fallback exists.

---

## Policy Resolution

Per-repository fields have priority over global settings:

```text
repository policy  > repo_config
repository caching > caching_policy
```

| Effective policy | Effective caching | Pulp RPM policy |
|------------------|-------------------|-----------------|
| `always` | `false` | `immediate` |
| `always` | `true` | `on_demand` |
| `partial` | `false` | `streamed` |
| `partial` | `true` | `on_demand` |
| `never` | either | `streamed` |

Container synchronization is independent of RPM policy. Its default is
`container_sync_policy: immediate` so OCI content is retained for offline use.

---

## Architecture Support

Repo Manager resolves every package source independently:

| Catalog source | Required configuration |
|----------------|------------------------|
| `x86_64`, RHEL 10.0 | `repositories."10.0".x86_64` |
| `aarch64`, RHEL 10.0 | `repositories."10.0".aarch64` |
| Both architectures | Both repository maps |

A single catalog may contain x86_64 management groups and aarch64 compute
groups. Only packages reachable from those groups are synchronized. Repository,
status and mirror identities include architecture, preventing cross-architecture
collisions.

---

## Concurrency Controls

These controls are independent:

| Setting | Default | Purpose |
|---------|---------|---------|
| `parallel_config.default_nthreads` | `3` | General catalog package worker processes |
| `rpm_repo_config.thread_pool_size` | `3` | RPM repositories processed in each Pulp stage |
| `dnf_config.max_concurrent_commands` | `1` | Maximum simultaneous DNF commands |

Increasing general workers does not increase DNF concurrency. Keep DNF at one;
reduce the other controls when Pulp CPU, memory, network, or storage is
constrained.

## Validation Checklist

- Catalog path exists and ends in `.json`.
- Every package source has a supported architecture and OS version.
- Every RPM source `reponame` exists in the matching repository map.
- Every non-public registry exists in `registries`.
- Every basic-auth registry has a matching Vault credential entry.
- Repository priority is between 1 and 100.
- `rpm_repo` does not resolve to streamed content.
- Both architectures are configured when selected by the catalog.
