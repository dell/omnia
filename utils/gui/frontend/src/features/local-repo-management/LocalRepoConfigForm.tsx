import { useState, useEffect, useMemo } from 'react';
import { useForm, useFieldArray } from 'react-hook-form';
import { zodResolver } from '@hookform/resolvers/zod';
import { getLocalRepoOsSchema } from '../configuration-wizard/schemas/localRepoUserRegistry';
import { Tabs } from '../configuration-wizard/components/Tabs';
import { LocalRepoUserRegistryCredentialsTab } from './tabs/LocalRepoUserRegistryCredentialsTab';
import { LocalRepoUserRepoTab } from './tabs/LocalRepoUserRepoTab';
import { LocalRepoOsRepoTab } from './tabs/LocalRepoOsRepoTab';
import { LocalRepoOsOmniaRepoTab } from './tabs/LocalRepoOsOmniaRepoTab';
import { LocalRepoOsSubscriptionTab } from './tabs/LocalRepoOsSubscriptionTab';
import { LocalRepoAdditionalReposTab } from './tabs/LocalRepoAdditionalReposTab';
import { DEFAULT_OMNIA_REPO_X86_64, DEFAULT_OMNIA_REPO_AARCH64 } from './localRepoDefaults';
import { useFormErrors } from '../configuration-wizard/hooks/useFormErrors';
import { useLocalRepoStore, type LocalRepoOsType } from './localRepoStore';

interface LocalRepoConfigFormProps {
  osType: LocalRepoOsType;
}

const getDefaultOmniaRepos = (osType: LocalRepoOsType, arch: 'x86_64' | 'aarch64') => {
  if (osType === 'rhel') {
    return arch === 'x86_64' ? DEFAULT_OMNIA_REPO_X86_64 : DEFAULT_OMNIA_REPO_AARCH64;
  }
  return [{ url: '', name: '' }];
};

