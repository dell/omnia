import type { PxeMappingRow } from '../utils/csvParser';

// Cluster-specific functional group discriminators (exclude shared os_* groups)
const SLURM_SPECIFIC_GROUPS = new Set([
  'slurm_control_node_x86_64',
  'slurm_node_x86_64',
  'slurm_node_aarch64',
  'login_node_x86_64',
  'login_node_aarch64',
  'login_compiler_node_x86_64',
  'login_compiler_node_aarch64',
]);

const K8S_SPECIFIC_GROUPS = new Set([
  'service_kube_control_plane_first_x86_64',
  'service_kube_control_plane_x86_64',
  'service_kube_node_x86_64',
]);

export interface PxeMappingAnalysis {
  clusterType: 'slurm' | 'k8s' | 'both' | null;
  networkInfo: {
    adminIps: string[];
    bmcIps: string[];
    ibIps: string[];
    adminSubnet?: string;
    ibSubnet?: string;
    adminNetmaskBits?: number;
    ibNetmaskBits?: number;
    adminAssignedRange?: string;
  };
}

export const analyzePxeMapping = (pxeData: PxeMappingRow[]): PxeMappingAnalysis => {
  const analysis: PxeMappingAnalysis = {
    clusterType: null,
    networkInfo: {
      adminIps: [],
      bmcIps: [],
      ibIps: [],
    },
  };

  if (!pxeData || pxeData.length === 0) {
    return analysis;
  }

  // Extract functional group names
  const functionalGroups = new Set<string>();
  const adminIps = new Set<string>();
  const bmcIps = new Set<string>();
  const ibIps = new Set<string>();

  pxeData.forEach(row => {
    if (row.FUNCTIONAL_GROUP_NAME) {
      functionalGroups.add(row.FUNCTIONAL_GROUP_NAME);
    }
    if (row.ADMIN_IP && isValidIpv4(row.ADMIN_IP)) adminIps.add(row.ADMIN_IP);
    if (row.BMC_IP && isValidIpv4(row.BMC_IP)) bmcIps.add(row.BMC_IP);
    if (row.IB_IP && isValidIpv4(row.IB_IP)) ibIps.add(row.IB_IP);
  });

  // Determine cluster type based on functional groups (using cluster-specific discriminators)
  const hasSlurmGroups = [...functionalGroups].some(group =>
    SLURM_SPECIFIC_GROUPS.has(group)
  );
  const hasK8sGroups = [...functionalGroups].some(group =>
    K8S_SPECIFIC_GROUPS.has(group)
  );

  if (hasSlurmGroups && hasK8sGroups) {
    analysis.clusterType = 'both';
  } else if (hasSlurmGroups) {
    analysis.clusterType = 'slurm';
  } else if (hasK8sGroups) {
    analysis.clusterType = 'k8s';
  }

  // Store network info
  analysis.networkInfo.adminIps = Array.from(adminIps);
  analysis.networkInfo.bmcIps = Array.from(bmcIps);
  analysis.networkInfo.ibIps = Array.from(ibIps);

  // Detect netmask bits from IPs first (needed for subnet calculation)
  analysis.networkInfo.adminNetmaskBits = detectNetmaskBits(analysis.networkInfo.adminIps);
  // IB netmask bits must match the admin network netmask bits
  analysis.networkInfo.ibNetmaskBits = analysis.networkInfo.adminNetmaskBits;

  // Detect subnets from IPs using the computed netmask bits
  if (analysis.networkInfo.adminNetmaskBits !== undefined) {
    analysis.networkInfo.adminSubnet = detectSubnet(analysis.networkInfo.adminIps, analysis.networkInfo.adminNetmaskBits);
  }
  if (analysis.networkInfo.ibNetmaskBits !== undefined && analysis.networkInfo.ibIps.length > 0) {
    analysis.networkInfo.ibSubnet = detectSubnet(analysis.networkInfo.ibIps, analysis.networkInfo.ibNetmaskBits);
  }

  // Detect assigned ranges from IPs
  analysis.networkInfo.adminAssignedRange = detectAssignedRange(analysis.networkInfo.adminIps);

  return analysis;
};

// Helper function to validate IPv4 address
const isValidIpv4 = (ip: string): boolean => {
  const p = ip.split('.').map(Number);
  return p.length === 4 && p.every(o => Number.isInteger(o) && o >= 0 && o <= 255);
};

// Helper function to convert IPv4 address to 32-bit unsigned integer
const ipToUint32 = (ip: string): number => {
  const p = ip.split('.').map(Number);
  if (p.length !== 4 || p.some(o => !Number.isInteger(o) || o < 0 || o > 255)) {
    throw new Error(`Invalid IPv4 address: "${ip}"`);
  }
  return ((p[0] << 24) | (p[1] << 16) | (p[2] << 8) | p[3]) >>> 0;
};

// Helper function to detect subnet from IP addresses using provided prefix length
const detectSubnet = (ips: string[], bits: number): string | undefined => {
  if (ips.length === 0) return undefined;

  const mask = bits === 0 ? 0 : (~0 << (32 - bits)) >>> 0;
  const network = (ipToUint32(ips[0]) & mask) >>> 0;

  return [
    (network >>> 24) & 0xff,
    (network >>> 16) & 0xff,
    (network >>> 8) & 0xff,
    network & 0xff,
  ].join('.');
};

// Helper function to detect netmask bits from IP addresses
const detectNetmaskBits = (ips: string[]): number | undefined => {
  if (ips.length === 0) return undefined;

  const ints = ips.map(ipToUint32);
  let min = ints[0];
  let max = ints[0];
  for (const v of ints) {
    if (v < min) min = v;
    if (v > max) max = v;
  }

  if (min === max) return 32;

  // XOR reveals which bits differ between the extremes.
  // Math.clz32 counts the leading zeros = the shared prefix length.
  const xor = (min ^ max) >>> 0;
  return Math.clz32(xor);
};

// Helper function to detect assigned IP range from IP addresses (O(n) min/max scan)
const detectAssignedRange = (ips: string[]): string | undefined => {
  if (ips.length === 0) return undefined;

  let minVal = ipToUint32(ips[0]);
  let maxVal = minVal;
  let minIp = ips[0];
  let maxIp = ips[0];

  for (const ip of ips) {
    const val = ipToUint32(ip);
    if (val < minVal) { minVal = val; minIp = ip; }
    if (val > maxVal) { maxVal = val; maxIp = ip; }
  }

  return `${minIp}-${maxIp}`;
};
