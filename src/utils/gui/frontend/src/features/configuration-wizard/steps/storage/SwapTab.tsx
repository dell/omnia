import type { UseFormRegister, Control } from 'react-hook-form';
import { useFieldArray, useWatch } from 'react-hook-form';
import Button from '../../../../components/Button';
import { StorageConfigFormData } from '../../schemas/storageConfig';
import type { FormFieldError } from '../../hooks/useFormErrors';

interface SwapTabProps {
  register: UseFormRegister<StorageConfigFormData>;
  control: Control<StorageConfigFormData>;
  enabled: boolean;
  onToggle: (enabled: boolean) => void;
  onClear: () => void;
  getError: (path: string) => FormFieldError | undefined;
}

export const SwapTab = ({ register, control, enabled, onToggle, onClear, getError }: SwapTabProps) => {
  const { fields, append, remove } = useFieldArray({
    control,
    name: 'swap',
  });

  const swapValues = useWatch({ control, name: 'swap' }) as any[] | undefined;

  return (
    <>
      <div className="form-group">
        <label className="form-label">Swap File Configurations (Optional)</label>
        <div className="form-checkbox">
          <input
            type="checkbox"
            id="enable-swap"
            checked={enabled}
            onChange={(e) => {
              onToggle(e.target.checked);
              if (!e.target.checked) {
                onClear();
              }
            }}
          />
          <label htmlFor="enable-swap">Enable Swap Configuration</label>
        </div>
      </div>

      <div className={!enabled ? 'disabled-section' : ''}>
        <div className="space-y-2 section-style">
          <p className="text-sm text-gray-600">
            Configure swap files for nodes. Size can be "auto" (uses maxsize) or a specific value (e.g., "2G").
          </p>

          {fields.map((field, index) => {
            const nameError = getError(`swap.${index}.name`);
            const filenameError = getError(`swap.${index}.filename`);
            const sizeError = getError(`swap.${index}.size`);
            const maxsizeError = getError(`swap.${index}.maxsize`);
            const functionalGroupPrefixError = getError(`swap.${index}.functional_group_prefix`);

            return (
            <div key={field.id} className="space-y-2 section-style">
              <div className="form-row">
                <div className="form-group">
                  <label className="form-label">Name (Optional)</label>
                  <input
                    type="text"
                    className={`form-input ${nameError ? 'error' : ''}`}
                    placeholder="e.g., swap_slurm"
                    disabled={!enabled}
                    {...register(`swap.${index}.name`)}
                  />
                  {nameError && <span className="error-message">{nameError.message}</span>}
                </div>
                <div className="form-group">
                  <label className="form-label">Filename (Required)</label>
                  <input
                    type="text"
                    className={`form-input ${filenameError ? 'error' : ''}`}
                    placeholder="e.g., /swapfile"
                    disabled={!enabled}
                    {...register(`swap.${index}.filename`)}
                  />
                  {filenameError && <span className="error-message">{filenameError.message}</span>}
                </div>
                <div className="form-group">
                  <label className="form-label">Size (Required)</label>
                  <input
                    type="text"
                    className={`form-input ${sizeError ? 'error' : ''}`}
                    placeholder="e.g., 2G or auto"
                    disabled={!enabled}
                    {...register(`swap.${index}.size`)}
                  />
                  {sizeError && <span className="error-message">{sizeError.message}</span>}
                </div>
              </div>
              <div className="form-row" style={{ gridTemplateColumns: '1fr 2fr' }}>
                <div className="form-group">
                  <label className="form-label">Max Size (Optional)</label>
                  <input
                    type="text"
                    className={`form-input ${maxsizeError ? 'error' : ''} ${swapValues?.[index]?.size !== 'auto' ? 'disabled-section' : ''}`}
                    placeholder="e.g., 4G"
                    disabled={!enabled || swapValues?.[index]?.size !== 'auto'}
                    {...register(`swap.${index}.maxsize`)}
                  />
                  <p className="text-sm text-gray-600 mt-1">Required when size is "auto"</p>
                  {maxsizeError && <span className="error-message">{maxsizeError.message}</span>}
                </div>
                <div className="form-group">
                  <label className="form-label">Functional Group Prefix (Required)</label>
                  <input
                    type="text"
                    className={`form-input ${functionalGroupPrefixError ? 'error' : ''}`}
                    placeholder="e.g., slurm,login"
                    disabled={!enabled}
                    {...register(`swap.${index}.functional_group_prefix` as any)}
                  />
                  <p className="text-sm text-gray-600 mt-1">Comma-separated values</p>
                  {functionalGroupPrefixError && <span className="error-message">{functionalGroupPrefixError.message}</span>}
                </div>
              </div>
              {fields.length > 1 && (
                <Button variant="secondary" onClick={() => remove(index)} disabled={!enabled}>
                  Remove Swap Entry
                </Button>
              )}
            </div>
            );
          })}

          <Button
            variant="primary"
            onClick={() => append({ name: '', filename: '', size: 'auto', maxsize: '', functional_group_prefix: [''] })}
            disabled={!enabled}
          >
            Add Swap Entry
          </Button>
        </div>
      </div>
    </>
  );
};
