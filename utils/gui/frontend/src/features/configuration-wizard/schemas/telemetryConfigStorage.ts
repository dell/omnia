import { z } from 'zod';
import { STORAGE_SIZE_PATTERN, SCRAPE_DURATION_PATTERN, CPU_RESOURCE_PATTERN, MEMORY_RESOURCE_PATTERN, YAML_FILE_PATTERN, IPV4_OR_HOSTNAME_PATTERN, CERT_PATH_PATTERN } from './common';

// Helper to parse duration strings like "30s", "1m", "1h" into seconds
const parseDuration = (duration: string): number => {
  const match = duration.match(/^(\d+)([smh])$/);
  if (!match) return 0;
  const value = parseInt(match[1], 10);
  const multipliers: Record<string, number> = { s: 1, m: 60, h: 3600 };
  return value * multipliers[match[2]];
};

// Helper to validate scrape timeout <= scrape interval
const scrapeTimeoutRefine = (
  data: { scrape_interval?: string; scrape_timeout?: string }
) => {
  if (data.scrape_interval && data.scrape_timeout) {
    return parseDuration(data.scrape_timeout) <= parseDuration(data.scrape_interval);
  }
  return true;
};

const SCRAPE_TIMEOUT_MESSAGE = {
  message: 'Scrape timeout must be less than or equal to scrape interval',
  path: ['scrape_timeout'],
};

// Resource schema for CPU and memory limits
const resourceSchema = z.object({
  requests: z.object({
    cpu: z.string().regex(CPU_RESOURCE_PATTERN, 'CPU must be in format like 100m, 500m, 1, or 2'),
    memory: z.string().regex(MEMORY_RESOURCE_PATTERN, 'Memory must be in format like 256Mi, 512Mi, or 1Gi'),
  }),
  limits: z.object({
    cpu: z.string().regex(CPU_RESOURCE_PATTERN, 'CPU must be in format like 100m, 500m, 1, or 2'),
    memory: z.string().regex(MEMORY_RESOURCE_PATTERN, 'Memory must be in format like 256Mi, 512Mi, or 1Gi'),
  }),
});

// Component with replicas and resources
const componentWithReplicasSchema = z.object({
  replicas: z.coerce.number().int().min(1),
  resources: resourceSchema,
});

// Component with replicas, pvc_size, and resources
const componentWithPvcSchema = z.object({
  replicas: z.coerce.number().int().min(1),
  pvc_size: z.string().regex(STORAGE_SIZE_PATTERN, 'Storage size must be in format like 8Gi, 512Mi').optional(),
  resources: resourceSchema,
});

