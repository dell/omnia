import type { UseFormRegister, FieldErrors, Control } from 'react-hook-form';
import { useFieldArray } from 'react-hook-form';
import Button from '../../../../components/Button';
import { CloudInitConfigFormData } from '../../schemas/cloudInitConfig';
import { useFormErrors } from '../../hooks/useFormErrors';
import type { ValidationError } from '../../utils/l2Validation';

interface CloudInitCommonTabProps {
  register: UseFormRegister<CloudInitConfigFormData>;
  errors: FieldErrors<CloudInitConfigFormData>;
  control: Control<CloudInitConfigFormData>;
  validationErrors?: ValidationError[];
}

export const CloudInitCommonTab = ({ register, errors, control, validationErrors }: CloudInitCommonTabProps) => {
  const getError = useFormErrors(errors, validationErrors);
  const { fields: writeFilesFields, append: appendWriteFile, remove: removeWriteFile } = useFieldArray({
    control,
    name: 'cloud_init_common.write_files',
  });

  const { fields: runcmdFields, append: appendRuncmd, remove: removeRuncmd } = useFieldArray({
    control,
    name: 'cloud_init_common.runcmd' as any,
  });

  const handleAppendRuncmd = () => {
    appendRuncmd({ command: '' });
  };

  const handleRemoveRuncmd = (index: number) => {
    removeRuncmd(index);
  };

  return (
    <div className="space-y-2 section-style">
      <p className="text-sm text-gray-600">
        These configurations are applied to ALL nodes during provisioning.
      </p>

      <div className="form-group">
        <label className="form-label">Write Files</label>
      </div>

      {writeFilesFields.map((field, index) => {
        const pathError = getError(`cloud_init_common.write_files.${index}.path`);
        const permissionsError = getError(`cloud_init_common.write_files.${index}.permissions`);
        const contentError = getError(`cloud_init_common.write_files.${index}.content`);
        return (
        <div key={field.id} className="space-y-2 section-style">
          <div className="form-row form-row-2-col">
            <div className="form-group">
              <label className="form-label">Path</label>
              <input
                type="text"
                className={`form-input ${pathError ? 'error' : ''}`}
                placeholder="e.g., /etc/motd"
                {...register(`cloud_init_common.write_files.${index}.path`)}
              />
              {pathError && <span className="error-message">{pathError.message}</span>}
            </div>
            <div className="form-group">
              <label className="form-label">Permissions</label>
              <input
                type="text"
                className={`form-input ${permissionsError ? 'error' : ''}`}
                placeholder="e.g., 0644"
                {...register(`cloud_init_common.write_files.${index}.permissions`)}
              />
              {permissionsError && <span className="error-message">{permissionsError.message}</span>}
            </div>
          </div>
          <div className="form-row form-row-2-col">
            <div className="form-group">
              <label className="form-label">Content</label>
              <textarea
                className={`form-input ${contentError ? 'error' : ''}`}
                rows={4}
                placeholder="File content..."
                {...register(`cloud_init_common.write_files.${index}.content`)}
              />
              {contentError && <span className="error-message">{contentError.message}</span>}
            </div>
            <div className="form-group">
              <Button variant="secondary" type="button" onClick={() => removeWriteFile(index)}>
                Remove File
              </Button>
            </div>
          </div>
        </div>
        );
      })}
      {writeFilesFields.length === 0 && (
        <p className="text-sm text-gray-600">No files configured. Click "+ Add File" to add a file.</p>
      )}
      <Button
        variant="primary"
        onClick={() => appendWriteFile({ path: '', content: '', permissions: '0644' })}
      >
        + Add File
      </Button>

      <div className="form-group">
        <label className="form-label">Run Commands</label>
      </div>

      {runcmdFields.map((field, index) => {
        const commandError = getError(`cloud_init_common.runcmd.${index}.command`);
        return (
        <div key={field.id} className="space-y-2 section-style">
          <div className="form-group">
            <div className="flex gap-2 items-end">
              <input
                type="text"
                className={`form-input flex-1 ${commandError ? 'error' : ''}`}
                placeholder="e.g., echo 'Hello World' >> /tmp/hello.txt"
                {...register(`cloud_init_common.runcmd.${index}.command`)}
              />
              <Button variant="secondary" onClick={() => handleRemoveRuncmd(index)}>
                Remove
              </Button>
            </div>
            {commandError && <span className="error-message">{commandError.message}</span>}
          </div>
        </div>
        );
      })}
      {runcmdFields.length === 0 && (
        <p className="text-sm text-gray-600">No commands configured. Click "+ Add Command" to add a command.</p>
      )}
      <Button
        variant="primary"
        onClick={handleAppendRuncmd}
      >
        + Add Command
      </Button>
    </div>
  );
};
