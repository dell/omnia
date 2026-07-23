import { useState, useEffect } from 'react';
import { useForm } from 'react-hook-form';
import { zodResolver } from '@hookform/resolvers/zod';
import { useConfigStore } from '../../configStore';
import { storageConfigSchema, type StorageConfigFormData } from '../../schemas/storageConfig';
import { clearL2ErrorsForStep } from '../../utils/l2Validation';
import { useFormErrors } from '../../hooks/useFormErrors';
import { Tabs } from '../../components/Tabs';
import { MountsTab } from './MountsTab';
import { MountParamsTab } from './MountParamsTab';
import { PowerVaultTab } from './PowerVaultTab';
import { SwapTab } from './SwapTab';
import { S3Tab } from './S3Tab';

const MOUNT_PARAMS_DEFAULTS = {
  nfs_default: { fs_type: 'nfs', mnt_opts: 'nosuid,rw,sync,hard', dump_freq: '0', fsck_pass: '0' },
  vast_rdma: { fs_type: 'nfs', mnt_opts: 'proto=rdma,nconnect=8,timeo=600,retrans=2,rsize=1048576,wsize=1048576,hard' },
  vast_tcp: { fs_type: 'nfs', mnt_opts: 'nosuid,rw,sync,hard' },
};

const S3_DEFAULTS = { provider: 'powerscale', endpoint_url: '' } as const;

const MOUNT_DEFAULTS = {
  name: '',
  source: '',
  mount_point: '',
  fs_type: 'nfs',
  mnt_opts: 'nosuid,rw,sync,hard',
  mount_on_oim: false,
  functional_group_prefix: [''],
  groups: [],
  node_key: '',
  node_mount_point: [],
  permissions: { owner: 'root', group: 'root', mode: '0755' }
};

const MOUNT_PARAMS_ENTRY_DEFAULTS = { profile_name: '', fs_type: 'nfs', mnt_opts: 'nosuid,rw,sync,hard', dump_freq: '0', fsck_pass: '0' };

const POWERVAULT_DEFAULTS = {
  name: '',
  ip: [''],
  port: 3260,
  iscsi_initiator: '',
  volume_id: '',
  mount_point: '',
  fs_type: 'xfs',
  functional_group_prefix: [''],
  node_key: '',
  node_mount_point: [],
  permissions: { owner: 'root', group: 'root', mode: '0755' }
};

const SWAP_DEFAULTS = { name: '', filename: '', size: 'auto', maxsize: '', functional_group_prefix: [''] };

