import { useEffect, useState } from 'react';
import { useForm } from 'react-hook-form';
import { zodResolver } from '@hookform/resolvers/zod';
import { useConfigStore } from '../../configStore';
import { OmniaHaDiscoveryFormData, omniaHaDiscoverySchema } from '../../schemas/omniaHaDiscoveryConfig';
import { clearL2ErrorsForStep } from '../../utils/l2Validation';
import { SlurmTab, EMPTY_SLURM_CLUSTER } from './SlurmTab';
import { K8sTab, EMPTY_K8S_CLUSTER, EMPTY_HA_CLUSTER } from './K8sTab';
import { Tabs } from '../../components/Tabs';
import { useFormErrors } from '../../hooks/useFormErrors';

export const OmniaHaDiscoveryStep = () => {
  const wizardData = useConfigStore((s) => s.wizardData);
  const updateWizardFields = useConfigStore((s) => s.updateWizardFields);
  const setStepValid = useConfigStore((s) => s.setStepValid);
  const clusterType = useConfigStore((s) => s.clusterType);
  const enableHa = useConfigStore((s) => s.enableHa);
  const validationErrors = useConfigStore((s) => s.validationErrors);
  const [activeTab, setActiveTab] = useState('slurm');

  // Auto-select appropriate tab based on cluster type
  useEffect(() => {
    if (clusterType === 'slurm') {
      setActiveTab('slurm');
    } else if (clusterType === 'k8s') {
      setActiveTab('k8s');
    }
  }, [clusterType]);

  const {
    register,
    formState: { errors },
    control,
    watch,
    setValue,
  } = useForm<OmniaHaDiscoveryFormData>({
    // zodResolver type inference conflicts with .default() and .refine() on optional fields
    // Runtime validation is fully enforced by the schema — this cast only affects compile-time types
    resolver: zodResolver(omniaHaDiscoverySchema) as any,
    defaultValues: {
      slurm_cluster: (wizardData.slurm_cluster as OmniaHaDiscoveryFormData['slurm_cluster']) || [{ ...EMPTY_SLURM_CLUSTER }],
      service_k8s_cluster: (wizardData.service_k8s_cluster as OmniaHaDiscoveryFormData['service_k8s_cluster']) || [{ ...EMPTY_K8S_CLUSTER }],
      service_k8s_cluster_ha: (Array.isArray(wizardData.service_k8s_cluster_ha) && (wizardData.service_k8s_cluster_ha as any[]).length > 0)
        ? (wizardData.service_k8s_cluster_ha as OmniaHaDiscoveryFormData['service_k8s_cluster_ha'])
        : [{ ...EMPTY_HA_CLUSTER }],
      enable_ha: (wizardData.enable_ha as boolean) ?? enableHa,
      security_config: (wizardData.security_config as OmniaHaDiscoveryFormData['security_config']) || { ldap_connection_type: 'TLS' },
    },
    mode: 'onTouched',
  });

  // Validate step and sync form changes to store (debounced to avoid excessive updates)
  useEffect(() => {
    // Validate immediately on mount
    const currentValues = watch();
    const initialResult = omniaHaDiscoverySchema.safeParse(currentValues);
    setStepValid(6, initialResult.success);
    clearL2ErrorsForStep(initialResult, 'Omnia Cluster Configuration', useConfigStore.getState);

    let timer: ReturnType<typeof setTimeout>;
    const subscription = watch((formValues) => {
      const result = omniaHaDiscoverySchema.safeParse(formValues);
      setStepValid(6, result.success);
      clearL2ErrorsForStep(result, 'Omnia Cluster Configuration', useConfigStore.getState);

      clearTimeout(timer);
      timer = setTimeout(() => {
        updateWizardFields({
          slurm_cluster: formValues.slurm_cluster,
          service_k8s_cluster: formValues.service_k8s_cluster,
          service_k8s_cluster_ha: formValues.service_k8s_cluster_ha,
          enable_ha: formValues.enable_ha,
          security_config: formValues.security_config,
        });
      }, 300);
    });

    return () => {
      clearTimeout(timer);
      subscription.unsubscribe();
    };
  }, [watch, setStepValid, updateWizardFields]);

  const getError = useFormErrors(errors, validationErrors);
  const ldapError = getError('security_config.ldap_connection_type');

  // Filter tabs based on cluster type
  const tabs = [
    {
      id: 'slurm',
      label: 'Slurm',
      component: <SlurmTab register={register} control={control} errors={errors} setValue={setValue} validationErrors={validationErrors} />,
    },
    {
      id: 'k8s',
      label: 'Kubernetes',
      component: <K8sTab register={register} control={control} errors={errors} setValue={setValue} enableHa={enableHa} validationErrors={validationErrors} />,
    },
  ].filter(tab => {
    if (clusterType === 'slurm') return tab.id === 'slurm';
    if (clusterType === 'k8s') return tab.id === 'k8s';
    return true; // both or null - show all tabs
  });

  return (
    <div className="space-y-6">
      {/* Security Configuration */}
      <div className="form-group">
        <label className="form-label">Security Configuration</label>
        <label className="form-label">LDAP Connection Type</label>
        <select
          className={`form-select ${ldapError ? 'error' : ''}`}
          {...register('security_config.ldap_connection_type')}
        >
          <option value="TLS">TLS (port 389)</option>
          <option value="SSL">SSL (port 636)</option>
        </select>
        <p className="text-sm text-gray-600 mt-1">
          Select the LDAP connection type. TLS uses port 389, SSL uses port 636.
        </p>
        {ldapError && <span className="error-message">{ldapError.message}</span>}
      </div>

      {/* Tabs for Slurm and K8s */}
      <Tabs tabs={tabs} activeTab={activeTab} onTabChange={setActiveTab} />
    </div>
  );
};
