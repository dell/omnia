# IPoIB IPv6 Configuration Guide

**Domain**: `orchestrator` | **Collection**: `omnia.orchestrator` | **Last updated**: October 2026

This guide covers InfiniBand over IP (IPoIB) IPv6 configuration for Omnia
clusters. Three modes are supported: **dual-stack** (IPv4 + IPv6),
**IPv4-only** (legacy default), and **IPv6-only** (IPv6 address without IPv4
on the IB interface).

---

## Prerequisites

- Mellanox ConnectX-6 or ConnectX-7 InfiniBand adapters with IPoIB support
- DOCA/OFED drivers installed (handled by Omnia cloud-init)
- OpenSM subnet manager running on the fabric
- InfiniBand link-layer connectivity verified (`ibstat` shows `LinkUp`)
- Omnia orchestrator domain configured (see [input-contract.md](contracts/input-contract.md))

---

## 1. Configuration Modes

### 1.1 Dual-Stack (IPv4 + IPv6)

Assigns both IPv4 and IPv6 addresses to the IB interface on each node.
Recommended for new deployments that need IPv6 connectivity while maintaining
IPv4 backward compatibility.

### 1.2 IPv4-Only (Legacy)

Assigns only IPv4 addresses. This is the default behavior when no IPv6 fields
are configured. Existing deployments continue to work without changes.

### 1.3 IPv6-Only

Assigns an IPv6 address without an IPv4 address on the IB interface. Use this
when the IB fabric is a dedicated IPv6 network.

---

## 2. Input File Configuration

Two input files control IB addressing: the PXE mapping CSV and the network
specification YAML.

### 2.1 PXE Mapping File (`pxe_mapping_file.csv`)

The PXE mapping CSV assigns per-node InfiniBand addresses. The file uses a
12-column format:

```
FUNCTIONAL_GROUP_NAME,GROUP_NAME,SERVICE_TAG,PARENT_SERVICE_TAG,HOSTNAME,ADMIN_MAC,ADMIN_IP,BMC_MAC,BMC_IP,IB_NIC_NAME,IB_IPV4,IB_IPV6
```

See [input-contract.md](contracts/input-contract.md) for the full column
specification.

#### Dual-Stack Example

```csv
FUNCTIONAL_GROUP_NAME,GROUP_NAME,SERVICE_TAG,PARENT_SERVICE_TAG,HOSTNAME,ADMIN_MAC,ADMIN_IP,BMC_MAC,BMC_IP,IB_NIC_NAME,IB_IPV4,IB_IPV6
slurm_node_rhel_10_0_x86_64,grp1,ABCD01,,node001,aa:bb:cc:dd:ee:01,172.16.107.41,aa:bb:cc:dd:ff:01,172.17.107.41,InfiniBand.Slot.7-1,192.168.0.41,fd00:1b::41
slurm_node_rhel_10_0_x86_64,grp1,ABCD02,,node002,aa:bb:cc:dd:ee:02,172.16.107.42,aa:bb:cc:dd:ff:02,172.17.107.42,InfiniBand.Slot.7-1,192.168.0.42,fd00:1b::42
slurm_node_rhel_10_0_x86_64,grp1,ABCD03,,node003,aa:bb:cc:dd:ee:03,172.16.107.43,aa:bb:cc:dd:ff:03,172.17.107.43,InfiniBand.Slot.7-1,192.168.0.43,fd00:1b::43
```

#### IPv4-Only Example (Legacy)

Leave the `IB_IPV6` column empty:

```csv
FUNCTIONAL_GROUP_NAME,GROUP_NAME,SERVICE_TAG,PARENT_SERVICE_TAG,HOSTNAME,ADMIN_MAC,ADMIN_IP,BMC_MAC,BMC_IP,IB_NIC_NAME,IB_IPV4,IB_IPV6
slurm_node_rhel_10_0_x86_64,grp1,ABCD01,,node001,aa:bb:cc:dd:ee:01,172.16.107.41,aa:bb:cc:dd:ff:01,172.17.107.41,InfiniBand.Slot.7-1,192.168.0.41,
```

Omnia also accepts the legacy 11-column format with `IB_IP` (without `IB_IPV6`).
The validator normalizes `IB_IP` to `IB_IPV4` automatically. No migration is
required for existing CSV files.

#### IPv6-Only Example

Leave the `IB_IPV4` column empty:

```csv
FUNCTIONAL_GROUP_NAME,GROUP_NAME,SERVICE_TAG,PARENT_SERVICE_TAG,HOSTNAME,ADMIN_MAC,ADMIN_IP,BMC_MAC,BMC_IP,IB_NIC_NAME,IB_IPV4,IB_IPV6
slurm_node_rhel_10_0_x86_64,grp1,ABCD01,,node001,aa:bb:cc:dd:ee:01,172.16.107.41,aa:bb:cc:dd:ff:01,172.17.107.41,InfiniBand.Slot.7-1,,fd00:1b::41
```

#### IB NIC Name Formats

The `IB_NIC_NAME` column uses Dell iDRAC FQDD notation:

