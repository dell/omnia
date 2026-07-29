import { useState, useEffect, useMemo, useRef } from 'react';
import { useNavigate } from 'react-router-dom';
import { DeploymentConfigsStep } from './steps/network/DeploymentConfigsStep';
import { useConfigStore } from './configStore';
import { useGenerateAll, useJobStatus } from '../../utils/hooks/useConfig';
import { showAlert } from '../toast/toastStore';
import type { JobStatus } from '../../utils/api';
import { parseAdminInventoryFile, ADMIN_INVENTORY_COLUMNS } from './utils/adminInventoryCsvParser';
import type { AdminInventoryRow } from './utils/adminInventoryCsvParser';

interface JobStatusResponse extends JobStatus {
  progress?: number;
  error?: string;
}

const MAGELLAN_STEPS = [
  { id: 1, title: 'Admin Inventory', description: 'Configure admin inventory for Magellan discovery' },
  { id: 2, title: 'Network Configuration', description: 'Configure network settings for Magellan discovery' },
  { id: 3, title: 'Summary & Generate', description: 'Review and generate discovery configuration files' },
];

export const MagellanDiscoveryFlow = () => {
  const navigate = useNavigate();
  const updateWizardFields = useConfigStore((s) => s.updateWizardFields);
  const updateWizardField = useConfigStore((s) => s.updateWizardField);
  const wizardData = useConfigStore((s) => s.wizardData);
  const setWizardActiveStep = useConfigStore((s) => s.setActiveStep);
  const setConfigMode = useConfigStore((s) => s.setConfigMode);
  const [activeStep, setActiveStep] = useState(1);
  const [isGenerating, setIsGenerating] = useState(false);
  const [generationError, setGenerationError] = useState<string | null>(null);
  const [generationProgress, setGenerationProgress] = useState(0);
  const [generationComplete, setGenerationComplete] = useState(false);
  const [jobId, setJobId] = useState<string | null>(null);
  const [parseError, setParseError] = useState<string | null>(null);
  const [editingRow, setEditingRow] = useState<number | null>(null);
  const [editFormData, setEditFormData] = useState<AdminInventoryRow | null>(null);
  const fileInputRef = useRef<HTMLInputElement>(null);

  const adminInventoryPath = (wizardData.admin_inventory_path as string) || '/opt/omnia/input/project_default/admin_inventory.csv';
  const parsedData = Array.isArray(wizardData.admin_inventory_data) ? wizardData.admin_inventory_data as AdminInventoryRow[] : [];

  const generateAll = useGenerateAll();
  const { data: jobStatus } = useJobStatus(jobId ?? '') as { data: JobStatusResponse | undefined };
  const activeJobStatus = jobId ? jobStatus : undefined;

  // Check if network configuration is valid for step 2
  const hasValidNetworkConfig = useMemo(() => {
    const networks = wizardData.Networks;
    if (!Array.isArray(networks) || networks.length === 0) return false;
    return networks.some((n: any) => n?.admin_network?.subnet?.trim?.());
  }, [wizardData.Networks]);

  // Check if step 1 is valid
  const isStep1Valid = useMemo(() => {
    return adminInventoryPath.trim().length > 0 && parsedData.length > 0;
  }, [adminInventoryPath, parsedData]);

  const handleNext = () => {
    if (activeStep < MAGELLAN_STEPS.length) {
      setActiveStep(activeStep + 1);
    }
  };

  const handleBack = () => {
    if (activeStep > 1) {
      setActiveStep(activeStep - 1);
    }
  };

  const handleCancel = () => {
    navigate('/wizard');
  };

  // CSV file upload
  const handleFileUpload = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;

    try {
      const data = await parseAdminInventoryFile(file);
      setParseError(null);
      updateWizardField('admin_inventory_data', data);
    } catch (error) {
      setParseError(error instanceof Error ? error.message : 'Failed to parse CSV file');
    }
  };

  // Inline table editing
  const handleAddRow = () => {
    const newRow: AdminInventoryRow = {
      SERVICE_TAG: '',
      GROUP_NAME: '',
      FUNCTIONAL_GROUP_NAME: '',
      ROW: '',
      RACK: '',
      SLOT: '',
      RANGE: '',
    };
    updateWizardField('admin_inventory_data', [...parsedData, newRow]);
    setEditingRow(parsedData.length);
    setEditFormData(newRow);
  };

  const handleEditRow = (index: number) => {
    setEditingRow(index);
    setEditFormData({ ...parsedData[index] });
  };

  const handleSaveRow = () => {
    if (editingRow !== null && editFormData) {
      const updatedData = [...parsedData];
      updatedData[editingRow] = editFormData;
      updateWizardField('admin_inventory_data', updatedData);
      setEditingRow(null);
      setEditFormData(null);
    }
  };

  const handleCancelEdit = () => {
    setEditingRow(null);
    setEditFormData(null);
  };

  const handleDeleteRow = (index: number) => {
    updateWizardField('admin_inventory_data', parsedData.filter((_, i) => i !== index));
  };

  const handleEditFieldChange = (field: keyof AdminInventoryRow, value: string) => {
    if (editFormData) {
      setEditFormData({ ...editFormData, [field]: value });
    }
  };

  const handleAdminInventoryPathChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    updateWizardField('admin_inventory_path', e.target.value);
  };

  // Generate handler
  const handleGenerate = async () => {
    setGenerationError(null);
    if (parsedData.length === 0) {
      setGenerationError('At least one admin inventory row is required before generating.');
      return;
    }
    setIsGenerating(true);
    setGenerationProgress(0);

    try {
      const magellanData = {
        enable_bmc_discovery: false,
        admin_inventory_path: adminInventoryPath,
        admin_inventory_data: parsedData,
        Networks: wizardData.Networks,
        files_to_generate: ['discovery_config.yml', 'admin_inventory.csv', 'network_spec.yml'],
      };

      const result = await generateAll.mutateAsync(magellanData) as unknown as { job_id: string };
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

        updateWizardFields({
          enable_bmc_discovery: false,
          admin_inventory_path: adminInventoryPath,
        });

        setConfigMode(null);
        showAlert('Magellan discovery configuration generated successfully.', 'success');
        setWizardActiveStep(1);
        navigate('/wizard');
      } else if (activeJobStatus.status === 'failed') {
        showAlert(activeJobStatus.error || 'Generation failed', 'error');
        setGenerationError(activeJobStatus.error || 'Failed to generate configuration files');
        setIsGenerating(false);
      }
    }
  }, [activeJobStatus, updateWizardFields, adminInventoryPath, navigate, setConfigMode, setWizardActiveStep]);

  const currentStep = MAGELLAN_STEPS.find(s => s.id === activeStep);

  return (
    <div className="space-y-6">
      <div className="wizard-header">
        <h1>Magellan Discovery Setup</h1>
        {currentStep && (
          <p className="wizard-description">{currentStep.description}</p>
        )}
      </div>

      {/* Step indicator */}
      <div className="step-indicator">
        {MAGELLAN_STEPS.map((step) => (
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
          <div className="space-y-6">
            <div className="card">
              <h2 className="text-xl font-semibold mb-4">Admin Inventory</h2>

              <div className="form-group">
                <label className="form-label">Admin Inventory CSV File</label>
                <input
                  type="file"
                  accept=".csv"
                  className="form-input"
                  onChange={handleFileUpload}
                  ref={fileInputRef}
                />
                {parseError && (
                  <div className="error-message mt-2">{parseError}</div>
                )}
                {parsedData.length === 0 && !parseError && (
                  <div className="mt-3">
                    <p className="text-muted">
                      No admin inventory data loaded. Upload a CSV file or create a new inventory.
                    </p>
                    <button
                      type="button"
                      onClick={handleAddRow}
                      className="button button-secondary mt-2"
                    >
                      Create New Inventory
                    </button>
                  </div>
                )}
              </div>

              <div className="form-group mt-4">
                <label className="form-label">Admin Inventory File Path (Required)</label>
                <input
                  type="text"
                  className="form-input"
                  placeholder="/opt/omnia/input/project_default/admin_inventory.csv"
                  value={adminInventoryPath}
                  onChange={handleAdminInventoryPathChange}
                />
                <p className="text-sm text-gray-600 mt-1">
                  Default: /opt/omnia/input/project_default/admin_inventory.csv
                </p>
              </div>
            </div>

            {parsedData.length > 0 && (
              <div className="pxe-mapping-container">
                <div className="pxe-mapping-header">
                  <h3>Admin Inventory Data ({parsedData.length} rows)</h3>
                  <button
                    type="button"
                    onClick={handleAddRow}
                    className="pxe-mapping-button pxe-mapping-button-primary pxe-mapping-button-small"
                  >
                    + Add Row
                  </button>
                </div>
                <div className="pxe-mapping-scroll-container">
                  <table className="pxe-mapping-table">
                    <thead>
                      <tr>
                        {ADMIN_INVENTORY_COLUMNS.map((col) => (
                          <th key={col}>
                            {col.replace(/_/g, ' ')}
                          </th>
                        ))}
                        <th>Actions</th>
                      </tr>
                    </thead>
                    <tbody>
                      {parsedData.map((row, index) => (
                        <tr key={index}>
                          {editingRow === index ? (
                            <>
                              {ADMIN_INVENTORY_COLUMNS.map((col) => (
                                <td key={col}>
                                  <input
                                    type="text"
                                    value={editFormData?.[col] || ''}
                                    onChange={(e) => handleEditFieldChange(col, e.target.value)}
                                    className="pxe-mapping-input"
                                    placeholder={col === 'SERVICE_TAG' ? 'Required' : 'Optional'}
                                  />
                                </td>
                              ))}
                              <td className="pxe-mapping-actions-cell">
                                <button
                                  type="button"
                                  onClick={handleSaveRow}
                                  className="pxe-mapping-button pxe-mapping-button-success pxe-mapping-button-small"
                                >
                                  Save
                                </button>
                                <button
                                  type="button"
                                  onClick={handleCancelEdit}
                                  className="pxe-mapping-button pxe-mapping-button-secondary pxe-mapping-button-small"
                                >
                                  Cancel
                                </button>
                              </td>
                            </>
                          ) : (
                            <>
                              {ADMIN_INVENTORY_COLUMNS.map((col) => (
                                <td key={col}>
                                  {row[col] || '-'}
                                </td>
                              ))}
                              <td className="pxe-mapping-actions-cell">
                                <button
                                  type="button"
                                  onClick={() => handleEditRow(index)}
                                  className="pxe-mapping-button pxe-mapping-button-primary pxe-mapping-button-small"
                                >
                                  Edit
                                </button>
                                <button
                                  type="button"
                                  onClick={() => handleDeleteRow(index)}
                                  className="pxe-mapping-button pxe-mapping-button-danger pxe-mapping-button-small"
                                >
                                  Delete
                                </button>
                              </td>
                            </>
                          )}
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              </div>
            )}

            <div className="wizard-footer">
              <button
                type="button"
                onClick={handleCancel}
                className="button button-secondary"
              >
                Cancel
              </button>
              <button
                type="button"
                onClick={handleNext}
                className="button button-tertiary"
                disabled={!isStep1Valid}
              >
                Next
              </button>
            </div>
          </div>
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
                  <h3 className="font-medium">Admin Inventory Path</h3>
                  <p className="text-gray-700">{adminInventoryPath}</p>
                </div>
                <div>
                  <h3 className="font-medium">Admin Inventory Rows</h3>
                  <p className="text-gray-700">{parsedData.length} row(s)</p>
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
                    <li>admin_inventory.csv</li>
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
                  Magellan discovery configuration files have been generated successfully.
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
