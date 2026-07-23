import { useWatch, UseFormRegister, Control, FieldErrors, UseFormSetValue } from 'react-hook-form';
import { useEffect, useRef } from 'react';
import Button from '../../../../components/Button';
import { OmniaHaDiscoveryFormData } from '../../schemas/omniaHaDiscoveryConfig';
import { useFormErrors } from '../../hooks/useFormErrors';
import { NodeHardwareDefaultsBuilder } from './NodeHardwareDefaultsBuilder';
import { ConfigSourcesEditor } from './ConfigSourcesEditor';
import type { ValidationError } from '../../utils/l2Validation';

interface SlurmClusterRowProps {
  index: number;
  register: UseFormRegister<OmniaHaDiscoveryFormData>;
  control: Control<OmniaHaDiscoveryFormData>;
  errors: FieldErrors<OmniaHaDiscoveryFormData>;
  setValue: UseFormSetValue<OmniaHaDiscoveryFormData>;
  remove: () => void;
  canRemove: boolean;
  validationErrors?: ValidationError[];
}

export const SlurmClusterRow = ({ index, register, control, errors, setValue, remove, canRemove, validationErrors }: SlurmClusterRowProps) => {
  const getError = useFormErrors(errors, validationErrors);

  // Render helper to reduce repetitive error boilerplate (not a component to avoid remounting)
  const renderField = (path: string, label: string, placeholder?: string, type = 'text', className?: string) => {
    const error = getError(path);
    return (
      <div className={`form-group ${className || ''}`}>
        <label className="form-label">{label}</label>
        <input
          type={type}
          className={`form-input ${error ? 'error' : ''}`}
          placeholder={placeholder}
          {...register(path as any)}
        />
        {error && <span className="error-message">{error.message}</span>}
      </div>
    );
  };

  // Watch only this cluster's node_discovery_mode
  const nodeDiscoveryMode = useWatch({
    control,
    name: `slurm_cluster.${index}.node_discovery_mode`,
  });

  const isHomogeneous = nodeDiscoveryMode === 'homogeneous';
  const wasPreviouslyHomogeneous = useRef(isHomogeneous);

  // Clear node_hardware_defaults when mode changes from homogeneous to heterogeneous
  useEffect(() => {
    if (wasPreviouslyHomogeneous.current && !isHomogeneous) {
      setValue(`slurm_cluster.${index}.node_hardware_defaults`, []);
    }
    wasPreviouslyHomogeneous.current = isHomogeneous;
  }, [isHomogeneous, index, setValue]);

  return (
    <div className="space-y-2 section-style">
      <div className="form-row form-row-2-col">
        {renderField(`slurm_cluster.${index}.cluster_name`, 'Slurm Cluster Name (Required)', 'e.g., slurm_cluster')}
        {renderField(`slurm_cluster.${index}.nfs_storage_name`, 'NFS Storage Name (Required)', 'Storage name from storage_config.yml')}
      </div>
      <div className="form-row form-row-2-col">
        {renderField(`slurm_cluster.${index}.vast_storage_name`, 'VAST Storage Name (Required)', 'VAST storage name from storage_config.yml')}
        <div className="form-group">
          <label className="form-label">Node Discovery Mode (Optional)</label>
          <select
            className="form-select"
            {...register(`slurm_cluster.${index}.node_discovery_mode`)}
          >
            <option value="">Select node discovery mode</option>
            <option value="heterogeneous">heterogeneous</option>
            <option value="homogeneous">homogeneous</option>
          </select>
        </div>
      </div>
      <div className={`form-group ${!isHomogeneous ? 'disabled-section' : ''}`}>
        <label className="form-label">Node Hardware Defaults (Optional - only used when node_discovery_mode is homogeneous)</label>
        <p className="text-sm text-gray-600 mt-1">Pre-define hardware specifications for homogeneous node groups. If a group is not listed, one node will be discovered via iDRAC and specs applied to all nodes in the group.</p>
        <NodeHardwareDefaultsBuilder
          clusterIndex={index}
          register={register}
          control={control}
          errors={errors}
          validationErrors={validationErrors}
          disabled={!isHomogeneous}
        />
      </div>
      <div className="form-group">
        <ConfigSourcesEditor
          clusterIndex={index}
          register={register}
          control={control}
          errors={errors}
          validationErrors={validationErrors}
        />
      </div>
      <div className="form-group">
        <div className="form-checkbox">
          <input
            id={`slurm_cluster.${index}.skip_merge`}
            type="checkbox"
            {...register(`slurm_cluster.${index}.skip_merge`)}
          />
          <label htmlFor={`slurm_cluster.${index}.skip_merge`}>Skip Merge Configuration Files (Optional)</label>
        </div>
      </div>
      {canRemove && (
        <Button variant="secondary" onClick={remove}>Remove Cluster</Button>
      )}
    </div>
  );
};
