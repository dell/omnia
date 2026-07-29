// export used
export { pxeFunctionalGroupsSchema, type PxeFunctionalGroupsFormData } from './pxeFunctionalGroups';
export { deploymentConfigsSchema, type DeploymentConfigsFormData } from './deploymentConfigs';
export { buildStreamGitLabSchema, type BuildStreamGitLabFormData } from './buildStreamGitLab';
export { getLocalRepoOsSchema } from './localRepoUserRegistry';
export { omniaHaDiscoverySchema, serviceK8sClusterHaSchema, type OmniaHaDiscoveryFormData } from './omniaHaDiscoveryConfig';
export { telemetryConfigStorageSchema, type TelemetryConfigStorageFormData } from './telemetryConfigStorage';
export { storageConfigSchema, type StorageConfigFormData } from './storageConfig';
export { cloudInitConfigSchema, type CloudInitConfigFormData } from './cloudInitConfig';

// Re-export common patterns
export * from './common';

