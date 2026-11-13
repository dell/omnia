# Custom Hostname Support

## Overview

Omnia supports human-readable hostnames (e.g., `gpu-worker-01`, `storage-node-a`) alongside the standard nid format (`nid001-nid999`) when `dns_enabled: true` in `orchestrator_config.yml`. This feature follows the OpenCHAMI custom hostname management approach to keep DHCP, DNS, and cloud-init in agreement.

## How It Works

When you use custom hostnames in the PXE mapping file, Omnia automatically:

1. **DHCP**: Adds specific CoreDHCP rules to offer the custom hostname via DHCP option 12
2. **DNS**: Creates separate CoreDNS server blocks with A records for custom hostnames
3. **Cloud-init**: The hostname is already set via the Metadata Service's hostname.yaml configuration

## Configuration

### PXE Mapping File

Simply use your desired hostname in the `HOSTNAME` column of `pxe_mapping_file.csv`:

```csv
FUNCTIONAL_GROUP_NAME,GROUP_NAME,SERVICE_TAG,HOSTNAME,ADMIN_MAC,ADMIN_IP,BMC_MAC,BMC_IP
slurm_node_rhel_10_2_x86_64,grp1,ABCD12,gpu-worker-01,aa:bb:cc:dd:ee:ff,172.16.107.43,aa:bb:cc:dd:ee:gg,172.17.107.43
slurm_node_rhel_10_2_x86_64,grp2,ABCD34,nid001,aa:bb:cc:dd:ee:hh,172.16.107.44,aa:bb:cc:dd:ee:ii,172.17.107.44
login_node_rhel_10_2_x86_64,grp3,ABCD56,login-server,aa:bb:cc:dd:ee:jj,172.16.107.45,aa:bb:cc:dd:ee:kk,172.17.107.45
```

You can mix custom hostnames and nid format in the same cluster. The system automatically detects which format you're using and configures DHCP and DNS accordingly.

### Validation

When `dns_enabled: true`, the PXE mapping validator accepts:
- **nid format**: `nid001` through `nid999` (existing behavior)
- **custom format**: Any valid hostname matching the pattern `^[a-z](?:[a-z0-9-]{0,61}[a-z0-9])?$`

No additional configuration flags are needed - the system auto-detects from the hostname format.

## Implementation Details

### DHCP Configuration

CoreDHCP adds specific rules for custom hostnames before the general nid pattern:

```yaml
# For custom hostnames (non-nid format)
rule=mac:aa:bb:cc:dd:ee:ff,hostname:gpu-worker-01
rule=mac:aa:bb:cc:dd:ee:gg,hostname:login-server

# General nid pattern (fallback for nid format hostnames)
rule=type:Node,hostname:nid{04d}
```

**Important**: 
- Custom rules use MAC address matching because XNAMEs are resolved from SMD during provisioning (not available during OpenCHAMI deployment)
- Custom rules come before the general pattern because CoreDHCP stops evaluation at the first match

### DNS Configuration

CoreDNS creates separate server blocks for custom hostnames using the hosts plugin:

```dns
gpu-worker-01.cluster.example:53 {
    hosts /dev/null {
        172.16.107.43 gpu-worker-01.cluster.example
        ttl 60
        no_reverse
        reload 0
    }
}
```

**Critical**: Custom DNS names need separate Corefile blocks (not inside the root `.:53` block) because CoreDNS's forward plugin runs before the hosts plugin. The separate block ensures custom-name queries are resolved by hosts before being forwarded upstream.

### Cloud-init Configuration

The hostname is set via the Metadata Service's `hostname.yaml` configuration, which uses the HOSTNAME from the PXE mapping file. This ensures cloud-init applies the same hostname that DHCP offered.

## Testing

After deploying custom hostnames, verify the configuration:

1. **Check DHCP response**:
   ```bash
   # On the node, check if the correct hostname was offered
   journalctl -u dhclient | grep "hostname"
   ```

2. **Query DNS for custom hostname**:
   ```bash
   dig @<oim-ip> gpu-worker-01.cluster.example A +short
   ```

3. **Query DNS for nid hostname** (if mixed):
   ```bash
   dig @<oim-ip> nid001.cluster.example A +short
   ```

4. **Boot a node and verify hostname**:
   ```bash
   # After cloud-init completes
   hostname
   hostname -f
   ```

5. **Check reverse DNS**:
   ```bash
   dig @<oim-ip> -x 172.16.107.43 +short
   ```

## Important Notes

- **Order matters**: Custom DHCP rules must come before the general nid pattern
- **DNS block separation**: Custom DNS names require separate Corefile blocks to avoid forwarding issues
- **Backward compatible**: Existing nid-based deployments continue to work without changes
- **Mix formats**: You can use both custom and nid hostnames in the same cluster
- **Single source of truth**: The PXE mapping file's HOSTNAME column is the authoritative source
- **Reverse DNS**: Continues to use inventory-based names (xnames/nids) even with custom forward hostnames

## References

This implementation follows the OpenCHAMI hostname management approach described in:
- [Managing OpenCHAMI Hostnames](https://openchami.org/blog/managing-openchami-hostnames/)
- CoreSMD v0.7.0 documentation
- OpenCHAMI v0.2.0 release configuration
