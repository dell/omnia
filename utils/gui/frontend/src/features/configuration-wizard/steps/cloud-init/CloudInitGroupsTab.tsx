import type { UseFormRegister, FieldErrors, Control } from 'react-hook-form';
import { useFieldArray } from 'react-hook-form';
import Button from '../../../../components/Button';
import { CloudInitConfigFormData } from '../../schemas/cloudInitConfig';
import { useFormErrors } from '../../hooks/useFormErrors';
import type { FormFieldError } from '../../hooks/useFormErrors';
import type { ValidationError } from '../../utils/l2Validation';

interface CloudInitGroupsTabProps {
  register: UseFormRegister<CloudInitConfigFormData>;
  errors: FieldErrors<CloudInitConfigFormData>;
  control: Control<CloudInitConfigFormData>;
  validationErrors?: ValidationError[];
}

export const CloudInitGroupsTab = ({ register, errors, control, validationErrors }: CloudInitGroupsTabProps) => {
  const getError = useFormErrors(errors, validationErrors);
  const { fields, append, remove } = useFieldArray({
    control,
    name: 'cloud_init_groups',
  });

  return (
    <div className="space-y-2 section-style">
      <p className="text-sm text-gray-600">
        Configure cloud-init overrides for specific functional groups. Group names must match functional groups from PXE mapping.
      </p>

      {fields.map((field, index) => {
        const groupNameError = getError(`cloud_init_groups.${index}.group_name`);
        return (
        <div key={field.id} className="space-y-2 section-style">
          <div className="form-group">
            <label className="form-label">Group {index + 1}</label>
          </div>
          <div className="form-group">
            <label className="form-label">Group Name</label>
            <div className="flex gap-2 items-end">
              <input
                type="text"
                className={`form-input flex-1 ${groupNameError ? 'error' : ''}`}
                placeholder="e.g., slurm_node_x86_64"
                {...register(`cloud_init_groups.${index}.group_name`)}
              />
              <Button variant="secondary" type="button" onClick={() => remove(index)}>
                Remove Group
              </Button>
            </div>
            {groupNameError && <span className="error-message">{groupNameError.message}</span>}
          </div>

          <div className="form-group">
            <label className="form-label">Write Files</label>
          </div>
          <GroupWriteFilesSection register={register} getError={getError} control={control} groupIndex={index} />

          <div className="form-group">
            <label className="form-label">Run Commands</label>
          </div>
          <GroupRuncmdSection register={register} getError={getError} control={control} groupIndex={index} />
        </div>
        );
      })}
      <Button
        variant="primary"
        onClick={() => append({ group_name: '', write_files: [], runcmd: [] })}
      >
        + Add Group
      </Button>
    </div>
  );
};

interface GroupWriteFilesSectionProps {
  register: UseFormRegister<CloudInitConfigFormData>;
  control: Control<CloudInitConfigFormData>;
  groupIndex: number;
  getError: (path: string) => FormFieldError | undefined;
}

const GroupWriteFilesSection = ({ register, control, groupIndex, getError }: GroupWriteFilesSectionProps) => {
  const { fields, append, remove } = useFieldArray({
    control,
    name: `cloud_init_groups.${groupIndex}.write_files` as any,
  });

  return (
    <>
      {fields.map((field, index) => {
        const pathError = getError(`cloud_init_groups.${groupIndex}.write_files.${index}.path`);
        const permissionsError = getError(`cloud_init_groups.${groupIndex}.write_files.${index}.permissions`);
        const contentError = getError(`cloud_init_groups.${groupIndex}.write_files.${index}.content`);
        return (
        <div key={field.id} className="space-y-2 section-style">
          <div className="form-row form-row-2-col">
            <div className="form-group">
              <label className="form-label">Path</label>
              <input
                type="text"
                className={`form-input ${pathError ? 'error' : ''}`}
                placeholder="e.g., /etc/motd"
                {...register(`cloud_init_groups.${groupIndex}.write_files.${index}.path` as any)}
              />
              {pathError && <span className="error-message">{pathError.message}</span>}
            </div>
            <div className="form-group">
              <label className="form-label">Permissions</label>
              <input
                type="text"
                className={`form-input ${permissionsError ? 'error' : ''}`}
                placeholder="e.g., 0644"
                {...register(`cloud_init_groups.${groupIndex}.write_files.${index}.permissions` as any)}
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
                {...register(`cloud_init_groups.${groupIndex}.write_files.${index}.content` as any)}
              />
              {contentError && <span className="error-message">{contentError.message}</span>}
            </div>
            <div className="form-group">
              <Button variant="secondary" type="button" onClick={() => remove(index)}>
                Remove File
              </Button>
            </div>
          </div>
        </div>
        );
      })}
      <Button
        variant="primary"
        onClick={() => append({ path: '', content: '', permissions: '0644' })}
      >
        + Add File
      </Button>
    </>
  );
};

interface GroupRuncmdSectionProps {
  register: UseFormRegister<CloudInitConfigFormData>;
  control: Control<CloudInitConfigFormData>;
  groupIndex: number;
  getError: (path: string) => FormFieldError | undefined;
}

const GroupRuncmdSection = ({ register, control, groupIndex, getError }: GroupRuncmdSectionProps) => {
  const { fields, append, remove } = useFieldArray({
    control,
    name: `cloud_init_groups.${groupIndex}.runcmd` as any,
  });

  const handleAppend = () => {
    append({ command: '' });
  };

  const handleRemove = (index: number) => {
    remove(index);
  };

  return (
    <>
      {fields.map((field, index) => {
        const commandError = getError(`cloud_init_groups.${groupIndex}.runcmd.${index}.command`);
        return (
        <div key={field.id} className="space-y-2 section-style">
          <div className="form-group">
            <div className="flex gap-2 items-end">
              <input
                type="text"
                className={`form-input flex-1 ${commandError ? 'error' : ''}`}
                placeholder="e.g., echo 'Group-specific command'"
                {...register(`cloud_init_groups.${groupIndex}.runcmd.${index}.command` as any)}
              />
              <Button variant="secondary" onClick={() => handleRemove(index)}>
                Remove
              </Button>
            </div>
            {commandError && <span className="error-message">{commandError.message}</span>}
          </div>
        </div>
        );
      })}
      <Button
        variant="primary"
        onClick={handleAppend}
      >
        + Add Command
      </Button>
    </>
  );
};
