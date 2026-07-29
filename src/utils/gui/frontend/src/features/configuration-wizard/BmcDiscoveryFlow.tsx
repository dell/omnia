import { useState, useEffect, useMemo } from 'react';
import { useNavigate } from 'react-router-dom';
import { useForm } from 'react-hook-form';
import { zodResolver } from '@hookform/resolvers/zod';
import { z } from 'zod';
import { IPV4_PATTERN } from './schemas/common';
import { DeploymentConfigsStep } from './steps/network/DeploymentConfigsStep';
import { useConfigStore } from './configStore';
import { useGenerateAll, useJobStatus } from '../../utils/hooks/useConfig';
import { showAlert } from '../toast/toastStore';
import type { JobStatus } from '../../utils/api';

interface JobStatusResponse extends JobStatus {
  progress?: number;
  error?: string;
}

const bmcCredentialsSchema = z.object({
  ome_ip: z.string().regex(IPV4_PATTERN, 'OME IP must be a valid IPv4 address'),
});

type BmcCredentialsFormData = z.infer<typeof bmcCredentialsSchema>;

const BMC_STEPS = [
  { id: 1, title: 'BMC Credentials', description: 'Enter Dell OpenManage Enterprise IP Address' },
  { id: 2, title: 'Network Configuration', description: 'Configure network settings for BMC discovery' },
  { id: 3, title: 'Summary & Generate', description: 'Review and generate discovery configuration files' },
];

