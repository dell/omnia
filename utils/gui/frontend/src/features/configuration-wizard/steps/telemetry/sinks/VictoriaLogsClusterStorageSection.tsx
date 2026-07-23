import type { UseFormRegister } from 'react-hook-form';
import { TelemetryConfigStorageFormData } from '../../../schemas/telemetryConfigStorage';
import type { FormFieldError } from '../../../hooks/useFormErrors';

interface VictoriaLogsClusterStorageSectionProps {
  enabled: boolean;
  register: UseFormRegister<TelemetryConfigStorageFormData>;
  getError: (path: string) => FormFieldError | undefined;
}

export const VictoriaLogsClusterStorageSection = ({ enabled, register, getError }: VictoriaLogsClusterStorageSectionProps) => {
  const vlstorageReplicasError = getError('victoria_logs_cluster_storage.vlstorage.replicas');
  const vlstorageCpuReqError = getError('victoria_logs_cluster_storage.vlstorage.resources.requests.cpu');
  const vlstorageMemReqError = getError('victoria_logs_cluster_storage.vlstorage.resources.requests.memory');
  const vlstorageCpuLimError = getError('victoria_logs_cluster_storage.vlstorage.resources.limits.cpu');
  const vlstorageMemLimError = getError('victoria_logs_cluster_storage.vlstorage.resources.limits.memory');
  const vlagentReplicasError = getError('victoria_logs_cluster_storage.vlagent.replicas');
  const vlagentPvcSizeError = getError('victoria_logs_cluster_storage.vlagent.pvc_size');
  const vlagentCpuReqError = getError('victoria_logs_cluster_storage.vlagent.resources.requests.cpu');
  const vlagentMemReqError = getError('victoria_logs_cluster_storage.vlagent.resources.requests.memory');
  const vlagentCpuLimError = getError('victoria_logs_cluster_storage.vlagent.resources.limits.cpu');
  const vlagentMemLimError = getError('victoria_logs_cluster_storage.vlagent.resources.limits.memory');

  return (
    <div className={!enabled ? 'disabled-section' : ''}>
      <div className="form-group">
        <label className="form-label">VictoriaLogs Cluster Storage Resources</label>
        <div className="resource-style">
          <div className="space-y-2">
            <h4 className="subsection-title">VLStorage Resources</h4>
            <div className="form-row form-row-5-col">
              <div className="form-group">
                <label className="form-label">Replicas</label>
                <input type="number" className={`form-input ${vlstorageReplicasError ? 'error' : ''}`} placeholder="e.g., 3" disabled={!enabled} {...register('victoria_logs_cluster_storage.vlstorage.replicas')} />
                {vlstorageReplicasError && <span className="error-message">{vlstorageReplicasError.message}</span>}
              </div>
              <div className="form-group">
                <label className="form-label">CPU Request</label>
                <input type="text" className={`form-input ${vlstorageCpuReqError ? 'error' : ''}`} placeholder="e.g., 100m" disabled={!enabled} {...register('victoria_logs_cluster_storage.vlstorage.resources.requests.cpu')} />
                {vlstorageCpuReqError && <span className="error-message">{vlstorageCpuReqError.message}</span>}
              </div>
              <div className="form-group">
                <label className="form-label">Memory Request</label>
                <input type="text" className={`form-input ${vlstorageMemReqError ? 'error' : ''}`} placeholder="e.g., 512Mi" disabled={!enabled} {...register('victoria_logs_cluster_storage.vlstorage.resources.requests.memory')} />
                {vlstorageMemReqError && <span className="error-message">{vlstorageMemReqError.message}</span>}
              </div>
              <div className="form-group">
                <label className="form-label">CPU Limit</label>
                <input type="text" className={`form-input ${vlstorageCpuLimError ? 'error' : ''}`} placeholder="e.g., 500m" disabled={!enabled} {...register('victoria_logs_cluster_storage.vlstorage.resources.limits.cpu')} />
                {vlstorageCpuLimError && <span className="error-message">{vlstorageCpuLimError.message}</span>}
              </div>
              <div className="form-group">
                <label className="form-label">Memory Limit</label>
                <input type="text" className={`form-input ${vlstorageMemLimError ? 'error' : ''}`} placeholder="e.g., 1Gi" disabled={!enabled} {...register('victoria_logs_cluster_storage.vlstorage.resources.limits.memory')} />
                {vlstorageMemLimError && <span className="error-message">{vlstorageMemLimError.message}</span>}
              </div>
            </div>

            <h4 className="subsection-title-spaced">VLAgent Resources</h4>
            <div className="form-row form-row-5-col">
              <div className="form-group">
                <label className="form-label">Replicas</label>
                <input type="number" className={`form-input ${vlagentReplicasError ? 'error' : ''}`} placeholder="e.g., 2" disabled={!enabled} {...register('victoria_logs_cluster_storage.vlagent.replicas')} />
                {vlagentReplicasError && <span className="error-message">{vlagentReplicasError.message}</span>}
              </div>
              <div className="form-group">
                <label className="form-label">PVC Size</label>
                <input type="text" className={`form-input ${vlagentPvcSizeError ? 'error' : ''}`} placeholder="e.g., 5Gi" disabled={!enabled} {...register('victoria_logs_cluster_storage.vlagent.pvc_size')} />
                {vlagentPvcSizeError && <span className="error-message">{vlagentPvcSizeError.message}</span>}
              </div>
              <div className="form-group">
                <label className="form-label">CPU Request</label>
                <input type="text" className={`form-input ${vlagentCpuReqError ? 'error' : ''}`} placeholder="e.g., 25m" disabled={!enabled} {...register('victoria_logs_cluster_storage.vlagent.resources.requests.cpu')} />
                {vlagentCpuReqError && <span className="error-message">{vlagentCpuReqError.message}</span>}
              </div>
              <div className="form-group">
                <label className="form-label">Memory Request</label>
                <input type="text" className={`form-input ${vlagentMemReqError ? 'error' : ''}`} placeholder="e.g., 64Mi" disabled={!enabled} {...register('victoria_logs_cluster_storage.vlagent.resources.requests.memory')} />
                {vlagentMemReqError && <span className="error-message">{vlagentMemReqError.message}</span>}
              </div>
              <div className="form-group">
                <label className="form-label">CPU Limit</label>
                <input type="text" className={`form-input ${vlagentCpuLimError ? 'error' : ''}`} placeholder="e.g., 100m" disabled={!enabled} {...register('victoria_logs_cluster_storage.vlagent.resources.limits.cpu')} />
                {vlagentCpuLimError && <span className="error-message">{vlagentCpuLimError.message}</span>}
              </div>
            </div>
            <div className="form-row form-row-5-col">
              <div className="form-group">
                <label className="form-label">Memory Limit</label>
                <input type="text" className={`form-input ${vlagentMemLimError ? 'error' : ''}`} placeholder="e.g., 256Mi" disabled={!enabled} {...register('victoria_logs_cluster_storage.vlagent.resources.limits.memory')} />
                {vlagentMemLimError && <span className="error-message">{vlagentMemLimError.message}</span>}
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};
