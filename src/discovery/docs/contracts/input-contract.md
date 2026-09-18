# Discovery — Input Contract

> **Last Updated**: Sep 16, 2026 | **Domain**: `discovery`

This document defines all input files consumed by the `discovery` domain.

`DISCOVERY_DATA_PATH` defaults to `$OMNIA_DATA_PATH/discovery` when the
component override is unset or empty.

---

## 1. discovery_config.yml

**Purpose**: Configures the OME connection used for server discovery.

**Location**: `$DISCOVERY_DATA_PATH/input/<project_name>/discovery_config.yml`

**Owner**: User (manually created)

### Key Fields

| Field | Type | Required | Default | Description |
|-------|------|----------|---------|-------------|
| `ome_ip` | string | Yes | — | IP address of the Dell OME appliance |

### Validation Rules

- File must exist and be valid YAML
- `ome_ip` must be a valid, non-loopback IPv4 address
- `precheck` verifies TCP connectivity from the OIM host to `ome_ip` on port
  443. It does not authenticate, validate the TLS certificate, or call the OME
  API.
- The execute flow repeats the same connectivity check before calling the OME
  API and collecting inventory.

---

## 2. network_spec.yml

**Purpose**: Defines network topology for IP derivation in PXE mapping.

**Location**: `$DISCOVERY_DATA_PATH/input/<project_name>/network_spec.yml`

**Owner**: User (manually created)

### Key Fields

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `Networks[].admin_network.subnet` | string | Yes | Admin network prefix used for ADMIN_IP derivation (e.g., `172.16.107.0`) |
| `Networks[].ib_network.subnet` | string | No | InfiniBand subnet for IB IP derivation |

### Validation Rules

- The execute flow requires the file to exist and be parseable YAML.
- Discovery currently consumes only `admin_network.subnet` and
  `ib_network.subnet`; it does not consume `netmask_bits`.
- These subnet values are not covered by the current L1/L2 validator. The
  mapping generator derives output addresses from the first two subnet octets
  and the last two BMC-IP octets.

---

## 3. discovery_credentials.yml

**Purpose**: Stores OME credentials (vault-encrypted).

**Location**: `$DISCOVERY_DATA_PATH/input/<project_name>/discovery_credentials.yml`

**Owner**: `discovery_credentials` role (auto-created, user-prompted)

### Key Fields

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `ome_username` | string | Yes | OME login username |
| `ome_password` | string | Yes | OME login password |

### Vault Key

- **Key file**: `$DISCOVERY_DATA_PATH/input/<project_name>/.discovery_credentials_key`
- Auto-generated if missing from 32 random bytes, Base64-encoded by OpenSSL

### Validation Rules

- File is created by `discovery_credentials` role if missing
- Must be vault-encrypted after credential prompting
- `ome_username` and `ome_password` must be non-empty

---

## 4. Runtime Controls

| Variable | Source | Type | Required | Description |
|----------|--------|------|----------|-------------|
| `OMNIA_PROJECT_NAME` | Environment | string | No | Project name (default: `project_default`) |
| `cleanup_credentials` | CLI extra variable | bool | No | Remove credentials during `cleanup` (default: `true`) |

### Usage

```bash
cd src/discovery/playbooks
ansible-playbook discovery.yml
OMNIA_PROJECT_NAME=my_project ansible-playbook discovery.yml
ansible-playbook discovery.yml --tags cleanup -e cleanup_credentials=false
ansible-playbook discovery.yml --tags cleanup_credentials
```

`cleanup_credentials=false` preserves only `discovery_credentials.yml` and
`.discovery_credentials_key`. Cleanup does not remove or create the current
project's Discovery output directory. When it exists, cleanup empties it and
leaves the directory in place. All other input files are preserved.
The `cleanup_credentials` tag removes only the credential file and vault key.

---

## 5. Dependency Summary

| Input | Source | Provided By |
|-------|--------|-------------|
| `discovery_config.yml` | User-created | User |
| `network_spec.yml` | User-created | User |
| `discovery_credentials.yml` | Auto-created | `discovery_credentials` role |