| Format | Example | Description |
|--------|---------|-------------|
| `InfiniBand.Slot.X-Y` | `InfiniBand.Slot.7-1` | Standard slot-based format |
| `InfiniBand.PCIe.Slot.X-Y` | `InfiniBand.PCIe.Slot.22-1` | PCIe slot format |
| `NIC.InfiniBand.X-Y` | `NIC.InfiniBand.3-1` | Alternative NIC prefix |
| `InfiniBand.Single-Y` | `InfiniBand.Single-1` | Single-port device |

Hexadecimal slot numbers are supported (e.g., `InfiniBand.Slot.b5-1`).

### 2.2 Network Specification (`network_spec.yml`)

The `ib_network` section of `network_spec.yml` defines subnet-level IB
network parameters:

```yaml
Networks:
  admin_network:
    # ... admin network fields ...

  ib_network:
    ipv4_subnet: "192.168.0.0"
    ipv4_netmask_bits: "24"
    ipv6_subnet: "fd00:1b::"
    ipv6_netmask_bits: "64"
    dns:
      - "192.168.0.1"
```

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `ipv4_subnet` | string | Yes, when IB IPv4 configured | InfiniBand IPv4 network address |
| `ipv4_netmask_bits` | string | Yes, when IB IPv4 configured | IPv4 CIDR prefix length (e.g., `"24"`) |
| `ipv6_subnet` | string | No | InfiniBand IPv6 network address |
| `ipv6_netmask_bits` | string | No | IPv6 CIDR prefix length (e.g., `"64"`) |
| `ib_addr_mode` | string | No | IB addressing mode: `ipv4-only` (default), `dual-stack`, or `ipv6-only` |
| `slurm_preferred_addr_family` | string | No | Required when `ib_addr_mode: dual-stack`. Set to `ipv4` or `ipv6` to choose which IB address Slurm uses for NodeAddr. |
| `dns` | list | No | InfiniBand DNS server addresses |

**Backward compatibility**: The legacy field names `subnet` and `netmask_bits`
are accepted and mapped to `ipv4_subnet` and `ipv4_netmask_bits` automatically.
No migration is required for existing `network_spec.yml` files.

### 2.3 Slurm Cluster Configuration (`omnia_config.yml`)

The `slurm_cluster` section controls node discovery and partition generation:

| Field | Type | Default | Description |
|-------|------|---------|-------------|
| `node_discovery_mode` | string | `heterogeneous` | Node discovery mode: `heterogeneous` (iDRAC-based), `homogeneous`, or `dynamic` (no iDRAC, `slurmd` auto-reports hardware) |

**Dynamic mode**: When `node_discovery_mode: dynamic`, minimal `NodeName`
entries are generated (hostname + NodeAddr only). No iDRAC discovery calls are
made. The `slurmd` daemon auto-reports hardware capabilities (CPUs, memory,
GPUs) to `slurmctld` at registration. This mode is useful for environments
where iDRAC is unavailable or IB-only management is preferred.

GPU and CPU convenience partitions are automatically generated when compute
nodes are defined.

---

## 3. How It Works

### 3.1 Provisioning Flow

1. **Validation**: The orchestrator validates the PXE mapping and network spec,
   checking IPv4 and IPv6 address formats, uniqueness, and subnet consistency.
2. **Cloud-init template rendering**: The `configure-ib-network.sh.j2` template
   generates a per-node bash script that maps admin IPs to IB addresses.
3. **Device selection**: On first boot, the script identifies the correct mlx5
   device using the slot number from `IB_NIC_NAME` and PCI topology via
   `dmidecode` and `ibdev2netdev`.
4. **IP assignment**: NetworkManager (`nmcli`) assigns the IPv4 and/or IPv6
   address to the resolved IB interface. When NetworkManager is unavailable,
   `iproute2` is used as a fallback.

### 3.2 Slurm NodeAddr Injection

When IB addressing is configured, the orchestrator automatically injects
`NodeAddr` into each Slurm node's configuration. This allows Slurm to use
the IB address for inter-daemon communication instead of the admin network.

**Address source priority:**

1. **IB allocation file** (JSON): Used when present. Address family is selected
   by `ib_addr_mode` and `slurm_preferred_addr_family`.
2. **PXE mapping CSV fallback**: When no IB allocation file exists, NodeAddr
   is derived from the `IB_IPV6` column (preferred) or `IB_IPV4` column
   (fallback) of the PXE mapping file.

**EnableIPv6**: When the selected NodeAddr is an IPv6 address,
`CommunicationParameters=EnableIPv6` is automatically added to `slurm.conf`.

**Login and compiler nodes**: These nodes also receive NodeAddr from the PXE
mapping or IB allocation, ensuring Slurm control communication uses the IB
fabric.

**`/etc/hosts` management**: Disabled by default (`ib_ipv6_manage_hosts: false`).
NodeAddr in `slurm.conf` is sufficient for Slurm IB communication. Enable only
if non-Slurm applications require hostname-to-IB-address resolution.

