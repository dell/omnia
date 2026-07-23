import { useEffect, useState, useRef } from 'react';
import { useConfigStore } from '../../configStore';
import { useNavigate } from 'react-router-dom';
import { analyzePxeMapping } from '../../utils/pxeMappingAnalyzer';
import { parsePxeMappingFile } from '../../utils/csvParser';

const CLUSTER_OPTIONS = [
  { value: 'slurm', label: 'Slurm Only', description: 'Slurm workload manager cluster' },
  { value: 'k8s', label: 'Kubernetes Only', description: 'Kubernetes service cluster' },
  { value: 'both', label: 'Both', description: 'Slurm + Kubernetes clusters' },
] as const;

const TELEMETRY_SOURCES = ['IDRAC', 'LDMS', 'DCGM', 'Powerscale', 'UFM', 'VAST', 'OME'] as const;

export const DeploymentSetupStep = () => {
  const clusterType = useConfigStore((s) => s.clusterType);
  const setClusterType = useConfigStore((s) => s.setClusterType);
  const enableHa = useConfigStore((s) => s.enableHa);
  const setEnableHa = useConfigStore((s) => s.setEnableHa);
  const enableCloudInit = useConfigStore((s) => s.enableCloudInit);
  const setEnableCloudInit = useConfigStore((s) => s.setEnableCloudInit);
  const enableBmcDiscovery = useConfigStore((s) => s.enableBmcDiscovery);
  const setEnableBmcDiscovery = useConfigStore((s) => s.setEnableBmcDiscovery);
  const selectedTelemetrySources = useConfigStore((s) => s.selectedTelemetrySources);
  const setSelectedTelemetrySources = useConfigStore((s) => s.setSelectedTelemetrySources);
  const enableBuildStream = useConfigStore((s) => s.enableBuildStream);
  const setEnableBuildStream = useConfigStore((s) => s.setEnableBuildStream);
  const enableGitlab = useConfigStore((s) => s.enableGitlab);
  const setEnableGitlab = useConfigStore((s) => s.setEnableGitlab);
  const enableTelemetry = useConfigStore((s) => s.enableTelemetry);
  const setEnableTelemetry = useConfigStore((s) => s.setEnableTelemetry);
  const setStepValid = useConfigStore((s) => s.setStepValid);
  const wizardData = useConfigStore((s) => s.wizardData);
  const pxeMappingData = useConfigStore((s) => s.wizardData.pxe_mapping_data as any[] | undefined);
  const updateWizardFields = useConfigStore((s) => s.updateWizardFields);
  const configMode = useConfigStore((s) => s.configMode);
  const setConfigMode = useConfigStore((s) => s.setConfigMode);
  const navigate = useNavigate();
  const [pxeFileError, setPxeFileError] = useState<string | null>(null);
  const fileInputRef = useRef<HTMLInputElement>(null);

  // Mark step as valid only when required selections are made
  useEffect(() => {
    const isValid = configMode !== null && clusterType !== null;
    setStepValid(1, isValid);
  }, [configMode, clusterType, setStepValid]);

  // Auto-detect configuration from PXE mapping data if available
  const prevPxeDataRef = useRef<unknown>(null);

  useEffect(() => {
    if (pxeMappingData && pxeMappingData.length > 0 && pxeMappingData !== prevPxeDataRef.current) {
      prevPxeDataRef.current = pxeMappingData;
      const analysis = analyzePxeMapping(pxeMappingData);

      // Auto-set cluster type if not already set (reliable detection)
      if (analysis.clusterType && !clusterType) {
        setClusterType(analysis.clusterType);
      }

      // Store network analysis for use in Network Configuration step
      updateWizardFields({
        pxe_network_analysis: analysis.networkInfo,
      });
    }
  }, [pxeMappingData, clusterType, setClusterType, updateWizardFields]);

  // Reset HA when cluster type changes to slurm
  useEffect(() => {
    if (clusterType === 'slurm' && enableHa) {
      setEnableHa(false);
    }
  }, [clusterType, enableHa, setEnableHa]);

  const handleConfigModeSelect = (mode: 'pxe_upload' | 'manual') => {
    if (mode === 'manual') {
      setConfigMode(mode);
      // Don't navigate away - let user configure on this page
    } else if (mode === 'pxe_upload') {
      // Focus the file input to guide the user
      fileInputRef.current?.click();
    }
  };

  const handlePxeFileUpload = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;

    try {
      const data = await parsePxeMappingFile(file);
      setPxeFileError(null);
      updateWizardFields({ pxe_mapping_data: data });
      setConfigMode('pxe_upload');
    } catch (error) {
      setPxeFileError(error instanceof Error ? error.message : 'Failed to parse CSV file');
    } finally {
      // Reset so the same file can be re-selected
      e.target.value = '';
    }
  };

  const handleTelemetrySourceToggle = (source: string) => {
    const isSelected = selectedTelemetrySources.includes(source);
    const newSources = isSelected
      ? selectedTelemetrySources.filter(s => s !== source)
      : [...selectedTelemetrySources, source];
    setSelectedTelemetrySources(newSources);

    // Update telemetry_sources in wizardData to match selection
    const currentTelemetrySources = (wizardData.telemetry_sources as any) || {};
    const updatedTelemetrySources = { ...currentTelemetrySources };

    if (isSelected) {
      // Source deselected - disable metrics
      if (updatedTelemetrySources[source]) {
        updatedTelemetrySources[source] = {
          ...updatedTelemetrySources[source],
          metrics_enabled: false,
          logs_enabled: false,
        };
      }
    } else {
      // Source selected - enable metrics
      if (updatedTelemetrySources[source]) {
        updatedTelemetrySources[source] = {
          ...updatedTelemetrySources[source],
          metrics_enabled: true,
        };
      } else {
        // Create source entry if it doesn't exist
        updatedTelemetrySources[source] = {
          metrics_enabled: true,
          collection_targets: [],
        };
      }
    }

    updateWizardFields({ telemetry_sources: updatedTelemetrySources });
  };

  const handleStartBmcDiscovery = () => {
    navigate('/wizard/bmc-discovery');
  };

  // Render functions (not components) to avoid remount on every render
  const renderClusterTypeSection = () => (
    <div className="card">
      <h2 className="text-xl font-semibold mb-4">Cluster Type</h2>
      {configMode === 'pxe_upload' && (
        <p className="text-gray-600 mb-4">Cluster type auto-detected from PXE mapping file</p>
      )}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-8">
        {CLUSTER_OPTIONS.map(({ value, label, description }) => (
          <label
            key={value}
            className={`deployment-setup-card ${clusterType === value ? 'selected' : ''}`}
          >
            <input
              type="radio"
              name="clusterType"
              value={value}
              checked={clusterType === value}
              onChange={(e) => setClusterType(e.target.value as 'slurm' | 'k8s' | 'both')}
              className="visually-hidden"
            />
            <div className="card-content">
              <h3 className="font-medium mb-2">{label}</h3>
              <p className="text-sm text-gray-600">{description}</p>
            </div>
          </label>
        ))}
      </div>

      {(clusterType === 'k8s' || clusterType === 'both') && (
        <div className="mt-6 pt-6 border-t">
          <div className="form-checkbox">
            <input
              type="checkbox"
              id={`enable-ha-${configMode}`}
              checked={enableHa}
              onChange={(e) => setEnableHa(e.target.checked)}
            />
            <label htmlFor={`enable-ha-${configMode}`}>Enable High Availability for Kubernetes</label>
          </div>
          <p className="text-sm text-gray-600 mt-1">
            When enabled, HA configuration section will be shown in the Kubernetes tab
          </p>
        </div>
      )}
    </div>
  );

  const renderOptionalFeaturesSection = () => (
    <div className="card">
      <h2 className="text-xl font-semibold mb-4">Optional Features</h2>

      <div className="space-y-2">
        <div className={`space-y-2 ${configMode === 'pxe_upload' ? 'disabled-section' : ''}`}>
          <div className="form-checkbox">
            <input
              type="checkbox"
              id={`enable-bmc-discovery-${configMode}`}
              checked={enableBmcDiscovery}
              onChange={(e) => setEnableBmcDiscovery(e.target.checked)}
              disabled={configMode === 'pxe_upload'}
            />
            <label htmlFor={`enable-bmc-discovery-${configMode}`}>Enable BMC Discovery via OME</label>
          </div>
          {enableBmcDiscovery && configMode !== 'pxe_upload' && (
            <button
              onClick={handleStartBmcDiscovery}
              className="button button-secondary ml-6 mt-2"
            >
              Start BMC Discovery
            </button>
          )}
          <p className="text-sm text-gray-600 ml-6">
            Automatically discover nodes via Dell OpenManage Enterprise
            {configMode === 'pxe_upload' && <span className="block text-orange-600 mt-1">(Disabled - PXE mapping file already uploaded)</span>}
          </p>
        </div>

        <div className="form-checkbox">
          <input
            type="checkbox"
            id={`enable-cloud-init-${configMode}`}
            checked={enableCloudInit}
            onChange={(e) => setEnableCloudInit(e.target.checked)}
          />
          <label htmlFor={`enable-cloud-init-${configMode}`}>Enable Cloud-Init Configuration</label>
        </div>
        <p className="text-sm text-gray-600 ml-6">
          Configure additional cloud-init write_files and runcmd for node provisioning
        </p>

        {(clusterType === 'k8s' || clusterType === 'both') && (
          <div className="pt-4 border-t">
            <div className="form-checkbox">
              <input
                type="checkbox"
                id={`enable-telemetry-${configMode}`}
                checked={enableTelemetry}
                onChange={(e) => {
                  setEnableTelemetry(e.target.checked);
                  // Clear all telemetry sources when telemetry is disabled
                  if (!e.target.checked) {
                    setSelectedTelemetrySources([]);
                    updateWizardFields({
                      telemetry_sources: {
                        idrac: { metrics_enabled: false, collection_targets: [] },
                        ldms: { metrics_enabled: false, collection_targets: [] },
                        dcgm: { metrics_enabled: false },
                        powerscale: { metrics_enabled: false, logs_enabled: false, collection_targets: [] },
                        ufm: { metrics_enabled: false, logs_enabled: false, collection_targets: [] },
                        vast: { metrics_enabled: false, logs_enabled: false, collection_targets: [] },
                        ome: { metrics_enabled: false, logs_enabled: false, collection_targets: [] },
                      }
                    });
                  }
                }}
              />
              <label htmlFor={`enable-telemetry-${configMode}`}>Enable Telemetry Configuration</label>
            </div>
            {enableTelemetry && (
              <>
                <p className="font-medium mb-3 mt-4">Telemetry Sources</p>
                <div className="grid grid-cols-2 md:grid-cols-4 gap-2 ml-6">
                  {TELEMETRY_SOURCES.map((source) => (
                    <label key={source} className="form-checkbox">
                      <input
                        type="checkbox"
                        checked={selectedTelemetrySources.includes(source.toLowerCase())}
                        onChange={() => handleTelemetrySourceToggle(source.toLowerCase())}
                      />
                      <span className="capitalize">{source.replace('_', '-')}</span>
                    </label>
                  ))}
                </div>
                <p className="text-sm text-gray-600 ml-6 mt-2">
                  Select telemetry sources to configure
                </p>
              </>
            )}
          </div>
        )}

        <div className="pt-4 border-t">
          <div className="form-checkbox">
            <input
              type="checkbox"
              id={`enable-build-stream-${configMode}`}
              checked={enableBuildStream}
              onChange={(e) => setEnableBuildStream(e.target.checked)}
            />
            <label htmlFor={`enable-build-stream-${configMode}`}>Enable Build Stream CI/CD</label>
          </div>
          <p className="text-sm text-gray-600 ml-6">
            Configure BuildStream host for catalog management
          </p>

          <div className="form-checkbox mt-3">
            <input
              type="checkbox"
              id={`enable-gitlab-${configMode}`}
              checked={enableGitlab}
              onChange={(e) => setEnableGitlab(e.target.checked)}
            />
            <label htmlFor={`enable-gitlab-${configMode}`}>Enable GitLab Server Configuration</label>
          </div>
          <p className="text-sm text-gray-600 ml-6">
            Configure GitLab server for project management
          </p>
        </div>
      </div>
    </div>
  );

  return (
    <div className="space-y-8">
      {!configMode && (
        <div className="card">
          <h2 className="text-xl font-semibold mb-4">Configuration Mode</h2>
          <p className="text-gray-600 mb-6">Choose how you want to configure your deployment:</p>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
            <label className="deployment-setup-card">
              <input
                type="radio"
                name="configMode"
                value="pxe_upload"
                checked={false}
                onChange={() => handleConfigModeSelect('pxe_upload')}
                className="visually-hidden"
              />
              <div className="card-content">
                <h3 className="font-medium mb-2">Upload PXE Mapping File</h3>
                <p className="text-sm text-gray-600 mb-4">Upload your PXE mapping file to auto-populate configuration based on discovered nodes</p>
                <input
                  type="file"
                  ref={fileInputRef}
                  accept=".csv"
                  onChange={handlePxeFileUpload}
                  onClick={(e) => e.stopPropagation()}
                  className="form-input"
                  style={{ maxWidth: '300px' }}
                />
                {pxeFileError && <p className="text-sm text-red-600 mt-2">{pxeFileError}</p>}
              </div>
            </label>

            <label className="deployment-setup-card">
              <input
                type="radio"
                name="configMode"
                value="manual"
                checked={false}
                onChange={() => handleConfigModeSelect('manual')}
                className="visually-hidden"
              />
              <div className="card-content">
                <h3 className="font-medium mb-2">Manual Configuration</h3>
                <p className="text-sm text-gray-600">Manually configure each step including PXE functional groups, network settings, and cluster configuration</p>
              </div>
            </label>
          </div>
        </div>
      )}

      {configMode && (
        <>
          {renderClusterTypeSection()}
          {renderOptionalFeaturesSection()}
        </>
      )}
    </div>
  );
};
