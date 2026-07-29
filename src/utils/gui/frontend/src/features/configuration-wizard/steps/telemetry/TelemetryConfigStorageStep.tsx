import { useEffect, useMemo, useRef, useState } from 'react';
import { useForm } from 'react-hook-form';
import * as yaml from 'js-yaml';
import { zodResolver } from '@hookform/resolvers/zod';
import { useConfigStore } from '../../configStore';
import { telemetryConfigStorageSchema, TelemetryConfigStorageFormData } from '../../schemas/telemetryConfigStorage';
import { clearL2ErrorsForStep } from '../../utils/l2Validation';
import { Tabs, TabConfig } from '../../components/Tabs';
import { IdracTab } from './IdracTab';
import { LdmsTab } from './LdmsTab';
import { DcgmTab } from './DcgmTab';
import { PowerscaleTab } from './PowerscaleTab';
import { UfmTab } from './UfmTab';
import { VastTab } from './VastTab';
import { OmeTab } from './OmeTab';
import { BridgesTab } from './BridgesTab';
import { SinksTab } from './SinksTab';
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
} from './telemetryDefaults';

const isObject = (item: any): boolean => {
  return item && typeof item === 'object' && !Array.isArray(item);
};

const readFileText = (file: File): Promise<string> => {
  return new Promise((resolve, reject) => {
    const reader = new FileReader();
    reader.onload = (event) => resolve(event.target?.result as string);
    reader.onerror = reject;
    reader.readAsText(file);
  });
};

const MAX_TELEMETRY_FILE_SIZE = 1024 * 1024; // 1 MB

const detectFileType = (
  fileName: string,
  parsed: any
): 'telemetry_config' | 'telemetry_storage_config' | null => {
  const lowerName = fileName.toLowerCase();
  if (lowerName.includes('telemetry_storage_config')) {
    return 'telemetry_storage_config';
  }
  if (lowerName.includes('telemetry_config') && !lowerName.includes('storage')) {
    return 'telemetry_config';
  }
  if (parsed && typeof parsed === 'object') {
    if ('telemetry_sources' in parsed) return 'telemetry_config';
    const storageKeys = [
      'victoria_cluster_storage',
      'victoria_logs_cluster_storage',
      'vector_storage',
      'csi_volume_exporter_storage',
      'csm_metrics_powerscale_storage',
      'idrac_telemetry_storage',
      'kafka_storage',
    ];
    if (storageKeys.some((key) => key in parsed)) {
      return 'telemetry_storage_config';
    }
  }
  return null;
};

/**
 * Merges `source` into `target` recursively.
 * - `null`/`undefined` values in `source` fall back to `target` values.
 * - Empty arrays/objects in `source` intentionally replace `target` values.
 * - Used both to initialize form defaults from wizardData and to merge uploaded YAML.
 */
const deepMerge = (target: any, source: any): any => {
  if (source === null || source === undefined) return target;
  const output: any = { ...target };
  Object.keys(source).forEach((key) => {
    const sourceVal = source[key];
    if (sourceVal === null || sourceVal === undefined) {
      if (!(key in output) || output[key] === null || output[key] === undefined) {
        output[key] = sourceVal;
      }
      return;
    }
    if (isObject(target?.[key]) && isObject(sourceVal) && !Array.isArray(sourceVal)) {
      output[key] = deepMerge(target?.[key] ?? {}, sourceVal);
    } else {
      output[key] = sourceVal;
    }
  });
  return output;
};

