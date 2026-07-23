import {
  pxeFunctionalGroupsSchema,
  deploymentConfigsSchema,
  storageConfigSchema,
  cloudInitConfigSchema,
  omniaHaDiscoverySchema,
  serviceK8sClusterHaSchema,
  telemetryConfigStorageSchema,
  buildStreamGitLabSchema,
} from '../schemas';
import {
  TELEMETRY_SOURCES_DEFAULTS,
  IDRAC_TELEMETRY_CONFIGURATIONS_DEFAULTS,
  TELEMETRY_BRIDGES_DEFAULTS,
  TELEMETRY_SINKS_DEFAULTS,
  LDMS_CONFIGURATIONS_DEFAULTS,
  POWERSCALE_CONFIGURATIONS_DEFAULTS,
  UFM_CONFIGURATION_DEFAULTS,
  VAST_CONFIGURATION_DEFAULTS,
  VICTORIA_CLUSTER_STORAGE_DEFAULTS,
  VICTORIA_LOGS_CLUSTER_STORAGE_DEFAULTS,
  VECTOR_STORAGE_DEFAULTS,
  CSI_VOLUME_EXPORTER_STORAGE_DEFAULTS,
  CSM_METRICS_POWERSCALE_STORAGE_DEFAULTS,
  IDRAC_TELEMETRY_STORAGE_DEFAULTS,
  KAFKA_STORAGE_DEFAULTS,
} from '../steps/telemetry/telemetryDefaults';
import { EMPTY_SLURM_CLUSTER } from '../steps/omnia/SlurmTab';
import { EMPTY_K8S_CLUSTER } from '../steps/omnia/K8sTab';

export interface ValidationError {
  step: string;
  field: string;
  message: string;
}

export interface ValidationResult {
  success: boolean;
  errors: ValidationError[];
}

interface L2ErrorStore {
  validationErrors: ValidationError[];
  removeValidationErrorsByField: (fields: string[]) => void;
}

// Clear L2 errors for fields that now pass validation in the current step.
// Reads fresh errors from the store via getStore() so the calling useEffect
// does not need to list validationErrors in its dependency array.
export const clearL2ErrorsForStep = (
  result: { success: boolean; error?: { issues: { path: PropertyKey[] }[] } },
  stepName: string,
  getStore: () => L2ErrorStore
): void => {
  const { validationErrors, removeValidationErrorsByField } = getStore();
  const currentStepL2Fields = validationErrors
    .filter((e) => e.step === stepName)
    .map((e) => e.field);
  if (currentStepL2Fields.length === 0) return;

  if (result.success) {
    removeValidationErrorsByField(currentStepL2Fields);
    return;
  }

  if (!result.error) return;
  const failingFields = new Set(
    result.error.issues.map((issue) => issue.path.map(String).join('.'))
  );
  const clearedFields = currentStepL2Fields.filter(
    (field) => !failingFields.has(field)
  );
  if (clearedFields.length > 0) {
    removeValidationErrorsByField(clearedFields);
  }
};

// Helper function to collect errors from Zod validation results
const collectErrors = (
  result: any,
  step: string,
  errors: ValidationError[],
  fieldPrefix = ''
) => {
  if (!result.success && result.error) {
    for (const issue of result.error.issues) {
      const fieldPath = fieldPrefix
        ? `${fieldPrefix}.${issue.path.join('.')}`
        : issue.path.join('.');
      errors.push({
        step,
        field: fieldPath,
        message: enhanceErrorMessage(step, fieldPath, issue.message),
      });
    }
  }
};

