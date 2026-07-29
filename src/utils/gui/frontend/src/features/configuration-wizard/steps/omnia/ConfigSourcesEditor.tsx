import { useState } from 'react';
import { useFieldArray, UseFormRegister, Control, FieldErrors, useWatch } from 'react-hook-form';
import { SlurmConfigFileName, SLURM_CONFIG_FILE_NAMES } from '../../schemas/common';
import { OmniaHaDiscoveryFormData } from '../../schemas/omniaHaDiscoveryConfig';
import { useFormErrors } from '../../hooks/useFormErrors';
import type { ValidationError } from '../../utils/l2Validation';

type ConfigSourceField = {
  id: string;
  name: SlurmConfigFileName;
  mode: 'yaml' | 'filepath';
  yaml_content: string;
  file_path: string;
};

interface ConfigSourcesEditorProps {
  clusterIndex: number;
  register: UseFormRegister<OmniaHaDiscoveryFormData>;
  control: Control<OmniaHaDiscoveryFormData>;
  errors: FieldErrors<OmniaHaDiscoveryFormData>;
  validationErrors?: ValidationError[];
}

export const ConfigSourcesEditor = ({ clusterIndex, register, control, errors, validationErrors }: ConfigSourcesEditorProps) => {
  const { fields, append, remove } = useFieldArray({
    control,
    name: `slurm_cluster.${clusterIndex}.config_sources`,
  });

  const [selectedToAdd, setSelectedToAdd] = useState<SlurmConfigFileName | ''>('');

  // Watch only the fields that drive UI logic (name and mode)
  const configSourceMeta = useWatch({
    control,
    name: fields.map((_, i) =>
      `slurm_cluster.${clusterIndex}.config_sources.${i}` as const
    ),
  }) || [];

  // For available names, only need the name field
  const activeNames = configSourceMeta.map((entry: any) => entry?.name);
  const availableNames = SLURM_CONFIG_FILE_NAMES.filter(
    (name) => !activeNames.includes(name)
  );

  const getError = useFormErrors(errors, validationErrors);

  const handleAdd = () => {
    if (selectedToAdd) {
      append({
        name: selectedToAdd,
        mode: 'yaml',
        yaml_content: '',
        file_path: '',
      });
      setSelectedToAdd('');
    }
  };

  const getMode = (index: number) =>
    configSourceMeta[index]?.mode || 'yaml';

  const addConfigControl = availableNames.length > 0 ? (
    <div className="flex gap-2 items-center margin-top-sm">
      <select
        className="form-select"
        value={selectedToAdd}
        onChange={(e) => setSelectedToAdd(e.target.value as SlurmConfigFileName)}
        style={{ maxWidth: '250px' }}
      >
        <option value="">Select config file</option>
        {availableNames.map((name) => (
          <option key={name} value={name}>{name}.conf</option>
        ))}
      </select>
      <button
        type="button"
        className="button button-secondary"
        onClick={handleAdd}
        disabled={!selectedToAdd}
      >
        + Add Config Source
      </button>
    </div>
  ) : null;

  return (
    <div className="form-group">
      <label className="form-label">Config Sources (Optional)</label>
      <p className="text-sm text-gray-600 mt-1">
        Define how Slurm configuration files are provided to the cluster.
        {fields.length === 0 ? ' Select from the supported config files below.' : ' Each config file can be provided as YAML configuration or a file path.'}
      </p>

      {fields.length === 0 && (
        <p className="text-small-muted padding-sm italic">
          No config sources configured.
        </p>
      )}

      {(fields as ConfigSourceField[]).map((field, index) => {
        const entryPath = `slurm_cluster.${clusterIndex}.config_sources.${index}`;
        const mode = getMode(index);
        const yamlContentError = getError(`${entryPath}.yaml_content`);
        const filePathError = getError(`${entryPath}.file_path`);

        return (
          <div key={field.id} className="space-y-2 section-style margin-top-sm">
            <div className="flex justify-between items-center">
              <h4 className="subsection-title">{field.name}.conf</h4>
              <button
                type="button"
                className="button button-secondary button-small"
                onClick={() => remove(index)}
              >
                Remove
              </button>
            </div>

            {/* Mode toggle */}
            <div>
              <label className="form-checkbox inline-flex items-center margin-right-md">
                <input
                  type="radio"
                  value="yaml"
                  {...register(`${entryPath}.mode` as any)}
                />
                <span className="ml-2">YAML Configuration</span>
              </label>
              <label className="form-checkbox inline-flex items-center">
                <input
                  type="radio"
                  value="filepath"
                  {...register(`${entryPath}.mode` as any)}
                />
                <span className="ml-2">File Path</span>
              </label>
            </div>

            {/* Content based on mode */}
            {mode === 'yaml' ? (
              <div className="form-group">
                <textarea
                  className={`form-input ${yamlContentError ? 'error' : ''}`}
                  rows={6}
                  placeholder={`# ${field.name}.conf key-value configuration\nSlurmctldTimeout: 60\nSlurmdTimeout: 150`}
                  style={{ fontFamily: 'monospace', fontSize: '13px' }}
                  {...register(`${entryPath}.yaml_content` as any)}
                />
                {yamlContentError && <span className="error-message">{yamlContentError.message}</span>}
              </div>
            ) : (
              <div className="form-group">
                <input
                  type="text"
                  className={`form-input ${filePathError ? 'error' : ''}`}
                  placeholder={`/opt/omnia/input/project_default/${field.name}.conf`}
                  {...register(`${entryPath}.file_path` as any)}
                />
                {filePathError && <span className="error-message">{filePathError.message}</span>}
              </div>
            )}
          </div>
        );
      })}

      {addConfigControl}
    </div>
  );
};