export const TelemetryConfigStorageStep = () => {
  const wizardData = useConfigStore((s) => s.wizardData);
  const updateWizardFields = useConfigStore((s) => s.updateWizardFields);
  const setStepValid = useConfigStore((s) => s.setStepValid);
  const telemetryActiveTab = useConfigStore((s) => s.telemetryActiveTab);
  const setTelemetryActiveTab = useConfigStore((s) => s.setTelemetryActiveTab);
  const selectedTelemetrySources = useConfigStore((s) => s.selectedTelemetrySources);
  const setSelectedTelemetrySources = useConfigStore((s) => s.setSelectedTelemetrySources);
  const validationErrors = useConfigStore((s) => s.validationErrors);

  const [uploadError, setUploadError] = useState<string | null>(null);
  const fileInputRef = useRef<HTMLInputElement>(null);

  const {
    register,
    formState: { errors },
    control,
    watch,
    reset,
  } = useForm<TelemetryConfigStorageFormData>({
    resolver: zodResolver(telemetryConfigStorageSchema) as any,
    defaultValues: {
      telemetry_sources: deepMerge(TELEMETRY_SOURCES_DEFAULTS, wizardData.telemetry_sources),
      telemetry_bridges: deepMerge(TELEMETRY_BRIDGES_DEFAULTS, wizardData.telemetry_bridges),
      telemetry_sinks: deepMerge(TELEMETRY_SINKS_DEFAULTS, wizardData.telemetry_sinks),
      idrac_telemetry_configurations: deepMerge(IDRAC_TELEMETRY_CONFIGURATIONS_DEFAULTS, wizardData.idrac_telemetry_configurations),
      ldms_configurations: deepMerge(LDMS_CONFIGURATIONS_DEFAULTS, wizardData.ldms_configurations),
      powerscale_configurations: deepMerge(POWERSCALE_CONFIGURATIONS_DEFAULTS, wizardData.powerscale_configurations),
      ufm_configuration: deepMerge(UFM_CONFIGURATION_DEFAULTS, wizardData.ufm_configuration),
      vast_configuration: deepMerge(VAST_CONFIGURATION_DEFAULTS, wizardData.vast_configuration),
      victoria_cluster_storage: deepMerge(VICTORIA_CLUSTER_STORAGE_DEFAULTS, (wizardData.victoria_cluster_storage as any) || {}),
      victoria_logs_cluster_storage: deepMerge(VICTORIA_LOGS_CLUSTER_STORAGE_DEFAULTS, (wizardData.victoria_logs_cluster_storage as any) || {}),
      vector_storage: deepMerge(VECTOR_STORAGE_DEFAULTS, (wizardData.vector_storage as any) || {}),
      csi_volume_exporter_storage: deepMerge(CSI_VOLUME_EXPORTER_STORAGE_DEFAULTS, (wizardData.csi_volume_exporter_storage as any) || {}),
      csm_metrics_powerscale_storage: deepMerge(CSM_METRICS_POWERSCALE_STORAGE_DEFAULTS, (wizardData.csm_metrics_powerscale_storage as any) || {}),
      idrac_telemetry_storage: deepMerge(IDRAC_TELEMETRY_STORAGE_DEFAULTS, (wizardData.idrac_telemetry_storage as any) || {}),
      kafka_storage: deepMerge(KAFKA_STORAGE_DEFAULTS, (wizardData.kafka_storage as any) || {}),
    },
    mode: 'onTouched',
  });

  // Update step validity and sync form changes to store (debounced to avoid excessive updates)
  useEffect(() => {
    const currentValues = watch();
    const initialResult = telemetryConfigStorageSchema.safeParse(currentValues);
    setStepValid(7, initialResult.success);
    clearL2ErrorsForStep(initialResult, 'Telemetry Configuration', useConfigStore.getState);

    let timer: ReturnType<typeof setTimeout>;
    const subscription = watch((formValues) => {
      const result = telemetryConfigStorageSchema.safeParse(formValues);
      setStepValid(7, result.success);
      clearL2ErrorsForStep(result, 'Telemetry Configuration', useConfigStore.getState);

      clearTimeout(timer);
      timer = setTimeout(() => {
        // Use parsed data (with coerced numbers) when valid, otherwise use raw formValues
        const dataToSync = result.success ? result.data : formValues;
        updateWizardFields({
          telemetry_sources: dataToSync.telemetry_sources,
          telemetry_bridges: dataToSync.telemetry_bridges,
          telemetry_sinks: dataToSync.telemetry_sinks,
          idrac_telemetry_configurations: dataToSync.idrac_telemetry_configurations,
          ldms_configurations: dataToSync.ldms_configurations,
          powerscale_configurations: dataToSync.powerscale_configurations,
          ufm_configuration: dataToSync.ufm_configuration,
          vast_configuration: dataToSync.vast_configuration,
          victoria_cluster_storage: dataToSync.victoria_cluster_storage,
          victoria_logs_cluster_storage: dataToSync.victoria_logs_cluster_storage,
          vector_storage: dataToSync.vector_storage,
          csi_volume_exporter_storage: dataToSync.csi_volume_exporter_storage,
          csm_metrics_powerscale_storage: dataToSync.csm_metrics_powerscale_storage,
          idrac_telemetry_storage: dataToSync.idrac_telemetry_storage,
          kafka_storage: dataToSync.kafka_storage,
        });
      }, 300);
    });
    return () => {
      clearTimeout(timer);
      subscription.unsubscribe();
    };
  }, [watch, setStepValid, updateWizardFields]);

  const handleFileUpload = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const files = e.target.files;
    if (!files || files.length === 0) {
      setUploadError('Please select one or two YAML files: telemetry_config.yml and/or telemetry_storage_config.yml');
      return;
    }
    if (files.length > 2) {
      setUploadError('Please select at most two YAML files.');
      return;
    }

    for (const file of Array.from(files)) {
      if (file.size > MAX_TELEMETRY_FILE_SIZE) {
        setUploadError(`File "${file.name}" is larger than 1 MB.`);
        return;
      }
    }

    try {
      const texts = await Promise.all(
        Array.from(files).map(async (file) => {
          const text = await readFileText(file);
          return { file, text };
        })
      );

      let configParsed: any = {};
      let storageParsed: any = {};
      let configCount = 0;
      let storageCount = 0;

      for (const { file, text } of texts) {
        let parsed: any;
        try {
          parsed = yaml.load(text);
        } catch (err) {
          throw new Error(`Failed to parse ${file.name}: ${err instanceof Error ? err.message : String(err)}`);
        }
        const type = detectFileType(file.name, parsed);
        if (type === 'telemetry_config') {
          configParsed = parsed;
          configCount++;
        } else if (type === 'telemetry_storage_config') {
          storageParsed = parsed;
          storageCount++;
        } else {
          throw new Error(`Could not identify "${file.name}" as telemetry_config.yml or telemetry_storage_config.yml.`);
        }
      }

      if (configCount > 1) {
        throw new Error('Multiple telemetry_config files were selected. Please select only one telemetry_config.yml.');
      }
      if (storageCount > 1) {
        throw new Error('Multiple telemetry_storage_config files were selected. Please select only one telemetry_storage_config.yml.');
      }

      const combined = { ...configParsed, ...storageParsed };

      const defaultSections = {
        telemetry_sources: TELEMETRY_SOURCES_DEFAULTS,
        telemetry_bridges: TELEMETRY_BRIDGES_DEFAULTS,
        telemetry_sinks: TELEMETRY_SINKS_DEFAULTS,
        idrac_telemetry_configurations: IDRAC_TELEMETRY_CONFIGURATIONS_DEFAULTS,
        ldms_configurations: LDMS_CONFIGURATIONS_DEFAULTS,
        powerscale_configurations: POWERSCALE_CONFIGURATIONS_DEFAULTS,
        ufm_configuration: UFM_CONFIGURATION_DEFAULTS,
        vast_configuration: VAST_CONFIGURATION_DEFAULTS,
        victoria_cluster_storage: VICTORIA_CLUSTER_STORAGE_DEFAULTS,
        victoria_logs_cluster_storage: VICTORIA_LOGS_CLUSTER_STORAGE_DEFAULTS,
        vector_storage: VECTOR_STORAGE_DEFAULTS,
        csi_volume_exporter_storage: CSI_VOLUME_EXPORTER_STORAGE_DEFAULTS,
        csm_metrics_powerscale_storage: CSM_METRICS_POWERSCALE_STORAGE_DEFAULTS,
        idrac_telemetry_storage: IDRAC_TELEMETRY_STORAGE_DEFAULTS,
        kafka_storage: KAFKA_STORAGE_DEFAULTS,
      };

      const mergedData: any = {};
      Object.keys(defaultSections).forEach((key) => {
        mergedData[key] = deepMerge(
          (defaultSections as any)[key],
          combined[key]
        );
      });

      const result = telemetryConfigStorageSchema.safeParse(mergedData);
      if (!result.success) {
        const issues = result.error.issues
          .map((issue) => `${issue.path.join('.')}: ${issue.message}`)
          .join('\n');
        setUploadError(`Validation failed:\n${issues}`);
        return;
      }

      const sources = result.data.telemetry_sources as any;
      const enabledSources = Object.entries(sources)
        .filter(([, value]: [string, any]) => value?.metrics_enabled || value?.logs_enabled)
        .map(([key]) => key);

      setSelectedTelemetrySources(enabledSources);

      updateWizardFields({
        telemetry_sources: mergedData.telemetry_sources,
        telemetry_bridges: mergedData.telemetry_bridges,
        telemetry_sinks: mergedData.telemetry_sinks,
        idrac_telemetry_configurations: mergedData.idrac_telemetry_configurations,
        ldms_configurations: mergedData.ldms_configurations,
        powerscale_configurations: mergedData.powerscale_configurations,
        ufm_configuration: mergedData.ufm_configuration,
        vast_configuration: mergedData.vast_configuration,
        victoria_cluster_storage: mergedData.victoria_cluster_storage,
        victoria_logs_cluster_storage: mergedData.victoria_logs_cluster_storage,
        vector_storage: mergedData.vector_storage,
        csi_volume_exporter_storage: mergedData.csi_volume_exporter_storage,
        csm_metrics_powerscale_storage: mergedData.csm_metrics_powerscale_storage,
        idrac_telemetry_storage: mergedData.idrac_telemetry_storage,
        kafka_storage: mergedData.kafka_storage,
      });

      reset(mergedData, { keepDirtyValues: false });

      const sourceTabIds = ['idrac', 'ldms', 'dcgm', 'powerscale', 'ufm', 'vast', 'ome'];
      if (
        sourceTabIds.includes(telemetryActiveTab) &&
        enabledSources.length > 0 &&
        !enabledSources.includes(telemetryActiveTab)
      ) {
        setTelemetryActiveTab(enabledSources[0]);
      }

      setUploadError(null);
    } catch (error) {
      setUploadError(error instanceof Error ? error.message : 'Failed to process telemetry files');
    } finally {
      e.target.value = '';
    }
  };

  // Watch metrics enabled flags for conditional rendering
  const idracMetricsEnabled = !!watch('telemetry_sources.idrac.metrics_enabled');
  const ldmsMetricsEnabled = !!watch('telemetry_sources.ldms.metrics_enabled');
  const powerscaleMetricsEnabled = !!watch('telemetry_sources.powerscale.metrics_enabled');
  const powerscaleLogsEnabled = !!watch('telemetry_sources.powerscale.logs_enabled');
  const ufmMetricsEnabled = !!watch('telemetry_sources.ufm.metrics_enabled');
  const ufmLogsEnabled = !!watch('telemetry_sources.ufm.logs_enabled');
  const vastMetricsEnabled = !!watch('telemetry_sources.vast.metrics_enabled');
  const vastLogsEnabled = !!watch('telemetry_sources.vast.logs_enabled');
  const omeMetricsEnabled = !!watch('telemetry_sources.ome.metrics_enabled');
  const omeLogsEnabled = !!watch('telemetry_sources.ome.logs_enabled');

  // Watch collection targets for conditional rendering
  const idracCollectionTargets = watch('telemetry_sources.idrac.collection_targets') || [];
  const ldmsCollectionTargets = watch('telemetry_sources.ldms.collection_targets') || [];
  const powerscaleCollectionTargets = watch('telemetry_sources.powerscale.collection_targets') || [];
  const ufmCollectionTargets = watch('telemetry_sources.ufm.collection_targets') || [];
  const vastCollectionTargets = watch('telemetry_sources.vast.collection_targets') || [];
  const omeCollectionTargets = watch('telemetry_sources.ome.collection_targets') || [];

  // Derived values for conditional rendering
  const needsVictoriaMetrics = useMemo(() =>
    (idracCollectionTargets.includes('victoria_metrics') && idracMetricsEnabled) ||
    (powerscaleCollectionTargets.includes('victoria_metrics') && powerscaleMetricsEnabled) ||
    (ufmCollectionTargets.includes('victoria_metrics') && ufmMetricsEnabled) ||
    (vastCollectionTargets.includes('victoria_metrics') && vastMetricsEnabled) ||
    (omeMetricsEnabled && omeCollectionTargets.includes('kafka')) ||
    (ldmsMetricsEnabled && ldmsCollectionTargets.includes('kafka')),
    [idracMetricsEnabled, ldmsMetricsEnabled, powerscaleMetricsEnabled, ufmMetricsEnabled, vastMetricsEnabled, omeMetricsEnabled, idracCollectionTargets, ldmsCollectionTargets, powerscaleCollectionTargets, ufmCollectionTargets, vastCollectionTargets, omeCollectionTargets]
  );

  const needsVictoriaLogs = useMemo(() =>
    (powerscaleCollectionTargets.includes('victoria_logs') && powerscaleLogsEnabled) ||
    (ufmCollectionTargets.includes('victoria_logs') && ufmLogsEnabled) ||
    (vastCollectionTargets.includes('victoria_logs') && vastLogsEnabled) ||
    (omeLogsEnabled && omeCollectionTargets.includes('kafka')),
    [powerscaleCollectionTargets, powerscaleLogsEnabled, ufmCollectionTargets, ufmLogsEnabled, vastCollectionTargets, vastLogsEnabled, omeLogsEnabled, omeCollectionTargets]
  );

  const needsKafka = useMemo(() =>
    (idracCollectionTargets.includes('kafka') && idracMetricsEnabled) ||
    (ldmsCollectionTargets.includes('kafka') && ldmsMetricsEnabled) ||
    (omeCollectionTargets.includes('kafka') && (omeMetricsEnabled || omeLogsEnabled)),
    [idracCollectionTargets, idracMetricsEnabled, ldmsCollectionTargets, ldmsMetricsEnabled, omeCollectionTargets, omeMetricsEnabled, omeLogsEnabled]
  );

  const needsVectorLdms = useMemo(() =>
    ldmsMetricsEnabled && ldmsCollectionTargets.includes('kafka'),
    [ldmsMetricsEnabled, ldmsCollectionTargets]
  );

  const needsVectorOmeMetrics = useMemo(() =>
    omeMetricsEnabled && omeCollectionTargets.includes('kafka'),
    [omeMetricsEnabled, omeCollectionTargets]
  );

  const needsVectorOmeLogs = useMemo(() =>
    omeLogsEnabled && omeCollectionTargets.includes('kafka'),
    [omeLogsEnabled, omeCollectionTargets]
  );

  // Filter tabs based on selected telemetry sources (always include Bridges and Sinks)
  const tabs: TabConfig[] = [
    {
      id: 'idrac',
      label: 'iDRAC',
      component: <IdracTab register={register} control={control} errors={errors} enabled={idracMetricsEnabled} needsKafka={idracCollectionTargets.includes('kafka')} needsVictoriaMetrics={idracCollectionTargets.includes('victoria_metrics')} validationErrors={validationErrors} />,
    },
    {
      id: 'ldms',
      label: 'LDMS',
      component: <LdmsTab register={register} control={control} errors={errors} enabled={ldmsMetricsEnabled} validationErrors={validationErrors} />,
    },
    {
      id: 'dcgm',
      label: 'DCGM',
      component: <DcgmTab />,
    },
    {
      id: 'powerscale',
      label: 'PowerScale',
      component: <PowerscaleTab register={register} control={control} errors={errors} enabled={powerscaleMetricsEnabled || powerscaleLogsEnabled} validationErrors={validationErrors} />,
    },
    {
      id: 'ufm',
      label: 'UFM',
      component: <UfmTab register={register} control={control} errors={errors} enabled={ufmMetricsEnabled || ufmLogsEnabled} validationErrors={validationErrors} />,
    },
    {
      id: 'vast',
      label: 'VAST',
      component: <VastTab register={register} control={control} errors={errors} enabled={vastMetricsEnabled || vastLogsEnabled} validationErrors={validationErrors} />,
    },
    {
      id: 'ome',
      label: 'OME',
      component: <OmeTab register={register} control={control} enabled={omeMetricsEnabled || omeLogsEnabled} />,
    },
    {
      id: 'bridges',
      label: 'Bridges',
      component: <BridgesTab register={register} errors={errors} needsVectorLdms={needsVectorLdms} needsVectorOmeMetrics={needsVectorOmeMetrics} needsVectorOmeLogs={needsVectorOmeLogs} validationErrors={validationErrors} />,
    },
    {
      id: 'sinks',
      label: 'Sinks',
      component: <SinksTab register={register} errors={errors} control={control} needsVictoriaMetrics={needsVictoriaMetrics} needsVictoriaLogs={needsVictoriaLogs} needsKafka={needsKafka} validationErrors={validationErrors} />,
    },
  ].filter(tab => {
    // Always include Bridges and Sinks
    if (tab.id === 'bridges' || tab.id === 'sinks') return true;
    // Include source tabs only if selected in guiding screen
    return selectedTelemetrySources.includes(tab.id);
  });

  return (
    <div className="space-y-6">
      <input
        id="telemetry-upload-input"
        ref={fileInputRef}
        type="file"
        multiple
        accept=".yml,.yaml"
        onChange={handleFileUpload}
        style={{ display: 'none' }}
      />

      {uploadError && (
        <div className="card">
          <div className="error-message" style={{ whiteSpace: 'pre-wrap' }}>
            {uploadError}
          </div>
        </div>
      )}

      {selectedTelemetrySources.length === 0 ? (
        <div className="card">
          <p className="text-muted">
            No telemetry sources selected — configure in Step 1 (Deployment Setup)
          </p>
        </div>
      ) : (
        <Tabs tabs={tabs} activeTab={telemetryActiveTab} onTabChange={setTelemetryActiveTab} />
      )}
    </div>
  );
};
