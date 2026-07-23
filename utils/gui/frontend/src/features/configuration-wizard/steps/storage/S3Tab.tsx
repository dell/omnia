import type { UseFormRegister, Control, UseFormSetValue } from 'react-hook-form';
import { useWatch } from 'react-hook-form';
import { StorageConfigFormData } from '../../schemas/storageConfig';
import type { FormFieldError } from '../../hooks/useFormErrors';

interface S3TabProps {
  register: UseFormRegister<StorageConfigFormData>;
  control: Control<StorageConfigFormData>;
  setValue: UseFormSetValue<StorageConfigFormData>;
  getError: (path: string) => FormFieldError | undefined;
}

export const S3Tab = ({ register, control, setValue, getError }: S3TabProps) => {
  const provider = useWatch({ control, name: 's3_configurations.provider' }) || 'powerscale';

  const providerField = register('s3_configurations.provider');
  const providerError = getError('s3_configurations.provider');
  const endpointUrlError = getError('s3_configurations.endpoint_url');
  return (
    <>
      <div className="space-y-2 section-style">
          <div className="form-group">
            <label className="form-label">S3 Storage Provider (Required)</label>
            <select
              className={`form-select ${providerError ? 'error' : ''}`}
              {...providerField}
              onChange={(e) => {
                providerField.onChange(e);
                if (e.target.value === 'minio') {
                  setValue('s3_configurations.endpoint_url', '');
                }
              }}
            >
              <option value="powerscale">PowerScale</option>
              <option value="minio">MinIO</option>
            </select>
            {providerError && <span className="error-message">{providerError.message}</span>}
          </div>

          <div className="form-group">
            <label className="form-label">S3 Endpoint URL (Required when PowerScale, Optional when MinIO)</label>
            <input
              type="text"
              className={`form-input ${endpointUrlError ? 'error' : ''} ${provider !== 'powerscale' ? 'disabled-section' : ''}`}
              placeholder="e.g., https://powerscale.example.com:9020"
              disabled={provider !== 'powerscale'}
              {...register('s3_configurations.endpoint_url')}
            />
            <p className="text-sm text-gray-600 mt-1">
              Required for PowerScale. Leave empty for MinIO (auto-configured).
            </p>
            {endpointUrlError && <span className="error-message">{endpointUrlError.message}</span>}
          </div>
        </div>
    </>
  );
};