// Helper function to convert technical field names to user-friendly names
const getDisplayName = (field: string): string => {
  // Remove array indices (e.g., .0, .1) from field path
  let cleanField = field.replace(/\.\d+/g, '');

  // Manual mappings for common top-level sections and fields that need better names
  const sectionMappings: Record<string, string> = {
    'service_k8s_cluster': 'Kubernetes cluster',
    'slurm_cluster': 'Slurm cluster',
    'service_k8s_cluster_ha': 'Kubernetes HA cluster',
    'pxe_mapping_file_path': 'PXE mapping file path',
    'pxe_mapping_data': 'PXE mapping data',
    'Networks': 'Networks',
    'admin_network': 'Admin network',
    'ib_network': 'InfiniBand network',
    'additional_subnets': 'Additional subnets',
    'mounts': 'Mounts',
    'mount_params': 'Mount parameters',
    'powervault_config': 'PowerVault configuration',
    'swap': 'Swap configuration',
    's3_configurations': 'S3 configurations',
    'cloud_init_common': 'Cloud-init common configuration',
    'cloud_init_groups': 'Cloud-init groups',
    'telemetry_sources': 'Telemetry sources',
    'telemetry_bridges': 'Telemetry bridges',
    'telemetry_sinks': 'Telemetry sinks',
    'build_stream_host_ip': 'Build Stream host IP',
    'build_stream_port': 'Build Stream port',
    'gitlab_host': 'GitLab host',
    'gitlab_https_port': 'GitLab HTTPS port',
    'user_registry': 'User registry',
    'user_registry_credential': 'User registry credential',
    'idrac_telemetry_configurations': 'iDRAC telemetry configurations',
    'ldms_configurations': 'LDMS configurations',
    'powerscale_configurations': 'PowerScale configurations',
    'ufm_configuration': 'UFM configuration',
    'vast_configuration': 'VAST configuration',
    'victoria_cluster_storage': 'Victoria cluster storage',
    'victoria_logs_cluster_storage': 'Victoria logs cluster storage',
    'vector_storage': 'Vector storage',
    'csi_volume_exporter_storage': 'CSI volume exporter storage',
    'csm_metrics_powerscale_storage': 'CSM metrics PowerScale storage',
    'idrac_telemetry_storage': 'iDRAC telemetry storage',
    'kafka_storage': 'Kafka storage',
  };

  // Check for exact match against section mappings
  if (sectionMappings[cleanField]) {
    return sectionMappings[cleanField];
  }

  // Split by dots and get the last meaningful part
  const parts = cleanField.split('.');
  
  // If we have a nested path, take the last 2 parts for context
  if (parts.length > 1) {
    const lastPart = parts[parts.length - 1];
    const secondLastPart = parts[parts.length - 2];
    
    // If the second to last part is a known section, use the last part directly
    if (Object.keys(sectionMappings).includes(secondLastPart)) {
      return formatFieldName(lastPart);
    }
    
    // Otherwise, combine the last two parts for context
    return formatFieldName(secondLastPart) + ' ' + formatFieldName(lastPart);
  }

  // Single field - just format it
  return formatFieldName(cleanField);
};

// Helper to format a single field name
const formatFieldName = (fieldName: string): string => {
  // Handle architecture strings before general formatting
  let formatted = fieldName
    .replace(/x86_64/gi, 'x86_64')
    .replace(/aarch64/gi, 'aarch64');
  
  // Replace remaining underscores with spaces
  formatted = formatted.replace(/_/g, ' ');
  
  // Capitalize each word
  formatted = formatted.replace(/\b\w/g, (char) => char.toUpperCase());
  
  // Handle common abbreviations
  formatted = formatted
    .replace(/\bIp\b/g, 'IP')
    .replace(/\bCpu\b/g, 'CPU')
    .replace(/\bIdrac\b/g, 'iDRAC')
    .replace(/\bLdms\b/g, 'LDMS')
    .replace(/\bUfm\b/g, 'UFM')
    .replace(/\bVast\b/g, 'VAST')
    .replace(/\bCsm\b/g, 'CSM')
    .replace(/\bKafka\b/g, 'Kafka')
    .replace(/\bGitlab\b/g, 'GitLab')
    .replace(/\bOtel\b/g, 'OTel')
    .replace(/\bPvc\b/g, 'PVC');
  
  return formatted.trim();
};

