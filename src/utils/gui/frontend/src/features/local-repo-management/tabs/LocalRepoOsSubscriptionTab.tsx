// Copyright 2026 Dell Inc. or its subsidiaries. All Rights Reserved.
//
// Licensed under the Apache License, Version 2.0 (the "License");
// you may not use this file except in compliance with the License.
// You may obtain a copy of the License at
//
//     http://www.apache.org/licenses/LICENSE-2.0
//
// Unless required by applicable law or agreed to in writing, software
// distributed under the License is distributed on an "AS IS" BASIS,
// WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
// See the License for the specific language governing permissions and
// limitations under the License.
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
