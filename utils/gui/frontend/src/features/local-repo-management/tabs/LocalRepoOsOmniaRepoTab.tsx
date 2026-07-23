import { UseFieldArrayReturn, UseFormRegister } from 'react-hook-form';
import Button from '../../../components/Button';
import type { FormFieldError } from '../../configuration-wizard/hooks/useFormErrors';

interface LocalRepoOsOmniaRepoTabProps {
  osType: 'rhel' | 'ubuntu';
  omniaRepoX86Fields: Array<{ id: string }>;
  omniaRepoAarch64Fields: Array<{ id: string }>;
  register: UseFormRegister<any>;
  getError: (path: string) => FormFieldError | undefined;
  appendOmniaRepoX86: UseFieldArrayReturn['append'];
  removeOmniaRepoX86: UseFieldArrayReturn['remove'];
  appendOmniaRepoAarch64: UseFieldArrayReturn['append'];
  removeOmniaRepoAarch64: UseFieldArrayReturn['remove'];
}

export const LocalRepoOsOmniaRepoTab = ({
  osType,
  omniaRepoX86Fields,
  omniaRepoAarch64Fields,
  register,
  getError,
  appendOmniaRepoX86,
  removeOmniaRepoX86,
  appendOmniaRepoAarch64,
  removeOmniaRepoAarch64,
}: LocalRepoOsOmniaRepoTabProps) => {
  const prefixX86 = `omnia_repo_url_${osType}_x86_64`;
  const prefixAarch64 = `omnia_repo_url_${osType}_aarch64`;
  const label = osType.toUpperCase();

  const renderRepoFields = (prefix: string, fieldId: string, index: number, remove: (idx: number) => void, fieldCount: number) => {
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
              {...register(`${prefix}.${index}.name` as any)}
            />
            {nameError && <span className="error-message">{nameError.message}</span>}
          </div>
          <div className="form-group">
            <label className="form-label">Policy (Optional)</label>
            <select className="form-select" {...register(`${prefix}.${index}.policy` as any)}>
              <option value="">Select policy</option>
              <option value="always">Always</option>
              <option value="partial">Partial</option>
            </select>
          </div>
          <div className="form-group">
            <label className="form-label">Caching (Optional - default: true)</label>
            <select className="form-select" {...register(`${prefix}.${index}.caching` as any)}>
              <option value="">Select caching</option>
              <option value="true">True</option>
              <option value="false">False</option>
            </select>
          </div>
        </div>
        {fieldCount > 1 && (
          <Button variant="secondary" onClick={() => remove(index)}>
            Remove Repository
          </Button>
        )}
      </div>
    );
  };

  return (
    <>
      <div className="form-group">
        <label className="form-label">Omnia Repository URLs (Mandatory for Omnia Features)</label>
        <p className="text-sm text-gray-600 text-small-muted margin-bottom-sm">
          These are mandatory repositories for Omnia features. Making incorrect changes can cause Omnia failure. Please edit cautiously.
        </p>
      </div>

      <div className="space-y-2 section-style">
        <h3>Omnia Repo URLs {label} x86_64</h3>
        {omniaRepoX86Fields.map((field, index) => renderRepoFields(prefixX86, field.id, index, removeOmniaRepoX86, omniaRepoX86Fields.length))}
        {omniaRepoX86Fields.length === 0 && (
          <p className="text-muted padding-sm italic">
            No x86_64 repositories configured. Click below to add one.
          </p>
        )}
        <Button variant="primary" onClick={() => appendOmniaRepoX86({ url: '', name: '' })}>
          Add Omnia Repo {label} x86_64 Repository
        </Button>

        <h3>Omnia Repo URLs {label} aarch64</h3>
        {omniaRepoAarch64Fields.map((field, index) => renderRepoFields(prefixAarch64, field.id, index, removeOmniaRepoAarch64, omniaRepoAarch64Fields.length))}
        {omniaRepoAarch64Fields.length === 0 && (
          <p className="text-muted padding-sm italic">
            No aarch64 repositories configured. Click below to add one.
          </p>
        )}
        <Button variant="primary" onClick={() => appendOmniaRepoAarch64({ url: '', name: '' })}>
          Add Omnia Repo {label} aarch64 Repository
        </Button>
      </div>
    </>
  );
};