// Helper function to enhance error messages with more context
const enhanceErrorMessage = (step: string, field: string, originalMessage: string): string => {
  // Remove trailing dots from field names
  const cleanField = field.replace(/\.$/, '');

  // Convert technical field name to user-friendly name
  const displayField = getDisplayName(cleanField);

  // Skip enhancement if the original message is already enhanced
  if (originalMessage.includes('Please provide') || originalMessage.includes('Please configure') || originalMessage.includes('Please complete')) {
    return originalMessage;
  }

  // Map of common error patterns to enhanced messages
  const errorEnhancements: Record<string, string> = {
    'expected array, received undefined': `The field '${displayField}' is missing. Please provide at least one ${displayField} configuration in the ${step} step.`,
    'expected string, received undefined': `The field '${displayField}' is required but not provided. Please enter a value in the ${step} step.`,
    'must be a valid': `The field '${displayField}' contains invalid data. Please check the format in the ${step} step.`,
  };

  // Check if any enhancement pattern matches (more precise matching)
  if (originalMessage.startsWith('At least one')) {
    return `Please configure at least one ${displayField} in the ${step} step.`;
  }
  if (originalMessage === 'Required' || originalMessage.endsWith('is required')) {
    return `The field '${displayField}' is required. Please complete this field in the ${step} step.`;
  }
  for (const [pattern, enhancement] of Object.entries(errorEnhancements)) {
    if (originalMessage.includes(pattern)) {
      return enhancement;
    }
  }

  // If no pattern matches, return original message with context
  if (cleanField) {
    return `${originalMessage} (field: ${displayField})`;
  }

  return originalMessage;
};

