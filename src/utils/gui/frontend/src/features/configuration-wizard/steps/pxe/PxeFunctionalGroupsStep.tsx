import { useState, useEffect, useRef } from 'react';
import { useForm } from 'react-hook-form';
import { zodResolver } from '@hookform/resolvers/zod';
import { pxeFunctionalGroupsSchema, PxeFunctionalGroupsFormData } from '../../schemas';
import { useConfigStore } from '../../configStore';
import { clearL2ErrorsForStep } from '../../utils/l2Validation';
import { parsePxeMappingFile, type PxeMappingRow, ALL_COLUMNS } from '../../utils/csvParser';
import { useFormErrors } from '../../hooks/useFormErrors';

// Functional groups filtered by cluster type
const FUNCTIONAL_GROUPS_BY_CLUSTER_TYPE: Record<string, string[]> = {
  slurm: [
    'slurm_control_node_x86_64',
    'slurm_node_x86_64',
    'slurm_node_aarch64',
    'login_node_x86_64',
    'login_node_aarch64',
    'login_compiler_node_x86_64',
    'login_compiler_node_aarch64',
    'os_x86_64',
    'os_aarch64',
  ],
  k8s: [
    'service_kube_control_plane_first_x86_64',
    'service_kube_control_plane_x86_64',
    'service_kube_node_x86_64',
    'os_x86_64',
    'os_aarch64',
  ],
  both: [
    'slurm_control_node_x86_64',
    'slurm_node_x86_64',
    'slurm_node_aarch64',
    'service_kube_control_plane_first_x86_64',
    'service_kube_control_plane_x86_64',
    'service_kube_node_x86_64',
    'login_node_x86_64',
    'login_node_aarch64',
    'login_compiler_node_x86_64',
    'login_compiler_node_aarch64',
    'os_x86_64',
    'os_aarch64',
  ],
};