### 3.3 Convenience Partitions

GPU and CPU convenience Slurm partitions are automatically created when
compute nodes are defined. These partitions group all compute nodes and
simplify job submission:

- **`gpu` partition**: All compute nodes, `State=UP`, `MaxTime=INFINITE`
- **`cpu` partition**: All compute nodes, `State=UP`, `MaxTime=INFINITE`

### 3.4 NetworkManager Configuration (Dual-Stack)

For dual-stack nodes, the cloud-init script configures:

```bash
# IPv4
nmcli con modify "$IB_INTERFACE" ipv4.method manual ipv4.addresses "$IB_IPV4/$NETMASK_BITS"

# IPv6
nmcli con modify "$IB_INTERFACE" ipv6.method manual ipv6.addresses "$IB_IPV6/$IPV6_NETMASK_BITS"
nmcli con modify "$IB_INTERFACE" ipv6.ip6-privacy 0
```

IPv6 privacy extensions are disabled (`ip6-privacy 0`) to ensure deterministic
IPoIB addressing. Temporary IPv6 addresses would break Slurm communication and
MPI job placement.

### 3.5 iproute2 Fallback

When NetworkManager is not available:

```bash
ip addr add "$IB_IPV4/$NETMASK_BITS" dev "$IB_INTERFACE"
ip addr add "$IB_IPV6/$IPV6_NETMASK_BITS" dev "$IB_INTERFACE"
sysctl -w "net.ipv6.conf.$IB_INTERFACE.use_tempaddr=0"
```

---

## 4. Validation Rules

### 4.1 PXE Mapping Validation

| Rule | Error Message |
|------|--------------|
| `IB_IPV4` must be a valid IPv4 address (when present) | `Row N: IB_IPV4 'x' is not a valid IPv4 address` |
| `IB_IPV6` must be a valid IPv6 address (when present) | `Row N: IB_IPV6 'x' is not a valid IPv6 address` |
| `IB_IPV4` values must be unique across all rows | `Duplicate values in IB_IPV4` |
| `IB_IPV6` values must be unique across all rows | `Duplicate values in IB_IPV6` |
| `IB_IPV6` requires `IB_NIC_NAME` to be present | `Row N: IB_IPV6 is set but IB_NIC_NAME is missing` |
| `IB_NIC_NAME` requires at least one IP (`IB_IPV4` or `IB_IPV6`) | `Row N: IB_NIC_NAME is set but no IB address is provided` |

### 4.2 Network Spec Validation

| Rule | Error Message |
|------|--------------|
| `ipv6_subnet` must be a valid IPv6 address | `ib_network: ipv6_subnet 'x' is not a valid IPv6 address` |
| `ipv6_netmask_bits` must be 1-128 | `ib_network: ipv6_netmask_bits 'x' is not a valid prefix length` |
| If `ipv6_subnet` is set, `ipv6_netmask_bits` is required | `ib_network: ipv6_subnet requires ipv6_netmask_bits` |

---

## 5. Verifying IB IPv6 Configuration

After provisioning, verify the IB IPv6 configuration on a target node:

```bash
# Check IB interface addresses
ip addr show ib0

# Expected output for dual-stack:
#   inet 192.168.0.41/24 scope global ib0
#   inet6 fd00:1b::41/64 scope global

# Test IPv6 connectivity between nodes
ping6 fd00:1b::42

# Check InfiniBand link state
ibstat

# Verify NetworkManager connection
nmcli con show ib0
```

---

## 6. Supported Hardware

| Adapter | Supported | Notes |
|---------|-----------|-------|
| Mellanox ConnectX-6 | Yes | HDR InfiniBand, dual-port |
| Mellanox ConnectX-7 | Yes | NDR InfiniBand, dual-port |
| Mellanox ConnectX-6 Dx | No | Ethernet-only (RoCE), no IPoIB |

The cloud-init script uses `ibstat` to filter Ethernet-only devices and only
configures interfaces with `Link layer: InfiniBand`.

---

## 7. Known Limitations

1. **IPv6 privacy extensions are disabled**: Temporary addresses (`use_tempaddr`)
   are disabled on IB interfaces for deterministic addressing. This is required
   for Slurm and MPI job placement.
2. **No IPv6 router advertisements**: IPoIB interfaces use static addressing
   only. SLAAC is not supported on IB networks.
3. **DNS**: InfiniBand DNS servers (configured in `network_spec.yml`) are added
   to the system resolver. IPv6 DNS servers are supported.
4. **Single IPv6 address per interface**: Each node receives at most one IPv6
   address per IB interface.

---

## Related Documentation

- [Input Contract](contracts/input-contract.md) -- PXE mapping CSV and network_spec.yml field reference
- [Troubleshooting](troubleshooting.md) -- IB IPv6 failure states and recovery
- [IPv6 Upgrade Guide](ipv6-upgrade-guide.md) -- Migration from IPv4-only to dual-stack
- [Hardware Identity Mapping](hardware-identity-mapping.md) -- Slot-to-PCI device resolution
