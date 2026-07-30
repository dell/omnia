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
import { useCallback, useMemo } from 'react';
import { FieldErrors } from 'react-hook-form';
import type { ValidationError } from '../utils/l2Validation';

const normalizePath = (path: string): string[] =>
  path.replace(/\[(\d+)\]/g, '.$1').split('.');

export interface FormFieldError {
  message: string;
  type?: string;
}

export const useFormErrors = (
  errors: FieldErrors,
  validationErrors?: ValidationError[]
): (path: string) => FormFieldError | undefined => {
  const l2ErrorMap = useMemo(() => {
    const map = new Map<string, ValidationError>();
    validationErrors?.forEach((e) =>
      map.set(normalizePath(e.field).join('.'), e)
    );
    return map;
  }, [validationErrors]);

  return useCallback(
    (path: string) => {
      const normalizedPath = normalizePath(path);
      const rhfError = normalizedPath.reduce<any>((obj, key) => obj?.[key], errors);
      if (rhfError?.message) return rhfError;

      const l2Error = l2ErrorMap.get(normalizedPath.join('.'));
      if (l2Error) return { message: l2Error.message, type: 'validate' };

      return undefined;
    },
    [errors, l2ErrorMap]
  );
};
