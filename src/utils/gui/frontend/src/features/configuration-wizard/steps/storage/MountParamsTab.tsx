import type { UseFormRegister, Control } from 'react-hook-form';
import { useFieldArray } from 'react-hook-form';
import Button from '../../../../components/Button';
import { StorageConfigFormData } from '../../schemas/storageConfig';
import type { FormFieldError } from '../../hooks/useFormErrors';

interface MountParamsTabProps {
  register: UseFormRegister<StorageConfigFormData>;
  control: Control<StorageConfigFormData>;
  enabled: boolean;
  onToggle: (enabled: boolean) => void;
  onClear: () => void;
  getError: (path: string) => FormFieldError | undefined;
}

export const MountParamsTab = ({ register, control, enabled, onToggle, onClear, getError }: MountParamsTabProps) => {
  // Use a helper array for dynamic mount params entries
  const { fields, append, remove } = useFieldArray({
    control,
    name: '_mount_params_entries',
  });

  return (
    <>
      <div className="form-group">
        <label className="form-label">Mount Parameter Profiles (Optional)</label>
        <div className="form-checkbox">
          <input
            type="checkbox"
            id="enable-mount-params"
            checked={enabled}
            onChange={(e) => {
              onToggle(e.target.checked);
              if (!e.target.checked) {
                onClear();
              }
            }}
          />
          <label htmlFor="enable-mount-params">Enable Mount Parameter Profiles</label>
        </div>
      </div>

      <div className={!enabled ? 'disabled-section' : ''}>
        <div className="space-y-2 section-style">
          <p className="text-sm text-gray-600">
            Define reusable mount profiles with fs_type and mnt_opts. Reference these profiles in mount entries.
          </p>

          {fields.map((field, index) => {
            const profileNameError = getError(`_mount_params_entries.${index}.profile_name`);
            const fsTypeError = getError(`_mount_params_entries.${index}.fs_type`);
            const dumpFreqError = getError(`_mount_params_entries.${index}.dump_freq`);
            const mntOptsError = getError(`_mount_params_entries.${index}.mnt_opts`);
            const fsckPassError = getError(`_mount_params_entries.${index}.fsck_pass`);

            return (
            <div key={field.id} className="space-y-2 section-style">
              <div className="form-row">
                <div className="form-group">
                  <label className="form-label">Profile Name (Required)</label>
                  <input
                    type="text"
                    className={`form-input ${profileNameError ? 'error' : ''}`}
                    placeholder="e.g., nfs_default"
                    disabled={!enabled}
                    {...register(`_mount_params_entries.${index}.profile_name`)}
                  />
                  {profileNameError && (
                    <span className="error-message">{profileNameError.message}</span>
                  )}
                </div>
                <div className="form-group">
                  <label className="form-label">Filesystem Type (Required)</label>
                  <select
                    className={`form-select ${fsTypeError ? 'error' : ''}`}
                    disabled={!enabled}
                    {...register(`_mount_params_entries.${index}.fs_type`)}
                  >
                    <option value="auto">auto</option>
                    <option value="ext2">ext2</option>
                    <option value="ext3">ext3</option>
                    <option value="ext4">ext4</option>
                    <option value="xfs">xfs</option>
                    <option value="nfs">nfs</option>
                    <option value="nfs4">nfs4</option>
                    <option value="cifs">cifs</option>
                    <option value="tmpfs">tmpfs</option>
                    <option value="cephfs">cephfs</option>
                    <option value="vfat">vfat</option>
                    <option value="ntfs">ntfs</option>
                    <option value="none">none</option>
                    <option value="fuse.s3fs">fuse.s3fs</option>
                  </select>
                  {fsTypeError && (
                    <span className="error-message">{fsTypeError.message}</span>
                  )}
                </div>
                <div className="form-group">
                  <label className="form-label">Dump Frequency (0-2) (Optional)</label>
                  <input
                    type="text"
                    className={`form-input ${dumpFreqError ? 'error' : ''}`}
                    placeholder="0"
                    disabled={!enabled}
                    {...register(`_mount_params_entries.${index}.dump_freq`)}
                  />
                  {dumpFreqError && (
                    <span className="error-message">{dumpFreqError.message}</span>
                  )}
                </div>
              </div>
              <div className="form-row" style={{ gridTemplateColumns: '2fr 1fr' }}>
                <div className="form-group">
                  <label className="form-label">Mount Options (Required)</label>
                  <input
                    type="text"
                    className={`form-input ${mntOptsError ? 'error' : ''}`}
                    placeholder="e.g., nosuid,rw,sync,hard"
                    disabled={!enabled}
                    {...register(`_mount_params_entries.${index}.mnt_opts`)}
                  />
                  {mntOptsError && (
                    <span className="error-message">{mntOptsError.message}</span>
                  )}
                </div>
                <div className="form-group">
                  <label className="form-label">FSCK Pass (0-9) (Optional)</label>
                  <input
                    type="text"
                    className={`form-input ${fsckPassError ? 'error' : ''}`}
                    placeholder="0"
                    disabled={!enabled}
                    {...register(`_mount_params_entries.${index}.fsck_pass`)}
                  />
                  {fsckPassError && (
                    <span className="error-message">{fsckPassError.message}</span>
                  )}
                </div>
              </div>
              {fields.length > 1 && (
                <Button variant="secondary" onClick={() => remove(index)} disabled={!enabled}>
                  Remove Profile
                </Button>
              )}
            </div>
            );
          })}

          <Button
            variant="primary"
            onClick={() => append({ profile_name: '', fs_type: 'nfs', mnt_opts: 'nosuid,rw,sync,hard', dump_freq: '0', fsck_pass: '0' })}
            disabled={!enabled}
          >
            Add Profile
          </Button>
        </div>
      </div>
    </>
  );
};