export const validateL2Configuration = (
  wizardData: any,
  clusterType: string | null,
  enableCloudInit: boolean,
  enableTelemetry: boolean,
  enableBuildStream: boolean,
  enableGitlab: boolean,
  enableHa: boolean
): ValidationResult => {
  const errors: ValidationError[] = [];

  // Step 2: PXE Functional Groups (always mandatory)
  const pxeResult = pxeFunctionalGroupsSchema.safeParse({
    pxe_mapping_file_path: wizardData.pxe_mapping_file_path || '/opt/omnia/input/project_default/pxe_mapping_file.csv',
    pxe_mapping_data: wizardData.pxe_mapping_data,
    language: wizardData.language || 'en_US.UTF-8',
    default_lease_time: wizardData.default_lease_time || '86400',
    dns_enabled: wizardData.dns_enabled,
    kernel_version_override: wizardData.kernel_version_override,
    additional_cloud_init_config_file: wizardData.additional_cloud_init_config_file,
  });
  collectErrors(pxeResult, 'PXE Functional Groups', errors);

  // Step 3: Network Configuration (always mandatory)
  // Check if Networks is populated from either form data or PXE analysis
  // PXE analysis stores network data in a different structure, need to transform it
  let networksData = wizardData.Networks;
  if (!networksData && wizardData.pxe_network_analysis) {
    // Transform PXE analysis data to schema format
    const pxeAnalysis = wizardData.pxe_network_analysis as any;
    networksData = [];
    if (pxeAnalysis.adminSubnet) {
      networksData.push({
        admin_network: {
          subnet: pxeAnalysis.adminSubnet,
          netmask_bits: String(pxeAnalysis.adminNetmaskBits || 24),
          primary_oim_admin_ip: pxeAnalysis.adminIps?.[0] || '',
          primary_oim_bmc_ip: pxeAnalysis.bmcIps?.[0] || '',
          dynamic_range: pxeAnalysis.adminAssignedRange || '',
          oim_nic_name: 'eno1',
        }
      });
    }
    if (pxeAnalysis.ibSubnet) {
      networksData.push({
        ib_network: {
          subnet: pxeAnalysis.ibSubnet,
          netmask_bits: String(pxeAnalysis.ibNetmaskBits || 24),
        }
      });
    }
  }

  // Default empty network structure so validation can produce field-level errors
  // even if the step hasn't synced its form values to the store yet
  if (!networksData || !Array.isArray(networksData) || networksData.length === 0) {
    networksData = [
      { admin_network: { oim_nic_name: '', subnet: '', netmask_bits: '', primary_oim_admin_ip: '', primary_oim_bmc_ip: '', dynamic_range: '', dns: [], ntp_servers: [], additional_subnets: [] } },
      { ib_network: { subnet: '', netmask_bits: '', dns: [] } },
      { additional_subnets: [] },
    ];
  }

  const hasNetworkData = networksData && Array.isArray(networksData) && networksData.length > 0 &&
    networksData.some((n: any) => {
      if (n.admin_network) {
        // Check if admin_network has at least some required fields filled
        return n.admin_network.subnet && n.admin_network.subnet.trim() !== '';
      }
      return false;
    });

  const networkData = {
    Networks: networksData,
  };
  const networkResult = deploymentConfigsSchema.safeParse(networkData);
  collectErrors(networkResult, 'Network Configuration', errors);

  if (!hasNetworkData) {
    // Networks not configured yet - add a fallback top-level error
    errors.push({
      step: 'Network Configuration',
      field: 'Networks',
      message: 'Network configuration is required. Please configure at least one admin network with subnet and IP addresses in the Network Configuration step.',
    });
  }

  // Step 4: Storage Configuration (always mandatory)
  // Always validate storage and provide safe defaults so missing/invalid data is reported.
  const mountParams = wizardData.mount_params;
  const safeMountParams = mountParams && typeof mountParams === 'object' && !Array.isArray(mountParams)
    ? mountParams
    : {};
  const storageResult = storageConfigSchema.safeParse({
    mounts: wizardData.mounts ?? [],
    mount_params: safeMountParams,
    powervault_config: wizardData.powervault_config ?? [],
    swap: wizardData.swap ?? [],
    s3_configurations: wizardData.s3_configurations ?? undefined,
    _mount_params_entries: wizardData._mount_params_entries ?? [],
    _ui_showMounts: wizardData._ui_showMounts ?? false,
    _ui_showMountParams: wizardData._ui_showMountParams ?? false,
    _ui_showPowerVault: wizardData._ui_showPowerVault ?? false,
    _ui_showSwap: wizardData._ui_showSwap ?? false,
  });
  collectErrors(storageResult, 'Storage Configuration', errors);

  // Step 5: Cloud-Init (only if enabled)
  if (enableCloudInit) {
    const cloudInitResult = cloudInitConfigSchema.safeParse({
      cloud_init_common: wizardData.cloud_init_common ?? { write_files: [], runcmd: [] },
      cloud_init_groups: wizardData.cloud_init_groups ?? [],
    });
    collectErrors(cloudInitResult, 'Cloud-Init Configuration', errors);
  }

  // Step 6: Omnia Cluster Configuration (always mandatory, cluster-type specific)
  if (clusterType === 'slurm' || clusterType === 'both') {
    const slurmResult = omniaHaDiscoverySchema.shape.slurm_cluster.safeParse(wizardData.slurm_cluster ?? [{ ...EMPTY_SLURM_CLUSTER }]);
    collectErrors(slurmResult, 'Omnia Cluster Configuration', errors, 'slurm_cluster');
  }

  if (clusterType === 'k8s' || clusterType === 'both') {
    const k8sResult = omniaHaDiscoverySchema.shape.service_k8s_cluster.safeParse(wizardData.service_k8s_cluster ?? [{ ...EMPTY_K8S_CLUSTER }]);
    collectErrors(k8sResult, 'Omnia Cluster Configuration', errors, 'service_k8s_cluster');

    // HA section (only if enabled)
    if (enableHa) {
      const haResult = serviceK8sClusterHaSchema.safeParse(wizardData.service_k8s_cluster_ha ?? []);
      collectErrors(haResult, 'Omnia Cluster Configuration', errors, 'service_k8s_cluster_ha');
    }
  }

  // Security Config (always required for all cluster types)
  const securityConfigResult = omniaHaDiscoverySchema.shape.security_config.safeParse(wizardData.security_config ?? { ldap_connection_type: 'TLS' });
  collectErrors(securityConfigResult, 'Omnia Cluster Configuration', errors, 'security_config');

  // Step 7: Telemetry Configuration (only if enabled and k8s/both)
  if (enableTelemetry && (clusterType === 'k8s' || clusterType === 'both')) {
    // Check which telemetry sources are actually enabled
    const telemetrySources = wizardData.telemetry_sources || TELEMETRY_SOURCES_DEFAULTS;
    const idracEnabled = !!telemetrySources.idrac?.metrics_enabled;
    const ldmsEnabled = !!telemetrySources.ldms?.metrics_enabled;
    const powerscaleEnabled = !!telemetrySources.powerscale?.metrics_enabled || !!telemetrySources.powerscale?.logs_enabled;
    const ufmEnabled = !!telemetrySources.ufm?.metrics_enabled || !!telemetrySources.ufm?.logs_enabled;
    const vastEnabled = !!telemetrySources.vast?.metrics_enabled || !!telemetrySources.vast?.logs_enabled;
    const omeEnabled = !!telemetrySources.ome?.metrics_enabled || !!telemetrySources.ome?.logs_enabled;

    // Check collection targets for conditional validation
    const idracTargets = telemetrySources.idrac?.collection_targets || [];
    const ldmsTargets = telemetrySources.ldms?.collection_targets || [];
    const powerscaleTargets = telemetrySources.powerscale?.collection_targets || [];
    const ufmTargets = telemetrySources.ufm?.collection_targets || [];
    const vastTargets = telemetrySources.vast?.collection_targets || [];
    const omeTargets = telemetrySources.ome?.collection_targets || [];

    // Determine which bridges are needed based on sources and targets
    const needsVectorLdms = ldmsEnabled && ldmsTargets.includes('kafka');
    const needsVectorOmeMetrics = omeEnabled && omeTargets.includes('kafka');
    const needsVectorOmeLogs = omeEnabled && omeTargets.includes('kafka');
    const needsBridges = needsVectorLdms || needsVectorOmeMetrics || needsVectorOmeLogs;

    // Determine which sinks are needed based on collection targets
    const needsVictoriaMetrics = (idracTargets.includes('victoria_metrics') && idracEnabled) ||
      (powerscaleTargets.includes('victoria_metrics') && powerscaleEnabled) ||
      (ufmTargets.includes('victoria_metrics') && ufmEnabled) ||
      (vastTargets.includes('victoria_metrics') && vastEnabled) ||
      (omeTargets.includes('kafka') && omeEnabled) ||
      (ldmsTargets.includes('kafka') && ldmsEnabled);
    const needsVictoriaLogs = (powerscaleTargets.includes('victoria_logs') && powerscaleEnabled) ||
      (ufmTargets.includes('victoria_logs') && ufmEnabled) ||
      (vastTargets.includes('victoria_logs') && vastEnabled) ||
      (omeTargets.includes('kafka') && omeEnabled);
    const needsKafka = (idracTargets.includes('kafka') && idracEnabled) ||
      (ldmsTargets.includes('kafka') && ldmsEnabled) ||
      (omeTargets.includes('kafka') && omeEnabled);

    // Build telemetry validation object with only enabled sources
    const telemetryValidationData: any = {
      telemetry_sources: wizardData.telemetry_sources ?? TELEMETRY_SOURCES_DEFAULTS,
    };

    // Only include bridges when needed
    if (needsBridges) {
      telemetryValidationData.telemetry_bridges = wizardData.telemetry_bridges ?? TELEMETRY_BRIDGES_DEFAULTS;
    }

    // Only include sinks when needed
    if (needsVictoriaMetrics || needsVictoriaLogs || needsKafka) {
      telemetryValidationData.telemetry_sinks = wizardData.telemetry_sinks ?? TELEMETRY_SINKS_DEFAULTS;
    }

    // Source-specific configurations only
    if (idracEnabled) {
      telemetryValidationData.idrac_telemetry_configurations = wizardData.idrac_telemetry_configurations ?? IDRAC_TELEMETRY_CONFIGURATIONS_DEFAULTS;
    }
    if (ldmsEnabled) {
      telemetryValidationData.ldms_configurations = wizardData.ldms_configurations ?? LDMS_CONFIGURATIONS_DEFAULTS;
    }
    if (powerscaleEnabled) {
      telemetryValidationData.powerscale_configurations = wizardData.powerscale_configurations ?? POWERSCALE_CONFIGURATIONS_DEFAULTS;
    }
    if (ufmEnabled) {
      telemetryValidationData.ufm_configuration = wizardData.ufm_configuration ?? UFM_CONFIGURATION_DEFAULTS;
    }
    if (vastEnabled) {
      telemetryValidationData.vast_configuration = wizardData.vast_configuration ?? VAST_CONFIGURATION_DEFAULTS;
    }

    // Storage resources — driven by what's needed, not what's enabled
    if (idracEnabled) {
      telemetryValidationData.idrac_telemetry_storage = wizardData.idrac_telemetry_storage ?? IDRAC_TELEMETRY_STORAGE_DEFAULTS;
    }
    if (powerscaleEnabled) {
      telemetryValidationData.csm_metrics_powerscale_storage = wizardData.csm_metrics_powerscale_storage ?? CSM_METRICS_POWERSCALE_STORAGE_DEFAULTS;
      telemetryValidationData.csi_volume_exporter_storage = wizardData.csi_volume_exporter_storage ?? CSI_VOLUME_EXPORTER_STORAGE_DEFAULTS;
    }
    if (needsVictoriaMetrics) {
      telemetryValidationData.victoria_cluster_storage = wizardData.victoria_cluster_storage ?? VICTORIA_CLUSTER_STORAGE_DEFAULTS;
    }
    if (needsVictoriaLogs) {
      telemetryValidationData.victoria_logs_cluster_storage = wizardData.victoria_logs_cluster_storage ?? VICTORIA_LOGS_CLUSTER_STORAGE_DEFAULTS;
    }
    if (needsKafka) {
      telemetryValidationData.kafka_storage = wizardData.kafka_storage ?? KAFKA_STORAGE_DEFAULTS;
    }
    if (needsVectorLdms || needsVectorOmeMetrics || needsVectorOmeLogs) {
      telemetryValidationData.vector_storage = wizardData.vector_storage ?? VECTOR_STORAGE_DEFAULTS;
    }

    const telemetryResult = telemetryConfigStorageSchema.safeParse(telemetryValidationData);
    collectErrors(telemetryResult, 'Telemetry Configuration', errors);
  }

  // Step 8: Build Stream & GitLab (only if enabled)
  // Validate separately to avoid errors for features that weren't enabled
  // Use full schema validation since .pick() doesn't work with refinements
  if (enableBuildStream || enableGitlab) {
    const buildStreamGitLabResult = buildStreamGitLabSchema.safeParse({
      enable_build_stream: wizardData.enable_build_stream ?? enableBuildStream,
      build_stream_host_ip: wizardData.build_stream_host_ip ?? '',
      build_stream_port: wizardData.build_stream_port ?? 8010,
      aarch64_inventory_host_ip: wizardData.aarch64_inventory_host_ip,
      enable_gitlab: wizardData.enable_gitlab ?? enableGitlab,
      gitlab_host: wizardData.gitlab_host ?? '',
      gitlab_project_name: wizardData.gitlab_project_name ?? 'omnia-catalog',
      gitlab_project_visibility: wizardData.gitlab_project_visibility ?? 'private',
      gitlab_default_branch: wizardData.gitlab_default_branch ?? 'main',
      gitlab_https_port: wizardData.gitlab_https_port ?? 443,
      gitlab_min_storage_gb: wizardData.gitlab_min_storage_gb ?? 20,
      gitlab_min_memory_gb: wizardData.gitlab_min_memory_gb ?? 4,
      gitlab_min_cpu_cores: wizardData.gitlab_min_cpu_cores ?? 2,
      gitlab_puma_workers: wizardData.gitlab_puma_workers ?? 2,
      gitlab_sidekiq_concurrency: wizardData.gitlab_sidekiq_concurrency ?? 10,
    });
    collectErrors(buildStreamGitLabResult, 'Build Stream & GitLab', errors);
  }

  // L2: Cross-step business rules

  // Note: Schema validation already handles "at least one cluster required" checks
  // No additional business rules needed for cluster configuration

  return {
    success: errors.length === 0,
    errors,
  };
};
