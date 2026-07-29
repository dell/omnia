import { UseFormRegister } from 'react-hook-form';
import { OsSubscriptionSection } from '../sections/OsSubscriptionSection';
import type { FormFieldError } from '../../configuration-wizard/hooks/useFormErrors';

interface LocalRepoOsSubscriptionTabProps {
  osType: 'rhel' | 'ubuntu';
  enabled: boolean;
  x86Fields: Array<{ id: string }>;
  aarch64Fields: Array<{ id: string }>;
  register: UseFormRegister<any>;
  getError: (path: string) => FormFieldError | undefined;
  appendX86: any;
  removeX86: any;
  appendAarch64: any;
  removeAarch64: any;
  onToggle: (enabled: boolean) => void;
}

export const LocalRepoOsSubscriptionTab = ({
  osType,
  enabled,
  x86Fields,
  aarch64Fields,
  register,
  getError,
  appendX86,
  removeX86,
  appendAarch64,
  removeAarch64,
  onToggle,
}: LocalRepoOsSubscriptionTabProps) => {
  return (
    <OsSubscriptionSection
      osType={osType}
      enabled={enabled}
      x86Fields={x86Fields}
      aarch64Fields={aarch64Fields}
      register={register}
      getError={getError}
      appendX86={appendX86}
      removeX86={removeX86}
      appendAarch64={appendAarch64}
      removeAarch64={removeAarch64}
      onToggle={onToggle}
    />
  );
};
