import { z } from 'zod';
import { POD_EXTERNAL_IP_RANGE_PATTERN, CIDR_PATTERN, GIGABYTES_PATTERN, IPV4_PATTERN, SLURM_CONFIG_FILE_NAMES } from './common';
import * as yaml from 'js-yaml';

// Schema for a single node hardware defaults entry
const nodeHardwareDefaultsEntry = z.object({
  group_name: z.string().min(1, 'Group name is required'),
  sockets: z.coerce.number().int().min(1, 'Must be at least 1'),
  cores_per_socket: z.coerce.number().int().min(1, 'Must be at least 1'),
  threads_per_core: z.coerce.number().int().min(1, 'Must be at least 1'),
  real_memory: z.coerce.number().int().min(1, 'Must be at least 1'),
  gres: z.string().default(''),
});

// Schema for a single config source entry
const configSourceEntrySchema = z.object({
  name: z.enum(SLURM_CONFIG_FILE_NAMES),
  mode: z.enum(['yaml', 'filepath']),
  yaml_content: z.string()
    .refine(
      (val) => {
        if (!val || val.trim() === '') return true;
        try { yaml.load(val); return true; } catch { return false; }
      },
      { message: 'Must be valid YAML' }
    )
    .default(''),
  file_path: z.string().default(''),
}).refine(
  (entry) => {
    if (entry.mode === 'filepath') {
      return entry.file_path.length > 0;
    }
    if (entry.mode === 'yaml') {
      return entry.yaml_content.trim().length > 0;
    }
    return true;
  },
  { message: 'Content is required for the selected mode' }
);

// Combined schema for Omnia Config, High Availability, and Discovery
export const omniaHaDiscoverySchema = z.object({
  // Omnia Config - Slurm Cluster
  slurm_cluster: z.array(z.object({
    cluster_name: z.string().min(1, 'Slurm cluster name is required'),
    nfs_storage_name: z.string().min(1, 'NFS storage name is required'),
    vast_storage_name: z.string().min(1, 'VAST storage name is required'),
    skip_merge: z.boolean().default(false),
    node_discovery_mode: z.enum(['homogeneous', 'heterogeneous']).default('heterogeneous'),
    node_hardware_defaults: z.array(nodeHardwareDefaultsEntry).default([]),
    config_sources: z.array(configSourceEntrySchema).default([]),
  })).min(1, 'At least one Slurm cluster configuration is required'),
  
  // Omnia Config - Service K8s Cluster
  service_k8s_cluster: z.array(z.object({
    cluster_name: z.string().min(1, 'K8s cluster name is required'),
    deployment: z.coerce.boolean().default(false),
    etcd_on_local_disk: z.boolean().default(false),
    k8s_cni: z.enum(['calico', 'flannel']).default('calico'),
    pod_external_ip_range: z.string().regex(POD_EXTERNAL_IP_RANGE_PATTERN, 'Pod external IP range must be a valid CIDR or IP range'),
    k8s_service_addresses: z.string().regex(CIDR_PATTERN, 'Service addresses must be a valid CIDR').default('10.233.0.0/18'),
    k8s_pod_network_cidr: z.string().regex(CIDR_PATTERN, 'Pod network CIDR must be a valid CIDR').default('10.233.64.0/18'),
    nfs_storage_name: z.string().optional(),
    k8s_crio_storage_size: z.string().regex(GIGABYTES_PATTERN, 'CRI-O storage size must be in format like 10G, 15G').default('20G'),
    csi_powerscale_driver_secret_file_path: z.string().optional(),
    csi_powerscale_driver_values_file_path: z.string().optional(),
  })).min(1, 'At least one K8s cluster configuration is required')
    .refine(
      (clusters) => clusters.filter((c) => c.deployment === true).length === 1,
      { message: 'Exactly one K8s cluster must have deployment enabled' }
    )
    .superRefine((clusters, ctx) => {
      clusters.forEach((cluster, index) => {
        if (
          cluster.csi_powerscale_driver_secret_file_path &&
          cluster.csi_powerscale_driver_secret_file_path.length > 0 &&
          (!cluster.csi_powerscale_driver_values_file_path ||
            cluster.csi_powerscale_driver_values_file_path.length === 0)
        ) {
          ctx.addIssue({
            code: z.ZodIssueCode.custom,
            message: 'Values file path is required when secret file path is provided',
            path: [index, 'csi_powerscale_driver_values_file_path'],
          });
        }
      });
    }),

  // High Availability - Service K8s Cluster HA (Optional)
  enable_ha: z.boolean().optional(),
  service_k8s_cluster_ha: z.array(z.object({
    cluster_name: z.string().optional(),
    enable_k8s_ha: z.boolean(),
    virtual_ip_address: z.string().optional(),
  })).optional(),

  // Security Config
  enable_security_config: z.boolean().optional(),
  security_config: z.object({
    ldap_connection_type: z.enum(['TLS', 'SSL']).default('TLS'),
  }).optional(),
}).superRefine((data, ctx) => {
  if (data.enable_ha) {
    if (!data.service_k8s_cluster_ha || data.service_k8s_cluster_ha.length === 0) {
      ctx.addIssue({
        code: z.ZodIssueCode.custom,
        message: 'At least one HA cluster is required when HA is enabled',
        path: ['service_k8s_cluster_ha'],
      });
    }
    data.service_k8s_cluster_ha?.forEach((ha, index) => {
      if (!ha.cluster_name || ha.cluster_name.trim() === '') {
        ctx.addIssue({
          code: z.ZodIssueCode.custom,
          message: 'K8s cluster name is required',
          path: ['service_k8s_cluster_ha', index, 'cluster_name'],
        });
      }
      if (!ha.virtual_ip_address || !IPV4_PATTERN.test(ha.virtual_ip_address)) {
        ctx.addIssue({
          code: z.ZodIssueCode.custom,
          message: 'Virtual IP address must be a valid IPv4 address',
          path: ['service_k8s_cluster_ha', index, 'virtual_ip_address'],
        });
      }
    });
  }
});

// Strict schema for L2 validation when HA is enabled
export const serviceK8sClusterHaSchema = z.array(z.object({
  cluster_name: z.string().min(1, 'K8s cluster name is required'),
  enable_k8s_ha: z.boolean(),
  virtual_ip_address: z.string().regex(IPV4_PATTERN, 'Virtual IP address must be a valid IPv4 address'),
}));

export type OmniaHaDiscoveryFormData = z.infer<typeof omniaHaDiscoverySchema>;