export const StorageConfigStep = () => {
  const wizardData = useConfigStore((s) => s.wizardData);
  const updateWizardFields = useConfigStore((s) => s.updateWizardFields);
  const setStepValid = useConfigStore((s) => s.setStepValid);
  const validationErrors = useConfigStore((s) => s.validationErrors);
  const [activeTab, setActiveTab] = useState(typeof wizardData._ui_storageActiveTab === 'string' ? wizardData._ui_storageActiveTab : 'mounts');
  const [showMounts, setShowMounts] = useState(typeof wizardData._ui_showMounts === 'boolean' ? wizardData._ui_showMounts : false);
  const [showMountParams, setShowMountParams] = useState(typeof wizardData._ui_showMountParams === 'boolean' ? wizardData._ui_showMountParams : false);
  const [showPowerVault, setShowPowerVault] = useState(typeof wizardData._ui_showPowerVault === 'boolean' ? wizardData._ui_showPowerVault : false);
  const [showSwap, setShowSwap] = useState(typeof wizardData._ui_showSwap === 'boolean' ? wizardData._ui_showSwap : false);

  const getArrayDefault = (value: any, enabled: boolean, defaultEntry: any) => {
    if (!enabled) return [];
    if (Array.isArray(value) && value.length > 0) return value;
    return [defaultEntry];
  };

  const storageDefaultValues = {
    mounts: getArrayDefault(wizardData.mounts, true, MOUNT_DEFAULTS),
    mount_params: showMountParams ? (wizardData.mount_params as any) || MOUNT_PARAMS_DEFAULTS : {},
    _mount_params_entries: getArrayDefault(wizardData._mount_params_entries, true, MOUNT_PARAMS_ENTRY_DEFAULTS),
    powervault_config: getArrayDefault(wizardData.powervault_config, true, POWERVAULT_DEFAULTS),
    swap: getArrayDefault(wizardData.swap, true, SWAP_DEFAULTS),
    s3_configurations: (wizardData.s3_configurations as any) || S3_DEFAULTS,
    _ui_showMounts: showMounts,
    _ui_showMountParams: showMountParams,
    _ui_showPowerVault: showPowerVault,
    _ui_showSwap: showSwap,
  };

  const {
    register,
    formState: { errors },
    control,
    watch,
    setValue,
    getValues,
    clearErrors,
  } = useForm<StorageConfigFormData>({
    resolver: zodResolver(storageConfigSchema) as any,
    defaultValues: storageDefaultValues,
    mode: 'onTouched',
  });

  const getError = useFormErrors(errors, validationErrors);

  // Update step validity and sync form changes to store (debounced)
  useEffect(() => {
    const currentValues = watch();
    const initialResult = storageConfigSchema.safeParse(currentValues);
    setStepValid(4, initialResult.success);
    clearL2ErrorsForStep(initialResult, 'Storage Configuration', useConfigStore.getState);

    let timer: ReturnType<typeof setTimeout>;
    const subscription = watch((formValues) => {
      const result = storageConfigSchema.safeParse(formValues);
      setStepValid(4, result.success);
      clearL2ErrorsForStep(result, 'Storage Configuration', useConfigStore.getState);

      clearTimeout(timer);
      timer = setTimeout(() => {
        // Transform _mount_params_entries array to mount_params record
        const mountParamsRecord: Record<string, any> = {};
        if (Array.isArray(formValues._mount_params_entries)) {
          formValues._mount_params_entries.forEach((entry: any) => {
            if (entry.profile_name) {
              mountParamsRecord[entry.profile_name] = {
                fs_type: entry.fs_type,
                mnt_opts: entry.mnt_opts,
                dump_freq: entry.dump_freq,
                fsck_pass: entry.fsck_pass,
              };
            }
          });
        }

        updateWizardFields({
          mounts: formValues.mounts,
          mount_params: Object.keys(mountParamsRecord).length > 0 ? mountParamsRecord : formValues.mount_params,
          _mount_params_entries: formValues._mount_params_entries,
          powervault_config: formValues.powervault_config,
          swap: formValues.swap,
          s3_configurations: formValues.s3_configurations,
        } as Partial<any>);
      }, 300);
    });

    return () => {
      clearTimeout(timer);
      subscription.unsubscribe();
    };
  }, [watch, setStepValid, updateWizardFields]);

  // UI state persistence — separate concern
  useEffect(() => {
    updateWizardFields({
      _ui_storageActiveTab: activeTab,
      _ui_showMounts: showMounts,
      _ui_showMountParams: showMountParams,
      _ui_showPowerVault: showPowerVault,
      _ui_showSwap: showSwap,
    });
  }, [activeTab, showMounts, showMountParams, showPowerVault, showSwap, updateWizardFields]);

  const ensureMountEntry = () => {
    const current = getValues('mounts');
    if (!Array.isArray(current) || current.length === 0) {
      setValue('mounts', [MOUNT_DEFAULTS] as any);
    }
  };
  const ensureMountParamsEntry = () => {
    const current = getValues('_mount_params_entries');
    if (!Array.isArray(current) || current.length === 0) {
      setValue('_mount_params_entries', [MOUNT_PARAMS_ENTRY_DEFAULTS] as any);
      setValue('mount_params', MOUNT_PARAMS_DEFAULTS as any);
    }
  };
  const ensurePowerVaultEntry = () => {
    const current = getValues('powervault_config');
    if (!Array.isArray(current) || current.length === 0) {
      setValue('powervault_config', [POWERVAULT_DEFAULTS] as any);
    }
  };
  const ensureSwapEntry = () => {
    const current = getValues('swap');
    if (!Array.isArray(current) || current.length === 0) {
      setValue('swap', [SWAP_DEFAULTS] as any);
    }
  };

  const tabs = [
    {
      id: 'mounts',
      label: 'Mounts',
      component: <MountsTab enabled={showMounts} register={register} control={control} onToggle={(val) => { setShowMounts(val); setValue('_ui_showMounts', val); if (val) ensureMountEntry(); }} onClear={() => { clearErrors('mounts'); }} getError={getError} />,
    },
    {
      id: 'mount-params',
      label: 'Mount Params',
      component: <MountParamsTab enabled={showMountParams} register={register} control={control} onToggle={(val) => { setShowMountParams(val); setValue('_ui_showMountParams', val); if (val) ensureMountParamsEntry(); }} onClear={() => { clearErrors('mount_params'); clearErrors('_mount_params_entries'); }} getError={getError} />,
    },
    {
      id: 'powervault',
      label: 'PowerVault',
      component: <PowerVaultTab enabled={showPowerVault} register={register} control={control} onToggle={(val) => { setShowPowerVault(val); setValue('_ui_showPowerVault', val); if (val) ensurePowerVaultEntry(); }} onClear={() => { clearErrors('powervault_config'); }} getError={getError} />,
    },
    {
      id: 'swap',
      label: 'Swap',
      component: <SwapTab enabled={showSwap} register={register} control={control} onToggle={(val) => { setShowSwap(val); setValue('_ui_showSwap', val); if (val) ensureSwapEntry(); }} onClear={() => { clearErrors('swap'); }} getError={getError} />,
    },
    {
      id: 's3',
      label: 'S3',
      component: <S3Tab register={register} control={control} setValue={setValue} getError={getError} />,
    },
  ];

  const storageError = getError('storage');

  return (
    <div className="space-y-6">
      {storageError && <div className="error-message">{storageError.message}</div>}
      <Tabs tabs={tabs} activeTab={activeTab} onTabChange={setActiveTab} />
    </div>
  );
};
