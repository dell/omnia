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
import type { UseFormRegister } from 'react-hook-form';
import { TelemetryConfigStorageFormData } from '../../../schemas/telemetryConfigStorage';
import type { FormFieldError } from '../../../hooks/useFormErrors';

interface KafkaConfigurationSectionProps {
  enabled: boolean;
  register: UseFormRegister<TelemetryConfigStorageFormData>;
  getError: (path: string) => FormFieldError | undefined;
}

export const KafkaConfigurationSection = ({ enabled, register, getError }: KafkaConfigurationSectionProps) => {
  const persistenceSizeError = getError('telemetry_sinks.kafka.persistence_size');
  const logRetentionHoursError = getError('telemetry_sinks.kafka.log_retention_hours');
  const logRetentionBytesError = getError('telemetry_sinks.kafka.log_retention_bytes');
  const logSegmentBytesError = getError('telemetry_sinks.kafka.log_segment_bytes');
  const topicPartitionsIdracError = getError('telemetry_sinks.kafka.topic_partitions.idrac');
  const topicPartitionsLdmsError = getError('telemetry_sinks.kafka.topic_partitions.ldms');

  return (
    <div className={!enabled ? 'disabled-section' : ''}>
      <div className="form-group">
        <label className="form-label">Kafka Configuration</label>
        <div className="section-style">
          <div className="space-y-2">
            <div className="form-row">
              <div className="form-group">
                <label className="form-label">Persistence Size</label>
                <input
                  type="text"
                  className={`form-input ${persistenceSizeError ? 'error' : ''}`}
                  placeholder="e.g., 8Gi"
                  disabled={!enabled}
                  {...register('telemetry_sinks.kafka.persistence_size')}
                />
                {persistenceSizeError && <span className="error-message">{persistenceSizeError.message}</span>}
              </div>
              <div className="form-group">
                <label className="form-label">Log Retention Hours</label>
                <input
                  type="number"
                  className={`form-input ${logRetentionHoursError ? 'error' : ''}`}
                  placeholder="e.g., 168"
                  disabled={!enabled}
                  {...register('telemetry_sinks.kafka.log_retention_hours')}
                />
                {logRetentionHoursError && <span className="error-message">{logRetentionHoursError.message}</span>}
              </div>
              <div className="form-group">
                <label className="form-label">Log Retention Bytes (Default: -1 for unlimited)</label>
                <input
                  type="number"
                  className={`form-input ${logRetentionBytesError ? 'error' : ''}`}
                  placeholder="e.g., -1"
                  disabled={!enabled}
                  {...register('telemetry_sinks.kafka.log_retention_bytes')}
                />
                {logRetentionBytesError && <span className="error-message">{logRetentionBytesError.message}</span>}
              </div>
            </div>
            <div className="form-row">
              <div className="form-group">
                <label className="form-label">Log Segment Bytes (Default: 1073741824)</label>
                <input
                  type="number"
                  className={`form-input ${logSegmentBytesError ? 'error' : ''}`}
                  placeholder="e.g., 1073741824"
                  disabled={!enabled}
                  {...register('telemetry_sinks.kafka.log_segment_bytes')}
                />
                {logSegmentBytesError && <span className="error-message">{logSegmentBytesError.message}</span>}
              </div>
              <div className="form-group">
                <label className="form-label">Topic Partitions - IDRAC (Default: 1)</label>
                <input
                  type="number"
                  className={`form-input ${topicPartitionsIdracError ? 'error' : ''}`}
                  placeholder="e.g., 1"
                  disabled={!enabled}
                  {...register('telemetry_sinks.kafka.topic_partitions.idrac')}
                />
                {topicPartitionsIdracError && <span className="error-message">{topicPartitionsIdracError.message}</span>}
              </div>
              <div className="form-group">
                <label className="form-label">Topic Partitions - LDMS (Default: 2)</label>
                <input
                  type="number"
                  className={`form-input ${topicPartitionsLdmsError ? 'error' : ''}`}
                  placeholder="e.g., 2"
                  disabled={!enabled}
                  {...register('telemetry_sinks.kafka.topic_partitions.ldms')}
                />
                {topicPartitionsLdmsError && <span className="error-message">{topicPartitionsLdmsError.message}</span>}
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};
