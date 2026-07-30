// Copyright 2026 Dell Inc. or its subsidiaries. All Rights Reserved.
//
// Licensed under the Apache License, Version 2.0 (the "License");
// you may not use this file except in compliance with the License.
// You may obtain a copy of the License at
//
//     http://www.apache.org/licenses/LICENSE-2.0
//
// Unless required by applicable law or agreed to in writing, software
// distributed under the License is distributed on an "AS IS" BASIS,
// WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
// See the License for the specific language governing permissions and
// limitations under the License.
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
