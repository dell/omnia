import { Controller, UseFormRegister, Control } from 'react-hook-form';
import { TelemetryConfigStorageFormData } from '../../schemas/telemetryConfigStorage';

interface OmeTabProps {
  register: UseFormRegister<TelemetryConfigStorageFormData>;
  control: Control<TelemetryConfigStorageFormData>;
  enabled?: boolean;
}

export const OmeTab = ({ register, control, enabled }: OmeTabProps) => {
  return (
    <div className="space-y-6">
      <div className="form-group">
        <label className="form-label">OME Telemetry Configuration</label>
        <div className="section-style">
          <div className="space-y-2">
            <div className="form-group">
              <label className="form-label">Enable Metrics Collection</label>
            </div>

            <div className="form-checkbox">
              <input
                id="telemetry_sources.ome.logs_enabled"
                type="checkbox"
                {...register('telemetry_sources.ome.logs_enabled')}
              />
              <label htmlFor="telemetry_sources.ome.logs_enabled">
                Enable OME logs collection
              </label>
            </div>

            <div className="form-checkbox">
              <Controller
                control={control}
                name="telemetry_sources.ome.collection_targets"
                render={({ field }) => (
                  <>
                    <input
                      id="ome-collection-kafka"
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
                    <label htmlFor="ome-collection-kafka">Kafka (required for OME)</label>
                  </>
                )}
              />
            </div>

            <div className={!enabled ? 'disabled-section' : ''}>
              <div className="form-group">
                <label className="form-label">OME Configuration</label>
                <p className="text-small-muted">OME is enabled with Kafka collection target. Additional configuration fields will appear here as needed.</p>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};
