import { useFieldArray, UseFormRegister, Control, FieldErrors, UseFormSetValue } from 'react-hook-form';
import { useEffect } from 'react';
import Button from '../../../../components/Button';
import { OmniaHaDiscoveryFormData } from '../../schemas/omniaHaDiscoveryConfig';
import { K8sClusterRow } from './K8sClusterRow';
import { useFormErrors } from '../../hooks/useFormErrors';
import type { ValidationError } from '../../utils/l2Validation';

interface K8sTabProps {
  register: UseFormRegister<OmniaHaDiscoveryFormData>;
  control: Control<OmniaHaDiscoveryFormData>;
  errors: FieldErrors<OmniaHaDiscoveryFormData>;
  setValue: UseFormSetValue<OmniaHaDiscoveryFormData>;
  enableHa: boolean; // HA toggle value from Deployment Setup
  validationErrors?: ValidationError[];
}

type K8sCluster = OmniaHaDiscoveryFormData['service_k8s_cluster'][number];
type HACluster = NonNullable<OmniaHaDiscoveryFormData['service_k8s_cluster_ha']>[number];

export const EMPTY_K8S_CLUSTER: Readonly<K8sCluster> = Object.freeze({
  cluster_name: '',
  deployment: false,
  etcd_on_local_disk: false,
  k8s_cni: 'calico',
  pod_external_ip_range: '',
  k8s_service_addresses: '10.233.0.0/18',
  k8s_pod_network_cidr: '10.233.64.0/18',
  nfs_storage_name: '',
  k8s_crio_storage_size: '20G',
});

export const EMPTY_HA_CLUSTER: Readonly<HACluster> = Object.freeze({
  cluster_name: '',
  enable_k8s_ha: false,
  virtual_ip_address: '',
});

export const K8sTab = ({ register, control, errors, setValue, enableHa, validationErrors }: K8sTabProps) => {
  // Use the shared useFormErrors hook instead of reimplementing
  const getError = useFormErrors(errors, validationErrors);

  // Sync enable_ha form value with the HA toggle so schema validation is conditional
  useEffect(() => {
    setValue('enable_ha', enableHa);
  }, [enableHa, setValue]);

  const { fields: k8sFields, append: appendK8s, remove: removeK8s } = useFieldArray({
    control,
    name: 'service_k8s_cluster',
  });

  const { fields: haFields, append: appendHA, remove: removeHA } = useFieldArray({
    control,
    name: 'service_k8s_cluster_ha',
  });

  // Sync each HA cluster's enable_k8s_ha flag with the top-level HA toggle
  useEffect(() => {
    haFields.forEach((_, index) => {
      setValue(`service_k8s_cluster_ha.${index}.enable_k8s_ha`, enableHa, { shouldValidate: false });
    });
  }, [enableHa, haFields, setValue]);

  // Get array-level error message (RHF puts refine errors under .root)
  const k8sArrayError =
    errors.service_k8s_cluster?.message ||
    (errors.service_k8s_cluster as any)?.root?.message;

  // Handle deployment checkbox changes (auto-uncheck others)
  const handleDeploymentChange = (changedIndex: number, checked: boolean) => {
    if (checked) {
      // Uncheck all other clusters
      k8sFields.forEach((_, i) => {
        if (i !== changedIndex) {
          setValue(`service_k8s_cluster.${i}.deployment`, false);
        }
      });
    }
    setValue(`service_k8s_cluster.${changedIndex}.deployment`, checked);
  };

  return (
    <div className="space-y-6">
      {/* Service K8s Cluster Configuration */}
      <div className="form-group">
        <label className="form-label">Service K8s Cluster Configuration (Required)</label>
        {k8sArrayError && <span className="error-message">{k8sArrayError}</span>}
        {k8sFields.map((field, index) => (
          <K8sClusterRow
            key={field.id}
            index={index}
            register={register}
            errors={errors}
            validationErrors={validationErrors}
            remove={() => removeK8s(index)}
            canRemove={k8sFields.length > 1}
            onDeploymentChange={(checked) => handleDeploymentChange(index, checked)}
          />
        ))}
        <Button variant="primary" onClick={() => appendK8s({ ...EMPTY_K8S_CLUSTER })}>Add K8s Cluster</Button>
      </div>

      {/* High Availability Configuration */}
      <div className={`form-group ${!enableHa ? 'disabled-section' : ''}`}>
        <label className="form-label">High Availability Configuration (Required)</label>
        {haFields.map((field, index) => {
          const clusterNameError = getError(`service_k8s_cluster_ha.${index}.cluster_name`);
          const virtualIpError = getError(`service_k8s_cluster_ha.${index}.virtual_ip_address`);

          return (
            <div key={field.id} className="space-y-2 section-style">
              <div className="form-row form-row-2-col">
                <div className="form-group">
                  <label className="form-label">K8s Cluster Name (Required)</label>
                  <input
                    type="text"
                    className={`form-input ${clusterNameError ? 'error' : ''}`}
                    placeholder="e.g., service_cluster"
                    disabled={!enableHa}
                    {...register(`service_k8s_cluster_ha.${index}.cluster_name`)}
                  />
                  {clusterNameError && <span className="error-message">{clusterNameError.message}</span>}
                </div>
                <div className="form-group">
                  <label className="form-label">Virtual IP Address (Required)</label>
                  <input
                    type="text"
                    className={`form-input ${virtualIpError ? 'error' : ''}`}
                    placeholder="e.g., 172.16.107.1"
                    disabled={!enableHa}
                    {...register(`service_k8s_cluster_ha.${index}.virtual_ip_address`)}
                  />
                  {virtualIpError && <span className="error-message">{virtualIpError.message}</span>}
                </div>
              </div>

              {haFields.length > 1 && (
                <Button variant="secondary" onClick={() => removeHA(index)} disabled={!enableHa}>Remove HA Cluster</Button>
              )}
            </div>
          );
        })}
        {enableHa && haFields.length === 0 && (
          <p className="text-muted padding-sm italic">
            No HA clusters configured. Click below to add one.
          </p>
        )}
        <Button variant="primary" onClick={() => appendHA({ ...EMPTY_HA_CLUSTER, enable_k8s_ha: enableHa })} disabled={!enableHa}>Add HA Cluster</Button>
      </div>
    </div>
  );
};
