import { UseFieldArrayReturn, UseFormRegister } from 'react-hook-form';
import Button from '../../../components/Button';
import type { FormFieldError } from '../../configuration-wizard/hooks/useFormErrors';

interface UserRegistrySectionProps {
  enabled: boolean;
  fields: Array<{ id: string }>;
  register: UseFormRegister<any>;
  getError: (path: string) => FormFieldError | undefined;
  append: UseFieldArrayReturn['append'];
  remove: UseFieldArrayReturn['remove'];
  onToggle: (enabled: boolean) => void;
  onClear: () => void;
}

export const UserRegistrySection = ({
  enabled,
  fields,
  register,
  getError,
  append,
  remove,
  onToggle,
  onClear,
}: UserRegistrySectionProps) => {

  return (
    <>
      <div className="form-group">
        <label className="form-label">User Registry (Optional)</label>
        <div className="form-checkbox">
          <input
            type="checkbox"
            id="enable-user-registry"
            checked={enabled}
            onChange={(e) => {
              onToggle(e.target.checked);
              if (!e.target.checked) {
                onClear();
              }
            }}
          />
          <label htmlFor="enable-user-registry">Enable User Registry Configuration</label>
        </div>
      </div>

      <div className={!enabled ? 'disabled-section' : ''}>
        <div className="space-y-2 padding-sm">
          {fields.map((field, index) => {
            const hostError = getError(`user_registry.${index}.host`);
            const certPathError = getError(`user_registry.${index}.cert_path`);
            const keyPathError = getError(`user_registry.${index}.key_path`);

            return (
              <div key={field.id} className="space-y-2 section-style">
                <div className="form-group">
                  <label className="form-label">User Registry Host (Required)</label>
                  <input
                    type="text"
                    className={`form-input ${hostError ? 'error' : ''}`}
                    placeholder="e.g., 172.16.107.254:5000"
                    disabled={!enabled}
                    {...register(`user_registry.${index}.host`)}
                  />
                  {hostError && <span className="error-message">{hostError.message}</span>}
                </div>
                <div className="form-group">
                  <label className="form-label">Certificate File Path (Optional - Required if host uses HTTPS)</label>
                  <input
                    type="text"
                    className={`form-input ${certPathError ? 'error' : ''}`}
                    placeholder="e.g., /path/to/certificate.crt"
                    disabled={!enabled}
                    {...register(`user_registry.${index}.cert_path`)}
                  />
                  {certPathError && <span className="error-message">{certPathError.message}</span>}
                </div>
                <div className="form-group">
                  <label className="form-label">Key File Path (Optional - Required if host uses HTTPS)</label>
                  <input
                    type="text"
                    className={`form-input ${keyPathError ? 'error' : ''}`}
                    placeholder="e.g., /path/to/private.key"
                    disabled={!enabled}
                    {...register(`user_registry.${index}.key_path`)}
                  />
                  {keyPathError && <span className="error-message">{keyPathError.message}</span>}
                </div>
                {fields.length > 1 && (
                  <Button variant="secondary" onClick={() => remove(index)} disabled={!enabled}>
                    Remove Registry
                  </Button>
                )}
              </div>
            );
          })}
          <Button variant="primary" onClick={() => append({ host: '', cert_path: '', key_path: '' })} disabled={!enabled}>
            Add User Registry
          </Button>
        </div>
      </div>
    </>
  );
};
