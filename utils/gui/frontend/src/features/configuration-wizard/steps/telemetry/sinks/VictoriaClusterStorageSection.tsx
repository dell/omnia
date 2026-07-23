import type { UseFormRegister } from 'react-hook-form';
import { TelemetryConfigStorageFormData } from '../../../schemas/telemetryConfigStorage';
import type { FormFieldError } from '../../../hooks/useFormErrors';

interface VictoriaClusterStorageSectionProps {
  enabled: boolean;
  register: UseFormRegister<TelemetryConfigStorageFormData>;
  getError: (path: string) => FormFieldError | undefined;
}

export const VictoriaClusterStorageSection = ({ enabled, register, getError }: VictoriaClusterStorageSectionProps) => {
  const vmstorageReplicasError = getError('victoria_cluster_storage.vmstorage.replicas');
  const vmstorageCpuReqError = getError('victoria_cluster_storage.vmstorage.resources.requests.cpu');
  const vmstorageMemReqError = getError('victoria_cluster_storage.vmstorage.resources.requests.memory');
  const vmstorageCpuLimError = getError('victoria_cluster_storage.vmstorage.resources.limits.cpu');
  const vmstorageMemLimError = getError('victoria_cluster_storage.vmstorage.resources.limits.memory');
  const vmagentReplicasError = getError('victoria_cluster_storage.vmagent.replicas');
  const vmagentCpuReqError = getError('victoria_cluster_storage.vmagent.resources.requests.cpu');
  const vmagentMemReqError = getError('victoria_cluster_storage.vmagent.resources.requests.memory');
  const vmagentCpuLimError = getError('victoria_cluster_storage.vmagent.resources.limits.cpu');
  const vmagentMemLimError = getError('victoria_cluster_storage.vmagent.resources.limits.memory');

  return (
    <div className={!enabled ? 'disabled-section' : ''}>
      <div className="form-group">
        <label className="form-label">Victoria Cluster Storage Resources</label>
        <div className="resource-style">
          <div className="space-y-2">
            <h4 className="subsection-title">VMStorage Resources</h4>
            <div className="form-row form-row-5-col">
              <div className="form-group">
                <label className="form-label">Replicas</label>
                <input type="number" className={`form-input ${vmstorageReplicasError ? 'error' : ''}`} placeholder="e.g., 3" disabled={!enabled} {...register('victoria_cluster_storage.vmstorage.replicas')} />
                {vmstorageReplicasError && <span className="error-message">{vmstorageReplicasError.message}</span>}
              </div>
              <div className="form-group">
                <label className="form-label">CPU Request</label>
                <input type="text" className={`form-input ${vmstorageCpuReqError ? 'error' : ''}`} placeholder="e.g., 250m" disabled={!enabled} {...register('victoria_cluster_storage.vmstorage.resources.requests.cpu')} />
                {vmstorageCpuReqError && <span className="error-message">{vmstorageCpuReqError.message}</span>}
              </div>
              <div className="form-group">
                <label className="form-label">Memory Request</label>
                <input type="text" className={`form-input ${vmstorageMemReqError ? 'error' : ''}`} placeholder="e.g., 1Gi" disabled={!enabled} {...register('victoria_cluster_storage.vmstorage.resources.requests.memory')} />
                {vmstorageMemReqError && <span className="error-message">{vmstorageMemReqError.message}</span>}
              </div>
              <div className="form-group">
                <label className="form-label">CPU Limit</label>
                <input type="text" className={`form-input ${vmstorageCpuLimError ? 'error' : ''}`} placeholder="e.g., 1000m" disabled={!enabled} {...register('victoria_cluster_storage.vmstorage.resources.limits.cpu')} />
                {vmstorageCpuLimError && <span className="error-message">{vmstorageCpuLimError.message}</span>}
              </div>
              <div className="form-group">
                <label className="form-label">Memory Limit</label>
                <input type="text" className={`form-input ${vmstorageMemLimError ? 'error' : ''}`} placeholder="e.g., 2Gi" disabled={!enabled} {...register('victoria_cluster_storage.vmstorage.resources.limits.memory')} />
                {vmstorageMemLimError && <span className="error-message">{vmstorageMemLimError.message}</span>}
              </div>
            </div>

            <h4 className="subsection-title-spaced">VMAgent Resources</h4>
            <div className="form-row form-row-5-col">
              <div className="form-group">
                <label className="form-label">Replicas</label>
                <input type="number" className={`form-input ${vmagentReplicasError ? 'error' : ''}`} placeholder="e.g., 2" disabled={!enabled} {...register('victoria_cluster_storage.vmagent.replicas')} />
                {vmagentReplicasError && <span className="error-message">{vmagentReplicasError.message}</span>}
              </div>
              <div className="form-group">
                <label className="form-label">CPU Request</label>
                <input type="text" className={`form-input ${vmagentCpuReqError ? 'error' : ''}`} placeholder="e.g., 50m" disabled={!enabled} {...register('victoria_cluster_storage.vmagent.resources.requests.cpu')} />
                {vmagentCpuReqError && <span className="error-message">{vmagentCpuReqError.message}</span>}
              </div>
              <div className="form-group">
                <label className="form-label">Memory Request</label>
                <input type="text" className={`form-input ${vmagentMemReqError ? 'error' : ''}`} placeholder="e.g., 128Mi" disabled={!enabled} {...register('victoria_cluster_storage.vmagent.resources.requests.memory')} />
                {vmagentMemReqError && <span className="error-message">{vmagentMemReqError.message}</span>}
              </div>
              <div className="form-group">
                <label className="form-label">CPU Limit</label>
                <input type="text" className={`form-input ${vmagentCpuLimError ? 'error' : ''}`} placeholder="e.g., 250m" disabled={!enabled} {...register('victoria_cluster_storage.vmagent.resources.limits.cpu')} />
                {vmagentCpuLimError && <span className="error-message">{vmagentCpuLimError.message}</span>}
              </div>
              <div className="form-group">
                <label className="form-label">Memory Limit</label>
                <input type="text" className={`form-input ${vmagentMemLimError ? 'error' : ''}`} placeholder="e.g., 512Mi" disabled={!enabled} {...register('victoria_cluster_storage.vmagent.resources.limits.memory')} />
                {vmagentMemLimError && <span className="error-message">{vmagentMemLimError.message}</span>}
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};
