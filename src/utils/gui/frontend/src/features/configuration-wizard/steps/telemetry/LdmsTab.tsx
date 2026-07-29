import { useFieldArray, Controller, UseFormRegister, Control, FieldErrors } from 'react-hook-form';
import Button from '../../../../components/Button';
import { TelemetryConfigStorageFormData } from '../../schemas/telemetryConfigStorage';
import { useFormErrors } from '../../hooks/useFormErrors';
import type { ValidationError } from '../../utils/l2Validation';

interface LdmsTabProps {
  register: UseFormRegister<TelemetryConfigStorageFormData>;
  control: Control<TelemetryConfigStorageFormData>;
  errors: FieldErrors<TelemetryConfigStorageFormData>;
  enabled?: boolean;
  validationErrors?: ValidationError[];
}

export const LdmsTab = ({ register, control, errors, enabled, validationErrors }: LdmsTabProps) => {
  const getError = useFormErrors(errors, validationErrors);

  const aggPortError = getError('ldms_configurations.agg_port');
  const storePortError = getError('ldms_configurations.store_port');
  const samplerPortError = getError('ldms_configurations.sampler_port');

  const { fields: samplerPluginFields, append: appendSamplerPlugin, remove: removeSamplerPlugin } = useFieldArray({
    control,
    name: 'ldms_configurations.sampler_plugins',
  });

  return (
    <div className="space-y-6">
      <div className="form-group">
        <label className="form-label">LDMS Telemetry Configuration</label>
        <div className="section-style">
          <div className="space-y-2">
            <div className="form-checkbox">
              <Controller
                control={control}
                name="telemetry_sources.ldms.collection_targets"
                render={({ field }) => (
                  <>
                    <input
                      id="ldms-collection-kafka"
                      type="checkbox"
                      value="kafka"
                      checked={(field.value || []).includes('kafka')}
                      onChange={(e) => {
                        const updated = e.target.checked
                          ? [...(field.value || []), 'kafka']
                          : (field.value || []).filter((v: string) => v !== 'kafka');
                        field.onChange(updated);
                      }}
                    />
                    <label htmlFor="ldms-collection-kafka">Kafka (required for LDMS)</label>
                  </>
                )}
              />
            </div>

            <div className={!enabled ? 'disabled-section' : ''}>
                <div className="form-row">
                  <div className="form-group">
                    <label className="form-label">Aggregator Port</label>
                    <input
                      type="number"
                      className={`form-input ${aggPortError ? 'error' : ''}`}
                      placeholder="e.g., 6001"
                      disabled={!enabled}
                      {...register('ldms_configurations.agg_port')}
                    />
                    {aggPortError && <span className="error-message">{aggPortError.message}</span>}
                  </div>
                  <div className="form-group">
                    <label className="form-label">Store Port</label>
                    <input
                      type="number"
                      className={`form-input ${storePortError ? 'error' : ''}`}
                      placeholder="e.g., 6001"
                      disabled={!enabled}
                      {...register('ldms_configurations.store_port')}
                    />
                    {storePortError && <span className="error-message">{storePortError.message}</span>}
                  </div>
                  <div className="form-group">
                    <label className="form-label">Sampler Port</label>
                    <input
                      type="number"
                      className={`form-input ${samplerPortError ? 'error' : ''}`}
                      placeholder="e.g., 10001"
                      disabled={!enabled}
                      {...register('ldms_configurations.sampler_port')}
                    />
                    {samplerPortError && <span className="error-message">{samplerPortError.message}</span>}
                  </div>
                </div>

                <div>
                  <label className="form-label">Sampler Plugins</label>
                  {samplerPluginFields.length === 0 && (
                    <p className="text-small-muted padding-sm italic">
                      No sampler plugins configured. Click below to add one.
                    </p>
                  )}
                  {samplerPluginFields.map((field, index) => {
                    const pluginNameError = getError(`ldms_configurations.sampler_plugins.${index}.plugin_name`);
                    const activationParamsError = getError(`ldms_configurations.sampler_plugins.${index}.activation_parameters`);
                    const configParamsError = getError(`ldms_configurations.sampler_plugins.${index}.config_parameters`);

                    return (
                    <div key={field.id} className="section-style margin-bottom-sm">
                      <div className="form-row form-row-2-col">
                        <div className="form-group">
                          <label className="form-label">Plugin Name (Required)</label>
                          <input
                            type="text"
                            className={`form-input ${pluginNameError ? 'error' : ''}`}
                            placeholder="e.g., meminfo"
                            disabled={!enabled}
                            {...register(`ldms_configurations.sampler_plugins.${index}.plugin_name`)}
                          />
                          {pluginNameError && <span className="error-message">{pluginNameError.message}</span>}
                        </div>
                        <div className="form-group">
                          <label className="form-label">Activation Parameters (Required)</label>
                          <input
                            type="text"
                            className={`form-input ${activationParamsError ? 'error' : ''}`}
                            placeholder="e.g., interval=30000000 offset=0"
                            disabled={!enabled}
                            {...register(`ldms_configurations.sampler_plugins.${index}.activation_parameters`)}
                          />
                          {activationParamsError && <span className="error-message">{activationParamsError.message}</span>}
                        </div>
                      </div>
                      <div className="form-group">
                        <label className="form-label">Config Parameters</label>
                        <input
                          type="text"
                          className={`form-input ${configParamsError ? 'error' : ''}`}
                          placeholder=""
                          disabled={!enabled}
                          {...register(`ldms_configurations.sampler_plugins.${index}.config_parameters`)}
                        />
                        {configParamsError && <span className="error-message">{configParamsError.message}</span>}
                      </div>
                      <Button variant="secondary" onClick={() => removeSamplerPlugin(index)} disabled={!enabled}>Remove Plugin</Button>
                    </div>
                    );
                  })}
                  <Button variant="primary" onClick={() => appendSamplerPlugin({ plugin_name: 'meminfo', config_parameters: '', activation_parameters: 'interval=30000000' })} disabled={!enabled}>Add Plugin</Button>
                </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};
