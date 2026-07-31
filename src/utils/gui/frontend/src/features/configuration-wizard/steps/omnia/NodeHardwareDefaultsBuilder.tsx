// Copyright 2026 Dell Inc. or its subsidiaries. All Rights Reserved.
//
// Licensed under the Apache License, Version 2.0 (the "License");
// you may not use this file except in compliance with the License.
// You may obtain a copy of the License at
//
//     http://www.apache.org/licenses/LICENSE-2.0
//
// Unless required by applicable law or agreed to in writing, software
// distributed under the License is distributed on an "AS IS" BASIS,
// WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
// See the License for the specific language governing permissions and
// limitations under the License.
import { useFieldArray, UseFormRegister, Control, FieldErrors } from 'react-hook-form';
import Button from '../../../../components/Button';
import { OmniaHaDiscoveryFormData } from '../../schemas/omniaHaDiscoveryConfig';
import { useFormErrors } from '../../hooks/useFormErrors';
import type { ValidationError } from '../../utils/l2Validation';

interface NodeHardwareDefaultsBuilderProps {
  clusterIndex: number;
  register: UseFormRegister<OmniaHaDiscoveryFormData>;
  control: Control<OmniaHaDiscoveryFormData>;
  errors: FieldErrors<OmniaHaDiscoveryFormData>;
  disabled?: boolean;
  validationErrors?: ValidationError[];
}

export const NodeHardwareDefaultsBuilder = ({ clusterIndex, register, control, errors, disabled = false, validationErrors }: NodeHardwareDefaultsBuilderProps) => {
  const { fields, append, remove } = useFieldArray({
    control,
    name: `slurm_cluster.${clusterIndex}.node_hardware_defaults`,
  });

  const getError = useFormErrors(errors, validationErrors);

  // Render helper to reduce repetitive error boilerplate
  const renderField = (
    path: string,
    label: string,
    placeholder?: string,
    type = 'text',
  ) => {
    const error = getError(path);
    return (
      <div className="form-group">
        <label className="form-label" style={{ whiteSpace: 'pre-wrap' }}>{label}</label>
        <input
          type={type}
          className={`form-input ${error ? 'error' : ''}`}
          placeholder={placeholder}
          min={type === 'number' ? '1' : undefined}
          disabled={disabled}
          {...register(path as any)}
        />
        {error && <span className="error-message">{error.message}</span>}
      </div>
    );
  };

  const addGroup = () => {
    append({
      group_name: '',
      sockets: 1,
      cores_per_socket: 1,
      threads_per_core: 1,
      real_memory: 1,
      gres: '',
    });
  };

  return (
    <div className="space-y-2">
      {fields.length === 0 && (
        <p className="text-small-muted padding-sm italic">
          No hardware default groups configured. Click below to add one.
        </p>
      )}
      {fields.map((field, index) => {
        const base = `slurm_cluster.${clusterIndex}.node_hardware_defaults.${index}`;
        return (
          <div key={field.id} className="space-y-2 section-style">
            <div className="form-row form-row-6-col">
              {renderField(`${base}.group_name`, 'Group Name (Required)', 'e.g., grp0')}
              {renderField(`${base}.sockets`, 'Sockets\n(Required)', 'e.g., 2', 'number')}
              {renderField(`${base}.cores_per_socket`, 'Cores per Socket\n(Required)', 'e.g., 64', 'number')}
              {renderField(`${base}.threads_per_core`, 'Threads per Core\n(Required)', 'e.g., 2', 'number')}
              {renderField(`${base}.real_memory`, 'Real Memory (MB)\n(Required)', 'e.g., 512000', 'number')}
              {renderField(`${base}.gres`, 'GPU Resources (Optional)', 'e.g., gpu:4')}
            </div>
            <Button variant="secondary" onClick={() => remove(index)} disabled={disabled}>Remove Group</Button>
          </div>
        );
      })}
      <Button variant="primary" onClick={addGroup} disabled={disabled}>Add Hardware Defaults Group</Button>
    </div>
  );
};