export const PxeFunctionalGroupsStep = () => {
  const updateWizardField = useConfigStore((s) => s.updateWizardField);
  const updateWizardFields = useConfigStore((s) => s.updateWizardFields);
  const wizardData = useConfigStore((s) => s.wizardData);
  const clusterType = useConfigStore((s) => s.clusterType);
  const setStepValid = useConfigStore((s) => s.setStepValid);
  const validationErrors = useConfigStore((s) => s.validationErrors);
  const [parseError, setParseError] = useState<string | null>(null);
  const [editingRow, setEditingRow] = useState<number | null>(null);
  const [editFormData, setEditFormData] = useState<PxeMappingRow | null>(null);
  const fileInputRef = useRef<HTMLInputElement>(null);

  // Read directly from store as single source of truth
  const parsedData = Array.isArray(wizardData.pxe_mapping_data) ? wizardData.pxe_mapping_data as PxeMappingRow[] : [];

  // Get filtered functional groups based on cluster type
  const getFilteredFunctionalGroups = (): string[] => {
    if (!clusterType) return FUNCTIONAL_GROUPS_BY_CLUSTER_TYPE.both;
    return FUNCTIONAL_GROUPS_BY_CLUSTER_TYPE[clusterType] || FUNCTIONAL_GROUPS_BY_CLUSTER_TYPE.both;
  };

  const {
    register,
    formState: { errors },
    watch,
  } = useForm<PxeFunctionalGroupsFormData>({
    // zodResolver type inference conflicts with .default() and .refine() on optional fields.
    // Runtime validation is fully enforced by the schema.
    resolver: zodResolver(pxeFunctionalGroupsSchema) as any,
    defaultValues: {
      pxe_mapping_file_path: (wizardData.pxe_mapping_file_path as string) || '/opt/omnia/input/project_default/pxe_mapping_file.csv',
      language: (wizardData.language as 'en_US.UTF-8' | undefined) || 'en_US.UTF-8',
      default_lease_time: (wizardData.default_lease_time as string | undefined) || '86400',
      dns_enabled: (wizardData.dns_enabled as boolean) || false,
      kernel_version_override: (wizardData.kernel_version_override as string | undefined) || '',
      additional_cloud_init_config_file: (wizardData.additional_cloud_init_config_file as string | undefined) || '',
    },
    mode: 'onTouched',
  });

  const getError = useFormErrors(errors, validationErrors);
  const pxeMappingFilePathError = getError('pxe_mapping_file_path');
  const defaultLeaseTimeError = getError('default_lease_time');
  const kernelVersionError = getError('kernel_version_override');
  const cloudInitConfigFileError = getError('additional_cloud_init_config_file');

  // Validate step and sync form changes to store (debounced to avoid excessive updates)
  useEffect(() => {
    // Validate immediately on mount
    const currentValues = watch();
    // Include pxe_mapping_data from store since it's managed outside the form
    const validationData = {
      ...currentValues,
      pxe_mapping_data: parsedData,
    };
    const initialResult = pxeFunctionalGroupsSchema.safeParse(validationData);
    setStepValid(2, initialResult.success);
    clearL2ErrorsForStep(initialResult, 'PXE Functional Groups', useConfigStore.getState);

    // Set language directly in store on mount and ensure it's always correct
    if (!wizardData.language || wizardData.language === '') {
      updateWizardField('language', 'en_US.UTF-8');
    }

    let timer: ReturnType<typeof setTimeout>;
    const subscription = watch((formValues) => {
      const result = pxeFunctionalGroupsSchema.safeParse({
        ...formValues,
        pxe_mapping_data: parsedData,
      });
      setStepValid(2, result.success);
      clearL2ErrorsForStep(result, 'PXE Functional Groups', useConfigStore.getState);

      clearTimeout(timer);
      timer = setTimeout(() => {
        updateWizardFields({
          pxe_mapping_file_path: formValues.pxe_mapping_file_path,
          language: 'en_US.UTF-8', // Always force this value
          default_lease_time: formValues.default_lease_time,
          dns_enabled: formValues.dns_enabled,
          kernel_version_override: formValues.kernel_version_override,
          additional_cloud_init_config_file: formValues.additional_cloud_init_config_file,
        });
      }, 300);
    });

    return () => {
      clearTimeout(timer);
      subscription.unsubscribe();
    };
  }, [watch, setStepValid, updateWizardFields, updateWizardField, wizardData.language, parsedData]);

  const handleFileUpload = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;

    try {
      const data = await parsePxeMappingFile(file);
      setParseError(null);
      updateWizardField('pxe_mapping_data', data);
    } catch (error) {
      setParseError(error instanceof Error ? error.message : 'Failed to parse CSV file');
    }
  };

  const handleAddRow = () => {
    const newRow: PxeMappingRow = {
      FUNCTIONAL_GROUP_NAME: '',
      GROUP_NAME: '',
      SERVICE_TAG: '',
      PARENT_SERVICE_TAG: '',
      HOSTNAME: '',
      ADMIN_MAC: '',
      ADMIN_IP: '',
      BMC_MAC: '',
      BMC_IP: '',
      IB_NIC_NAME: '',
      IB_IP: '',
    };
    updateWizardField('pxe_mapping_data', [...parsedData, newRow]);
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
      updateWizardField('pxe_mapping_data', updatedData);
      setEditingRow(null);
      setEditFormData(null);
    }
  };

  const handleCancelEdit = () => {
    setEditingRow(null);
    setEditFormData(null);
  };

  const handleDeleteRow = (index: number) => {
    updateWizardField('pxe_mapping_data', parsedData.filter((_, i) => i !== index));
  };

  const handleEditFieldChange = (field: keyof PxeMappingRow, value: string) => {
    if (editFormData) {
      setEditFormData({ ...editFormData, [field]: value });
    }
  };

  return (
    <div className="space-y-6 overflow-hidden width-full box-border">
      <div className="form-group">
        <label className="form-label">PXE Mapping File (Required)</label>
        <input
          type="file"
          accept=".csv"
          className="form-input"
          required
          onChange={handleFileUpload}
          ref={fileInputRef}
        />
        {parseError && (
          <div className="error-message mt-2">{parseError}</div>
        )}
        {parsedData.length === 0 && !parseError && (
          <div className="mt-3">
            <p className={`${getError('pxe_mapping_data') ? 'error-message' : 'text-muted'}`}>
              {getError('pxe_mapping_data')?.message || 'No PXE mapping data loaded. Upload a CSV file or create a new mapping.'}
            </p>
            <button
              type="button"
              onClick={handleAddRow}
              className="button button-secondary mt-2"
            >
              Create New Mapping
            </button>
          </div>
        )}
      </div>

      <div className="form-group">
        <label className="form-label">PXE Mapping File Path (Required)</label>
        <input
          type="text"
          className={`form-input ${pxeMappingFilePathError ? 'error' : ''}`}
          placeholder="/opt/omnia/input/project_default/pxe_mapping_file.csv"
          {...register('pxe_mapping_file_path')}
        />
        <p className="text-sm text-gray-600 mt-1">
          Default: /opt/omnia/input/project_default/pxe_mapping_file.csv
        </p>
        {pxeMappingFilePathError && <span className="error-message">{pxeMappingFilePathError.message}</span>}
      </div>

      {parsedData.length > 0 && (
        <div className="pxe-mapping-container">
          <div className="pxe-mapping-header">
            <h3>PXE Mapping Data ({parsedData.length} rows)</h3>
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
                  {ALL_COLUMNS.map((col) => (
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
                        {ALL_COLUMNS.map((col) => (
                          <td key={col}>
                            {col === 'FUNCTIONAL_GROUP_NAME' ? (
                              <>
                                <input
                                  type="text"
                                  list="fg-name-options"
                                  value={editFormData?.[col] || ''}
                                  onChange={(e) => handleEditFieldChange(col, e.target.value)}
                                  className="pxe-mapping-input"
                                  placeholder="Select or type functional group..."
                                />
                                <datalist id="fg-name-options">
                                  {getFilteredFunctionalGroups().map((group) => (
                                    <option key={group} value={group} />
                                  ))}
                                </datalist>
                              </>
                            ) : (
                              <input
                                type="text"
                                value={editFormData?.[col] || ''}
                                onChange={(e) => handleEditFieldChange(col, e.target.value)}
                                className="pxe-mapping-input"
                              />
                            )}
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
                        {ALL_COLUMNS.map((col) => (
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

      <div className="form-row" style={{ gridTemplateColumns: '1fr 1.5fr 2fr' }}>
        <div className="form-group">
          <label className="form-label">System Language (Required)</label>
          <input
            type="text"
            className="form-input"
            value="en_US.UTF-8"
            disabled
            style={{ cursor: 'not-allowed'}}
          />
          <input type="hidden" {...register('language')} />
          <p className="text-sm text-gray-600 mt-1">
            Only en_US.UTF-8 is supported
          </p>
        </div>

        <div className="form-group">
          <label className="form-label">DHCP Default Lease Time (Seconds)</label>
          <input
            type="number"
            className={`form-input ${defaultLeaseTimeError ? 'error' : ''}`}
            required
            placeholder="86400"
            min="21600"
            max="31536000"
            {...register('default_lease_time')}
          />
          <p className="text-sm text-gray-600 mt-1">
            Default: 86400
          </p>
          {defaultLeaseTimeError && <span className="error-message">{defaultLeaseTimeError.message}</span>}
        </div>

        <div className="form-group">
          <label className="form-label">Kernel Version Override</label>
          <input
            type="text"
            className={`form-input ${kernelVersionError ? 'error' : ''}`}
            placeholder="e.g., 6.12.0-55.76.1.el10_0"
            {...register('kernel_version_override')}
          />
          <p className="text-sm text-gray-600 mt-1">
            Optional - auto-select latest if empty
          </p>
          {kernelVersionError && <span className="error-message">{kernelVersionError.message}</span>}
        </div>
      </div>

      <div className="form-group">
        <div className="form-checkbox">
          <input
            type="checkbox"
            id="dns-enabled"
            {...register('dns_enabled')}
          />
          <label htmlFor="dns-enabled">Enable DNS-based hostname resolution (Optional)</label>
        </div>
      </div>

      <div className="form-group">
        <label className="form-label">Additional Cloud-Init Config File (Optional)</label>
        <input 
          type="text" 
          className={`form-input ${cloudInitConfigFileError ? 'error' : ''}`}
          placeholder="e.g., /path/to/additional_cloud_init.yml"
          {...register('additional_cloud_init_config_file')}
        />
        <p className="text-sm text-gray-600 mt-1">
          Path to additional cloud-init configuration file for stateless node provisioning
        </p>
        {cloudInitConfigFileError && <span className="error-message">{cloudInitConfigFileError.message}</span>}
      </div>
    </div>
  );
};
