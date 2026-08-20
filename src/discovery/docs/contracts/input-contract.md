# Discovery — Input Contract

> **Last Updated**: Jul 22, 2026 | **Domain**: `discovery`

This document defines all input files consumed by the `discovery` domain.

---

## 1. discovery_config.yml

**Purpose**: Configures the discovery mechanism and OME connection.

**Location**: `/opt/omnia/input/<project_name>/discovery/discovery_config.yml`

**Owner**: User (manually created)

### Key Fields

| Field | Type | Required | Default | Description |
|-------|------|----------|---------|-------------|
| `enable_bmc_discovery` | bool | Yes | `false` | Enable BMC discovery via OME |
| `ome_ip` | string | Yes (OME) | — | IP address of Dell OME appliance |

### Validation Rules

- File must exist and be valid YAML
- `enable_bmc_discovery` must be `true` when `discovery_mechanism=ome`
- `ome_ip` must be a valid IPv4 address when OME discovery is enabled
- OME must be reachable on port 443

---

## 2. network_spec.yml

**Purpose**: Defines network topology for IP derivation in PXE mapping.

**Location**: `/opt/omnia/input/<project_name>/discovery/network_spec.yml`

**Owner**: User (manually created)

### Key Fields

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `Networks[].admin_network.subnet` | string | Yes | Admin network subnet (e.g., `172.16.0.0`) |
| `Networks[].admin_network.netmask_bits` | string | Yes | Subnet mask bits (e.g., `24`) |
| `Networks[].ib_network.subnet` | string | No | InfiniBand subnet for IB IP derivation |

### Validation Rules

- File must exist and be valid YAML
- `admin_network.subnet` must be a valid network address
- `ib_network.subnet` is optional; when absent, IB_IP columns are empty

---

## 3. omnia_config_credentials.yml

**Purpose**: Stores OME credentials (vault-encrypted).

**Location**: `/opt/omnia/input/<project_name>/omnia_config_credentials.yml`

**Owner**: Credential utility (auto-created, user-prompted)

### Key Fields

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `ome_username` | string | Yes (OME) | OME login username |
| `ome_password` | string | Yes (OME) | OME login password |

### Vault Key

- **Key file**: `/opt/omnia/input/<project_name>/.omnia_config_credentials_key`
- Auto-generated if missing (32-char random ASCII)

### Validation Rules

- File is created by `discovery_credentials` role if missing
- Must be vault-encrypted after credential prompting
- `ome_username` and `ome_password` must be non-empty when OME discovery is used

---

## 4. Extra Variables (CLI)

| Variable | Type | Required | Description |
|----------|------|----------|-------------|
| `discovery_mechanism` | string | Yes | Discovery backend: `ome` or `magellan` |
| `project_name` | string | No | Project name (default: `project_default`) |

### Usage

```bash
ansible-playbook discovery.yml -e "discovery_mechanism=ome"
ansible-playbook discovery.yml -e "discovery_mechanism=ome" -e "project_name=my_project"
```

---

## 5. Dependency Summary

| Input | Source | Provided By |
|-------|--------|-------------|
| `discovery_config.yml` | User-created | User |
| `network_spec.yml` | User-created | User |
| `omnia_config_credentials.yml` | Auto-created | `discovery_credentials` role |
| `discovery_mechanism` | CLI extra var | User |
