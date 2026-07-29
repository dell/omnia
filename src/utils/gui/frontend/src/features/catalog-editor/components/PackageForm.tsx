import React from 'react';
import { useFormContext, Controller, useWatch } from 'react-hook-form';
import { useFormErrors } from '../../configuration-wizard/hooks/useFormErrors';

interface PackageFormProps {
  onSubmit: (data: any) => void;
  onCancel: () => void;
  submitLabel: string;
  title: string;
  variant?: 'package' | 'infrastructure' | 'driver';
}

const PACKAGE_TYPES = [
  'rpm',
  'rpm_repo',
  'tarball',
  'iso',
  'git',
  'image',
  'pip_module',
  'manifest',
];

const ARCHITECTURES = ['x86_64', 'aarch64'];

const PackageForm: React.FC<PackageFormProps> = ({
  onSubmit,
  onCancel,
  submitLabel,
  title,
  variant = 'package',
}) => {
  const {
    register,
    control,
    handleSubmit,
    setValue,
    getValues,
    formState,
  } = useFormContext();
  const getError = useFormErrors(formState.errors);

  const nameError = getError('Name');
  const typeError = getError('Type');
  const architectureError = getError('Architecture');
  const versionError = getError('Version');
  const tagError = getError('Tag');
  const uriError = getError('Uri');
  const supportedOSNameError = getError('SupportedOS.0.Name');
  const supportedOSVersionError = getError('SupportedOS.0.Version');
  const supportedFunctionsError = getError('SupportedFunctions.0.Name');
  const driverBrandError = getError('Config.DriverBrand');
  const driverTypeError = getError('Config.DriverType');

  const architecture = (useWatch({ control, name: 'Architecture' }) as string[]) || [];
  const sources = (useWatch({ control, name: 'Sources' }) as any[]) || [];

  const handleArchitectureChange = (current: string[], arch: string) => (e: React.ChangeEvent<HTMLInputElement>) => {
    const updated = e.target.checked
      ? [...current, arch]
      : current.filter((a) => a !== arch);

    setValue('Architecture', updated, { shouldValidate: false });

    if (variant === 'driver') return;

    const newSources = updated.map((a) => {
      const existing = sources.find((s) => s.Architecture === a);
      return existing || { Architecture: a, RepoName: '', Uri: '' };
    });
    setValue('Sources', newSources, { shouldValidate: false });
  };

  const handleSourceChange = (arch: string, field: 'RepoName' | 'Uri') => (e: React.ChangeEvent<HTMLInputElement>) => {
    const value = e.target.value;
    const currentSources = [...((getValues('Sources') as any[]) || [])];
    const idx = currentSources.findIndex((s) => s.Architecture === arch);

    if (idx === -1) {
      if (!value.trim()) return;
      currentSources.push({ Architecture: arch, [field]: value });
    } else {
      currentSources[idx] = { ...currentSources[idx], [field]: value };
      if (
        !currentSources[idx].RepoName?.trim() &&
        !currentSources[idx].Uri?.trim()
      ) {
        currentSources.splice(idx, 1);
      }
    }

    setValue('Sources', currentSources, { shouldValidate: false });
  };

  return (
    <form onSubmit={handleSubmit(onSubmit)} className="section-box">
      <h3>{title}</h3>
      {formState.errors.root && (
        <div className="error-message mb-2">
          {formState.errors.root.message as string}
        </div>
      )}
      <div className="grid-2-col">
        <div className="form-group">
          <label className="form-label">Name:</label>
          <input
            type="text"
            {...register('Name')}
            className={`form-input ${nameError ? 'error' : ''}`}
          />
          {nameError && (
            <span className="error-message">{nameError?.message}</span>
          )}
        </div>
        <div className="form-group">
          <label className="form-label">Type:</label>
          <select
            {...register('Type')}
            className={`form-select ${typeError ? 'error' : ''}`}
          >
            {PACKAGE_TYPES.map((type) => (
              <option key={type} value={type}>
                {type}
              </option>
            ))}
          </select>
          {typeError && (
            <span className="error-message">{typeError?.message}</span>
          )}
        </div>
        <div className="form-group">
          <label className="form-label">Architecture:</label>
          <Controller
            name="Architecture"
            control={control}
            render={({ field }) => (
              <div className="flex gap-2">
                {ARCHITECTURES.map((arch) => (
                  <label key={arch} className="form-checkbox">
                    <input
                      type="checkbox"
                      checked={(field.value || []).includes(arch)}
                      onChange={handleArchitectureChange(field.value || [], arch)}
                    />
                    {arch}
                  </label>
                ))}
              </div>
            )}
          />
          {architectureError && (
            <span className="error-message">
              {architectureError?.message}
            </span>
          )}
        </div>
        {(variant === 'driver' || variant === 'infrastructure') && (
          <div className="form-group">
            <label className="form-label">URI:</label>
            <input
              type="text"
              {...register('Uri')}
              className={`form-input ${uriError ? 'error' : ''}`}
              placeholder="e.g., https://example.com/file.tar.gz"
            />
            {uriError && (
              <span className="error-message">
                {uriError?.message}
              </span>
            )}
          </div>
        )}
        <div className="form-group">
          <label className="form-label">Version:</label>
          <input
            type="text"
            {...register('Version')}
            className={`form-input ${versionError ? 'error' : ''}`}
          />
          {versionError && (
            <span className="error-message">
              {versionError?.message}
            </span>
          )}
        </div>
        {variant !== 'driver' && (
          <div className="form-group">
            <label className="form-label">Tag:</label>
            <input
              type="text"
              {...register('Tag')}
              className={`form-input ${tagError ? 'error' : ''}`}
            />
            {tagError && (
              <span className="error-message">{tagError?.message}</span>
            )}
          </div>
        )}
        {variant === 'package' && (
          <>
            <div className="form-group">
              <label className="form-label">OS Name:</label>
              <input
                type="text"
                {...register('SupportedOS.0.Name')}
                className={`form-input ${supportedOSNameError ? 'error' : ''}`}
              />
              {supportedOSNameError && (
                <span className="error-message">
                  {supportedOSNameError?.message}
                </span>
              )}
            </div>
            <div className="form-group">
              <label className="form-label">OS Version:</label>
              <input
                type="text"
                {...register('SupportedOS.0.Version')}
                className={`form-input ${supportedOSVersionError ? 'error' : ''}`}
              />
              {supportedOSVersionError && (
                <span className="error-message">
                  {supportedOSVersionError?.message}
                </span>
              )}
            </div>
          </>
        )}
        {variant === 'infrastructure' && (
          <div className="form-group">
            <label className="form-label">Function Name:</label>
            <input
              type="text"
              {...register('SupportedFunctions.0.Name')}
              className={`form-input ${supportedFunctionsError ? 'error' : ''}`}
            />
            {supportedFunctionsError && (
              <span className="error-message">
                {supportedFunctionsError?.message}
              </span>
            )}
          </div>
        )}
        {variant === 'driver' && (
          <>
            <div className="form-group">
              <label className="form-label">Driver Brand:</label>
              <input
                type="text"
                {...register('Config.DriverBrand')}
                className={`form-input ${driverBrandError ? 'error' : ''}`}
              />
              {driverBrandError && (
                <span className="error-message">
                  {driverBrandError?.message}
                </span>
              )}
            </div>
            <div className="form-group">
              <label className="form-label">Driver Type:</label>
              <input
                type="text"
                {...register('Config.DriverType')}
                className={`form-input ${driverTypeError ? 'error' : ''}`}
              />
              {driverTypeError && (
                <span className="error-message">
                  {driverTypeError?.message}
                </span>
              )}
            </div>
          </>
        )}
        {variant !== 'driver' && architecture.map((arch) => {
          const sourceIndex = sources.findIndex((s) => s.Architecture === arch);
          const source = sources[sourceIndex] || {
            Architecture: arch,
            RepoName: '',
            Uri: '',
          };
          const uriError = sourceIndex >= 0 ? getError(`Sources.${sourceIndex}.Uri`) : undefined;
          const repoNameError = sourceIndex >= 0 ? getError(`Sources.${sourceIndex}.RepoName`) : undefined;
          const presenceError = uriError && !source.Uri?.trim() ? uriError : undefined;
          return (
            <div key={arch} className="source-item">
              <h4 className="source-arch-label">Source for {arch}</h4>
              <div className="grid-2-col">
                <div className="form-group">
                  <label className="form-label">Repo Name:</label>
                  <input
                    type="text"
                    value={source.RepoName || ''}
                    onChange={handleSourceChange(arch, 'RepoName')}
                    className={`form-input ${repoNameError || presenceError ? 'error' : ''}`}
                    placeholder="e.g., baseos"
                  />
                  {(repoNameError || presenceError) && (
                    <span className="error-message">
                      {(repoNameError || presenceError)?.message}
                    </span>
                  )}
                </div>
                <div className="form-group">
                  <label className="form-label">Or URI:</label>
                  <input
                    type="text"
                    value={source.Uri || ''}
                    onChange={handleSourceChange(arch, 'Uri')}
                    className={`form-input ${uriError ? 'error' : ''}`}
                    placeholder="e.g., https://example.com/file.tar.gz"
                  />
                  {uriError && (
                    <span className="error-message">
                      {uriError.message}
                    </span>
                  )}
                </div>
              </div>
            </div>
          );
        })}
      </div>
      <div className="flex gap-2 mt-4">
        <button type="submit" className="button button-primary">
          {submitLabel}
        </button>
        <button type="button" onClick={onCancel} className="button button-secondary">
          Cancel
        </button>
      </div>
    </form>
  );
};

export default PackageForm;
