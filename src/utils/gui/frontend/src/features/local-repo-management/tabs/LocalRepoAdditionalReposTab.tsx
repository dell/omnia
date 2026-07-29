import { UseFormRegister } from 'react-hook-form';
import { AdditionalReposSection } from '../sections/AdditionalReposSection';
import type { FormFieldError } from '../../configuration-wizard/hooks/useFormErrors';

interface LocalRepoAdditionalReposTabProps {
  enabled: boolean;
  x86Fields: Array<{ id: string }>;
  aarch64Fields: Array<{ id: string }>;
  register: UseFormRegister<any>;
  getError: (path: string) => FormFieldError | undefined;
  appendX86: any;  // schema mismatch
  removeX86: any;
  appendAarch64: any;
  removeAarch64: any;
  onToggle: (enabled: boolean) => void;
}

export const LocalRepoAdditionalReposTab = ({
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
}: LocalRepoAdditionalReposTabProps) => {
  return (
    <AdditionalReposSection
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
