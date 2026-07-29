import { UseFormRegister } from 'react-hook-form';
import { UserRegistrySection } from '../sections/UserRegistrySection';
import { CredentialsSection } from '../sections/CredentialsSection';
import type { FormFieldError } from '../../configuration-wizard/hooks/useFormErrors';

interface LocalRepoUserRegistryCredentialsTabProps {
  userRegistryEnabled: boolean;
  credentialsEnabled: boolean;
  userRegistryFields: Array<{ id: string }>;
  userCredentialFields: Array<{ id: string }>;
  register: UseFormRegister<any>;
  getError: (path: string) => FormFieldError | undefined;
  appendUserRegistry: any;
  removeUserRegistry: any;
  appendUserCredential: any;
  removeUserCredential: any;
  onToggleUserRegistry: (enabled: boolean) => void;
  onToggleCredentials: (enabled: boolean) => void;
  onClearUserRegistry: () => void;
  onClearCredentials: () => void;
}

export const LocalRepoUserRegistryCredentialsTab = ({
  userRegistryEnabled,
  credentialsEnabled,
  userRegistryFields,
  userCredentialFields,
  register,
  getError,
  appendUserRegistry,
  removeUserRegistry,
  appendUserCredential,
  removeUserCredential,
  onToggleUserRegistry,
  onToggleCredentials,
  onClearUserRegistry,
  onClearCredentials,
}: LocalRepoUserRegistryCredentialsTabProps) => {
  return (
    <div className="space-y-2">
      <UserRegistrySection
        enabled={userRegistryEnabled}
        fields={userRegistryFields}
        register={register}
        getError={getError}
        append={appendUserRegistry}
        remove={removeUserRegistry}
        onToggle={onToggleUserRegistry}
        onClear={onClearUserRegistry}
      />

      <CredentialsSection
        enabled={credentialsEnabled}
        fields={userCredentialFields}
        register={register}
        getError={getError}
        append={appendUserCredential}
        remove={removeUserCredential}
        onToggle={onToggleCredentials}
        onClear={onClearCredentials}
      />
    </div>
  );
};
