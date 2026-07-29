import { UseFieldArrayReturn, UseFormRegister } from 'react-hook-form';
import Button from '../../../components/Button';
import type { FormFieldError } from '../../configuration-wizard/hooks/useFormErrors';

interface LocalRepoOsRepoTabProps {
  osType: 'rhel' | 'ubuntu';
  enabled: boolean;
  osX86Fields: Array<{ id: string }>;
  osAarch64Fields: Array<{ id: string }>;
  register: UseFormRegister<any>;
  getError: (path: string) => FormFieldError | undefined;
  appendOsX86: UseFieldArrayReturn['append'];
  removeOsX86: UseFieldArrayReturn['remove'];
  appendOsAarch64: UseFieldArrayReturn['append'];
  removeOsAarch64: UseFieldArrayReturn['remove'];
  onToggle: (enabled: boolean) => void;
  onClear: () => void;
}

export const LocalRepoOsRepoTab = ({
  osType,
  enabled,
  osX86Fields,
  osAarch64Fields,
  register,
  getError,
  appendOsX86,
  removeOsX86,
  appendOsAarch64,
  removeOsAarch64,
  onToggle,
  onClear,
}: LocalRepoOsRepoTabProps) => {
  const prefixX86 = `${osType}_os_url_x86_64`;
  const prefixAarch64 = `${osType}_os_url_aarch64`;
  const label = `${osType.toUpperCase()} OS`;
  const renderRepoFields = (prefix: string, fieldId: string, index: number, remove: (idx: number) => void, fieldCount: number, disabled = false) => {
    const urlError = getError(`${prefix}.${index}.url`);
    const gpgkeyError = getError(`${prefix}.${index}.gpgkey`);
    const nameError = getError(`${prefix}.${index}.name`);

    return (
    <div key={fieldId} className="space-y-2 section-style">
      <div className="form-group">
        <label className="form-label">Repository URL (Required)</label>
        <input
          type="text"
          className={`form-input ${urlError ? 'error' : ''}`}
          placeholder="Repository URL"
          disabled={!enabled || disabled}
          {...register(`${prefix}.${index}.url` as any)}
        />
        {urlError && <span className="error-message">{urlError.message}</span>}
      </div>
      <div className="form-group">
        <label className="form-label">GPG Key URL (Optional)</label>
        <input
          type="text"
          className={`form-input ${gpgkeyError ? 'error' : ''}`}
          placeholder="GPG key URL"
          disabled={!enabled || disabled}
          {...register(`${prefix}.${index}.gpgkey` as any)}
        />
        {gpgkeyError && <span className="error-message">{gpgkeyError.message}</span>}
      </div>
      <div className="form-row">
        <div className="form-group">
          <label className="form-label">Repository Name (Required)</label>
          <input
            type="text"
            className={`form-input ${nameError ? 'error' : ''}`}
            placeholder="Repository name"
            disabled={!enabled || disabled}
            {...register(`${prefix}.${index}.name` as any)}
          />
          {nameError && <span className="error-message">{nameError.message}</span>}
        </div>
        <div className="form-group">
          <label className="form-label">Policy (Optional)</label>
          <select className="form-select" disabled={!enabled || disabled} {...register(`${prefix}.${index}.policy` as any)}>
            <option value="">Select policy</option>
            <option value="always">Always</option>
            <option value="partial">Partial</option>
          </select>
        </div>
        <div className="form-group">
          <label className="form-label">Caching (Optional - default: true)</label>
          <select className="form-select" disabled={!enabled || disabled} {...register(`${prefix}.${index}.caching` as any)}>
            <option value="">Select caching</option>
            <option value="true">True</option>
            <option value="false">False</option>
          </select>
        </div>
      </div>
      {!disabled && fieldCount > 1 && (
        <Button variant="secondary" onClick={() => remove(index)} disabled={!enabled}>
          Remove Repository
        </Button>
      )}
    </div>
    );
  };

  return (
    <>
      <div className="form-group">
        <label className="form-label">{label} Repository URLs (Optional)</label>
        <div className="form-checkbox">
          <input
            type="checkbox"
            id={`enable-${osType}-repos`}
            checked={enabled}
            onChange={(e) => {
              onToggle(e.target.checked);
              if (!e.target.checked) {
                onClear();
              }
            }}
          />
          <label htmlFor={`enable-${osType}-repos`}>Enable {label} Repository URLs Configuration</label>
        </div>
      </div>

      <div className={!enabled ? 'disabled-section' : ''}>
        <div className="space-y-2 section-style">
          <h3>{label} Repositories x86_64</h3>
          {osX86Fields.map((field, index) => renderRepoFields(prefixX86, field.id, index, removeOsX86, osX86Fields.length))}
          <Button variant="primary" onClick={() => appendOsX86({ url: '', name: '' })} disabled={!enabled}>
            Add {label} x86_64 Repository
          </Button>

          <h3>{label} Repositories aarch64</h3>
          {osAarch64Fields.map((field, index) => renderRepoFields(prefixAarch64, field.id, index, removeOsAarch64, osAarch64Fields.length))}
          <Button variant="primary" onClick={() => appendOsAarch64({ url: '', name: '' })} disabled={!enabled}>
            Add {label} aarch64 Repository
          </Button>
        </div>
      </div>
    </>
  );
};
