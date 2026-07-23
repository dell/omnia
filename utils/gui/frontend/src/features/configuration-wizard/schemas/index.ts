import { z } from 'zod';

// export used
export { pxeFunctionalGroupsSchema, type PxeFunctionalGroupsFormData } from './pxeFunctionalGroups';
export { deploymentConfigsSchema, type DeploymentConfigsFormData } from './deploymentConfigs';
export { buildStreamGitLabSchema, type BuildStreamGitLabFormData } from './buildStreamGitLab';
export { localRepoUserRegistrySchema, type LocalRepoUserRegistryFormData, localRepoUbuntuSchema, type LocalRepoUbuntuFormData, getLocalRepoOsSchema } from './localRepoUserRegistry';
export { omniaHaDiscoverySchema, serviceK8sClusterHaSchema, type OmniaHaDiscoveryFormData } from './omniaHaDiscoveryConfig';
export { telemetryConfigStorageSchema, type TelemetryConfigStorageFormData } from './telemetryConfigStorage';
export { storageConfigSchema, type StorageConfigFormData } from './storageConfig';
export { cloudInitConfigSchema, type CloudInitConfigFormData } from './cloudInitConfig';

// Re-export common patterns
export * from './common';

// Complete Wizard Schema (combines all sections)
import { pxeFunctionalGroupsSchema } from './pxeFunctionalGroups';
import { deploymentConfigsSchema } from './deploymentConfigs';
import { omniaHaDiscoverySchema } from './omniaHaDiscoveryConfig';
import { telemetryConfigStorageSchema } from './telemetryConfigStorage';
import { buildStreamGitLabSchema } from './buildStreamGitLab';
import { storageConfigSchema } from './storageConfig';
import { cloudInitConfigSchema } from './cloudInitConfig';

export const wizardSchema = z.object({
  ...pxeFunctionalGroupsSchema.shape,
  ...deploymentConfigsSchema.shape,
  ...storageConfigSchema.shape,
  ...cloudInitConfigSchema.shape,
  ...omniaHaDiscoverySchema.shape,
  ...telemetryConfigStorageSchema.shape,
  ...buildStreamGitLabSchema.shape,
  showCredentials: z.boolean().optional(),
  user_registry_name: z.string().optional(),
  user_registry_username: z.string().optional(),
  user_registry_password: z.string().optional(),
});

export type WizardFormData = z.infer<typeof wizardSchema>;
