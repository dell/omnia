import { Controller, UseFormRegister, Control, FieldErrors, useWatch } from 'react-hook-form';
import { TelemetryConfigStorageFormData } from '../../schemas/telemetryConfigStorage';
import { useFormErrors } from '../../hooks/useFormErrors';
import type { ValidationError } from '../../utils/l2Validation';

interface VastTabProps {
  register: UseFormRegister<TelemetryConfigStorageFormData>;
  control: Control<TelemetryConfigStorageFormData>;
  errors: FieldErrors<TelemetryConfigStorageFormData>;
  enabled?: boolean;
  validationErrors?: ValidationError[];
}

export const VastTab = ({ register, control, errors, enabled, validationErrors }: VastTabProps) => {
  const getError = useFormErrors(errors, validationErrors);

  const vastEndpointError = getError('vast_configuration.vast_endpoint');
  const vastMetricsPortError = getError('vast_configuration.vast_metrics_port');
  const authModeError = getError('vast_configuration.auth_mode');
  const metricsPathError = getError('vast_configuration.metrics_path');
  const scrapeIntervalError = getError('vast_configuration.scrape_interval');
  const scrapeTimeoutError = getError('vast_configuration.scrape_timeout');
  const tlsModeError = getError('vast_configuration.tls_mode');
  const vastCaCertPathError = getError('vast_configuration.vast_ca_cert_path');

  // Watch TLS mode to conditionally disable CA cert path field
  const tlsMode = useWatch({
    control,
    name: 'vast_configuration.tls_mode',
  });

  return (
    <div className="space-y-6">
      <div className="form-group">
        <label className="form-label">VAST Telemetry Configuration</label>
        <div className="section-style">
          <div className="space-y-2">
            <div className="form-group">
              <label className="form-label">Enable Metrics Collection</label>
            </div>
            <div className="form-checkbox">
              <input
                id="telemetry_sources.vast.logs_enabled"
                type="checkbox"
                {...register('telemetry_sources.vast.logs_enabled')}
              />
              <label htmlFor="telemetry_sources.vast.logs_enabled">
                Enable VAST logs collection
              </label>
            </div>

            <div>
              <label className="form-label">Collection Targets</label>
              <Controller
                control={control}
                name="telemetry_sources.vast.collection_targets"
                render={({ field }) => (
                  <>
                    {['victoria_metrics', 'victoria_logs'].map((target) => (
                      <div key={target} className="form-checkbox">
                        <input
                          id={`vast-collection-${target}`}
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
                        <label htmlFor={`vast-collection-${target}`}>
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
                      <label className="form-label">VAST Endpoint (Required)</label>
                      <input
                        type="text"
                        className={`form-input ${vastEndpointError ? 'error' : ''}`}
                        placeholder="VAST cluster IP or hostname"
                        disabled={!enabled}
                        {...register('vast_configuration.vast_endpoint')}
                      />
                      {vastEndpointError && <span className="error-message">{vastEndpointError.message}</span>}
                    </div>
                    <div className="form-group">
                      <label className="form-label">VAST Metrics Port</label>
                      <input
                        type="number"
                        className={`form-input ${vastMetricsPortError ? 'error' : ''}`}
                        placeholder="e.g., 443"
                        disabled={!enabled}
                        {...register('vast_configuration.vast_metrics_port')}
                      />
                      {vastMetricsPortError && <span className="error-message">{vastMetricsPortError.message}</span>}
                    </div>
                    <div className="form-group">
                      <label className="form-label">Auth Mode</label>
                      <select className={`form-select ${authModeError ? 'error' : ''}`} disabled={!enabled} {...register('vast_configuration.auth_mode')}>
                        <option value="basic">Basic</option>
                        <option value="none">None</option>
                      </select>
                      {authModeError && <span className="error-message">{authModeError.message}</span>}
                    </div>
                  </div>
                </div>

                <div className="form-group">
                  <label className="form-label">Metrics Path</label>
                  <input
                    type="text"
                    className={`form-input ${metricsPathError ? 'error' : ''}`}
                    placeholder="/api/prometheusmetrics/all"
                    disabled={!enabled}
                    {...register('vast_configuration.metrics_path')}
                  />
                  {metricsPathError && <span className="error-message">{metricsPathError.message}</span>}
                </div>

                <div className="form-group">
                  <div className="form-row">
                    <div className="form-group">
                      <label className="form-label">Scrape Interval</label>
                      <input
                        type="text"
                        className={`form-input ${scrapeIntervalError ? 'error' : ''}`}
                        placeholder="e.g., 30s"
                        disabled={!enabled}
                        {...register('vast_configuration.scrape_interval')}
                      />
                      {scrapeIntervalError && <span className="error-message">{scrapeIntervalError.message}</span>}
                    </div>
                    <div className="form-group">
                      <label className="form-label">Scrape Timeout</label>
                      <input
                        type="text"
                        className={`form-input ${scrapeTimeoutError ? 'error' : ''}`}
                        placeholder="e.g., 15s"
                        disabled={!enabled}
                        {...register('vast_configuration.scrape_timeout')}
                      />
                      {scrapeTimeoutError && <span className="error-message">{scrapeTimeoutError.message}</span>}
                    </div>
                    <div className="form-group">
                      <label className="form-label">TLS Mode</label>
                      <select className={`form-select ${tlsModeError ? 'error' : ''}`} disabled={!enabled} {...register('vast_configuration.tls_mode')}>
                        <option value="self_signed">Self-signed</option>
                        <option value="ca_signed">CA-signed</option>
                      </select>
                      {tlsModeError && <span className="error-message">{tlsModeError.message}</span>}
                    </div>
                  </div>
                </div>

                <div className="form-group">
                  <label className="form-label">VAST CA Cert Path (Required when TLS mode is CA Signed)</label>
                  <input
                    type="text"
                    className={`form-input ${vastCaCertPathError ? 'error' : ''} ${tlsMode === 'self_signed' ? 'disabled-section' : ''}`}
                    placeholder="Path to CA certificate"
                    readOnly={tlsMode === 'self_signed'}
                    disabled={!enabled}
                    {...register('vast_configuration.vast_ca_cert_path')}
                  />
                  {vastCaCertPathError && <span className="error-message">{vastCaCertPathError.message}</span>}
                </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};
