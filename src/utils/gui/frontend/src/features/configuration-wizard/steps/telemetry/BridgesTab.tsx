import { UseFormRegister, FieldErrors } from 'react-hook-form';
import { TelemetryConfigStorageFormData } from '../../schemas/telemetryConfigStorage';
import { useFormErrors } from '../../hooks/useFormErrors';
import type { ValidationError } from '../../utils/l2Validation';

interface BridgesTabProps {
  register: UseFormRegister<TelemetryConfigStorageFormData>;
  errors: FieldErrors<TelemetryConfigStorageFormData>;
  needsVectorLdms?: boolean;
  needsVectorOmeMetrics?: boolean;
  needsVectorOmeLogs?: boolean;
  validationErrors?: ValidationError[];
}

export const BridgesTab = ({ register, errors, needsVectorLdms, needsVectorOmeMetrics, needsVectorOmeLogs, validationErrors }: BridgesTabProps) => {
  const getError = useFormErrors(errors, validationErrors);

  const omeIdentifierError = getError('telemetry_bridges.vector_ome.ome_identifier');
  const ldmsReplicasError = getError('vector_storage.ldms.replicas');
  const ldmsCpuReqError = getError('vector_storage.ldms.resources.requests.cpu');
  const ldmsMemReqError = getError('vector_storage.ldms.resources.requests.memory');
  const ldmsCpuLimError = getError('vector_storage.ldms.resources.limits.cpu');
  const ldmsMemLimError = getError('vector_storage.ldms.resources.limits.memory');
  const omeReplicasError = getError('vector_storage.ome.replicas');
  const omeCpuReqError = getError('vector_storage.ome.resources.requests.cpu');
  const omeMemReqError = getError('vector_storage.ome.resources.requests.memory');
  const omeCpuLimError = getError('vector_storage.ome.resources.limits.cpu');
  const omeMemLimError = getError('vector_storage.ome.resources.limits.memory');
  const vmagentReplicasError = getError('vector_storage.vmagent_vector.replicas');
  const vmagentPvcSizeError = getError('vector_storage.vmagent_vector.pvc_size');
  const vmagentCpuReqError = getError('vector_storage.vmagent_vector.resources.requests.cpu');
  const vmagentMemReqError = getError('vector_storage.vmagent_vector.resources.requests.memory');
  const vmagentCpuLimError = getError('vector_storage.vmagent_vector.resources.limits.cpu');
  const vmagentMemLimError = getError('vector_storage.vmagent_vector.resources.limits.memory');
  const vlagentReplicasError = getError('vector_storage.vlagent_vector.replicas');
  const vlagentPvcSizeError = getError('vector_storage.vlagent_vector.pvc_size');
  const vlagentCpuReqError = getError('vector_storage.vlagent_vector.resources.requests.cpu');
  const vlagentMemReqError = getError('vector_storage.vlagent_vector.resources.requests.memory');
  const vlagentCpuLimError = getError('vector_storage.vlagent_vector.resources.limits.cpu');
  const vlagentMemLimError = getError('vector_storage.vlagent_vector.resources.limits.memory');

  return (
    <div className="space-y-6">
      <div className="form-group">
        <label className="form-label">Telemetry Bridges Configuration</label>
        {!needsVectorLdms && !(needsVectorOmeMetrics || needsVectorOmeLogs) && (
          <p className="text-small-muted">Bridges configuration is not needed. Enable LDMS or OME with Kafka collection target to configure bridges.</p>
        )}
        <div className="section-style">
          <div className="space-y-2">
            <div className={!needsVectorLdms ? 'disabled-section' : ''}>
              <div className="form-group">
                <label className="form-label">Vector-LDMS Bridge</label>
                <div className="form-checkbox">
                  <input
                    id="telemetry_bridges.vector_ldms.metrics_enabled"
                    type="checkbox"
                    disabled={!needsVectorLdms}
                    {...register('telemetry_bridges.vector_ldms.metrics_enabled')}
                  />
                  <label htmlFor="telemetry_bridges.vector_ldms.metrics_enabled">
                    Enable routing LDMS data from Kafka to Victoria Metrics
                  </label>
                </div>
              </div>
            </div>

            <div className={!(needsVectorOmeMetrics || needsVectorOmeLogs) ? 'disabled-section' : ''}>
              <div className="form-group">
                <label className="form-label">Vector-OME Bridge</label>
                <div className="form-checkbox">
                  <input
                    id="telemetry_bridges.vector_ome.metrics_enabled"
                    type="checkbox"
                    disabled={!(needsVectorOmeMetrics || needsVectorOmeLogs)}
                    {...register('telemetry_bridges.vector_ome.metrics_enabled')}
                  />
                  <label htmlFor="telemetry_bridges.vector_ome.metrics_enabled">
                    Enable routing OME metrics from Kafka to Victoria Metrics
                  </label>
                </div>
                <div className="form-checkbox">
                  <input
                    id="telemetry_bridges.vector_ome.logs_enabled"
                    type="checkbox"
                    disabled={!(needsVectorOmeMetrics || needsVectorOmeLogs)}
                    {...register('telemetry_bridges.vector_ome.logs_enabled')}
                  />
                  <label htmlFor="telemetry_bridges.vector_ome.logs_enabled">
                    Enable routing OME logs from Kafka to Victoria Logs
                  </label>
                </div>
                <div>
                  <label className="form-label">OME Identifier</label>
                  <input
                    type="text"
                    className={`form-input ${omeIdentifierError ? 'error' : ''}`}
                    placeholder="ome"
                    disabled={!(needsVectorOmeMetrics || needsVectorOmeLogs)}
                    {...register('telemetry_bridges.vector_ome.ome_identifier')}
                  />
                  {omeIdentifierError && <span className="error-message">{omeIdentifierError.message}</span>}
                </div>
              </div>
            </div>

          </div>
        </div>
      </div>

        <div className="form-group">
          <label className="form-label">Vector Storage Resources</label>
          <div className="resource-style">
            <div className="space-y-2">
              <div className={!needsVectorLdms ? 'disabled-section' : ''}>
                  <h4 className="subsection-title">Vector-LDMS Resources</h4>
                  <div className="form-row form-row-5-col">
                    <div className="form-group">
                      <label className="form-label">Replicas</label>
                      <input
                        type="number"
                        className={`form-input ${ldmsReplicasError ? 'error' : ''}`}
                        placeholder="e.g., 2"
                        disabled={!needsVectorLdms}
                        {...register('vector_storage.ldms.replicas')}
                      />
                      {ldmsReplicasError && <span className="error-message">{ldmsReplicasError.message}</span>}
                    </div>
                    <div className="form-group">
                      <label className="form-label">CPU Request</label>
                      <input
                        type="text"
                        className={`form-input ${ldmsCpuReqError ? 'error' : ''}`}
                        placeholder="e.g., 50m"
                        disabled={!needsVectorLdms}
                        {...register('vector_storage.ldms.resources.requests.cpu')}
                      />
                      {ldmsCpuReqError && <span className="error-message">{ldmsCpuReqError.message}</span>}
                    </div>
                    <div className="form-group">
                      <label className="form-label">Memory Request</label>
                      <input
                        type="text"
                        className={`form-input ${ldmsMemReqError ? 'error' : ''}`}
                        placeholder="e.g., 128Mi"
                        disabled={!needsVectorLdms}
                        {...register('vector_storage.ldms.resources.requests.memory')}
                      />
                      {ldmsMemReqError && <span className="error-message">{ldmsMemReqError.message}</span>}
                    </div>
                    <div className="form-group">
                      <label className="form-label">CPU Limit</label>
                      <input
                        type="text"
                        className={`form-input ${ldmsCpuLimError ? 'error' : ''}`}
                        placeholder="e.g., 250m"
                        disabled={!needsVectorLdms}
                        {...register('vector_storage.ldms.resources.limits.cpu')}
                      />
                      {ldmsCpuLimError && <span className="error-message">{ldmsCpuLimError.message}</span>}
                    </div>
                    <div className="form-group">
                      <label className="form-label">Memory Limit</label>
                      <input
                        type="text"
                        className={`form-input ${ldmsMemLimError ? 'error' : ''}`}
                        placeholder="e.g., 256Mi"
                        disabled={!needsVectorLdms}
                        {...register('vector_storage.ldms.resources.limits.memory')}
                      />
                      {ldmsMemLimError && <span className="error-message">{ldmsMemLimError.message}</span>}
                    </div>
                  </div>
              </div>

              <div className={!(needsVectorOmeMetrics || needsVectorOmeLogs) ? 'disabled-section' : ''}>
                  <h4 className="subsection-title-spaced">Vector-OME Resources</h4>
                  <div className="form-row form-row-5-col">
                    <div className="form-group">
                      <label className="form-label">Replicas</label>
                      <input
                        type="number"
                        className={`form-input ${omeReplicasError ? 'error' : ''}`}
                        placeholder="e.g., 2"
                        disabled={!(needsVectorOmeMetrics || needsVectorOmeLogs)}
                        {...register('vector_storage.ome.replicas')}
                      />
                      {omeReplicasError && <span className="error-message">{omeReplicasError.message}</span>}
                    </div>
                    <div className="form-group">
                      <label className="form-label">CPU Request</label>
                      <input
                        type="text"
                        className={`form-input ${omeCpuReqError ? 'error' : ''}`}
                        placeholder="e.g., 100m"
                        disabled={!(needsVectorOmeMetrics || needsVectorOmeLogs)}
                        {...register('vector_storage.ome.resources.requests.cpu')}
                      />
                      {omeCpuReqError && <span className="error-message">{omeCpuReqError.message}</span>}
                    </div>
                    <div className="form-group">
                      <label className="form-label">Memory Request</label>
                      <input
                        type="text"
                        className={`form-input ${omeMemReqError ? 'error' : ''}`}
                        placeholder="e.g., 256Mi"
                        disabled={!(needsVectorOmeMetrics || needsVectorOmeLogs)}
                        {...register('vector_storage.ome.resources.requests.memory')}
                      />
                      {omeMemReqError && <span className="error-message">{omeMemReqError.message}</span>}
                    </div>
                    <div className="form-group">
                      <label className="form-label">CPU Limit</label>
                      <input
                        type="text"
                        className={`form-input ${omeCpuLimError ? 'error' : ''}`}
                        placeholder="e.g., 500m"
                        disabled={!(needsVectorOmeMetrics || needsVectorOmeLogs)}
                        {...register('vector_storage.ome.resources.limits.cpu')}
                      />
                      {omeCpuLimError && <span className="error-message">{omeCpuLimError.message}</span>}
                    </div>
                    <div className="form-group">
                      <label className="form-label">Memory Limit</label>
                      <input
                        type="text"
                        className={`form-input ${omeMemLimError ? 'error' : ''}`}
                        placeholder="e.g., 512Mi"
                        disabled={!(needsVectorOmeMetrics || needsVectorOmeLogs)}
                        {...register('vector_storage.ome.resources.limits.memory')}
                      />
                      {omeMemLimError && <span className="error-message">{omeMemLimError.message}</span>}
                    </div>
                  </div>
              </div>

              <div className={!(needsVectorLdms || needsVectorOmeMetrics) ? 'disabled-section' : ''}>
                  <h4 className="subsection-title-spaced">VMAgent-Vector Resources</h4>
                  <div className="form-row form-row-6-col">
                    <div className="form-group">
                      <label className="form-label">Replicas</label>
                      <input
                        type="number"
                        className={`form-input ${vmagentReplicasError ? 'error' : ''}`}
                        placeholder="e.g., 2"
                        disabled={!(needsVectorLdms || needsVectorOmeMetrics)}
                        {...register('vector_storage.vmagent_vector.replicas')}
                      />
                      {vmagentReplicasError && <span className="error-message">{vmagentReplicasError.message}</span>}
                    </div>
                    <div className="form-group">
                      <label className="form-label">PVC Size</label>
                      <input
                        type="text"
                        className={`form-input ${vmagentPvcSizeError ? 'error' : ''}`}
                        placeholder="e.g., 5Gi"
                        disabled={!(needsVectorLdms || needsVectorOmeMetrics)}
                        {...register('vector_storage.vmagent_vector.pvc_size')}
                      />
                      {vmagentPvcSizeError && <span className="error-message">{vmagentPvcSizeError.message}</span>}
                    </div>
                    <div className="form-group">
                      <label className="form-label">CPU Request</label>
                      <input
                        type="text"
                        className={`form-input ${vmagentCpuReqError ? 'error' : ''}`}
                        placeholder="e.g., 50m"
                        disabled={!(needsVectorLdms || needsVectorOmeMetrics)}
                        {...register('vector_storage.vmagent_vector.resources.requests.cpu')}
                      />
                      {vmagentCpuReqError && <span className="error-message">{vmagentCpuReqError.message}</span>}
                    </div>
                    <div className="form-group">
                      <label className="form-label">Memory Request</label>
                      <input
                        type="text"
                        className={`form-input ${vmagentMemReqError ? 'error' : ''}`}
                        placeholder="e.g., 128Mi"
                        disabled={!(needsVectorLdms || needsVectorOmeMetrics)}
                        {...register('vector_storage.vmagent_vector.resources.requests.memory')}
                      />
                      {vmagentMemReqError && <span className="error-message">{vmagentMemReqError.message}</span>}
                    </div>
                    <div className="form-group">
                      <label className="form-label">CPU Limit</label>
                      <input
                        type="text"
                        className={`form-input ${vmagentCpuLimError ? 'error' : ''}`}
                        placeholder="e.g., 250m"
                        disabled={!(needsVectorLdms || needsVectorOmeMetrics)}
                        {...register('vector_storage.vmagent_vector.resources.limits.cpu')}
                      />
                      {vmagentCpuLimError && <span className="error-message">{vmagentCpuLimError.message}</span>}
                    </div>
                    <div className="form-group">
                      <label className="form-label">Memory Limit</label>
                      <input
                        type="text"
                        className={`form-input ${vmagentMemLimError ? 'error' : ''}`}
                        placeholder="e.g., 256Mi"
                        disabled={!(needsVectorLdms || needsVectorOmeMetrics)}
                        {...register('vector_storage.vmagent_vector.resources.limits.memory')}
                      />
                      {vmagentMemLimError && <span className="error-message">{vmagentMemLimError.message}</span>}
                    </div>
                  </div>
              </div>

              <div className={!needsVectorOmeLogs ? 'disabled-section' : ''}>
                  <h4 className="subsection-title-spaced">VLAgent-Vector Resources</h4>
                  <div className="form-row form-row-6-col">
                    <div className="form-group">
                      <label className="form-label">Replicas</label>
                      <input
                        type="number"
                        className={`form-input ${vlagentReplicasError ? 'error' : ''}`}
                        placeholder="e.g., 2"
                        disabled={!needsVectorOmeLogs}
                        {...register('vector_storage.vlagent_vector.replicas')}
                      />
                      {vlagentReplicasError && <span className="error-message">{vlagentReplicasError.message}</span>}
                    </div>
                    <div className="form-group">
                      <label className="form-label">PVC Size</label>
                      <input
                        type="text"
                        className={`form-input ${vlagentPvcSizeError ? 'error' : ''}`}
                        placeholder="e.g., 5Gi"
                        disabled={!needsVectorOmeLogs}
                        {...register('vector_storage.vlagent_vector.pvc_size')}
                      />
                      {vlagentPvcSizeError && <span className="error-message">{vlagentPvcSizeError.message}</span>}
                    </div>
                    <div className="form-group">
                      <label className="form-label">CPU Request</label>
                      <input
                        type="text"
                        className={`form-input ${vlagentCpuReqError ? 'error' : ''}`}
                        placeholder="e.g., 50m"
                        disabled={!needsVectorOmeLogs}
                        {...register('vector_storage.vlagent_vector.resources.requests.cpu')}
                      />
                      {vlagentCpuReqError && <span className="error-message">{vlagentCpuReqError.message}</span>}
                    </div>
                    <div className="form-group">
                      <label className="form-label">Memory Request</label>
                      <input
                        type="text"
                        className={`form-input ${vlagentMemReqError ? 'error' : ''}`}
                        placeholder="e.g., 128Mi"
                        disabled={!needsVectorOmeLogs}
                        {...register('vector_storage.vlagent_vector.resources.requests.memory')}
                      />
                      {vlagentMemReqError && <span className="error-message">{vlagentMemReqError.message}</span>}
                    </div>
                    <div className="form-group">
                      <label className="form-label">CPU Limit</label>
                      <input
                        type="text"
                        className={`form-input ${vlagentCpuLimError ? 'error' : ''}`}
                        placeholder="e.g., 250m"
                        disabled={!needsVectorOmeLogs}
                        {...register('vector_storage.vlagent_vector.resources.limits.cpu')}
                      />
                      {vlagentCpuLimError && <span className="error-message">{vlagentCpuLimError.message}</span>}
                    </div>
                    <div className="form-group">
                      <label className="form-label">Memory Limit</label>
                      <input
                        type="text"
                        className={`form-input ${vlagentMemLimError ? 'error' : ''}`}
                        placeholder="e.g., 256Mi"
                        disabled={!needsVectorOmeLogs}
                        {...register('vector_storage.vlagent_vector.resources.limits.memory')}
                      />
                      {vlagentMemLimError && <span className="error-message">{vlagentMemLimError.message}</span>}
                    </div>
                  </div>
              </div>
            </div>
          </div>
        </div>
    </div>
  );
};