// Combined schema for Telemetry Config and Telemetry Storage
export const telemetryConfigStorageSchema = z.object({
  // Telemetry Sources (from telemetry_config)
  telemetry_sources: z.object({
    idrac: z.object({
      metrics_enabled: z.boolean().default(false),
      collection_targets: z.array(z.enum(['victoria_metrics', 'kafka'])).default([]),
    }),
    ldms: z.object({
      metrics_enabled: z.boolean().default(false),
      collection_targets: z.array(z.enum(['kafka'])).max(1).default([]),
    }),
    dcgm: z.object({
      metrics_enabled: z.boolean().default(false),
    }),
    powerscale: z.object({
      metrics_enabled: z.boolean().default(false),
      logs_enabled: z.boolean().default(false),
      collection_targets: z.array(z.enum(['victoria_metrics', 'victoria_logs'])).default([]),
    }),
    ufm: z.object({
      metrics_enabled: z.boolean().default(false),
      logs_enabled: z.boolean().default(false),
      collection_targets: z.array(z.enum(['victoria_metrics', 'victoria_logs'])).default([]),
    }),
    vast: z.object({
      metrics_enabled: z.boolean().default(false),
      logs_enabled: z.boolean().default(false),
      collection_targets: z.array(z.enum(['victoria_metrics', 'victoria_logs'])).default([]),
    }),
    ome: z.object({
      metrics_enabled: z.boolean().default(false),
      logs_enabled: z.boolean().default(false),
      collection_targets: z.array(z.enum(['kafka'])).max(1).default([]),
    }),
  }),
  telemetry_bridges: z.object({
    vector_ldms: z.object({
      metrics_enabled: z.boolean().default(false),
    }).optional(),
    vector_ome: z.object({
      metrics_enabled: z.boolean().default(false),
      logs_enabled: z.boolean().default(false),
      ome_identifier: z.string().min(1).default('ome'),
    }).optional(),
  }).optional(),
  telemetry_sinks: z.object({
    victoria_metrics: z.object({
      persistence_size: z.string().regex(STORAGE_SIZE_PATTERN, 'Storage size must be in format like 8Gi, 512Mi').default('8Gi'),
      retention_period: z.coerce.number().min(24, 'Retention period must be at least 24 hours').default(168),
      additional_metric_remote_write_endpoints: z.array(z.object({
        url: z.string().url('URL must be valid'),
        tls_insecure_skip_verify: z.boolean().default(false),
      })).default([]),
    }).optional(),
    victoria_logs: z.object({
      storage_size: z.string().regex(STORAGE_SIZE_PATTERN, 'Storage size must be in format like 8Gi, 512Mi').default('8Gi'),
      retention_period: z.coerce.number().min(24, 'Retention period must be at least 24 hours').default(168),
      additional_log_write_endpoints: z.array(z.object({
        url: z.string().url('URL must be valid'),
        tls_insecure_skip_verify: z.boolean().default(false),
      })).default([]),
    }).optional(),
    kafka: z.object({
      persistence_size: z.string().regex(STORAGE_SIZE_PATTERN, 'Storage size must be in format like 8Gi, 512Mi').default('8Gi'),
      log_retention_hours: z.coerce.number().min(1, 'Log retention must be at least 1 hour').default(168),
      log_retention_bytes: z.coerce.number().default(-1),
      log_segment_bytes: z.coerce.number().min(1).default(1073741824),
      topic_partitions: z.object({
        idrac: z.coerce.number().min(1).max(100).default(1),
        ldms: z.coerce.number().min(1).max(100).default(2),
      }),
    }).optional(),
  }).optional(),
  idrac_telemetry_configurations: z.object({
    mysqldb_storage: z.string().regex(STORAGE_SIZE_PATTERN, 'Storage size must be in format like 8Gi, 512Mi').default('1Gi'),
  }).optional(),
  ldms_configurations: z.object({
    agg_port: z.coerce.number().min(6001).max(6100).default(6001),
    store_port: z.coerce.number().min(6001).max(6100).default(6001),
    sampler_port: z.coerce.number().min(10001).max(10100).default(10001),
    sampler_plugins: z.array(z.object({
      plugin_name: z.string().min(1, 'Plugin name is required'),
      config_parameters: z.string().optional(),
      activation_parameters: z.string().regex(/^interval=[1-9][0-9]*(\s+offset=[0-9]+)?$/, 'Must be in format interval=<non-zero-number> or interval=<non-zero-number> offset=<number>'),
    })).refine(
      (plugins) => {
        // If plugin_name is slurm_sampler, config_parameters is required and must contain specific fields
        for (const plugin of plugins) {
          if (plugin.plugin_name === 'slurm_sampler') {
            if (!plugin.config_parameters) {
              return false;
            }
            // Must contain component_id, stream, job_count, and task_count
            const hasComponentId = /component_id=/.test(plugin.config_parameters);
            const hasStream = /stream=/.test(plugin.config_parameters);
            const hasJobCount = /job_count=/.test(plugin.config_parameters);
            const hasTaskCount = /task_count=/.test(plugin.config_parameters);
            if (!hasComponentId || !hasStream || !hasJobCount || !hasTaskCount) {
              return false;
            }
          }
          // If plugin_name starts with procnetdev, config_parameters (if provided) must match ifaces pattern
          if (plugin.plugin_name.startsWith('procnetdev') && plugin.config_parameters) {
            const ifacesMatch = /ifaces=[a-zA-Z0-9_,]+/.test(plugin.config_parameters);
            if (!ifacesMatch) {
              return false;
            }
          }
        }
        return true;
      },
      { message: 'slurm_sampler requires config_parameters with component_id, stream, job_count, and task_count; procnetdev* config_parameters must include ifaces if provided' }
    ),
  }).optional(),
  powerscale_configurations: z.object({
    otel_collector_storage_size: z.string().regex(STORAGE_SIZE_PATTERN, 'Storage size must be in format like 8Gi, 512Mi').default('5Gi'),
    csm_observability_values_file_path: z.union([z.literal(''), z.string().regex(YAML_FILE_PATTERN, 'File must end with .yml or .yaml')]).optional(),
  }).optional(),
  ufm_configuration: z.object({
    ufm_endpoint: z.union([z.literal(''), z.string().regex(IPV4_OR_HOSTNAME_PATTERN, 'UFM endpoint must be a valid IPv4 address or hostname')]).optional(),
    ufm_metrics_port: z.coerce.number().min(1).max(65535).default(9001),
    scrape_interval: z.string().regex(SCRAPE_DURATION_PATTERN, 'Must be in format like 30s, 5m, 1h').default('30s'),
    scrape_timeout: z.string().regex(SCRAPE_DURATION_PATTERN, 'Must be in format like 30s, 5m, 1h').default('15s'),
    tls_mode: z.enum(['self_signed', 'ca_signed']).default('self_signed'),
    ufm_ca_cert_path: z.string().regex(CERT_PATH_PATTERN, 'CA cert path must be a valid .crt file path or empty').default(''),
    auth_mode: z.enum(['basic', 'none']).default('basic'),
  })
  .refine(scrapeTimeoutRefine, SCRAPE_TIMEOUT_MESSAGE)
  .refine(
    (data) => {
      if (data.tls_mode === 'ca_signed') {
        return !!data.ufm_ca_cert_path && data.ufm_ca_cert_path.length > 0;
      }
      return true;
    },
    {
      message: 'CA cert path is required when TLS mode is CA-signed',
      path: ['ufm_ca_cert_path'],
    }
  )
  .optional(),
  vast_configuration: z.object({
    vast_endpoint: z.union([z.literal(''), z.string().regex(IPV4_OR_HOSTNAME_PATTERN, 'VAST endpoint must be a valid IPv4 address or hostname')]).optional(),
    vast_metrics_port: z.coerce.number().min(1).max(65535).default(443),
    metrics_path: z.string().default('/api/prometheusmetrics/all'),
    scrape_interval: z.string().regex(SCRAPE_DURATION_PATTERN, 'Must be in format like 30s, 5m, 1h').default('30s'),
    scrape_timeout: z.string().regex(SCRAPE_DURATION_PATTERN, 'Must be in format like 30s, 5m, 1h').default('15s'),
    tls_mode: z.enum(['self_signed', 'ca_signed']).default('self_signed'),
    vast_ca_cert_path: z.string().regex(CERT_PATH_PATTERN, 'CA cert path must be a valid .crt file path or empty').default(''),
    auth_mode: z.enum(['basic', 'none']).default('basic'),
  })
  .refine(scrapeTimeoutRefine, SCRAPE_TIMEOUT_MESSAGE)
  .refine(
    (data) => {
      if (data.tls_mode === 'ca_signed') {
        return !!data.vast_ca_cert_path && data.vast_ca_cert_path.length > 0;
      }
      return true;
    },
    {
      message: 'CA cert path is required when TLS mode is CA-signed',
      path: ['vast_ca_cert_path'],
    }
  )
  .optional(),

  // Telemetry Storage (from telemetry_storage_config)
  victoria_cluster_storage: z.object({
    vmstorage: componentWithReplicasSchema,
    vminsert: componentWithReplicasSchema,
    vmselect: componentWithReplicasSchema,
    vmagent: componentWithReplicasSchema,
  }).optional(),
  
  victoria_logs_cluster_storage: z.object({
    vlstorage: componentWithReplicasSchema,
    vlinsert: componentWithReplicasSchema,
    vlselect: componentWithReplicasSchema,
    vlagent: componentWithPvcSchema,
  }).optional(),
  
  vector_storage: z.object({
    ldms: componentWithReplicasSchema,
    ome: componentWithReplicasSchema,
    vlagent_vector: componentWithPvcSchema,
    vmagent_vector: componentWithPvcSchema,
  }).optional(),
  
  csi_volume_exporter_storage: z.object({
    resources: resourceSchema,
  }).optional(),
  
  csm_metrics_powerscale_storage: z.object({
    resources: resourceSchema,
  }).optional(),
  
  idrac_telemetry_storage: z.object({
    mysqldb: z.object({
      resources: resourceSchema,
    }),
    activemq: z.object({
      resources: resourceSchema,
    }),
    receiver: z.object({
      resources: resourceSchema,
    }),
    kafka_pump: z.object({
      resources: resourceSchema,
    }),
    victoria_pump: z.object({
      resources: resourceSchema,
    }),
  }).optional(),
  
  kafka_storage: z.object({
    kafka: z.object({
      resources: resourceSchema,
    }),
    entity_operator: z.object({
      user_operator: z.object({
        resources: resourceSchema,
      }),
    }),
  }).optional(),
}).refine(
  (data) => {
    const powerscale = data.telemetry_sources?.powerscale;
    if (powerscale?.metrics_enabled || powerscale?.logs_enabled) {
      const path = data.powerscale_configurations?.csm_observability_values_file_path || '';
      return path.length > 0 && YAML_FILE_PATTERN.test(path);
    }
    return true;
  },
  {
    message: 'CSM Observability values file path is required and must end with .yml or .yaml',
    path: ['powerscale_configurations', 'csm_observability_values_file_path'],
  }
)
.refine(
  (data) => {
    const ufm = data.telemetry_sources?.ufm;
    if (ufm?.metrics_enabled || ufm?.logs_enabled) {
      const endpoint = data.ufm_configuration?.ufm_endpoint || '';
      return endpoint.length > 0 && IPV4_OR_HOSTNAME_PATTERN.test(endpoint);
    }
    return true;
  },
  {
    message: 'UFM endpoint is required and must be a valid IPv4 address or hostname',
    path: ['ufm_configuration', 'ufm_endpoint'],
  }
)
.refine(
  (data) => {
    const vast = data.telemetry_sources?.vast;
    if (vast?.metrics_enabled || vast?.logs_enabled) {
      const endpoint = data.vast_configuration?.vast_endpoint || '';
      return endpoint.length > 0 && IPV4_OR_HOSTNAME_PATTERN.test(endpoint);
    }
    return true;
  },
  {
    message: 'VAST endpoint is required and must be a valid IPv4 address or hostname',
    path: ['vast_configuration', 'vast_endpoint'],
  }
);

export type TelemetryConfigStorageFormData = z.infer<typeof telemetryConfigStorageSchema>;