export const LocalRepoConfigForm = ({ osType }: LocalRepoConfigFormProps) => {
  const store = useLocalRepoStore();
  const storeData = store[osType];
  const setOsData = store.setOsData;

  const showOsReposKey = `_ui_show${osType.charAt(0).toUpperCase() + osType.slice(1)}Repos` as const;
  const showOsSubscriptionKey = `_ui_show${osType.charAt(0).toUpperCase() + osType.slice(1)}Subscription` as const;

  const [activeTab, setActiveTab] = useState(
    typeof storeData._ui_activeTab === 'string' ? storeData._ui_activeTab : 'credentials'
  );
  const [showCredentials, setShowCredentials] = useState(
    typeof storeData._ui_showCredentials === 'boolean' ? storeData._ui_showCredentials : false
  );
  const [showUserRegistry, setShowUserRegistry] = useState(
    typeof storeData._ui_showUserRegistry === 'boolean' ? storeData._ui_showUserRegistry : false
  );
  const [showUserRepos, setShowUserRepos] = useState(
    typeof storeData._ui_showUserRepos === 'boolean' ? storeData._ui_showUserRepos : false
  );
  const [showOsRepos, setShowOsRepos] = useState(
    typeof storeData[showOsReposKey] === 'boolean' ? storeData[showOsReposKey] : false
  );
  const [showOsSubscription, setShowOsSubscription] = useState(
    typeof storeData[showOsSubscriptionKey] === 'boolean' ? storeData[showOsSubscriptionKey] : false
  );
  const [showAdditionalRepos, setShowAdditionalRepos] = useState(
    typeof storeData._ui_showAdditionalRepos === 'boolean' ? storeData._ui_showAdditionalRepos : false
  );

  const osPrefix = osType;
  const osKeyX86 = `${osPrefix}_os_url_x86_64`;
  const osKeyAarch64 = `${osPrefix}_os_url_aarch64`;
  const omniaKeyX86 = `omnia_repo_url_${osPrefix}_x86_64`;
  const omniaKeyAarch64 = `omnia_repo_url_${osPrefix}_aarch64`;
  const subscriptionKeyX86 = `${osPrefix}_subscription_repo_config_x86_64`;
  const subscriptionKeyAarch64 = `${osPrefix}_subscription_repo_config_aarch64`;

  const defaultValues = useMemo(() => {
    const ensureArray = (value: any, fallback: any[]) => (Array.isArray(value) && value.length > 0 ? value : fallback);
    const d: Record<string, any> = {};

    d.user_registry_credential = ensureArray(storeData.user_registry_credential, [{ name: '', username: '', password: '' }]);
    d.user_registry = ensureArray(storeData.user_registry, [{ host: '', cert_path: '', key_path: '' }]);
    d.user_repo_url_x86_64 = ensureArray(storeData.user_repo_url_x86_64, [{ url: '', name: '' }]);
    d.user_repo_url_aarch64 = ensureArray(storeData.user_repo_url_aarch64, [{ url: '', name: '' }]);
    d.additional_repos_x86_64 = ensureArray(storeData.additional_repos_x86_64, [{ url: '', name: '', gpgkey: '' }]);
    d.additional_repos_aarch64 = ensureArray(storeData.additional_repos_aarch64, [{ url: '', name: '', gpgkey: '' }]);

    d[osKeyX86] = ensureArray(storeData[osKeyX86], [{ url: '', name: '' }]);
    d[osKeyAarch64] = ensureArray(storeData[osKeyAarch64], [{ url: '', name: '' }]);
    d[omniaKeyX86] = Array.isArray(storeData[omniaKeyX86])
      ? storeData[omniaKeyX86]
      : getDefaultOmniaRepos(osType, 'x86_64');
    d[omniaKeyAarch64] = Array.isArray(storeData[omniaKeyAarch64])
      ? storeData[omniaKeyAarch64]
      : getDefaultOmniaRepos(osType, 'aarch64');
    d[subscriptionKeyX86] = ensureArray(storeData[subscriptionKeyX86], [{ url: '', name: '', gpgkey: '' }]);
    d[subscriptionKeyAarch64] = ensureArray(storeData[subscriptionKeyAarch64], [{ url: '', name: '', gpgkey: '' }]);

    return d;
  }, [storeData, osType, osKeyX86, osKeyAarch64, omniaKeyX86, omniaKeyAarch64, subscriptionKeyX86, subscriptionKeyAarch64]);

  const formSchema = useMemo(() => getLocalRepoOsSchema(osType), [osType]);

  const {
    register,
    formState: { errors },
    control,
    watch,
    getValues,
    setValue,
  } = useForm<any>({
    resolver: zodResolver(formSchema) as any,
    defaultValues,
    mode: 'onTouched',
  });

  // Sync form data to the local repo store
  useEffect(() => {
    const currentValues = getValues();
    setOsData(osType, currentValues);

    let timer: ReturnType<typeof setTimeout>;
    const subscription = watch((formValues) => {
      clearTimeout(timer);
      timer = setTimeout(() => {
        setOsData(osType, formValues);
      }, 300);
    });
    return () => { clearTimeout(timer); subscription.unsubscribe(); };
  }, [watch, getValues, setOsData, osType]);

  // Persist UI toggles back to the store
  useEffect(() => {
    setOsData(osType, {
      _ui_activeTab: activeTab,
      _ui_showCredentials: showCredentials,
      _ui_showUserRegistry: showUserRegistry,
      _ui_showUserRepos: showUserRepos,
      _ui_showAdditionalRepos: showAdditionalRepos,
      [showOsReposKey]: showOsRepos,
      [showOsSubscriptionKey]: showOsSubscription,
    });
  }, [activeTab, showCredentials, showUserRegistry, showUserRepos, showAdditionalRepos, showOsRepos, showOsSubscription, setOsData, osType, showOsReposKey, showOsSubscriptionKey]);

  const getError = useFormErrors(errors, undefined);

  const { fields: userCredentialFields, append: appendUserCredential, remove: removeUserCredential } = useFieldArray({
    control,
    name: 'user_registry_credential',
  });

  const { fields: userRegistryFields, append: appendUserRegistry, remove: removeUserRegistry } = useFieldArray({
    control,
    name: 'user_registry',
  });

  const { fields: userRepoX86Fields, append: appendUserRepoX86, remove: removeUserRepoX86 } = useFieldArray({
    control,
    name: 'user_repo_url_x86_64',
  });

  const { fields: userRepoAarch64Fields, append: appendUserRepoAarch64, remove: removeUserRepoAarch64 } = useFieldArray({
    control,
    name: 'user_repo_url_aarch64',
  });

  const { fields: osX86Fields, append: appendOsX86, remove: removeOsX86 } = useFieldArray({
    control,
    name: osKeyX86,
  });

  const { fields: osAarch64Fields, append: appendOsAarch64, remove: removeOsAarch64 } = useFieldArray({
    control,
    name: osKeyAarch64,
  });

  const { fields: omniaRepoX86Fields, append: appendOmniaRepoX86, remove: removeOmniaRepoX86 } = useFieldArray({
    control,
    name: omniaKeyX86,
  });

  const { fields: omniaRepoAarch64Fields, append: appendOmniaRepoAarch64, remove: removeOmniaRepoAarch64 } = useFieldArray({
    control,
    name: omniaKeyAarch64,
  });

  const { fields: subscriptionX86Fields, append: appendSubscriptionX86, remove: removeSubscriptionX86 } = useFieldArray({
    control,
    name: subscriptionKeyX86,
  });

  const { fields: subscriptionAarch64Fields, append: appendSubscriptionAarch64, remove: removeSubscriptionAarch64 } = useFieldArray({
    control,
    name: subscriptionKeyAarch64,
  });

  const { fields: additionalReposX86Fields, append: appendAdditionalReposX86, remove: removeAdditionalReposX86 } = useFieldArray({
    control,
    name: 'additional_repos_x86_64',
  });

  const { fields: additionalReposAarch64Fields, append: appendAdditionalReposAarch64, remove: removeAdditionalReposAarch64 } = useFieldArray({
    control,
    name: 'additional_repos_aarch64',
  });

  return (
    <Tabs
      tabs={[
        {
          id: 'credentials',
          label: 'User Registry & Credentials',
          component: (
            <LocalRepoUserRegistryCredentialsTab
              userRegistryEnabled={showUserRegistry}
              credentialsEnabled={showCredentials}
              userRegistryFields={userRegistryFields}
              userCredentialFields={userCredentialFields}
              register={register}
              getError={getError}
              appendUserRegistry={appendUserRegistry}
              removeUserRegistry={removeUserRegistry}
              appendUserCredential={appendUserCredential}
              removeUserCredential={removeUserCredential}
              onToggleUserRegistry={setShowUserRegistry}
              onToggleCredentials={setShowCredentials}
              onClearUserRegistry={() => {
                setValue('user_registry', []);
                setOsData(osType, { user_registry: [] });
              }}
              onClearCredentials={() => {
                setValue('user_registry_credential', []);
                setOsData(osType, { user_registry_credential: [] });
              }}
            />
          ),
        },
        {
          id: 'user-repos',
          label: 'User Repos',
          component: (
            <LocalRepoUserRepoTab
              enabled={showUserRepos}
              x86Fields={userRepoX86Fields}
              aarch64Fields={userRepoAarch64Fields}
              register={register}
              getError={getError}
              appendX86={appendUserRepoX86}
              removeX86={removeUserRepoX86}
              appendAarch64={appendUserRepoAarch64}
              removeAarch64={removeUserRepoAarch64}
              onToggle={setShowUserRepos}
              onClear={() => {
                setValue('user_repo_url_x86_64', []);
                setValue('user_repo_url_aarch64', []);
                setOsData(osType, { user_repo_url_x86_64: [], user_repo_url_aarch64: [] });
              }}
            />
          ),
        },
        {
          id: 'os-repos',
          label: `${osType.toUpperCase()} OS Repos`,
          component: (
            <LocalRepoOsRepoTab
              osType={osType}
              enabled={showOsRepos}
              osX86Fields={osX86Fields}
              osAarch64Fields={osAarch64Fields}
              register={register}
              getError={getError}
              appendOsX86={appendOsX86}
              removeOsX86={removeOsX86}
              appendOsAarch64={appendOsAarch64}
              removeOsAarch64={removeOsAarch64}
              onToggle={setShowOsRepos}
              onClear={() => {
                setValue(osKeyX86, []);
                setValue(osKeyAarch64, []);
                setOsData(osType, { [osKeyX86]: [], [osKeyAarch64]: [] });
              }}
            />
          ),
        },
        {
          id: 'omnia-repos',
          label: 'Omnia Repos',
          component: (
            <LocalRepoOsOmniaRepoTab
              osType={osType}
              omniaRepoX86Fields={omniaRepoX86Fields}
              omniaRepoAarch64Fields={omniaRepoAarch64Fields}
              register={register}
              getError={getError}
              appendOmniaRepoX86={appendOmniaRepoX86}
              removeOmniaRepoX86={removeOmniaRepoX86}
              appendOmniaRepoAarch64={appendOmniaRepoAarch64}
              removeOmniaRepoAarch64={removeOmniaRepoAarch64}
            />
          ),
        },
        {
          id: 'subscription',
          label: `${osType.toUpperCase()} Subscription`,
          component: (
            <LocalRepoOsSubscriptionTab
              osType={osType}
              enabled={showOsSubscription}
              x86Fields={subscriptionX86Fields}
              aarch64Fields={subscriptionAarch64Fields}
              register={register}
              getError={getError}
              appendX86={appendSubscriptionX86}
              removeX86={removeSubscriptionX86}
              appendAarch64={appendSubscriptionAarch64}
              removeAarch64={removeSubscriptionAarch64}
              onToggle={setShowOsSubscription}
            />
          ),
        },
        {
          id: 'additional-repos',
          label: 'Additional Repos',
          component: (
            <LocalRepoAdditionalReposTab
              enabled={showAdditionalRepos}
              x86Fields={additionalReposX86Fields}
              aarch64Fields={additionalReposAarch64Fields}
              register={register}
              getError={getError}
              appendX86={appendAdditionalReposX86}
              removeX86={removeAdditionalReposX86}
              appendAarch64={appendAdditionalReposAarch64}
              removeAarch64={removeAdditionalReposAarch64}
              onToggle={setShowAdditionalRepos}
            />
          ),
        },
      ]}
      activeTab={activeTab}
      onTabChange={setActiveTab}
    />
  );
};

export default LocalRepoConfigForm;
