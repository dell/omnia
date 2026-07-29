import { useEffect } from 'react';
import { useForm, Controller, useFieldArray } from 'react-hook-form';
import { zodResolver } from '@hookform/resolvers/zod';
import { deploymentConfigsSchema, DeploymentConfigsFormData } from '../../schemas';
import { useConfigStore } from '../../configStore';
import { clearL2ErrorsForStep } from '../../utils/l2Validation';
import { DnsInput } from '../../components/DnsInput';
import { useFormErrors } from '../../hooks/useFormErrors';

const defaultAdminNetwork = {
  oim_nic_name: '',
  subnet: '',
  netmask_bits: '',
  primary_oim_admin_ip: '',
  primary_oim_bmc_ip: '',
  dynamic_range: '',
  dns: [] as string[],
  ntp_servers: [] as { address: string; type: 'server' | 'pool' }[],
  additional_subnets: [] as any[],
};

const defaultIbNetwork = {
  subnet: '',
  netmask_bits: '',
  dns: [] as string[],
};

const normalizeNetworks = (networks: any): DeploymentConfigsFormData['Networks'] => {
  const networkArray = Array.isArray(networks) ? networks : [];
  const adminEntry = networkArray.find((n: any) => n?.admin_network);
  const ibEntry = networkArray.find((n: any) => n?.ib_network);
  const additionalEntry = networkArray.find((n: any) => n?.additional_subnets);

  return [
    {
      admin_network: {
        ...defaultAdminNetwork,
        ...(adminEntry?.admin_network || {}),
      },
    },
    {
      ib_network: {
        ...defaultIbNetwork,
        ...(ibEntry?.ib_network || {}),
      },
    },
    {
      additional_subnets: Array.isArray(additionalEntry?.additional_subnets)
        ? additionalEntry.additional_subnets
        : [],
    },
  ];
};

