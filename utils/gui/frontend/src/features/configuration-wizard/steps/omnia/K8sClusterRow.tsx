import { UseFormRegister, FieldErrors } from 'react-hook-form';
import Button from '../../../../components/Button';
import { OmniaHaDiscoveryFormData } from '../../schemas/omniaHaDiscoveryConfig';
import { useFormErrors } from '../../hooks/useFormErrors';
import type { ValidationError } from '../../utils/l2Validation';

interface K8sClusterRowProps {
  index: number;
  register: UseFormRegister<OmniaHaDiscoveryFormData>;
  errors: FieldErrors<OmniaHaDiscoveryFormData>;
  remove: () => void;
  canRemove: boolean;
  onDeploymentChange?: (checked: boolean) => void;
  validationErrors?: ValidationError[];
}

export const K8sClusterRow = ({ index, register, errors, remove, canRemove, onDeploymentChange, validationErrors }: K8sClusterRowProps) => {
  const getError = useFormErrors(errors, validationErrors);
  const clusterNameError = getError(`service_k8s_cluster.${index}.cluster_name`);
  const deploymentError = getError(`service_k8s_cluster.${index}.deployment`);
  const k8sCniError = getError(`service_k8s_cluster.${index}.k8s_cni`);
  const podExternalIpError = getError(`service_k8s_cluster.${index}.pod_external_ip_range`);
  const k8sServiceAddressesError = getError(`service_k8s_cluster.${index}.k8s_service_addresses`);
  const k8sPodNetworkCidrError = getError(`service_k8s_cluster.${index}.k8s_pod_network_cidr`);
  const nfsStorageNameError = getError(`service_k8s_cluster.${index}.nfs_storage_name`);
  const k8sCrioStorageSizeError = getError(`service_k8s_cluster.${index}.k8s_crio_storage_size`);
  const csiSecretFilePathError = getError(`service_k8s_cluster.${index}.csi_powerscale_driver_secret_file_path`);
  const csiValuesFilePathError = getError(`service_k8s_cluster.${index}.csi_powerscale_driver_values_file_path`);

  return (
    <div className="space-y-2 section-style">
      <div className="form-row">
        <div className="form-group">
          <label className="form-label">Kubernetes Cluster Name (Required)</label>
          <input
            type="text"
            className={`form-input ${clusterNameError ? 'error' : ''}`}
            placeholder="e.g., service_cluster"
            {...register(`service_k8s_cluster.${index}.cluster_name`)}
          />
          {clusterNameError && <span className="error-message">{clusterNameError.message}</span>}
        </div>
        <div className="form-group">
          <label className="form-label">Deployment (Required)</label>
          <select
            className={`form-select ${deploymentError ? 'error' : ''}`}
            {...register(`service_k8s_cluster.${index}.deployment`)}
            onChange={(e) => {
              onDeploymentChange?.(e.target.value === 'true');
            }}
          >
            <option value="false">Disabled</option>
            <option value="true">Enabled</option>
          </select>
          <p className="text-sm text-gray-600 mt-1">Exactly one cluster must have deployment enabled</p>
          {deploymentError && <span className="error-message">{deploymentError.message}</span>}
        </div>
        <div className="form-group">
          <label className="form-label">CNI Plugin (Required)</label>
          <select
            className={`form-select ${k8sCniError ? 'error' : ''}`}
            {...register(`service_k8s_cluster.${index}.k8s_cni`)}
          >
            <option value="">Select CNI</option>
            <option value="calico">calico</option>
            <option value="flannel">flannel</option>
          </select>
          <p className="text-sm text-gray-600 mt-1">Default: calico</p>
          {k8sCniError && <span className="error-message">{k8sCniError.message}</span>}
        </div>
      </div>
      <div className="form-row">
        <div className="form-group">
          <label className="form-label">Pod External IP Range (Required)</label>
          <input
            type="text"
            className={`form-input ${podExternalIpError ? 'error' : ''}`}
            placeholder="e.g., 172.16.107.170-172.16.107.200"
            {...register(`service_k8s_cluster.${index}.pod_external_ip_range`)}
          />
          {podExternalIpError && <span className="error-message">{podExternalIpError.message}</span>}
        </div>
        <div className="form-group">
          <label className="form-label">Service Addresses (Optional)</label>
          <input
            type="text"
            className={`form-input ${k8sServiceAddressesError ? 'error' : ''}`}
            placeholder="e.g., 10.233.0.0/18"
            {...register(`service_k8s_cluster.${index}.k8s_service_addresses`)}
          />
          <p className="text-sm text-gray-600 mt-1">Default: 10.233.0.0/18</p>
          {k8sServiceAddressesError && <span className="error-message">{k8sServiceAddressesError.message}</span>}
        </div>
        <div className="form-group">
          <label className="form-label">Pod Network CIDR (Optional)</label>
          <input
            type="text"
            className={`form-input ${k8sPodNetworkCidrError ? 'error' : ''}`}
            placeholder="e.g., 10.233.64.0/18"
            {...register(`service_k8s_cluster.${index}.k8s_pod_network_cidr`)}
          />
          <p className="text-sm text-gray-600 mt-1">Default: 10.233.64.0/18</p>
          {k8sPodNetworkCidrError && <span className="error-message">{k8sPodNetworkCidrError.message}</span>}
        </div>
      </div>
      <div className="form-row" style={{ gridTemplateColumns: '2fr 1fr' }}>
        <div className="form-group">
          <label className="form-label">NFS Storage Name (Optional)</label>
          <input
            type="text"
            className={`form-input ${nfsStorageNameError ? 'error' : ''}`}
            placeholder="Storage name from storage_config.yml"
            {...register(`service_k8s_cluster.${index}.nfs_storage_name`)}
          />
          {nfsStorageNameError && <span className="error-message">{nfsStorageNameError.message}</span>}
        </div>
        <div className="form-group">
          <label className="form-label">CRI-O Storage Size (Optional)</label>
          <input
            type="text"
            className={`form-input ${k8sCrioStorageSizeError ? 'error' : ''}`}
            placeholder="e.g., 20G"
            {...register(`service_k8s_cluster.${index}.k8s_crio_storage_size`)}
          />
          {k8sCrioStorageSizeError && <span className="error-message">{k8sCrioStorageSizeError.message}</span>}
        </div>
      </div>
      <div className="form-group">
        <label className="form-label">CSI PowerScale Secret File Path (Optional)</label>
        <input
          type="text"
          className={`form-input ${csiSecretFilePathError ? 'error' : ''}`}
          placeholder="Absolute path to secret.yaml"
          {...register(`service_k8s_cluster.${index}.csi_powerscale_driver_secret_file_path`)}
        />
        {csiSecretFilePathError && <span className="error-message">{csiSecretFilePathError.message}</span>}
      </div>
      <div className="form-group">
        <label className="form-label">CSI PowerScale Values File Path (Optional)</label>
        <input
          type="text"
          className={`form-input ${csiValuesFilePathError ? 'error' : ''}`}
          placeholder="Absolute path to values.yaml"
          {...register(`service_k8s_cluster.${index}.csi_powerscale_driver_values_file_path`)}
        />
        {csiValuesFilePathError && <span className="error-message">{csiValuesFilePathError.message}</span>}
      </div>
      <div className="form-group">
        <div className="form-checkbox">
          <input
            id={`service_k8s_cluster.${index}.etcd_on_local_disk`}
            type="checkbox"
            {...register(`service_k8s_cluster.${index}.etcd_on_local_disk`)}
          />
          <label htmlFor={`service_k8s_cluster.${index}.etcd_on_local_disk`}>
            etcd on Local Disk (Optional)
          </label>
        </div>
      </div>
      {canRemove && (
        <Button variant="secondary" onClick={remove}>Remove Cluster</Button>
      )}
    </div>
  );
};