export const BmcDiscoveryFlow = () => {
  const navigate = useNavigate();
  const updateWizardFields = useConfigStore((s) => s.updateWizardFields);
  const wizardData = useConfigStore((s) => s.wizardData);
  const setWizardActiveStep = useConfigStore((s) => s.setActiveStep);
  const setConfigMode = useConfigStore((s) => s.setConfigMode);
  const [activeStep, setActiveStep] = useState(1);
  const [isGenerating, setIsGenerating] = useState(false);
  const [generationError, setGenerationError] = useState<string | null>(null);
  const [generationProgress, setGenerationProgress] = useState(0);
  const [generationComplete, setGenerationComplete] = useState(false);
  const [jobId, setJobId] = useState<string | null>(null);
  const omeIpFromStore = (wizardData.ome_ip as string) || '';

  const generateAll = useGenerateAll();
  const { data: jobStatus } = useJobStatus(jobId ?? '') as { data: JobStatusResponse | undefined };
  const activeJobStatus = jobId ? jobStatus : undefined;

  const {
    register,
    handleSubmit,
    formState: { errors },
    watch,
  } = useForm<BmcCredentialsFormData>({
    resolver: zodResolver(bmcCredentialsSchema) as any,
    mode: 'onTouched',
    defaultValues: {
      ome_ip: (wizardData.ome_ip as string) || '',
    },
  });

  const omeIp = watch('ome_ip');

  // Check if network configuration is valid for step 2
  const hasValidNetworkConfig = useMemo(() => {
    const networks = wizardData.Networks;
    if (!Array.isArray(networks) || networks.length === 0) return false;
    return networks.some((n: any) => n?.admin_network?.subnet?.trim?.());
  }, [wizardData.Networks]);

  const handleNext = () => {
    if (activeStep === 1) {
      // Sync form data to store before advancing
      updateWizardFields({ ome_ip: omeIp });
    }
    if (activeStep < BMC_STEPS.length) {
      setActiveStep(activeStep + 1);
    }
  };

  const handleBack = () => {
    if (activeStep > 1) {
      setActiveStep(activeStep - 1);
    }
  };

  const handleBmcCredentialsSubmit = (data: BmcCredentialsFormData) => {
    updateWizardFields({ ome_ip: data.ome_ip });
    handleNext();
  };

  const handleGenerate = async () => {
    setGenerationError(null);
    if (!omeIpFromStore || !IPV4_PATTERN.test(omeIpFromStore)) {
      setGenerationError('A valid OME IP address is required before generating.');
      return;
    }
    setIsGenerating(true);
    setGenerationProgress(0);

    try {
      // Prepare the data for backend - only include BMC discovery relevant fields
      const bmcData = {
        ome_ip: omeIpFromStore,
        Networks: wizardData.Networks,
        enable_bmc_discovery: true,
        language: 'en_US.UTF-8',
        files_to_generate: ['discovery_config.yml', 'network_spec.yml'],
      };

      // Call the backend API to generate files
      const result = await generateAll.mutateAsync(bmcData) as unknown as { job_id: string };
      if (result.job_id) {
        setJobId(result.job_id);
      }
    } catch (error) {
      showAlert(error instanceof Error ? error.message : 'Generation failed', 'error');
      setGenerationError(error instanceof Error ? error.message : 'Failed to generate configuration files');
      setIsGenerating(false);
    }
  };

  // Update progress based on job status
  useEffect(() => {
    if (activeJobStatus) {
      setGenerationProgress(activeJobStatus.progress || 0);

      if (activeJobStatus.status === 'completed') {
        setGenerationComplete(true);
        setIsGenerating(false);

        // Store the generated files info
        updateWizardFields({
          enable_bmc_discovery: true,
          ome_ip: omeIpFromStore,
        });

        // Reset configMode to null so user sees configuration mode selection
        setConfigMode(null);

        // Notify the user and navigate to the main wizard as soon as the job completes
        showAlert('BMC discovery configuration generated successfully.', 'success');
        setWizardActiveStep(1);
        navigate('/wizard');
      } else if (activeJobStatus.status === 'failed') {
        showAlert(activeJobStatus.error || 'Generation failed', 'error');
        setGenerationError(activeJobStatus.error || 'Failed to generate configuration files');
        setIsGenerating(false);
      }
    }
  }, [activeJobStatus, updateWizardFields, omeIpFromStore, navigate, setConfigMode, setWizardActiveStep]);

  const handleCancel = () => {
    navigate('/wizard');
  };

  const currentStep = BMC_STEPS.find(s => s.id === activeStep);

  return (
    <div className="space-y-6">
      <div className="wizard-header">
        <h1>BMC Discovery Setup</h1>
        {currentStep && (
          <p className="wizard-description">{currentStep.description}</p>
        )}
      </div>

      {/* Step indicator */}
      <div className="step-indicator">
        {BMC_STEPS.map((step) => (
          <div
            key={step.id}
            className={`step-item ${step.id === activeStep ? 'active' : ''} ${step.id < activeStep ? 'completed' : ''}`}
          >
            <div className="step-number">{step.id < activeStep ? '✓' : step.id}</div>
            <div className="step-label">{step.title}</div>
          </div>
        ))}
      </div>

      {generationError && (
        <div className="error-message">
          {generationError}
        </div>
      )}

      {/* Step content */}
      <div className="wizard-content">
        {activeStep === 1 && (
          <form onSubmit={handleSubmit(handleBmcCredentialsSubmit)} className="space-y-6">
            <div className="card">
              <h2 className="text-xl font-semibold mb-4">Dell OpenManage Enterprise</h2>
              <div className="form-group">
                <label className="form-label">OME IP Address (Required)</label>
                <input
                  type="text"
                  className={`form-input ${errors.ome_ip ? 'error' : ''}`}
                  placeholder="e.g., 192.168.1.100"
                  {...register('ome_ip')}
                />
                <p className="text-sm text-gray-600 mt-1">
                  Enter the IP address of your Dell OpenManage Enterprise server
                </p>
                {errors.ome_ip && <span className="error-message">{errors.ome_ip.message}</span>}
              </div>
            </div>

            <div className="wizard-footer">
              <button
                type="button"
                onClick={handleCancel}
                className="button button-secondary"
              >
                Cancel
              </button>
              <button type="submit" className="button button-tertiary">
                Next
              </button>
            </div>
          </form>
        )}

        {activeStep === 2 && (
          <div className="space-y-6">
            <div className="card">
              <h2 className="text-xl font-semibold mb-4">Network Configuration</h2>
              <DeploymentConfigsStep />
            </div>

            <div className="wizard-footer">
              <button
                type="button"
                onClick={handleBack}
                className="button button-secondary"
              >
                Back
              </button>
              <button
                type="button"
                onClick={handleNext}
                className="button button-tertiary"
                disabled={!hasValidNetworkConfig}
              >
                Next
              </button>
            </div>
          </div>
        )}

        {activeStep === 3 && (
          <div className="space-y-6">
            <div className="card">
              <h2 className="text-xl font-semibold mb-4">Summary</h2>
              <div className="space-y-2">
                <div>
                  <h3 className="font-medium">OME IP Address</h3>
                  <p className="text-gray-700">{wizardData.ome_ip as string || omeIp}</p>
                </div>
                <div>
                  <h3 className="font-medium">Network Configuration</h3>
                  <p className="text-gray-700">
                    Network settings will be included in the generated files
                  </p>
                </div>
                <div className="p-4 bg-gray-50 rounded">
                  <h3 className="font-medium mb-2">Files to Generate</h3>
                  <ul className="list-disc list-inside text-gray-700">
                    <li>discovery_config.yml</li>
                    <li>network_spec.yml</li>
                  </ul>
                </div>
              </div>
            </div>

            {isGenerating && (
              <div className="card card-primary">
                <h3 className="text-primary">Generating Configuration Files...</h3>
                <div className="mt-4">
                  <div className="progress-bar">
                    <div className="progress-fill" style={{ width: `${generationProgress}%` }} />
                  </div>
                  <p className="mt-2 text-secondary">
                    {generationProgress}% Complete
                  </p>
                </div>
              </div>
            )}

            {generationComplete && (
              <div className="card card-success">
                <h3 className="text-success">Generation Complete!</h3>
                <p className="text-secondary">
                  Discovery configuration files have been generated successfully.
                </p>
              </div>
            )}

            <div className="wizard-footer">
              <button
                type="button"
                onClick={handleBack}
                className="button button-secondary"
                disabled={isGenerating}
              >
                Back
              </button>
              <button
                type="button"
                onClick={handleGenerate}
                className="button button-primary"
                disabled={isGenerating}
              >
                {isGenerating ? 'Generating...' : 'Generate & Continue'}
              </button>
            </div>
          </div>
        )}
      </div>
    </div>
  );
};
