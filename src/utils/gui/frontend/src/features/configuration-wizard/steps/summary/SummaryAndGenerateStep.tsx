import { useState, useEffect } from 'react';
import { useConfigStore } from '../../configStore';
import { useGenerateAll, useJobStatus } from '../../../../utils/hooks/useConfig';
import { API_BASE_URL } from '../../../../utils/api';
import { showAlert } from '../../../toast/toastStore';
import { transformSlurmClusters } from '../../utils/transformSlurmCluster';
import { validateL2Configuration } from '../../utils/l2Validation';

export const SummaryAndGenerateStep = () => {
  const {
    wizardData,
    clusterType,
    enableCloudInit,
    enableBuildStream,
    enableGitlab,
    enableTelemetry,
    enableHa,
    setValidationErrors,
    clearValidationErrors
  } = useConfigStore();
  const [isGenerating, setIsGenerating] = useState(false);
  const [generationProgress, setGenerationProgress] = useState(0);
  const [generationComplete, setGenerationComplete] = useState(false);
  const [jobId, setJobId] = useState<string | null>(null);
  const [generationResult, setGenerationResult] = useState<any>(null);
  const [validationErrorData, setValidationErrorData] = useState<Record<string, string[]> | null>(null);
  const [outputDir, setOutputDir] = useState('');
  
  const generateAll = useGenerateAll();
  const { data: jobStatus } = useJobStatus(jobId || '');

  const handleDownloadFiles = async () => {
    try {
      // Call the backend to download the generated files
      const response = await fetch(`${API_BASE_URL}/config/download-files`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({ input_dir: generationResult?.input_dir }),
      });

      console.log('Download response status:', response.status);

      if (!response.ok) {
        const errorData = await response.json().catch(() => ({ detail: 'Failed to download files' }));
        console.log('Download error data:', errorData);
        const errorMessage = errorData.detail || errorData.error || 'Failed to download files';
        // Show toast notification for all download errors
        showAlert(errorMessage, 'error');
        return;
      }

      // Get the blob and trigger download
      const blob = await response.blob();
      const url = window.URL.createObjectURL(blob);
      const link = document.createElement('a');
      link.href = url;
      link.download = `omnia-config-files-${Date.now()}.zip`;
      document.body.appendChild(link);
      link.click();
      document.body.removeChild(link);
      // Delay revoking the object URL so the browser has time to start the download
      setTimeout(() => window.URL.revokeObjectURL(url), 1000);
    } catch (error) {
      console.error('Download error:', error);
      showAlert(error instanceof Error ? error.message : 'Download failed', 'error');
    }
  };


  const handleGenerate = async () => {
    // Run full L1 + L2 validation against store data
    const validationResult = validateL2Configuration(
      wizardData,
      clusterType,
      enableCloudInit,
      enableTelemetry,
      enableBuildStream,
      enableGitlab,
      enableHa
    );

    if (!validationResult.success) {
      // Store validation errors in configStore for display on form fields
      setValidationErrors(validationResult.errors);

      // Group errors by step for user-friendly display and deduplicate by field
      const grouped = validationResult.errors.reduce((acc, err) => {
        acc[err.step] = acc[err.step] || {};
        const cleanField = err.field.replace(/\.$/, '');
        // Only keep the first error for each field to avoid duplicates
        if (!acc[err.step][cleanField]) {
          acc[err.step][cleanField] = err.message;
        }
        return acc;
      }, {} as Record<string, Record<string, string>>);

      // Convert back to array format for display
      const groupedArray = Object.entries(grouped).map(([step, fieldMap]) => ({
        step,
        messages: Object.values(fieldMap)
      }));

      setValidationErrorData(groupedArray.reduce((acc, item) => {
        acc[item.step] = item.messages;
        return acc;
      }, {} as Record<string, string[]>));
      return;
    }

    // Validation passed - clear any stored errors and proceed with generation
    clearValidationErrors();
    setValidationErrorData(null);
    setIsGenerating(true);
    setGenerationProgress(0);
    
    try {
      // Transform slurm_cluster data before sending to backend
      const transformedData = {
        ...wizardData,
        output_dir: outputDir,
        slurm_cluster: transformSlurmClusters(wizardData.slurm_cluster as any),
        language: 'en_US.UTF-8', // Always force correct language value
      };

      // Send all wizard data including pxe_mapping_data
      const result = await generateAll.mutateAsync(transformedData as any);
      if ((result as any).job_id) {
        setJobId((result as any).job_id);
      }
    } catch (error) {
      showAlert(error instanceof Error ? error.message : 'Generation failed', 'error');
      setIsGenerating(false);
    }
  };

  // Update progress based on job status
  useEffect(() => {
    if (jobStatus) {
      console.log('Job status received:', jobStatus);
      setGenerationProgress((jobStatus as any).progress || 0);
      
      if ((jobStatus as any).status === 'completed') {
        setGenerationComplete(true);
        setIsGenerating(false);
        setGenerationResult((jobStatus as any).result);
      } else if ((jobStatus as any).status === 'failed') {
        showAlert((jobStatus as any).error || 'Generation failed', 'error');
        setIsGenerating(false);
        setGenerationResult((jobStatus as any).result);
      }
    }
  }, [jobStatus]);

  // Helper function to count only networks that have been filled out
  const getConfiguredNetworkCount = (networks: any): number => {
    if (!Array.isArray(networks)) return 0;
    return networks.filter((n: any) => {
      if (n?.admin_network?.subnet?.trim?.()) return true;
      if (n?.ib_network?.subnet?.trim?.()) return true;
      if (Array.isArray(n?.additional_subnets) && n.additional_subnets.some((s: any) => s?.subnet?.trim?.())) return true;
      return false;
    }).length;
  };

  // Helper function to check if data is meaningful
  const hasMeaningfulData = (data: any): boolean => {
    if (!data) return false;
    if (typeof data === 'boolean') return data;
    if (typeof data === 'string') return data.trim().length > 0;
    if (typeof data === 'number') return data !== 0;
    if (Array.isArray(data)) {
      // For arrays, check if any item has meaningful data
      return data.some((item: any) => {
        if (typeof item === 'object' && item !== null) {
          // For cluster objects, cluster_name must be filled to be considered configured
          if (item.cluster_name !== undefined) {
            return item.cluster_name.toString().trim().length > 0;
          }
          // For other objects, check if any key has meaningful value
          return Object.values(item).some((val: any) => {
            if (typeof val === 'string') return val.trim().length > 0;
            if (typeof val === 'number') return val !== 0;
            return val !== null && val !== undefined;
          });
        }
        return false;
      });
    }
    if (typeof data === 'object') {
      return Object.keys(data).length > 0;
    }
    return false;
  };

  const networkCount = getConfiguredNetworkCount(wizardData.Networks);

  return (
    <div className="space-y-6">
      <div className="card">
        <h2>Configuration Summary</h2>
        <div className="space-y-2">
          <div>
            <strong>PXE Functional Groups:</strong> {hasMeaningfulData(wizardData.pxe_mapping_data) ? `${Array.isArray(wizardData.pxe_mapping_data) ? (wizardData.pxe_mapping_data as any[]).length : 0} row(s)` : 'Not uploaded'}
          </div>

          <div>
            <strong>Network Configuration:</strong> {networkCount > 0 ? 'Network configured' : 'Not configured'}
          </div>

          <div>
            <strong>Omnia Config:</strong>
            <div style={{ paddingLeft: '20px', marginTop: '8px' }}>
              <div>Slurm Cluster: {hasMeaningfulData(wizardData.slurm_cluster) ? `${Array.isArray(wizardData.slurm_cluster) ? (wizardData.slurm_cluster as any[]).length : 0} cluster(s)` : 'Not configured'}</div>
              <div>Service K8s Cluster: {hasMeaningfulData(wizardData.service_k8s_cluster) ? `${Array.isArray(wizardData.service_k8s_cluster) ? (wizardData.service_k8s_cluster as any[]).length : 0} cluster(s)` : 'Not configured'}</div>
            </div>
          </div>

          {enableCloudInit && (
            <div>
              <strong>Cloud-Init Config:</strong> {hasMeaningfulData(wizardData.cloud_init_common) || hasMeaningfulData(wizardData.cloud_init_groups) ? 'Configured' : 'Not configured'}
            </div>
          )}

          {(clusterType === 'k8s' || clusterType === 'both') && enableTelemetry && (
            <div>
              <strong>Telemetry Config: </strong>
              {(() => {
                const sources = (wizardData.telemetry_sources as any) || {};
                const configuredSources = [];
                if (sources.idrac?.metrics_enabled) configuredSources.push('iDRAC');
                if (sources.ldms?.metrics_enabled) configuredSources.push('LDMS');
                if (sources.dcgm?.metrics_enabled) configuredSources.push('DCGM');
                if (sources.powerscale?.metrics_enabled || sources.powerscale?.logs_enabled) configuredSources.push('PowerScale');
                if (sources.ufm?.metrics_enabled || sources.ufm?.logs_enabled) configuredSources.push('UFM');
                if (sources.vast?.metrics_enabled || sources.vast?.logs_enabled) configuredSources.push('VAST');
                if (sources.ome?.metrics_enabled || sources.ome?.logs_enabled) configuredSources.push('OME');
                return configuredSources.length > 0 ? configuredSources.join(', ') : 'Not configured';
              })()}
            </div>
          )}

          {enableBuildStream && (
            <div>
              <strong>Build Stream:</strong> {hasMeaningfulData(wizardData.enable_build_stream) ? 'Enabled' : 'Not enabled'}
            </div>
          )}

          {enableGitlab && (
            <div>
              <strong>GitLab Config:</strong> {hasMeaningfulData(wizardData.gitlab_host) ? 'Configured' : 'Not configured'}
            </div>
          )}

          {enableHa && (
            <div>
              <strong>High Availability:</strong> {hasMeaningfulData(wizardData.service_k8s_cluster_ha) ? `${(wizardData.service_k8s_cluster_ha as any[]).length} HA cluster(s)` : 'Not configured'}
            </div>
          )}

          {(clusterType === 'k8s' || clusterType === 'both') && enableTelemetry && (
            <div>
              <strong>Telemetry Storage:</strong> {hasMeaningfulData(wizardData.telemetry_sinks) ? 'Configured' : 'Not configured'}
            </div>
          )}

          <div>
            <strong>Storage Config:</strong> {hasMeaningfulData(wizardData.mounts) || hasMeaningfulData(wizardData.mount_params) || hasMeaningfulData(wizardData.powervault_config) || hasMeaningfulData(wizardData.swap) || hasMeaningfulData(wizardData.s3_configurations) ? 'Configured' : 'Not configured'}
          </div>

          <div>
            <strong>Security Config:</strong> Enabled
          </div>
        </div>
      </div>

      {validationErrorData && (
        <div className="card" style={{ borderColor: '#c62828', backgroundColor: '#ffebee' }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
            <h3 style={{ color: '#c62828', margin: 0 }}>Generation Failed</h3>
            <button
              onClick={() => setValidationErrorData(null)}
              style={{
                background: 'none',
                border: 'none',
                color: '#c62828',
                fontSize: '20px',
                cursor: 'pointer',
                padding: '4px 8px'
              }}
            >
              ×
            </button>
          </div>
          <div style={{ marginTop: '16px', color: '#546e7a' }}>
            <p style={{ marginBottom: '12px' }}>Please fix the following validation errors before generating configuration files:</p>
            {Object.entries(validationErrorData).map(([step, msgs]) => (
              <div key={step} style={{ marginBottom: '16px', padding: '12px', backgroundColor: '#fff', borderRadius: '4px', border: '1px solid #ffcdd2' }}>
                <h4 style={{ margin: '0 0 8px 0', color: '#c62828' }}>{step}</h4>
                <ul style={{ margin: 0, paddingLeft: '20px', color: '#546e7a' }}>
                  {msgs.map((msg: string, idx: number) => (
                    <li key={idx} style={{ marginBottom: '4px' }}>{msg}</li>
                  ))}
                </ul>
              </div>
            ))}
          </div>
        </div>
      )}

      {isGenerating && (
        <div className="card" style={{ borderColor: '#0097a7' }}>
          <h3 style={{ color: '#0097a7' }}>Generating Configuration Files...</h3>
          <div style={{ marginTop: '16px' }}>
            <div style={{ backgroundColor: '#e0e0e0', borderRadius: '4px', height: '24px', overflow: 'hidden' }}>
              <div 
                style={{ 
                  backgroundColor: '#0097a7', 
                  height: '100%', 
                  width: `${generationProgress}%`,
                  transition: 'width 0.3s ease'
                }}
              />
            </div>
            <p style={{ marginTop: '8px', color: '#546e7a' }}>
              {generationProgress}% Complete
            </p>
          </div>
        </div>
      )}

      {generationComplete && (
        <div className="card" style={{ borderColor: '#2e7d32', backgroundColor: '#e8f5e9' }}>
          <h3 style={{ color: '#2e7d32' }}>Generation Complete!</h3>
          <p style={{ color: '#546e7a' }}>
            All configuration files have been generated successfully.
          </p>
          {generationResult && (
            <div style={{ marginTop: '16px', padding: '16px', backgroundColor: '#fff', borderRadius: '4px', border: '1px solid #ddd' }}>
              <div style={{ marginBottom: '12px' }}>
                <strong>Configuration Files:</strong> {generationResult.input_dir || 'N/A'}
              </div>
            </div>
          )}
          <div style={{ marginTop: '16px', display: 'flex', gap: '12px' }}>
            <button
              onClick={handleDownloadFiles}
              className="button button-primary"
            >
              Download Files
            </button>
          </div>
        </div>
      )}

      {!generationComplete && !isGenerating && (
        <div className="card" style={{ borderColor: '#0097a7', backgroundColor: '#e0f4f8' }}>
          <h3 style={{ color: '#0097a7' }}>Ready to Generate</h3>
          <p style={{ color: '#546e7a' }}>
            Click the Generate button below to generate all deployment configuration files based on your selections.
            This will create all necessary YAML configuration files for your OMNIA deployment.
            Note: Catalog is managed separately through the Catalog Editor.
          </p>
          <div className="form-group" style={{ marginTop: '16px' }}>
            <label className="form-label">Output Directory (Optional)</label>
            <input
              type="text"
              value={outputDir}
              onChange={(e) => setOutputDir(e.target.value)}
              className="form-input"
              placeholder="Leave empty to use default server directory"
            />
            <p className="text-small-muted" style={{ marginTop: '4px' }}>
              Server-side directory where generated files will be saved
            </p>
          </div>
          <div style={{ marginTop: '16px', display: 'flex', gap: '12px' }}>
            <button
              onClick={handleGenerate}
              className="button button-primary"
            >
              Generate Configuration Files
            </button>
          </div>
        </div>
      )}
    </div>
  );
};
