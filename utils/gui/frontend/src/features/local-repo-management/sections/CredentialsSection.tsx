import { UseFieldArrayReturn, UseFormRegister } from 'react-hook-form';
import Button from '../../../components/Button';
import type { FormFieldError } from '../../configuration-wizard/hooks/useFormErrors';

interface CredentialsSectionProps {
  enabled: boolean;
  fields: Array<{ id: string }>;
  register: UseFormRegister<any>;
  getError: (path: string) => FormFieldError | undefined;
  append: UseFieldArrayReturn['append'];
  remove: UseFieldArrayReturn['remove'];
  onToggle: (enabled: boolean) => void;
  onClear: () => void;
}

export const CredentialsSection = ({
  enabled,
  fields,
  register,
  getError,
  append,
  remove,
  onToggle,
  onClear,
}: CredentialsSectionProps) => {
  return (
    <>
      <div className="form-group">
        <label className="form-label">User Registry Credential (Optional)</label>
        <div className="form-checkbox">
          <input
            type="checkbox"
            id="enable-credentials"
            checked={enabled}
            onChange={(e) => {
              onToggle(e.target.checked);
              if (!e.target.checked) {
                onClear();
              }
            }}
          />
          <label htmlFor="enable-credentials">Enable user registry credentials</label>
        </div>
      </div>

      <div className={!enabled ? 'disabled-section' : ''}>
        <div className="space-y-2 padding-sm">
          {fields.map((field, index) => {
            const nameError = getError(`user_registry_credential.${index}.name`);
            const usernameError = getError(`user_registry_credential.${index}.username`);
            const passwordError = getError(`user_registry_credential.${index}.password`);

            return (
              <div key={field.id} className="space-y-2 section-style">
                <div className="form-row">
                  <div className="form-group">
                    <label className="form-label">User Registry Name (Required)</label>
                    <input
                      type="text"
                      className={`form-input ${nameError ? 'error' : ''}`}
                      placeholder="Must match local_repo_config.yml"
                      disabled={!enabled}
                      {...register(`user_registry_credential.${index}.name`)}
                    />
                    {nameError && <span className="error-message">{nameError.message}</span>}
                  </div>
                  <div className="form-group">
                    <label className="form-label">Username (Optional)</label>
                    <input
                      type="text"
                      className={`form-input ${usernameError ? 'error' : ''}`}
                      placeholder="Registry username"
                      disabled={!enabled}
                      {...register(`user_registry_credential.${index}.username`)}
                    />
                    {usernameError && <span className="error-message">{usernameError.message}</span>}
                  </div>
                  <div className="form-group">
                    <label className="form-label">Password (Optional)</label>
                    <input
                      type="password"
                      className={`form-input ${passwordError ? 'error' : ''}`}
                      placeholder="Registry password"
                      disabled={!enabled}
                      {...register(`user_registry_credential.${index}.password`)}
                    />
                    {passwordError && <span className="error-message">{passwordError.message}</span>}
                  </div>
                </div>
                {fields.length > 1 && (
                  <Button variant="secondary" onClick={() => remove(index)} disabled={!enabled}>
                    Remove Credential
                  </Button>
                )}
              </div>
            );
          })}
          {enabled && fields.length === 0 && (
            <p className="text-small-muted padding-sm italic">
              No credentials configured. Click below to add one.
            </p>
          )}
          <Button variant="primary" onClick={() => append({ name: '', username: '', password: '' })} disabled={!enabled}>
            Add User Registry Credential
          </Button>
        </div>
      </div>
    </>
  );
};
