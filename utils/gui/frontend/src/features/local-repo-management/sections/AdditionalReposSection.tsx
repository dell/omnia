import { UseFieldArrayReturn, UseFormRegister } from 'react-hook-form';
import Button from '../../../components/Button';
import type { FormFieldError } from '../../configuration-wizard/hooks/useFormErrors';

interface AdditionalReposSectionProps {
  enabled: boolean;
  x86Fields: Array<{ id: string }>;
  aarch64Fields: Array<{ id: string }>;
  register: UseFormRegister<any>;
  getError: (path: string) => FormFieldError | undefined;
  appendX86: UseFieldArrayReturn['append'];
  removeX86: UseFieldArrayReturn['remove'];
  appendAarch64: UseFieldArrayReturn['append'];
  removeAarch64: UseFieldArrayReturn['remove'];
  onToggle: (enabled: boolean) => void;
}

export const AdditionalReposSection = ({
  enabled,
  x86Fields,
  aarch64Fields,
  register,
  getError,
  appendX86,
  removeX86,
  appendAarch64,
  removeAarch64,
  onToggle,
}: AdditionalReposSectionProps) => {
  const renderRepoFields = (prefix: string, fieldId: string, index: number, remove: (idx: number) => void, fieldCount: number, disabled: boolean = false) => {
    const urlError = getError(`${prefix}.${index}.url`);
    const gpgkeyError = getError(`${prefix}.${index}.gpgkey`);
    const nameError = getError(`${prefix}.${index}.name`);
    const policyError = getError(`${prefix}.${index}.policy`);
    const cachingError = getError(`${prefix}.${index}.caching`);

    return (
      <div key={fieldId} className="space-y-2 section-style">
        <div className="form-group">
          <label className="form-label">Repository URL (Required)</label>
          <input
            type="text"
            className={`form-input ${urlError ? 'error' : ''}`}
            placeholder="Repository URL"
            disabled={!enabled || disabled}
            {...register(`${prefix}.${index}.url`)}
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
            {...register(`${prefix}.${index}.gpgkey`)}
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
              {...register(`${prefix}.${index}.name`)}
            />
            {nameError && <span className="error-message">{nameError.message}</span>}
          </div>
          <div className="form-group">
            <label className="form-label">Policy (Optional)</label>
            <select className={`form-select ${policyError ? 'error' : ''}`} disabled={!enabled || disabled} {...register(`${prefix}.${index}.policy`)}>
              <option value="">Select policy</option>
              <option value="always">Always</option>
              <option value="partial">Partial</option>
            </select>
            {policyError && <span className="error-message">{policyError.message}</span>}
          </div>
          <div className="form-group">
            <label className="form-label">Caching (Optional - default: true)</label>
            <select className={`form-select ${cachingError ? 'error' : ''}`} disabled={!enabled || disabled} {...register(`${prefix}.${index}.caching`)}>
              <option value="">Select caching</option>
              <option value="true">True</option>
              <option value="false">False</option>
            </select>
            {cachingError && <span className="error-message">{cachingError.message}</span>}
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
        <label className="form-label">Additional Repositories (Optional)</label>
        <div className="form-checkbox">
          <input
            type="checkbox"
            id="enable-additional-repos"
            checked={enabled}
            onChange={(e) => onToggle(e.target.checked)}
          />
          <label htmlFor="enable-additional-repos">Enable Additional Repositories Configuration</label>
        </div>
      </div>

      <div className={!enabled ? 'disabled-section' : ''}>
        <div className="space-y-2 section-style">
          <h3>Additional Repositories x86_64</h3>
          {x86Fields.map((field, index) => renderRepoFields('additional_repos_x86_64', field.id, index, removeX86, x86Fields.length))}
          <Button variant="primary" onClick={() => appendX86({ url: '', name: '', gpgkey: '' })} disabled={!enabled}>
            Add Additional x86_64 Repository
          </Button>

          <h3>Additional Repositories aarch64</h3>
          {aarch64Fields.map((field, index) => renderRepoFields('additional_repos_aarch64', field.id, index, removeAarch64, aarch64Fields.length))}
          <Button variant="primary" onClick={() => appendAarch64({ url: '', name: '', gpgkey: '' })} disabled={!enabled}>
            Add Additional aarch64 Repository
          </Button>
        </div>
      </div>
    </>
  );
};
