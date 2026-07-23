import { Controller, UseFormRegister, Control, FieldErrors, useWatch } from 'react-hook-form';
import { TelemetryConfigStorageFormData } from '../../schemas/telemetryConfigStorage';
import { useFormErrors } from '../../hooks/useFormErrors';
import type { ValidationError } from '../../utils/l2Validation';

interface UfmTabProps {
  register: UseFormRegister<TelemetryConfigStorageFormData>;
  control: Control<TelemetryConfigStorageFormData>;
  errors: FieldErrors<TelemetryConfigStorageFormData>;
  enabled?: boolean;
  validationErrors?: ValidationError[];
}

export const UfmTab = ({ register, control, errors, enabled, validationErrors }: UfmTabProps) => {
  const getError = useFormErrors(errors, validationErrors);

  const ufmEndpointError = getError('ufm_configuration.ufm_endpoint');
  const ufmMetricsPortError = getError('ufm_configuration.ufm_metrics_port');
  const scrapeIntervalError = getError('ufm_configuration.scrape_interval');
  const scrapeTimeoutError = getError('ufm_configuration.scrape_timeout');
  const tlsModeError = getError('ufm_configuration.tls_mode');
  const authModeError = getError('ufm_configuration.auth_mode');
  const ufmCaCertPathError = getError('ufm_configuration.ufm_ca_cert_path');

  // Watch TLS mode to conditionally disable CA cert path field
  const tlsMode = useWatch({
    control,
    name: 'ufm_configuration.tls_mode',
  });

  return (
    <div className="space-y-6">
      <div className="form-group">
        <label className="form-label">UFM Telemetry Configuration</label>
        <div className="section-style">
          <div className="space-y-2">
            <div className="form-group">
              <label className="form-label">Enable Metrics Collection</label>
            </div>

            <div className="form-checkbox">
              <input
                id="telemetry_sources.ufm.logs_enabled"
                type="checkbox"
                {...register('telemetry_sources.ufm.logs_enabled')}
              />
              <label htmlFor="telemetry_sources.ufm.logs_enabled">
                Enable UFM logs collection
              </label>
            </div>

            <div>
              <label className="form-label">Collection Targets</label>
              <Controller
                control={control}
                name="telemetry_sources.ufm.collection_targets"
                render={({ field }) => (
                  <>
                    {['victoria_metrics', 'victoria_logs'].map((target) => (
                      <div key={target} className="form-checkbox">
                        <input
                          id={`ufm-collection-${target}`}
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
                        <label htmlFor={`ufm-collection-${target}`}>
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
                  <div className="form-row">
                    <div className="form-group">
                      <label className="form-label">UFM Endpoint (Required)</label>
                      <input
                        type="text"
                        className={`form-input ${ufmEndpointError ? 'error' : ''}`}
                        placeholder="UFM appliance IP or hostname"
                        disabled={!enabled}
                        {...register('ufm_configuration.ufm_endpoint')}
                      />
                      {ufmEndpointError && <span className="error-message">{ufmEndpointError.message}</span>}
                    </div>
                    <div className="form-group">
                      <label className="form-label">UFM Metrics Port</label>
                      <input
                        type="number"
                        className={`form-input ${ufmMetricsPortError ? 'error' : ''}`}
                        placeholder="e.g., 9001"
                        disabled={!enabled}
                        {...register('ufm_configuration.ufm_metrics_port')}
                      />
                      {ufmMetricsPortError && <span className="error-message">{ufmMetricsPortError.message}</span>}
                    </div>
                    <div className="form-group">
                      <label className="form-label">Scrape Interval</label>
                      <input
                        type="text"
                        className={`form-input ${scrapeIntervalError ? 'error' : ''}`}
                        placeholder="e.g., 30s"
                        disabled={!enabled}
                        {...register('ufm_configuration.scrape_interval')}
                      />
                      {scrapeIntervalError && <span className="error-message">{scrapeIntervalError.message}</span>}
                    </div>
                  </div>
                </div>

                <div className="form-group">
                  <div className="form-row">
                    <div className="form-group">
                      <label className="form-label">Scrape Timeout</label>
                      <input
                        type="text"
                        className={`form-input ${scrapeTimeoutError ? 'error' : ''}`}
                        placeholder="e.g., 15s"
                        disabled={!enabled}
                        {...register('ufm_configuration.scrape_timeout')}
                      />
                      {scrapeTimeoutError && <span className="error-message">{scrapeTimeoutError.message}</span>}
                    </div>
                    <div className="form-group">
                      <label className="form-label">TLS Mode</label>
                      <select className={`form-select ${tlsModeError ? 'error' : ''}`} disabled={!enabled} {...register('ufm_configuration.tls_mode')}>
                        <option value="self_signed">Self-signed</option>
                        <option value="ca_signed">CA-signed</option>
                      </select>
                      {tlsModeError && <span className="error-message">{tlsModeError.message}</span>}
                    </div>
                    <div className="form-group">
                      <label className="form-label">Auth Mode</label>
                      <select className={`form-select ${authModeError ? 'error' : ''}`} disabled={!enabled} {...register('ufm_configuration.auth_mode')}>
                        <option value="basic">Basic</option>
                        <option value="none">None</option>
                      </select>
                      {authModeError && <span className="error-message">{authModeError.message}</span>}
                    </div>
                  </div>
                </div>

                <div className="form-group">
                  <label className="form-label">UFM CA Cert Path (Required when TLS mode is CA Signed)</label>
                  <input
                    type="text"
                    className={`form-input ${ufmCaCertPathError ? 'error' : ''} ${tlsMode === 'self_signed' ? 'disabled-section' : ''}`}
                    placeholder="Path to CA certificate"
                    readOnly={tlsMode === 'self_signed'}
                    disabled={!enabled}
                    {...register('ufm_configuration.ufm_ca_cert_path')}
                  />
                  {ufmCaCertPathError && <span className="error-message">{ufmCaCertPathError.message}</span>}
                </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};
