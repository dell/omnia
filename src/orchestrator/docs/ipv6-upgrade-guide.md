# IPoIB IPv6 Upgrade Guide

**Domain**: `orchestrator` | **Collection**: `omnia.orchestrator` | **Last updated**: October 2026

This guide covers migrating an existing Omnia cluster from IPv4-only InfiniBand
configuration to dual-stack (IPv4 + IPv6).

---

## Overview

Omnia supports backward-compatible migration. Existing IPv4-only input files
continue to work without modification. To add IPv6, update your input files
and re-provision the affected nodes.

---

## Step 1: Update `network_spec.yml`

Add the `ipv6_subnet` and `ipv6_netmask_bits` fields to the `ib_network`
section. The existing `subnet` / `netmask_bits` fields (or `ipv4_subnet` /
`ipv4_netmask_bits`) are unchanged.

**Before (IPv4-only):**

```yaml
Networks:
  ib_network:
    subnet: "192.168.0.0"
    netmask_bits: "24"
```

**After (dual-stack):**

```yaml
Networks:
  ib_network:
    ipv4_subnet: "192.168.0.0"
    ipv4_netmask_bits: "24"
    ipv6_subnet: "fd00:1b::"
    ipv6_netmask_bits: "64"
    ib_addr_mode: "dual-stack"
    slurm_preferred_addr_family: "ipv6"  # Required for dual-stack
```

> **Note**: Renaming `subnet` to `ipv4_subnet` is optional. Both field names
> are accepted. The legacy names are normalized automatically.

The `ib_addr_mode` field controls which addressing mode is used:
- `ipv4-only` (default): IPv4 addresses only
- `dual-stack`: Both IPv4 and IPv6 addresses; requires `slurm_preferred_addr_family`
- `ipv6-only`: IPv6 addresses only

The `slurm_preferred_addr_family` field (`ipv4` or `ipv6`) is required when
`ib_addr_mode: dual-stack`. It determines which IB address Slurm uses for
`NodeAddr` (inter-daemon communication).

---

## Step 2: Update `pxe_mapping_file.csv`

Add the `IB_IPV6` column to each row. If your file uses the legacy `IB_IP`
header, you may optionally rename it to `IB_IPV4`, but this is not required.

**Before (11-column legacy):**

```csv
FUNCTIONAL_GROUP_NAME,GROUP_NAME,SERVICE_TAG,PARENT_SERVICE_TAG,HOSTNAME,ADMIN_MAC,ADMIN_IP,BMC_MAC,BMC_IP,IB_NIC_NAME,IB_IP
slurm_node_rhel_10_0_x86_64,grp1,ABCD01,,node001,aa:bb:cc:dd:ee:01,172.16.107.41,aa:bb:cc:dd:ff:01,172.17.107.41,InfiniBand.Slot.7-1,192.168.0.41
```

**After (12-column with IPv6):**

```csv
FUNCTIONAL_GROUP_NAME,GROUP_NAME,SERVICE_TAG,PARENT_SERVICE_TAG,HOSTNAME,ADMIN_MAC,ADMIN_IP,BMC_MAC,BMC_IP,IB_NIC_NAME,IB_IPV4,IB_IPV6
slurm_node_rhel_10_0_x86_64,grp1,ABCD01,,node001,aa:bb:cc:dd:ee:01,172.16.107.41,aa:bb:cc:dd:ff:01,172.17.107.41,InfiniBand.Slot.7-1,192.168.0.41,fd00:1b::41
```

**Quick conversion** (on the OIM, if renaming the header):

```bash
cd "$ORCHESTRATOR_DATA_PATH/input/$OMNIA_PROJECT_NAME"

# Rename IB_IP to IB_IPV4 and add IB_IPV6 column
sed -i '1s/IB_IP$/IB_IPV4,IB_IPV6/' pxe_mapping_file.csv

# Append empty IB_IPV6 to each data row (IPv4-only until you add addresses)
sed -i '2,$s/$/,/' pxe_mapping_file.csv
```

Then edit each row to add the desired IPv6 address in the `IB_IPV6` column.

---

## Step 3: Validate

Run the orchestrator validation to confirm the updated input files are correct:

```bash
cd src/orchestrator/playbooks
ansible-playbook orchestrator.yml --tags validate
```

---

## Step 4: Re-Provision

Re-provision the cluster to apply IPv6 addresses:

```bash
cd src/orchestrator/playbooks
ansible-playbook orchestrator.yml --tags provision
```

Cloud-init will configure both IPv4 and IPv6 on the IB interface during the
next node boot. The provisioning is idempotent -- re-running it on nodes that
already have the correct configuration is safe.

---

## Rollback

To remove IPv6 and return to IPv4-only:

1. Remove `ipv6_subnet` and `ipv6_netmask_bits` from `network_spec.yml`
2. Clear the `IB_IPV6` column in `pxe_mapping_file.csv` (or revert to 11-column format)
3. Re-provision the affected nodes

---

## FAQ

**Q: Do I need to stop workloads during the migration?**

A: No. IPv6 address assignment is additive. The existing IPv4 address and
active connections are not disrupted. However, nodes must be rebooted (via
re-provision) for the IPv6 address to take effect.

**Q: Can I migrate nodes incrementally?**

A: Yes. Add `IB_IPV6` addresses to individual rows in the PXE mapping file.
Nodes without an `IB_IPV6` value remain IPv4-only. Re-provision only the nodes
that need IPv6.

**Q: What if I use the legacy `subnet` / `netmask_bits` field names?**

A: They continue to work. The orchestrator normalizes them to `ipv4_subnet` /
`ipv4_netmask_bits` internally. You can add `ipv6_subnet` / `ipv6_netmask_bits`
alongside the legacy field names.

---

## Related Documentation

- [IPoIB IPv6 Configuration Guide](ipv6-infiniband-configuration.md)
- [Input Contract](contracts/input-contract.md)
- [Troubleshooting](troubleshooting.md)
