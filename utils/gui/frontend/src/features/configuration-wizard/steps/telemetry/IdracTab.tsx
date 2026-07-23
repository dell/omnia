import { Controller, UseFormRegister, Control, FieldErrors } from 'react-hook-form';
import { TelemetryConfigStorageFormData } from '../../schemas/telemetryConfigStorage';
import { useFormErrors } from '../../hooks/useFormErrors';
import type { FormFieldError } from '../../hooks/useFormErrors';
import type { ValidationError } from '../../utils/l2Validation';

interface IdracTabProps {
  register: UseFormRegister<TelemetryConfigStorageFormData>;
  control: Control<TelemetryConfigStorageFormData>;
  errors: FieldErrors<TelemetryConfigStorageFormData>;
  enabled?: boolean;
  needsKafka?: boolean;
  needsVictoriaMetrics?: boolean;
  validationErrors?: ValidationError[];
}

interface ResourceFieldsProps {
  basePath: string;
  disabled: boolean;
  defaults: { cpuReq: string; memReq: string; cpuLim: string; memLim: string };
  register: UseFormRegister<TelemetryConfigStorageFormData>;
  getError: (path: string) => FormFieldError | undefined;
}

const ResourceFields = ({ basePath, disabled, defaults, register, getError }: ResourceFieldsProps) => {
  const fields = [
    { label: 'CPU Request', path: 'requests.cpu', placeholder: defaults.cpuReq },
    { label: 'Memory Request', path: 'requests.memory', placeholder: defaults.memReq },
    { label: 'CPU Limit', path: 'limits.cpu', placeholder: defaults.cpuLim },
    { label: 'Memory Limit', path: 'limits.memory', placeholder: defaults.memLim },
  ];

  return (
    <div className="form-row form-row-4-col">
      {fields.map(({ label, path, placeholder }) => {
        const fullPath = `${basePath}.resources.${path}` as any;
        const error = getError(fullPath);
        return (
          <div key={path} className="form-group">
            <label className="form-label">{label}</label>
            <input
              type="text"
              className={`form-input ${error ? 'error' : ''}`}
              placeholder={`e.g., ${placeholder}`}
              disabled={disabled}
              {...register(fullPath)}
            />
            {error && <span className="error-message">{error.message}</span>}
          </div>
        );
      })}
    </div>
  );
};

export const IdracTab = ({ register, control, errors, enabled, needsKafka, needsVictoriaMetrics, validationErrors }: IdracTabProps) => {
  const getError = useFormErrors(errors, validationErrors);
  const mysqlStorageError = getError('idrac_telemetry_configurations.mysqldb_storage');

  return (
    <div className="space-y-6">
      <div className="form-group">
        <label className="form-label">iDRAC Telemetry Configuration</label>
        <div className="section-style">
          <div className="space-y-2">
            <div className="form-group">
              <label className="form-label">Collection Targets</label>
              <Controller
                control={control}
                name="telemetry_sources.idrac.collection_targets"
                render={({ field }) => (
                  <>
                    {['victoria_metrics', 'kafka'].map((target) => (
                      <div key={target} className="form-checkbox">
                        <input
                          id={`idrac-collection-${target}`}
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
                        <label htmlFor={`idrac-collection-${target}`}>
                          {target === 'victoria_metrics' ? 'VictoriaMetrics' : 'Kafka'}
                        </label>
                      </div>
                    ))}
                  </>
                )}
              />
            </div>

            <div className={!enabled ? 'disabled-section' : ''}>
              <div>
                <label className="form-label">MySQL Database Storage Size (Default: 1Gi)</label>
                <input
                  type="text"
                  className={`form-input ${mysqlStorageError ? 'error' : ''}`}
                  placeholder="e.g., 1Gi"
                  disabled={!enabled}
                  {...register('idrac_telemetry_configurations.mysqldb_storage')}
                />
                {mysqlStorageError && <span className="error-message">{mysqlStorageError.message}</span>}
              </div>
            </div>
          </div>
        </div>
      </div>

      <div className={!enabled ? 'disabled-section' : ''}>
        <div className="form-group">
          <label className="form-label">iDRAC Telemetry Storage Resources</label>
          <div className="resource-style">
            <div className="space-y-2">
              <h4 className="subsection-title">MySQL Database Resources</h4>
              <ResourceFields
                basePath="idrac_telemetry_storage.mysqldb"
                disabled={!enabled}
                defaults={{ cpuReq: '100m', memReq: '256Mi', cpuLim: '500m', memLim: '512Mi' }}
                register={register}
                getError={getError}
              />

              <h4 className="subsection-title-spaced">ActiveMQ Resources</h4>
              <ResourceFields
                basePath="idrac_telemetry_storage.activemq"
                disabled={!enabled}
                defaults={{ cpuReq: '100m', memReq: '512Mi', cpuLim: '500m', memLim: '1536Mi' }}
                register={register}
                getError={getError}
              />

              <h4 className="subsection-title-spaced">Receiver Resources</h4>
              <ResourceFields
                basePath="idrac_telemetry_storage.receiver"
                disabled={!enabled}
                defaults={{ cpuReq: '100m', memReq: '128Mi', cpuLim: '500m', memLim: '256Mi' }}
                register={register}
                getError={getError}
              />

              <div className={!needsKafka ? 'disabled-section' : ''}>
                  <h4 className="subsection-title-spaced">Kafka Pump Resources</h4>
                  <ResourceFields
                    basePath="idrac_telemetry_storage.kafka_pump"
                    disabled={!needsKafka}
                    defaults={{ cpuReq: '50m', memReq: '128Mi', cpuLim: '200m', memLim: '512Mi' }}
                    register={register}
                    getError={getError}
                  />
              </div>

              <div className={!needsVictoriaMetrics ? 'disabled-section' : ''}>
                  <h4 className="subsection-title-spaced">Victoria Pump Resources</h4>
                  <ResourceFields
                    basePath="idrac_telemetry_storage.victoria_pump"
                    disabled={!needsVictoriaMetrics}
                    defaults={{ cpuReq: '50m', memReq: '128Mi', cpuLim: '200m', memLim: '512Mi' }}
                    register={register}
                    getError={getError}
                  />
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};
