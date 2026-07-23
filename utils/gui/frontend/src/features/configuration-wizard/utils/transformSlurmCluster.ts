import { transformNodeHardwareDefaults } from './transformNodeHardwareDefaults';
import { transformConfigSources } from './transformConfigSources';

type SlurmClusterFormData = {
  cluster_name: string;
  nfs_storage_name: string;
  vast_storage_name: string;
  skip_merge: boolean;
  node_discovery_mode: 'homogeneous' | 'heterogeneous' | '';
  node_hardware_defaults: any[];
  config_sources: any[];
};

export const transformSlurmCluster = (
  cluster: SlurmClusterFormData
): Record<string, any> => {
  const result: Record<string, any> = {
    cluster_name: cluster.cluster_name,
    nfs_storage_name: cluster.nfs_storage_name,
    vast_storage_name: cluster.vast_storage_name,
    skip_merge: cluster.skip_merge,
    node_discovery_mode: cluster.node_discovery_mode,
  };

  // Transform node_hardware_defaults: array → keyed map
  if (cluster.node_hardware_defaults && cluster.node_hardware_defaults.length > 0) {
    result.node_hardware_defaults = transformNodeHardwareDefaults(
      cluster.node_hardware_defaults
    );
  }

  // Transform config_sources: array → keyed map
  if (cluster.config_sources && cluster.config_sources.length > 0) {
    result.config_sources = transformConfigSources(cluster.config_sources);
  }

  return result;
};

// Transform all clusters
export const transformSlurmClusters = (
  clusters: SlurmClusterFormData[]
): Record<string, any>[] => {
  if (!Array.isArray(clusters)) return [];
  return clusters.map(transformSlurmCluster);
};