export const DeploymentConfigsStep = () => {
  const { wizardData, updateWizardField, setStepValid, validationErrors } = useConfigStore();

  const {
    register,
    formState: { errors },
    control,
    watch,
    setValue,
    getValues,
  } = useForm<DeploymentConfigsFormData>({
    resolver: zodResolver(deploymentConfigsSchema),
    defaultValues: {
      Networks: normalizeNetworks(wizardData.Networks),
    },
    mode: 'onTouched',
  });

  // Helper to safely access deeply nested errors (merges RHF and L2 validation errors)
  const getError = useFormErrors(errors, validationErrors);

  const { fields: additionalSubnets, append: appendSubnet, remove: removeSubnet } = useFieldArray({
    control,
    name: 'Networks.0.admin_network.additional_subnets' as any,
  });

  const { fields: topLevelAdditionalSubnets, append: appendTopLevelSubnet, remove: removeTopLevelSubnet } = useFieldArray({
    control,
    name: 'Networks.2.additional_subnets' as any,
  });

  const { fields: ntpServers, append: appendNtpServer, remove: removeNtpServer } = useFieldArray({
    control,
    name: 'Networks.0.admin_network.ntp_servers' as any,
  });

  // Auto-fill network configuration from PXE mapping analysis if available
  // Only populate from PXE if Networks doesn't already exist (from BMC mini-flow)
  useEffect(() => {
    const pxeNetworkAnalysis = wizardData.pxe_network_analysis as any;

    if (pxeNetworkAnalysis && !wizardData.Networks) {
      // Auto-fill admin network
      if (pxeNetworkAnalysis.adminSubnet) {
        setValue('Networks.0.admin_network.subnet', pxeNetworkAnalysis.adminSubnet);
        setValue('Networks.0.admin_network.netmask_bits', String(pxeNetworkAnalysis.adminNetmaskBits || 24));
      }
      if (pxeNetworkAnalysis.adminIps && pxeNetworkAnalysis.adminIps.length > 0) {
        setValue('Networks.0.admin_network.primary_oim_admin_ip', pxeNetworkAnalysis.adminIps[0]);
      }
      if (pxeNetworkAnalysis.bmcIps && pxeNetworkAnalysis.bmcIps.length > 0) {
        setValue('Networks.0.admin_network.primary_oim_bmc_ip', pxeNetworkAnalysis.bmcIps[0]);
      }
      if (pxeNetworkAnalysis.adminAssignedRange) {
        setValue('Networks.0.admin_network.dynamic_range', pxeNetworkAnalysis.adminAssignedRange);
      }

      // Auto-fill IB network if available (no dynamic_range in IB schema)
      if (pxeNetworkAnalysis.ibSubnet) {
        setValue('Networks.1.ib_network.subnet', pxeNetworkAnalysis.ibSubnet);
        setValue('Networks.1.ib_network.netmask_bits', String(pxeNetworkAnalysis.ibNetmaskBits || 24));
      }

      // Set default NIC name
      setValue('Networks.0.admin_network.oim_nic_name', 'eno1');
    }
  }, [wizardData.pxe_network_analysis, wizardData.Networks, setValue]);

  // Sync initial Networks values to store immediately so Summary validation works
  // even if the user navigates quickly, then keep syncing subsequent changes
  useEffect(() => {
    updateWizardField('Networks', getValues('Networks'));
  }, []);

  // Validate step and sync form changes to store (debounced to avoid excessive updates)
  useEffect(() => {
    let timer: ReturnType<typeof setTimeout>;
    const subscription = watch((formValues) => {
      // Validate the form
      const result = deploymentConfigsSchema.safeParse(formValues);
      setStepValid(3, result.success);
      clearL2ErrorsForStep(result, 'Network Configuration', useConfigStore.getState);
      
      // Debounced store sync
      clearTimeout(timer);
      timer = setTimeout(() => {
        updateWizardField('Networks', formValues.Networks);
      }, 300);
    });

    return () => {
      clearTimeout(timer);
      subscription.unsubscribe();
    };
  }, [watch, updateWizardField]);

  const networksError = getError('Networks');

  return (
    <div className="space-y-6">
      {networksError && <div className="error-message">{networksError.message}</div>}

      {/* Admin Network */}
      <div className="form-group">
        <label className="form-label">Admin Network Configuration (Required)</label>
        <div className="space-y-2 section-box">
          <div className="form-row">
            <div className="form-group form-col-1">
              <label className="form-label">OIM Network Interface Name (Required)</label>
              <input
                type="text"
                className={`form-input ${getError('Networks.0.admin_network.oim_nic_name') ? 'error' : ''}`}
                placeholder="e.g., eno1"
                {...register('Networks.0.admin_network.oim_nic_name')}
              />
              {getError('Networks.0.admin_network.oim_nic_name') && <span className="error-message">{getError('Networks.0.admin_network.oim_nic_name')?.message}</span>}
            </div>

            <div className="form-group form-col-1">
              <label className="form-label">Subnet (Required)</label>
              <input
                type="text"
                className={`form-input ${getError('Networks.0.admin_network.subnet') ? 'error' : ''}`}
                placeholder="e.g., 172.16.0.0"
                {...register('Networks.0.admin_network.subnet')}
              />
              {getError('Networks.0.admin_network.subnet') && <span className="error-message">{getError('Networks.0.admin_network.subnet')?.message}</span>}
            </div>

            <div className="form-group form-col-1">
              <label className="form-label">Netmask Bits (Required)</label>
              <input
                type="number"
                className={`form-input ${getError('Networks.0.admin_network.netmask_bits') ? 'error' : ''}`}
                placeholder="e.g., 24"
                {...register('Networks.0.admin_network.netmask_bits')}
              />
              {getError('Networks.0.admin_network.netmask_bits') && <span className="error-message">{getError('Networks.0.admin_network.netmask_bits')?.message}</span>}
            </div>
          </div>

          <div className="form-row">
            <div className="form-group">
              <label className="form-label">Primary OIM Admin IP Address (Required)</label>
              <input
                type="text"
                className={`form-input ${getError('Networks.0.admin_network.primary_oim_admin_ip') ? 'error' : ''}`}
                placeholder="e.g., 172.16.107.254"
                {...register('Networks.0.admin_network.primary_oim_admin_ip')}
              />
              {getError('Networks.0.admin_network.primary_oim_admin_ip') && <span className="error-message">{getError('Networks.0.admin_network.primary_oim_admin_ip')?.message}</span>}
            </div>

            <div className="form-group">
              <label className="form-label">Primary OIM BMC IP Address (Optional)</label>
              <input
                type="text"
                className={`form-input ${getError('Networks.0.admin_network.primary_oim_bmc_ip') ? 'error' : ''}`}
                placeholder="e.g., 172.16.107.253"
                {...register('Networks.0.admin_network.primary_oim_bmc_ip')}
              />
              {getError('Networks.0.admin_network.primary_oim_bmc_ip') && <span className="error-message">{getError('Networks.0.admin_network.primary_oim_bmc_ip')?.message}</span>}
            </div>

            <div className="form-group">
              <label className="form-label">Dynamic IP Range (Required)</label>
              <input
                type="text"
                className={`form-input ${getError('Networks.0.admin_network.dynamic_range') ? 'error' : ''}`}
                placeholder="e.g., 172.16.107.201-172.16.107.250"
                {...register('Networks.0.admin_network.dynamic_range')}
              />
              {getError('Networks.0.admin_network.dynamic_range') && <span className="error-message">{getError('Networks.0.admin_network.dynamic_range')?.message}</span>}
            </div>
          </div>

          <div className="form-group">
            <label className="form-label">DNS Servers (Optional)</label>
            <Controller
              control={control}
              name="Networks.0.admin_network.dns"
              render={({ field, fieldState: { error } }) => (
                <DnsInput
                  value={field.value || []}
                  onChange={field.onChange}
                  onBlur={field.onBlur}
                  error={error || getError('Networks.0.admin_network.dns')}
                  placeholder="comma-separated IPs, e.g., 8.8.8.8,8.8.4.4"
                />
              )}
            />
          </div>

          <div className="form-group">
            <label className="form-label">NTP Servers (Optional)</label>
            {ntpServers.length === 0 && (
              <p className="text-muted padding-sm italic">No NTP servers configured. Click below to add one.</p>
            )}
            {ntpServers.map((item, index) => (
              <div key={item.id} className="section-box" style={{ marginBottom: '8px', padding: '12px' }}>
                <div className="form-row form-row-2-col">
                  <div className="form-group">
                    <label className="form-label">Address (Required)</label>
                    <input
                      type="text"
                      className={`form-input ${getError(`Networks.0.admin_network.ntp_servers.${index}.address`) ? 'error' : ''}`}
                      placeholder="e.g., 172.16.10.80 or pool.ntp.org"
                      {...register(`Networks.0.admin_network.ntp_servers.${index}.address`)}
                    />
                    {getError(`Networks.0.admin_network.ntp_servers.${index}.address`) && <span className="error-message">{getError(`Networks.0.admin_network.ntp_servers.${index}.address`)?.message}</span>}
                  </div>
                  <div className="form-group">
                    <label className="form-label">Type</label>
                    <select
                      className={`form-select ${getError(`Networks.0.admin_network.ntp_servers.${index}.type`) ? 'error' : ''}`}
                      {...register(`Networks.0.admin_network.ntp_servers.${index}.type`)}
                    >
                      <option value="server">server</option>
                      <option value="pool">pool</option>
                    </select>
                    {getError(`Networks.0.admin_network.ntp_servers.${index}.type`) && <span className="error-message">{getError(`Networks.0.admin_network.ntp_servers.${index}.type`)?.message}</span>}
                  </div>
                </div>
                <button type="button" className="button button-danger button-small" style={{ marginTop: '4px' }} onClick={() => removeNtpServer(index)}>Remove NTP Server</button>
              </div>
            ))}
            <button type="button" className="button button-secondary button-small" onClick={() => appendNtpServer({ address: '', type: 'server' })}>+ Add NTP Server</button>
          </div>

          <div className="form-group">
            <label className="form-label">Additional Subnets (Optional)</label>
            {additionalSubnets.length === 0 && (
              <p className="text-muted padding-sm italic">No additional subnets configured. Click below to add one.</p>
            )}
            {additionalSubnets.map((item, index) => (
              <div key={item.id} className="section-box" style={{ marginBottom: '8px', padding: '12px' }}>
                <div className="form-row" style={{ gridTemplateColumns: '1.5fr 1fr 1.5fr 2fr' }}>
                  <div className="form-group">
                    <label className="form-label">Subnet (Required)</label>
                    <input
                      type="text"
                      className={`form-input ${getError(`Networks.0.admin_network.additional_subnets.${index}.subnet`) ? 'error' : ''}`}
                      placeholder="e.g., 10.40.1.0"
                      {...register(`Networks.0.admin_network.additional_subnets.${index}.subnet`)}
                    />
                    {getError(`Networks.0.admin_network.additional_subnets.${index}.subnet`) && <span className="error-message">{getError(`Networks.0.admin_network.additional_subnets.${index}.subnet`)?.message}</span>}
                  </div>
                  <div className="form-group">
                    <label className="form-label">Netmask Bits (Required)</label>
                    <input
                      type="number"
                      className={`form-input ${getError(`Networks.0.admin_network.additional_subnets.${index}.netmask_bits`) ? 'error' : ''}`}
                      placeholder="e.g., 24"
                      {...register(`Networks.0.admin_network.additional_subnets.${index}.netmask_bits`)}
                    />
                    {getError(`Networks.0.admin_network.additional_subnets.${index}.netmask_bits`) && <span className="error-message">{getError(`Networks.0.admin_network.additional_subnets.${index}.netmask_bits`)?.message}</span>}
                  </div>
                  <div className="form-group">
                    <label className="form-label">Router (Required)</label>
                    <input
                      type="text"
                      className={`form-input ${getError(`Networks.0.admin_network.additional_subnets.${index}.router`) ? 'error' : ''}`}
                      placeholder="e.g., 10.40.1.1"
                      {...register(`Networks.0.admin_network.additional_subnets.${index}.router`)}
                    />
                    {getError(`Networks.0.admin_network.additional_subnets.${index}.router`) && <span className="error-message">{getError(`Networks.0.admin_network.additional_subnets.${index}.router`)?.message}</span>}
                  </div>
                  <div className="form-group">
                    <label className="form-label">Dynamic Range (Required)</label>
                    <input
                      type="text"
                      className={`form-input ${getError(`Networks.0.admin_network.additional_subnets.${index}.dynamic_range`) ? 'error' : ''}`}
                      placeholder="e.g., 10.40.1.100-10.40.1.200"
                      {...register(`Networks.0.admin_network.additional_subnets.${index}.dynamic_range`)}
                    />
                    {getError(`Networks.0.admin_network.additional_subnets.${index}.dynamic_range`) && <span className="error-message">{getError(`Networks.0.admin_network.additional_subnets.${index}.dynamic_range`)?.message}</span>}
                  </div>
                </div>
                <button type="button" className="button button-danger button-small" style={{ marginTop: '4px' }} onClick={() => removeSubnet(index)}>Remove Subnet</button>
              </div>
            ))}
            <button type="button" className="button button-secondary button-small" onClick={() => appendSubnet({ subnet: '', netmask_bits: '', router: '', dynamic_range: '' })}>+ Add Subnet</button>
          </div>
        </div>
      </div>

      {/* InfiniBand Network */}
      <div className="form-group">
        <label className="form-label">InfiniBand Network Configuration (Optional)</label>
        <div className="space-y-2 section-box">
          <div className="form-row form-row-3-col">
            <div className="form-group">
              <label className="form-label">Subnet (Required)</label>
              <input
                type="text"
                className={`form-input ${getError('Networks.1.ib_network.subnet') ? 'error' : ''}`}
                placeholder="e.g., 192.168.0.0"
                {...register('Networks.1.ib_network.subnet')}
              />
              {getError('Networks.1.ib_network.subnet') && <span className="error-message">{getError('Networks.1.ib_network.subnet')?.message}</span>}
            </div>

            <div className="form-group">
              <label className="form-label">Netmask Bits (Required)</label>
              <input
                type="number"
                className={`form-input ${getError('Networks.1.ib_network.netmask_bits') ? 'error' : ''}`}
                placeholder="e.g., 24"
                {...register('Networks.1.ib_network.netmask_bits')}
              />
              {getError('Networks.1.ib_network.netmask_bits') && <span className="error-message">{getError('Networks.1.ib_network.netmask_bits')?.message}</span>}
            </div>

            <div className="form-group">
              <label className="form-label">DNS Servers (Optional)</label>
              <Controller
                control={control}
                name="Networks.1.ib_network.dns"
                render={({ field, fieldState: { error } }) => (
                  <DnsInput
                    value={field.value || []}
                    onChange={field.onChange}
                    onBlur={field.onBlur}
                    error={error || getError('Networks.1.ib_network.dns')}
                    placeholder="comma-separated IPs, e.g., 8.8.8.8,8.8.4.4"
                  />
                )}
              />
            </div>
          </div>
        </div>
      </div>

      {/* Top-level Additional Subnets */}
      <div className="form-group">
        <label className="form-label">Additional Subnets (Optional - for multi-RAC/multi-subnet PXE)</label>
        {topLevelAdditionalSubnets.length === 0 && (
          <p className="text-muted padding-sm italic">No additional subnets configured. Click below to add one.</p>
        )}
        {topLevelAdditionalSubnets.map((item, index) => (
          <div key={item.id} className="section-box" style={{ marginBottom: '8px', padding: '12px' }}>
            <div className="form-row" style={{ gridTemplateColumns: '1.5fr 1fr 1.5fr 2fr' }}>
              <div className="form-group">
                <label className="form-label">Subnet (Required)</label>
                <input
                  type="text"
                  className={`form-input ${getError(`Networks.2.additional_subnets.${index}.subnet`) ? 'error' : ''}`}
                  placeholder="e.g., 10.40.1.0"
                  {...register(`Networks.2.additional_subnets.${index}.subnet`)}
                />
                {getError(`Networks.2.additional_subnets.${index}.subnet`) && <span className="error-message">{getError(`Networks.2.additional_subnets.${index}.subnet`)?.message}</span>}
              </div>
              <div className="form-group">
                <label className="form-label">Netmask Bits (Required)</label>
                <input
                  type="number"
                  className={`form-input ${getError(`Networks.2.additional_subnets.${index}.netmask_bits`) ? 'error' : ''}`}
                  placeholder="e.g., 24"
                  {...register(`Networks.2.additional_subnets.${index}.netmask_bits`)}
                />
                {getError(`Networks.2.additional_subnets.${index}.netmask_bits`) && <span className="error-message">{getError(`Networks.2.additional_subnets.${index}.netmask_bits`)?.message}</span>}
              </div>
              <div className="form-group">
                <label className="form-label">Router (Required)</label>
                <input
                  type="text"
                  className={`form-input ${getError(`Networks.2.additional_subnets.${index}.router`) ? 'error' : ''}`}
                  placeholder="e.g., 10.40.1.1"
                  {...register(`Networks.2.additional_subnets.${index}.router`)}
                />
                {getError(`Networks.2.additional_subnets.${index}.router`) && <span className="error-message">{getError(`Networks.2.additional_subnets.${index}.router`)?.message}</span>}
              </div>
              <div className="form-group">
                <label className="form-label">Dynamic Range (Required)</label>
                <input
                  type="text"
                  className={`form-input ${getError(`Networks.2.additional_subnets.${index}.dynamic_range`) ? 'error' : ''}`}
                  placeholder="e.g., 10.40.1.100-10.40.1.200"
                  {...register(`Networks.2.additional_subnets.${index}.dynamic_range`)}
                />
                {getError(`Networks.2.additional_subnets.${index}.dynamic_range`) && <span className="error-message">{getError(`Networks.2.additional_subnets.${index}.dynamic_range`)?.message}</span>}
              </div>
            </div>
            <button type="button" className="button button-danger button-small" style={{ marginTop: '4px' }} onClick={() => removeTopLevelSubnet(index)}>Remove Subnet</button>
          </div>
        ))}
        <button type="button" className="button button-secondary button-small" onClick={() => appendTopLevelSubnet({ subnet: '', netmask_bits: '', router: '', dynamic_range: '' })}>+ Add Subnet</button>
      </div>
    </div>
  );
};
