# Repo Manager -- Input Contract

**Domain**: `repo_manager` | **Collection**: `omnia.repo_manager`

---

## 1. repo_manager_config.yml

**Purpose**: Defines RPM repositories, container registries and synchronization
policies.

**Location**: `<REPO_MANAGER_DATA_PATH>/input/<project>/repo_manager_config.yml`

**Schema**: `plugins/module_utils/input_validation/schema/repo_manager_config.json`

### Top-Level Fields

| Field | Type | Required | Default | Description |
|-------|------|----------|---------|-------------|
| `catalog_config` | object | No | -- | Compatibility catalog reference; runtime catalog selection uses `CATALOG_FILE_PATH` |
| `repo_config` | string | Yes | -- | Global RPM policy: `always` or `partial` |
| `caching_policy` | boolean | No | `true` | Global RPM caching behavior |
| `registries` | object or null | No | null | Custom container registries keyed by catalog registry name |
| `repositories` | object | Yes | -- | OS version -> architecture -> repository definitions |

Unknown top-level and nested keys are rejected. Configuration keys are lowercase;
user-provided values such as usernames, passwords and repository names retain
their original case.

### Repository Structure

```yaml
repo_config: partial
caching_policy: true

repositories:
  "10.0":
    x86_64:
      baseos: {}
      appstream: {}
      codeready-builder: {}
      epel:
        url: "https://download.example.com/epel/10/Everything/x86_64/"
        gpgkey: "https://download.example.com/keys/RPM-GPG-KEY-EPEL-10"
        policy: partial
        caching: true
        priority: 99
    aarch64:
      baseos: {}
      appstream: {}
      codeready-builder: {}
```

The architecture key must be `x86_64` or `aarch64`.

### Repository Fields

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `url` | string or null | Conditional | Required without subscription-provided content |
| `gpgkey` | string or null | No | GPG key URL |
| `policy` | string | No | Per-repository override: `always`, `partial` or `never` |
| `caching` | boolean | No | Per-repository caching override |
| `priority` | integer | No | DNF priority from 1 through 100 |
| `sslcacert` | string or null | No | Repository CA certificate |
| `sslclientkey` | string or null | No | mTLS client key |
| `sslclientcert` | string or null | No | mTLS client certificate |

`additional_repos` and `user_repos` can contain extra named repository entries
using the same fields.

All `additional_repos` for one architecture are exposed through a single Pulp
distribution and must resolve to one effective priority. Missing `priority`
means 99 for this comparison. `user_repos` remain independent and may use
different priorities.

### Subscription Rules

| Subscription state | Repository entry | Result |
|--------------------|------------------|--------|
| Enabled | `baseos: {}` | Resolve the matching RHEL EUS repository and entitlement certificates |
| Enabled | Entry contains a user URL | Use the user-provided URL and settings |
| Disabled | Entry contains a valid URL | Use the configured URL |
| Disabled | Empty BaseOS/AppStream/CRB entry | Validation fails with the missing source |

Resolution is performed independently for every catalog OS version and
architecture. An x86_64 subscription on the OIM does not automatically provide
aarch64 content unless the subscription exposes that architecture.

### Registry Structure

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
      ca_path: ""
      client_cert_path: ""
      client_key_path: ""
      insecure: false
