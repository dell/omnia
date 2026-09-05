# Orchestrator — Output Contract

> **Last Updated**: Jul 22, 2026 | **Domain**: `orchestrator`

This document defines all output artifacts produced by the `orchestrator` domain.

---

## 1. functional_groups_config.yml

**Purpose**: Maps PXE mapping file entries into functional groups used by BSS, cloud-init, and service configuration roles.

**Location**: `$OMNIA_DATA_PATH/.data/functional_groups_config.yml`

**Producer**: `orchestrator_functional_groups` role (Step 3)

**Consumers**:
- `configure_ochami` — BSS boot params per functional group
- `orchestrator_validations` — image validation per functional group
- `telemetry`, `slurm_config`, `k8s_config` — service deployment scoping

### Structure

```yaml
functional_groups:
  - name: "slurm_control_node_x86_64"
    nodes:
      - hostname: "node001"
        admin_ip: "10.5.0.101"
        admin_mac: "aa:bb:cc:dd:ee:01"
        bmc_ip: "10.3.0.101"
        service_tag: "ABC1234"
  - name: "slurm_node_x86_64"
    nodes:
      - hostname: "node002"
        admin_ip: "10.5.0.102"
        ...
```

---

## 2. OpenCHAMI Configuration Artifacts

Produced by `configure_ochami` role on the OIM host.

### 2.1 BSS Boot Parameters

**Location**: Configured via OpenCHAMI BSS API (not file-based)

| Parameter | Source | Description |
|-----------|--------|-------------|
| `kernel` | `s3_configurations.endpoint_url` + `build_status.kernel` | S3 URL to vmlinuz |
| `initrd` | `s3_configurations.endpoint_url` + `build_status.initrd` | S3 URL to initramfs |
| `params` | BSS template (`bss.yaml.j2`) | Boot parameters including root image, cloud-init, network |

### 2.2 Cloud-Init Configurations

| File | Scope | Description |
|------|-------|-------------|
| `cloud-init-default.yaml` | Global | Default cloud-init for all nodes |
| `cloud-init-group-*.yaml` | Per functional group | Group-specific packages, mounts, services |
| `cloud-init-node-*.yaml` | Per node | Node-specific hostname, network, SSH keys |

---

## 3. Node Orchestration Files

### 3.1 nodes.yaml

**Location**: Generated on OIM by `configure_ochami`

**Purpose**: Master node inventory for OpenCHAMI SMD registration

### 3.2 hostname.yaml

**Purpose**: Hostname assignments for xname-to-hostname mapping

### 3.3 groups.yaml

**Purpose**: Functional group definitions for OpenCHAMI

---

## 4. Ansible Inventory

**Location**: `$OMNIA_DATA_PATH/hosts`

**Producer**: `passwordless_ssh` role

**Purpose**: Dynamic Ansible inventory for service configuration plays

---

## 5. Deployed Services

The orchestrator deploys the following on OIM and compute nodes:

### 5.1 OpenCHAMI (on OIM)

| Service | Description |
|---------|-------------|
| `openchami.target` | Systemd target for all OpenCHAMI services |
| SMD | State Management Daemon — node inventory |
| BSS | Boot Script Service — PXE boot parameters |
| cloud-init-server | Cloud-init metadata service |
| CoreDHCP | DHCP server for PXE boot |
| CoreDNS | DNS server (when `dns_enabled`) |
| HAProxy | TLS termination proxy |
| Hydra | OAuth2 provider |
| PostgreSQL | Database backend |

### 5.2 Node Services (on compute nodes via cloud-init)

| Service | Condition | Description |
|---------|-----------|-------------|
| Kubernetes | `k8s_config` role | K8s cluster setup |
| Slurm | `slurm_config` role | Slurm scheduler |
| OpenLDAP | `openldap` role | Directory service |
| Telemetry | `telemetry` role | Monitoring stack |
| Storage mounts | `mount_config` role | NFS/CIFS/local mounts |

---

## 6. Cleanup

Running `cleanup_orchestrator.yml` removes:
- OpenCHAMI containers and systemd units
- BSS/cloud-init configurations
- Generated functional groups
- Ansible inventory
- Credentials (opt-in with `--tags credentials`)

---

## 7. Consumers Summary

| Consumer Domain | What It Reads | Purpose |
|----------------|---------------|---------|
| Compute nodes (PXE) | BSS boot params + cloud-init | Boot and configure nodes |
| `telemetry` role | `functional_groups_config.yml` | Deploy telemetry per group |
| `slurm_config` role | `functional_groups_config.yml`, `nodes.yaml` | Configure Slurm partitions |
| `k8s_config` role | `functional_groups_config.yml`, `nodes.yaml` | Configure K8s clusters |
