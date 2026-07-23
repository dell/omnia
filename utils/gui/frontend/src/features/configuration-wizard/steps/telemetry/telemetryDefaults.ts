// Default telemetry configuration and storage values
// Used to pre-fill the Telemetry Configuration form and to merge uploaded YAML values.

export const TELEMETRY_SOURCES_DEFAULTS = {
  idrac: { metrics_enabled: false, collection_targets: [] as string[] },
  ldms: { metrics_enabled: false, collection_targets: [] as string[] },
  dcgm: { metrics_enabled: false },
  powerscale: { metrics_enabled: false, logs_enabled: false, collection_targets: [] as string[] },
  ufm: { metrics_enabled: false, logs_enabled: false, collection_targets: [] as string[] },
  vast: { metrics_enabled: false, logs_enabled: false, collection_targets: [] as string[] },
  ome: { metrics_enabled: false, logs_enabled: false, collection_targets: [] as string[] },
};

export const IDRAC_TELEMETRY_CONFIGURATIONS_DEFAULTS = {
  mysqldb_storage: '1Gi',
};

export const TELEMETRY_BRIDGES_DEFAULTS = {
  vector_ldms: { metrics_enabled: false },
  vector_ome: { metrics_enabled: false, logs_enabled: false, ome_identifier: 'ome' },
};

export const TELEMETRY_SINKS_DEFAULTS = {
  victoria_metrics: { persistence_size: '8Gi', retention_period: 168 },
  victoria_logs: { storage_size: '8Gi', retention_period: 168 },
  kafka: {
    log_retention_hours: 168,
    persistence_size: '8Gi',
    log_retention_bytes: -1,
    log_segment_bytes: 1073741824,
    topic_partitions: { idrac: 1, ldms: 2 },
  },
};

export const LDMS_CONFIGURATIONS_DEFAULTS = {
  agg_port: 6001,
  store_port: 6001,
  sampler_port: 10001,
  sampler_plugins: [{ plugin_name: 'meminfo', activation_parameters: 'interval=30000000' }],
};

export const POWERSCALE_CONFIGURATIONS_DEFAULTS = {
  otel_collector_storage_size: '5Gi',
  csm_observability_values_file_path: '',
};

export const UFM_CONFIGURATION_DEFAULTS = {
  ufm_endpoint: '',
  ufm_metrics_port: 9001,
  scrape_interval: '30s',
  scrape_timeout: '15s',
  tls_mode: 'self_signed',
  ufm_ca_cert_path: '',
  auth_mode: 'basic',
};

export const VAST_CONFIGURATION_DEFAULTS = {
  vast_endpoint: '',
  vast_metrics_port: 443,
  metrics_path: '/api/prometheusmetrics/all',
  scrape_interval: '30s',
  scrape_timeout: '15s',
  tls_mode: 'self_signed',
  vast_ca_cert_path: '',
  auth_mode: 'basic',
};

export const VICTORIA_CLUSTER_STORAGE_DEFAULTS = {
  vmstorage: {
    replicas: 3,
    resources: {
      requests: { memory: '1Gi', cpu: '250m' },
      limits: { memory: '2Gi', cpu: '1000m' },
    },
  },
  vminsert: {
    replicas: 2,
    resources: {
      requests: { memory: '256Mi', cpu: '100m' },
      limits: { memory: '512Mi', cpu: '500m' },
    },
  },
  vmselect: {
    replicas: 2,
    resources: {
      requests: { memory: '256Mi', cpu: '100m' },
      limits: { memory: '512Mi', cpu: '500m' },
    },
  },
  vmagent: {
    replicas: 2,
    resources: {
      requests: { memory: '128Mi', cpu: '50m' },
      limits: { memory: '512Mi', cpu: '250m' },
    },
  },
};

export const VICTORIA_LOGS_CLUSTER_STORAGE_DEFAULTS = {
  vlstorage: {
    replicas: 3,
    resources: {
      requests: { memory: '512Mi', cpu: '100m' },
      limits: { memory: '1Gi', cpu: '500m' },
    },
  },
  vlinsert: {
    replicas: 2,
    resources: {
      requests: { memory: '256Mi', cpu: '100m' },
      limits: { memory: '512Mi', cpu: '500m' },
    },
  },
  vlselect: {
    replicas: 2,
    resources: {
      requests: { memory: '256Mi', cpu: '100m' },
      limits: { memory: '512Mi', cpu: '500m' },
    },
  },
  vlagent: {
    replicas: 2,
    pvc_size: '5Gi',
    resources: {
      requests: { memory: '64Mi', cpu: '25m' },
      limits: { memory: '256Mi', cpu: '100m' },
    },
  },
};

export const VECTOR_STORAGE_DEFAULTS = {
  ldms: {
    replicas: 2,
    resources: {
      requests: { memory: '128Mi', cpu: '50m' },
      limits: { memory: '256Mi', cpu: '250m' },
    },
  },
  ome: {
    replicas: 2,
    resources: {
      requests: { memory: '256Mi', cpu: '100m' },
      limits: { memory: '512Mi', cpu: '500m' },
    },
  },
  vlagent_vector: {
    replicas: 2,
    pvc_size: '5Gi',
    resources: {
      requests: { memory: '128Mi', cpu: '50m' },
      limits: { memory: '256Mi', cpu: '250m' },
    },
  },
  vmagent_vector: {
    replicas: 2,
    pvc_size: '5Gi',
    resources: {
      requests: { memory: '128Mi', cpu: '50m' },
      limits: { memory: '256Mi', cpu: '250m' },
    },
  },
};

export const CSI_VOLUME_EXPORTER_STORAGE_DEFAULTS = {
  resources: {
    requests: { cpu: '50m', memory: '64Mi' },
    limits: { cpu: '200m', memory: '256Mi' },
  },
};

export const CSM_METRICS_POWERSCALE_STORAGE_DEFAULTS = {
  resources: {
    requests: { cpu: '100m', memory: '128Mi' },
    limits: { cpu: '500m', memory: '512Mi' },
  },
};

export const IDRAC_TELEMETRY_STORAGE_DEFAULTS = {
  mysqldb: {
    resources: {
      requests: { cpu: '100m', memory: '256Mi' },
      limits: { cpu: '500m', memory: '512Mi' },
    },
  },
  activemq: {
    resources: {
      requests: { cpu: '100m', memory: '512Mi' },
      limits: { cpu: '500m', memory: '1536Mi' },
    },
  },
  receiver: {
    resources: {
      requests: { cpu: '100m', memory: '128Mi' },
      limits: { cpu: '500m', memory: '256Mi' },
    },
  },
  kafka_pump: {
    resources: {
      requests: { cpu: '50m', memory: '128Mi' },
      limits: { cpu: '200m', memory: '512Mi' },
    },
  },
  victoria_pump: {
    resources: {
      requests: { cpu: '50m', memory: '128Mi' },
      limits: { cpu: '200m', memory: '512Mi' },
    },
  },
};

export const KAFKA_STORAGE_DEFAULTS = {
  kafka: {
    resources: {
      requests: { memory: '512Mi', cpu: '200m' },
      limits: { memory: '1Gi', cpu: '1000m' },
    },
  },
  entity_operator: {
    user_operator: {
      resources: {
        requests: { memory: '512Mi', cpu: '200m' },
        limits: { memory: '512Mi', cpu: '1000m' },
      },
    },
  },
};
