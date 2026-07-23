import { Controller, UseFormRegister, Control, FieldErrors } from 'react-hook-form';
import { TelemetryConfigStorageFormData } from '../../schemas/telemetryConfigStorage';
import { useFormErrors } from '../../hooks/useFormErrors';
import type { ValidationError } from '../../utils/l2Validation';

interface PowerscaleTabProps {
  register: UseFormRegister<TelemetryConfigStorageFormData>;
  control: Control<TelemetryConfigStorageFormData>;
  errors: FieldErrors<TelemetryConfigStorageFormData>;
  enabled?: boolean;
  validationErrors?: ValidationError[];
}

export const PowerscaleTab = ({ register, control, errors, enabled, validationErrors }: PowerscaleTabProps) => {
  const getError = useFormErrors(errors, validationErrors);

  const otelStorageError = getError('powerscale_configurations.otel_collector_storage_size');
  const csmValuesPathError = getError('powerscale_configurations.csm_observability_values_file_path');
  const cpuReqError = getError('csm_metrics_powerscale_storage.resources.requests.cpu');
  const memReqError = getError('csm_metrics_powerscale_storage.resources.requests.memory');
  const cpuLimError = getError('csm_metrics_powerscale_storage.resources.limits.cpu');
  const memLimError = getError('csm_metrics_powerscale_storage.resources.limits.memory');

  return (
    <div className="space-y-6">
      <div className="form-group">
        <label className="form-label">PowerScale Telemetry Configuration</label>
        <div className="section-style">
          <div className="space-y-2">
            <div className="form-group">
              <label className="form-label">Enable Metrics Collection</label>
            </div>

            <div className="form-checkbox">
              <input
                id="telemetry_sources.powerscale.logs_enabled"
                type="checkbox"
                {...register('telemetry_sources.powerscale.logs_enabled')}
              />
              <label htmlFor="telemetry_sources.powerscale.logs_enabled">
                Enable PowerScale logs collection
              </label>
            </div>

            <div>
              <label className="form-label">Collection Targets</label>
              <Controller
                control={control}
                name="telemetry_sources.powerscale.collection_targets"
                render={({ field }) => (
                  <>
                    {['victoria_metrics', 'victoria_logs'].map((target) => (
                      <div key={target} className="form-checkbox">
                        <input
                          id={`powerscale-collection-${target}`}
                          type="checkbox"
                          value={target}
                          checked={(field.value || []).includes(target as any)}
                          onChange={(e) => {
                            const updated = e.target.checked
                              ? [...(field.value || []), target]
                              : (field.value || []).filter((v: string) => v !== target);
                            field.onChange(updated);
                          }}
                        />
                        <label htmlFor={`powerscale-collection-${target}`}>
                          {target === 'victoria_metrics' ? 'Victoria Metrics' : 'Victoria Logs'}
                        </label>
                      </div>
                    ))}
                  </>
                )}
              />
            </div>

            <div className={!enabled ? 'disabled-section' : ''}>
                <div className="form-group">
                  <label className="form-label">OTEL Collector Storage Size (Required)</label>
                  <input
                    type="text"
                    className={`form-input ${otelStorageError ? 'error' : ''}`}
                    placeholder="e.g., 5Gi"
                    disabled={!enabled}
                    {...register('powerscale_configurations.otel_collector_storage_size')}
                  />
                  {otelStorageError && <span className="error-message">{otelStorageError.message}</span>}
                </div>

                <div className="form-group">
                  <label className="form-label">CSM Observability Values File Path (Required)</label>
                  <input
                    type="text"
                    className={`form-input ${csmValuesPathError ? 'error' : ''}`}
                    placeholder="Path to values.yaml"
                    disabled={!enabled}
                    {...register('powerscale_configurations.csm_observability_values_file_path')}
                  />
                  {csmValuesPathError && <span className="error-message">{csmValuesPathError.message}</span>}
                </div>
            </div>
          </div>
        </div>
      </div>

      <div className={!enabled ? 'disabled-section' : ''}>
        <div className="form-group">
          <label className="form-label">CSM Metrics PowerScale Resources</label>
          <div className="resource-style">
            <div className="space-y-2">
              <h4 className="subsection-title">Resource Limits</h4>
              <div className="grid-4-col">
                <div className="form-group">
                  <label className="form-label">CPU Request</label>
                  <input
                    type="text"
                    className={`form-input ${cpuReqError ? 'error' : ''}`}
                    placeholder="e.g., 100m"
                    disabled={!enabled}
                    {...register('csm_metrics_powerscale_storage.resources.requests.cpu')}
                  />
                  {cpuReqError && <span className="error-message">{cpuReqError.message}</span>}
                </div>
                <div className="form-group">
                  <label className="form-label">Memory Request</label>
                  <input
                    type="text"
                    className={`form-input ${memReqError ? 'error' : ''}`}
                    placeholder="e.g., 128Mi"
                    disabled={!enabled}
                    {...register('csm_metrics_powerscale_storage.resources.requests.memory')}
                  />
                  {memReqError && <span className="error-message">{memReqError.message}</span>}
                </div>
                <div className="form-group">
                  <label className="form-label">CPU Limit</label>
                  <input
                    type="text"
                    className={`form-input ${cpuLimError ? 'error' : ''}`}
                    placeholder="e.g., 500m"
                    disabled={!enabled}
                    {...register('csm_metrics_powerscale_storage.resources.limits.cpu')}
                  />
                  {cpuLimError && <span className="error-message">{cpuLimError.message}</span>}
                </div>
                <div className="form-group">
                  <label className="form-label">Memory Limit</label>
                  <input
                    type="text"
                    className={`form-input ${memLimError ? 'error' : ''}`}
                    placeholder="e.g., 512Mi"
                    disabled={!enabled}
                    {...register('csm_metrics_powerscale_storage.resources.limits.memory')}
                  />
                  {memLimError && <span className="error-message">{memLimError.message}</span>}
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};
