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
