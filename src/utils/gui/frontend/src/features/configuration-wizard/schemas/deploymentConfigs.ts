import { z } from 'zod';
import { IPV4_PATTERN, NETMASK_BITS_PATTERN, DYNAMIC_RANGE_PATTERN, IPV4_OR_HOSTNAME_PATTERN } from './common';

// Shared additional subnet entry schema (used by admin_network and top-level additional_subnets)
const additionalSubnetEntrySchema = z.object({
  subnet: z.string().regex(IPV4_PATTERN, 'Subnet must be a valid IPv4 address'),
  netmask_bits: z.string().regex(NETMASK_BITS_PATTERN, 'Netmask bits must be between 1 and 32'),
  router: z.string().regex(IPV4_PATTERN, 'Router must be a valid IPv4 address'),
  dynamic_range: z.string().regex(DYNAMIC_RANGE_PATTERN, 'Dynamic range must be in format IP-IP'),
});

// Admin Network Schema
const adminNetworkSchema = z.object({
  oim_nic_name: z.string().min(1, 'Network interface name is required'),
  subnet: z.string().regex(IPV4_PATTERN, 'Admin subnet must be a valid IPv4 address'),
  netmask_bits: z.string().regex(NETMASK_BITS_PATTERN, 'Netmask bits must be between 1 and 32'),
  primary_oim_admin_ip: z.string().regex(IPV4_PATTERN, 'Primary OIM admin IP must be a valid IPv4 address'),
  primary_oim_bmc_ip: z.union([
    z.literal(''),
    z.string().regex(IPV4_PATTERN, 'Primary OIM BMC IP must be a valid IPv4 address'),
  ]),
  dynamic_range: z.string().regex(DYNAMIC_RANGE_PATTERN, 'Dynamic range must be in format IP-IP'),
  dns: z.array(z.string().regex(IPV4_PATTERN, 'DNS server must be a valid IPv4 address')).optional(),
  ntp_servers: z.array(z.object({
    address: z.string().regex(IPV4_OR_HOSTNAME_PATTERN, 'NTP server address must be a valid IPv4 address or hostname'),
    type: z.enum(['server', 'pool']),
  })).optional(),
  additional_subnets: z.array(additionalSubnetEntrySchema).optional(),
});

// IB Network Schema (all fields optional; if any IB value is provided, subnet and netmask are required)
const ibNetworkSchema = z.object({
  subnet: z.string().regex(IPV4_PATTERN, 'IB subnet must be a valid IPv4 address').or(z.literal('')).optional(),
  netmask_bits: z.string().regex(NETMASK_BITS_PATTERN, 'IB netmask bits must be between 1 and 32').or(z.literal('')).optional(),
  dns: z.array(z.string().regex(IPV4_PATTERN, 'DNS server must be a valid IPv4 address')).optional(),
}).refine(
  (data) => {
    const hasAnyIbValue =
      (data.subnet?.trim() ?? '') !== '' ||
      (data.netmask_bits?.trim() ?? '') !== '' ||
      (data.dns && data.dns.length > 0);
    if (hasAnyIbValue) {
      return (data.subnet?.trim() ?? '') !== '' && (data.netmask_bits?.trim() ?? '') !== '';
    }
    return true;
  },
  { message: 'IB subnet and netmask bits are required when configuring InfiniBand', path: ['subnet'] }
);

// Deployment Configs Schema (based on network_spec.json)
export const deploymentConfigsSchema = z.object({
  Networks: z.array(z.union([
    z.object({ admin_network: adminNetworkSchema }),
    z.object({ ib_network: ibNetworkSchema }),
    z.object({ additional_subnets: z.array(additionalSubnetEntrySchema) }),
  ])).min(1, 'At least one network configuration is required')
  .refine(
    (networks) => networks.some((n) => 'admin_network' in n),
    { message: 'At least one admin_network must be provided' }
  )
  .refine(
    (networks) => {
      const adminNet = networks.find((n) => 'admin_network' in n);
      const ibNet = networks.find((n) => 'ib_network' in n);
      if (adminNet && ibNet) {
        const adminNetmask = (adminNet as any).admin_network.netmask_bits;
        const ibNetmask = (ibNet as any).ib_network.netmask_bits;
        if (adminNetmask?.trim() && ibNetmask?.trim()) {
          return adminNetmask === ibNetmask;
        }
      }
      return true;
    },
    { message: 'IB network netmask_bits must match admin network netmask_bits' }
  ),
});

export type DeploymentConfigsFormData = z.infer<typeof deploymentConfigsSchema>;
