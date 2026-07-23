import type { UseFormRegister, Control } from 'react-hook-form';
import { useFieldArray } from 'react-hook-form';
import Button from '../../../../../components/Button';
import { TelemetryConfigStorageFormData } from '../../../schemas/telemetryConfigStorage';
import type { FormFieldError } from '../../../hooks/useFormErrors';

interface VictoriaMetricsSectionProps {
  enabled: boolean;
  register: UseFormRegister<TelemetryConfigStorageFormData>;
  control: Control<TelemetryConfigStorageFormData>;
  getError: (path: string) => FormFieldError | undefined;
}

export const VictoriaMetricsSection = ({ enabled, register, control, getError }: VictoriaMetricsSectionProps) => {
  const persistenceSizeError = getError('telemetry_sinks.victoria_metrics.persistence_size');
  const retentionPeriodError = getError('telemetry_sinks.victoria_metrics.retention_period');

  const { fields, append, remove } = useFieldArray({
    control,
    name: 'telemetry_sinks.victoria_metrics.additional_metric_remote_write_endpoints',
  });

  return (
    <div className={!enabled ? 'disabled-section' : ''}>
      <div className="form-group">
        <label className="form-label">VictoriaMetrics Configuration</label>
        <div className="section-style">
          <div className="space-y-2">
            <div className="form-row form-row-2-col">
              <div className="form-group">
                <label className="form-label">Persistence Size</label>
                <input
                  type="text"
                  className={`form-input ${persistenceSizeError ? 'error' : ''}`}
                  placeholder="e.g., 8Gi"
                  disabled={!enabled}
                  {...register('telemetry_sinks.victoria_metrics.persistence_size')}
                />
                {persistenceSizeError && <span className="error-message">{persistenceSizeError.message}</span>}
              </div>
              <div className="form-group">
                <label className="form-label">Retention Period (hours)</label>
                <input
                  type="number"
                  className={`form-input ${retentionPeriodError ? 'error' : ''}`}
                  placeholder="e.g., 168"
                  disabled={!enabled}
                  {...register('telemetry_sinks.victoria_metrics.retention_period')}
                />
                {retentionPeriodError && <span className="error-message">{retentionPeriodError.message}</span>}
              </div>
            </div>
            <div>
              <label className="form-label">Additional Metric Remote Write Endpoints (Optional)</label>
              {fields.map((field, index) => {
                const urlError = getError(`telemetry_sinks.victoria_metrics.additional_metric_remote_write_endpoints.${index}.url`);
                return (
                <div key={field.id} className="form-row form-row-2-col">
                  <div className="form-group">
                    <input
                      type="text"
                      className={`form-input ${urlError ? 'error' : ''}`}
                      placeholder="https://external-server:8480/insert/0/prometheus/api/v1/write"
                      disabled={!enabled}
                      {...register(`telemetry_sinks.victoria_metrics.additional_metric_remote_write_endpoints.${index}.url`)}
                    />
                    {urlError && <span className="error-message">{urlError.message}</span>}
                  </div>
                  <div className="form-group flex items-center justify-between">
                    <div className="form-checkbox" style={{ marginBottom: 0 }}>
                      <input
                        type="checkbox"
                        id={`tls-insecure-${index}`}
                        disabled={!enabled}
                        {...register(`telemetry_sinks.victoria_metrics.additional_metric_remote_write_endpoints.${index}.tls_insecure_skip_verify`)}
                      />
                      <label htmlFor={`tls-insecure-${index}`}>Skip TLS Verification</label>
                    </div>
                    <Button variant="secondary" onClick={() => remove(index)} disabled={!enabled}>
                      Remove
                    </Button>
                  </div>
                </div>
                );
              })}
              <div className="mt-4">
                <Button variant="secondary" onClick={() => append({ url: '', tls_insecure_skip_verify: false })} disabled={!enabled}>
                  + Add Endpoint
                </Button>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};
