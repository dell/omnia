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

interface KafkaStorageResourcesSectionProps {
  enabled: boolean;
  register: UseFormRegister<TelemetryConfigStorageFormData>;
  getError: (path: string) => FormFieldError | undefined;
}

export const KafkaStorageResourcesSection = ({ enabled, register, getError }: KafkaStorageResourcesSectionProps) => {
  const kafkaCpuReqError = getError('kafka_storage.kafka.resources.requests.cpu');
  const kafkaMemReqError = getError('kafka_storage.kafka.resources.requests.memory');
  const kafkaCpuLimError = getError('kafka_storage.kafka.resources.limits.cpu');
  const kafkaMemLimError = getError('kafka_storage.kafka.resources.limits.memory');
  const entityOpCpuReqError = getError('kafka_storage.entity_operator.user_operator.resources.requests.cpu');
  const entityOpMemReqError = getError('kafka_storage.entity_operator.user_operator.resources.requests.memory');
  const entityOpCpuLimError = getError('kafka_storage.entity_operator.user_operator.resources.limits.cpu');
  const entityOpMemLimError = getError('kafka_storage.entity_operator.user_operator.resources.limits.memory');

  return (
    <div className={!enabled ? 'disabled-section' : ''}>
      <div className="form-group">
        <label className="form-label">Kafka Storage Resources</label>
        <div className="resource-style">
          <div className="space-y-2">
            <h4 className="subsection-title">Kafka Resources</h4>
            <div className="grid-4-col">
              <div className="form-group">
                <label className="form-label">CPU Request</label>
                <input type="text" className={`form-input ${kafkaCpuReqError ? 'error' : ''}`} placeholder="e.g., 200m" disabled={!enabled} {...register('kafka_storage.kafka.resources.requests.cpu')} />
                {kafkaCpuReqError && <span className="error-message">{kafkaCpuReqError.message}</span>}
              </div>
              <div className="form-group">
                <label className="form-label">Memory Request</label>
                <input type="text" className={`form-input ${kafkaMemReqError ? 'error' : ''}`} placeholder="e.g., 512Mi" disabled={!enabled} {...register('kafka_storage.kafka.resources.requests.memory')} />
                {kafkaMemReqError && <span className="error-message">{kafkaMemReqError.message}</span>}
              </div>
              <div className="form-group">
                <label className="form-label">CPU Limit</label>
                <input type="text" className={`form-input ${kafkaCpuLimError ? 'error' : ''}`} placeholder="e.g., 1000m" disabled={!enabled} {...register('kafka_storage.kafka.resources.limits.cpu')} />
                {kafkaCpuLimError && <span className="error-message">{kafkaCpuLimError.message}</span>}
              </div>
              <div className="form-group">
                <label className="form-label">Memory Limit</label>
                <input type="text" className={`form-input ${kafkaMemLimError ? 'error' : ''}`} placeholder="e.g., 1Gi" disabled={!enabled} {...register('kafka_storage.kafka.resources.limits.memory')} />
                {kafkaMemLimError && <span className="error-message">{kafkaMemLimError.message}</span>}
              </div>
            </div>

            <h4 className="subsection-title-spaced">Entity Operator - User Operator Resources</h4>
            <div className="grid-4-col">
              <div className="form-group">
                <label className="form-label">CPU Request</label>
                <input type="text" className={`form-input ${entityOpCpuReqError ? 'error' : ''}`} placeholder="e.g., 200m" disabled={!enabled} {...register('kafka_storage.entity_operator.user_operator.resources.requests.cpu')} />
                {entityOpCpuReqError && <span className="error-message">{entityOpCpuReqError.message}</span>}
              </div>
              <div className="form-group">
                <label className="form-label">Memory Request</label>
                <input type="text" className={`form-input ${entityOpMemReqError ? 'error' : ''}`} placeholder="e.g., 512Mi" disabled={!enabled} {...register('kafka_storage.entity_operator.user_operator.resources.requests.memory')} />
                {entityOpMemReqError && <span className="error-message">{entityOpMemReqError.message}</span>}
              </div>
              <div className="form-group">
                <label className="form-label">CPU Limit</label>
                <input type="text" className={`form-input ${entityOpCpuLimError ? 'error' : ''}`} placeholder="e.g., 1000m" disabled={!enabled} {...register('kafka_storage.entity_operator.user_operator.resources.limits.cpu')} />
                {entityOpCpuLimError && <span className="error-message">{entityOpCpuLimError.message}</span>}
              </div>
              <div className="form-group">
                <label className="form-label">Memory Limit</label>
                <input type="text" className={`form-input ${entityOpMemLimError ? 'error' : ''}`} placeholder="e.g., 512Mi" disabled={!enabled} {...register('kafka_storage.entity_operator.user_operator.resources.limits.memory')} />
                {entityOpMemLimError && <span className="error-message">{entityOpMemLimError.message}</span>}
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};
