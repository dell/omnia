import { useState, useEffect } from 'react';
import { useForm } from 'react-hook-form';
import { zodResolver } from '@hookform/resolvers/zod';
import { useConfigStore } from '../../configStore';
import { cloudInitConfigSchema, type CloudInitConfigFormData } from '../../schemas/cloudInitConfig';
import { clearL2ErrorsForStep } from '../../utils/l2Validation';
import { Tabs } from '../../components/Tabs';
import { CloudInitCommonTab } from './CloudInitCommonTab';
import { CloudInitGroupsTab } from './CloudInitGroupsTab';

const CLOUD_INIT_DEFAULTS = {
  cloud_init_common: { write_files: [], runcmd: [] },
  cloud_init_groups: [],
};

export const CloudInitConfigStep = () => {
  const wizardData = useConfigStore((s) => s.wizardData);
  const updateWizardFields = useConfigStore((s) => s.updateWizardFields);
  const setStepValid = useConfigStore((s) => s.setStepValid);
  const validationErrors = useConfigStore((s) => s.validationErrors);
  const [activeTab, setActiveTab] = useState(typeof wizardData._ui_cloudInitActiveTab === 'string' ? wizardData._ui_cloudInitActiveTab : 'common');

  const {
    register,
    formState: { errors },
    control,
    watch,
  } = useForm<CloudInitConfigFormData>({
    resolver: zodResolver(cloudInitConfigSchema) as any,
    defaultValues: {
      cloud_init_common: (wizardData.cloud_init_common as any) || CLOUD_INIT_DEFAULTS.cloud_init_common,
      cloud_init_groups: (wizardData.cloud_init_groups as any) || CLOUD_INIT_DEFAULTS.cloud_init_groups,
    },
    mode: 'onTouched',
  });

  // Update step validity and sync form changes to store (debounced)
  useEffect(() => {
    const currentValues = watch();
    const initialResult = cloudInitConfigSchema.safeParse(currentValues);
    setStepValid(5, initialResult.success);
    clearL2ErrorsForStep(initialResult, 'Cloud-Init Configuration', useConfigStore.getState);

    let timer: ReturnType<typeof setTimeout>;
    const subscription = watch((formValues) => {
      const result = cloudInitConfigSchema.safeParse(formValues);
      setStepValid(5, result.success);
      clearL2ErrorsForStep(result, 'Cloud-Init Configuration', useConfigStore.getState);

      clearTimeout(timer);
      timer = setTimeout(() => {
        updateWizardFields({
          cloud_init_common: formValues.cloud_init_common,
          cloud_init_groups: formValues.cloud_init_groups,
        });
      }, 300);
    });

    return () => {
      clearTimeout(timer);
      subscription.unsubscribe();
    };
  }, [watch, setStepValid, updateWizardFields]);

  // Persist UI state separately
  useEffect(() => {
    updateWizardFields({
      _ui_cloudInitActiveTab: activeTab,
    });
  }, [activeTab, updateWizardFields]);

  const tabs = [
    {
      id: 'common',
      label: 'Common',
      component: <CloudInitCommonTab register={register} errors={errors} control={control} validationErrors={validationErrors} />,
    },
    {
      id: 'groups',
      label: 'Groups',
      component: <CloudInitGroupsTab register={register} errors={errors} control={control} validationErrors={validationErrors} />,
    },
  ];

  return <Tabs tabs={tabs} activeTab={activeTab} onTabChange={setActiveTab} />;
};
