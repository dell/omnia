import { z } from 'zod';

// IPv4 octet pattern: 0-255
const IPV4_OCTET = '(?:25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)';
// IPv4 address pattern: four octets separated by dots
const IPV4_ADDR = `(?:${IPV4_OCTET}\\.){3}${IPV4_OCTET}`;

// Regex patterns matching L1 validation
export const IPV4_PATTERN = /^(?:(?:25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)\.){3}(?:25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)$/;
export const IPV4_OR_EMPTY_PATTERN = /^$|^((25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)\.){3}(25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)$/;
export const IPV4_OR_HOSTNAME_PATTERN = /^(?:(?:(?:25[0-5]|2[0-4]\d|[01]?\d{1,2})\.){3}(?:25[0-5]|2[0-4]\d|[01]?\d{1,2})|(?:[a-zA-Z0-9](?:[a-zA-Z0-9-]{0,61}[a-zA-Z0-9])?\.)+[a-zA-Z]{2,})$/;
export const STORAGE_SIZE_PATTERN = /^[0-9]+(Ki|Mi|Gi|Ti|Pi|Ei)$/;
export const GIGABYTES_PATTERN = /^[1-9][0-9]*G$/;
export const URL_PATTERN = /^(https?:\/\/).+/;
export const HOST_PORT_PATTERN = /^[a-zA-Z0-9.-]+:[0-9]+$/;
export const SCRAPE_DURATION_PATTERN = /^[0-9]+[smh]$/;
export const CPU_RESOURCE_PATTERN = /^[0-9]+m?$/; // Matches e.g., "100m", "500m", "1", "2"
export const MEMORY_RESOURCE_PATTERN = /^[0-9]+(Ki|Mi|Gi|Ti|Pi|Ei)$/; // Matches e.g., "256Mi", "512Mi", "1Gi", "8Gi"
export const YAML_FILE_PATTERN = /^.*\.(yml|yaml)$/; // Matches files ending with .yml or .yaml
export const HOSTNAME_OR_URL_PATTERN = /^(https?:\/\/)?[a-zA-Z0-9.-]+(:[0-9]+)?$/; // Matches hostname or URL
export const CERT_PATH_PATTERN = /^$|^\/[a-zA-Z0-9/._-]*\.crt$/; // Matches cert path or empty
export const NETMASK_BITS_PATTERN = /^(1[0-9]|2[0-9]|[1-9])$|^3[0-2]$/;
// Matches IP range format: IP-IP (e.g., "172.16.0.1-172.16.0.254")
export const DYNAMIC_RANGE_PATTERN = /^(?:(?:25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)\.){3}(?:25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)-(?:(?:25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)\.){3}(?:25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)$/;
// Matches RPM GPG key URIs (e.g., "https://example.com/key.gpg")
export const GPGKEY_PATTERN = /^([a-zA-Z][a-zA-Z0-9+.-]*:\/\/\S+)$/;
export const KEY_PATH_PATTERN = /^$|^\/[a-zA-Z0-9/._-]*\.key$/;
export const PROJECT_NAME_PATTERN = /^[a-zA-Z0-9][a-zA-Z0-9_\-\.]*$/;
// CIDR notation: IP/prefix (prefix 0-32)
export const CIDR_PATTERN = new RegExp(`^${IPV4_ADDR}\\/(?:[0-9]|[12][0-9]|3[0-2])$`);
// Pod external IP range: IP-IP or CIDR or empty
export const POD_EXTERNAL_IP_RANGE_PATTERN = new RegExp(`^${IPV4_ADDR}-${IPV4_ADDR}$|^${IPV4_ADDR}\\/(?:[0-9]|[12][0-9]|3[0-2])$|^$`);

// Slurm config file names
export const SLURM_CONFIG_FILE_NAMES = [
  'slurm', 'cgroup', 'slurmdbd', 'gres', 'acct_gather',
  'helpers', 'job_container', 'mpi', 'oci', 'topology', 'burst_buffer',
] as const;

export type SlurmConfigFileName = typeof SLURM_CONFIG_FILE_NAMES[number];

// Schema 1.1 Package Schema with applicable_functional_layers
export const packageSchema = z.object({
  name: z.string(),
  type: z.enum(['rpm', 'rpm_repo', 'tarball', 'git', 'image', 'pip_module']),
  version: z.string().optional(),
  uri: z.string().url().optional(),
  repo_name: z.string().optional(),
  architecture: z.union([z.string(), z.array(z.string())]).optional(),
  // Schema 1.1 fields
  applicable_functional_layers: z.array(z.string()).optional(),
  // Driver-specific configuration (Schema 1.1)
  config: z.object({
    DriverBrand: z.string().optional(),
    DriverType: z.string().optional(),
  }).catchall(z.unknown()).optional(),
  // Infrastructure supported functions (Schema 1.1)
  supported_functions: z.array(z.object({
    Name: z.string(),
  }).catchall(z.unknown())).optional(),
}).passthrough(); // Preserve unknown keys for forward compatibility

export type Package = z.infer<typeof packageSchema>;