```

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `base_url` | string | Yes | Registry base URL including scheme |
| `port` | integer | Yes | Registry port from 1 through 65535 |
| `auth.type` | string | Yes | `none` or `basic` |
| `auth.credentials.vault_path` | string | For `basic` | Key under `registry_credentials` |
| `tls.ca_path` | string or null | No | Custom registry CA |
| `tls.client_cert_path` | string or null | No | mTLS certificate |
| `tls.client_key_path` | string or null | No | mTLS key |
| `tls.insecure` | boolean | No | Disable TLS verification; not recommended |

Known public registries can be used directly. A configured private registry must
match the catalog source's `registry` value and, for basic authentication, a
Vault credential entry.

---

## 2. repo_manager_endpoint_config.yml

**Purpose**: Defines the host-facing Pulp HTTPS endpoint.

**Location**: `<REPO_MANAGER_DATA_PATH>/input/<project>/repo_manager_endpoint_config.yml`

**Schema**: `plugins/module_utils/input_validation/schema/repo_manager_endpoint_config.json`

```yaml
pulp_server_port: 2225
# Optional. SYSTEM_ADMIN_NIC_IPV4 is used when omitted.
# pulp_server_ip: "192.0.2.10"
```

| Field | Type | Required | Default | Description |
|-------|------|----------|---------|-------------|
| `pulp_server_port` | integer | Yes | `2225` | Host HTTPS port from 1 through 65535 |
| `pulp_server_ip` | IPv4 string | No | `SYSTEM_ADMIN_NIC_IPV4` | Host IP advertised to consumers |

Pulp protocol and certificate paths are not user inputs. HTTPS is mandatory;
certificate paths are derived from `REPO_MANAGER_DATA_PATH`.

---

## 3. Catalog JSON

**Purpose**: Selects functional layers, groups, packages, versions,
architectures and sources to synchronize.

**Location**: Exact `.json` path from `CATALOG_FILE_PATH`.

**Producer**: Catalog operations or an approved external catalog pipeline.

### Required Structure

```json
{
  "catalog": {
    "name": "rhel-10.0",
    "version": "1.0",
    "identifier": "example-catalog",
    "description": "Example RHEL catalog",
    "functionallayer": [
      {
        "name": "baseos_rhel_10_0_x86_64",
        "components": ["baseos_group"]
      }
    ],
    "groups": {
      "baseos_group": {
        "name": "baseos_group",
        "type": "base_os",
        "description": "Base OS packages",
        "components": ["bash"],
        "os": "rhel",
        "os_version": "10.0"
      }
    },
    "packages": {
      "bash": {
        "name": "bash",
        "packagetype": "rpm",
        "sources": [
          {
            "architecture": "x86_64",
            "reponame": "baseos",
            "name": "rhel",
            "version": ["10.0"]
          }
        ]
      }
    }
  }
}
```

### Package Fields Consumed

| Field | Purpose |
|-------|---------|
| `name` | Upstream package, image or artifact name |
| `packagetype` | Selects the Repo Manager processing path |
| `version` or `tag` | Package version or OCI image tag |
| `sources[].architecture` | Selects `x86_64` or `aarch64` |
| `sources[].version` | Selects one or more OS versions |
| `sources[].reponame` | Maps RPM content to `repositories` |
| `sources[].registry` | Maps OCI images to public or configured registries |

Every referenced repository and non-public registry must resolve before download
starts. Multiple tags of the same image are independent catalog identities.

See [Content Configuration Guide](../content-configuration-guide.md) and
[Catalog Operations](../catalog_operations.md).

---

## 4. repo_manager_config_credentials.yml

**Purpose**: Stores Pulp, Docker Hub and private-registry credentials.

**Location**: `<REPO_MANAGER_DATA_PATH>/input/<project>/repo_manager_config_credentials.yml`

**Generated by**: `collect_repo_credentials` role.

**Vault key**: `<REPO_MANAGER_DATA_PATH>/input/<project>/.repo_manager_config_credentials_key`

Both files are root-owned with mode `0600`. The credential file is encrypted
with Ansible Vault at rest.

```yaml
pulp_username: "admin"
pulp_password: "<secret>"
docker_username: ''
docker_password: ''

registry_credentials:
  registries/harbor-production:
    registry: "harbor.example.com"
    username: "omnia-pull-user"
    password: "<secret>"
```

| Field | Required | Description |
|-------|----------|-------------|
| `pulp_username` | Yes | Pulp administrator username |
| `pulp_password` | Yes | Pulp administrator password |
| `docker_username` | No | Docker Hub username |
| `docker_password` | With Docker username | Docker Hub password/token |
| `registry_credentials.<vault_path>.registry` | For private registry auth | Registry mapping |
| `registry_credentials.<vault_path>.username` | For basic auth | Registry username |
| `registry_credentials.<vault_path>.password` | For basic auth | Registry password/token |

When Docker Hub credentials are not used, both Docker values are stored as
empty strings. Missing, YAML null, whitespace-only, and legacy `"None"` values
are normalized to `''`; anonymous public pulls do not run `podman login`.

Do not edit encrypted values directly and never commit either credential file.

---

## 5. Environment Variables

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `SYSTEM_ADMIN_NIC_IPV4` | Yes | -- | OIM admin-network IPv4 and default Pulp IP |
| `CATALOG_FILE_PATH` | Yes | -- | Exact catalog `.json` path |
| `OMNIA_DATA_PATH` | No | `/opt/omnia` | Omnia data root |
| `REPO_MANAGER_DATA_PATH` | No | `<OMNIA_DATA_PATH>/repo_manager` | Repo Manager runtime root |
| `REPO_MANAGER_INPUT_PROJECT_DIR` | No | Derived | Explicit project input directory override |
| `OMNIA_PROJECT_NAME` | No | `project_default` | Project directory name |

---

## 6. Dependency Diagram

```text
repo_manager_config.yml        repo_manager_endpoint_config.yml
 repositories + registries     HTTPS IP + host port
             |                         |
             +------------+------------+
                          |
catalog JSON ------------>| Repo Manager
 packages + sources       |      |
                          |      +--> Pulp RPM/Container/File/Python
Vault credentials ------->|      |
RHEL subscription ------->|      +--> repo_status.yml
```

## Validation Rules

| Rule | Result when invalid |
|------|---------------------|
| Required file missing | Fail before Pulp operations |
| Unknown configuration key | Schema validation failure |
| Catalog path is not `.json` | Validation failure with exact path |
| Catalog repository mapping missing | Report package, version and architecture |
| Private registry mapping missing | Report registry and affected images |
| Basic auth has no Vault mapping | Credential validation failure |
| Repository priority outside 1--100 | Schema validation failure |
| `rpm_repo` resolves to streamed content | Policy validation failure |
