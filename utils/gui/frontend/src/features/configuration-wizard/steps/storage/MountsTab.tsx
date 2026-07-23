import type { UseFormRegister, Control } from 'react-hook-form';
import { useFieldArray } from 'react-hook-form';
import { useState } from 'react';
import Button from '../../../../components/Button';
import { StorageConfigFormData } from '../../schemas/storageConfig';
import type { FormFieldError } from '../../hooks/useFormErrors';

interface MountsTabProps {
  register: UseFormRegister<StorageConfigFormData>;
  control: Control<StorageConfigFormData>;
  enabled: boolean;
  onToggle: (enabled: boolean) => void;
  onClear: () => void;
  getError: (path: string) => FormFieldError | undefined;
}

export const MountsTab = ({ register, control, enabled, onToggle, onClear, getError }: MountsTabProps) => {
  const { fields, append, remove } = useFieldArray({
    control,
    name: 'mounts',
  });

  const [targetingMode, setTargetingMode] = useState<Record<number, 'prefix' | 'groups' | null>>({});

  const handleTargetingChange = (index: number, mode: 'prefix' | 'groups', value: string) => {
    if (value.trim()) {
      setTargetingMode(prev => ({ ...prev, [index]: mode }));
    } else {
      setTargetingMode(prev => ({ ...prev, [index]: null }));
    }
  };

  return (
    <>
      <div className="form-group">
        <label className="form-label">Mount Configurations (Optional)</label>
        <div className="form-checkbox">
          <input
            type="checkbox"
            id="enable-mounts"
            checked={enabled}
            onChange={(e) => {
              onToggle(e.target.checked);
              if (!e.target.checked) {
                onClear();
              }
            }}
          />
          <label htmlFor="enable-mounts">Enable Mount Configuration</label>
        </div>
      </div>

      <div className={!enabled ? 'disabled-section' : ''}>
        <div className="space-y-2 section-style">
          <p className="text-sm text-gray-600">
            Configure NFS, local, CIFS, or other filesystem mounts for nodes.
          </p>

          {fields.map((field, index) => {
            const nameError = getError(`mounts.${index}.name`);
            const sourceError = getError(`mounts.${index}.source`);
            const mountPointError = getError(`mounts.${index}.mount_point`);
            const fsTypeError = getError(`mounts.${index}.fs_type`);
            const mntOptsError = getError(`mounts.${index}.mnt_opts`);
            const mountParamsError = getError(`mounts.${index}.mount_params`);
            const dumpFreqError = getError(`mounts.${index}.dump_freq`);
            const fsckPassError = getError(`mounts.${index}.fsck_pass`);
            const mountOnOimError = getError(`mounts.${index}.mount_on_oim`);
            const functionalGroupPrefixError = getError(`mounts.${index}.functional_group_prefix`);
            const groupsError = getError(`mounts.${index}.groups`);
            const nodeKeyError = getError(`mounts.${index}.node_key`);
            const nodeMountPointError = getError(`mounts.${index}.node_mount_point`);
            const permissionsOwnerError = getError(`mounts.${index}.permissions.owner`);
            const permissionsGroupError = getError(`mounts.${index}.permissions.group`);
            const permissionsModeError = getError(`mounts.${index}.permissions.mode`);

            return (
            <div key={field.id} className="space-y-2 section-style">
              <div className="form-row">
                <div className="form-group">
                  <label className="form-label">Name (Required)</label>
                  <input
                    type="text"
                    className={`form-input ${nameError ? 'error' : ''}`}
                    placeholder="e.g., nfs_slurm"
                    disabled={!enabled}
                    {...register(`mounts.${index}.name`)}
                  />
                  {nameError && <span className="error-message">{nameError.message}</span>}
                </div>
                <div className="form-group">
                  <label className="form-label">Source (Required)</label>
                  <input
                    type="text"
                    className={`form-input ${sourceError ? 'error' : ''}`}
                    placeholder="e.g., 172.16.107.168:/mnt/share/omnia"
                    disabled={!enabled}
                    {...register(`mounts.${index}.source`)}
                  />
                  {sourceError && <span className="error-message">{sourceError.message}</span>}
                </div>
                <div className="form-group">
                  <label className="form-label">Mount Point (Required)</label>
                  <input
                    type="text"
                    className={`form-input ${mountPointError ? 'error' : ''}`}
                    placeholder="e.g., /share_omnia"
                    disabled={!enabled}
                    {...register(`mounts.${index}.mount_point`)}
                  />
                  {mountPointError && <span className="error-message">{mountPointError.message}</span>}
                </div>
              </div>
              <div className="form-row">
                <div className="form-group">
                  <label className="form-label">Filesystem Type (Optional)</label>
                  <select
                    className={`form-select ${fsTypeError ? 'error' : ''}`}
                    disabled={!enabled}
                    {...register(`mounts.${index}.fs_type`)}
                  >
                    <option value="">Select...</option>
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
                  {fsTypeError && <span className="error-message">{fsTypeError.message}</span>}
                </div>
                <div className="form-group">
                  <label className="form-label">Mount Options (Optional)</label>
                  <input
                    type="text"
                    className={`form-input ${mntOptsError ? 'error' : ''}`}
                    placeholder="e.g., nosuid,rw,sync,hard"
                    disabled={!enabled}
                    {...register(`mounts.${index}.mnt_opts`)}
                  />
                  {mntOptsError && <span className="error-message">{mntOptsError.message}</span>}
                </div>
                <div className="form-group">
                  <label className="form-label">Mount Parameters (Optional)</label>
                  <input
                    type="text"
                    className={`form-input ${mountParamsError ? 'error' : ''}`}
                    placeholder="e.g., nfs_default"
                    disabled={!enabled}
                    {...register(`mounts.${index}.mount_params`)}
                  />
                  {mountParamsError && <span className="error-message">{mountParamsError.message}</span>}
                </div>
              </div>
              <div className="form-row">
                <div className="form-group">
                  <label className="form-label">Dump Frequency (0-2) (Optional)</label>
                  <input
                    type="text"
                    className={`form-input ${dumpFreqError ? 'error' : ''}`}
                    placeholder="0"
                    disabled={!enabled}
                    {...register(`mounts.${index}.dump_freq`)}
                  />
                  {dumpFreqError && <span className="error-message">{dumpFreqError.message}</span>}
                </div>
                <div className="form-group">
                  <label className="form-label">FSCK Pass (0-9) (Optional)</label>
                  <input
                    type="text"
                    className={`form-input ${fsckPassError ? 'error' : ''}`}
                    placeholder="0"
                    disabled={!enabled}
                    {...register(`mounts.${index}.fsck_pass`)}
                  />
                  {fsckPassError && <span className="error-message">{fsckPassError.message}</span>}
                </div>
                <div className="form-group">
                  <label className="form-label">Mount on OIM (Optional)</label>
                  <select
                    className={`form-select ${mountOnOimError ? 'error' : ''}`}
                    disabled={!enabled}
                    {...register(`mounts.${index}.mount_on_oim`)}
                  >
                    <option value="false">No</option>
                    <option value="true">Yes</option>
                  </select>
                </div>
              </div>
              <div className="form-group">
                <label className="form-label">Targeting</label>
                <div className="form-row form-row-2-col">
                  <div className="form-group">
                    <label className="form-label">Functional Group Prefix (Required)</label>
                    <input
                      type="text"
                      className={`form-input ${functionalGroupPrefixError ? 'error' : ''} ${targetingMode[index] === 'groups' ? 'disabled-section' : ''}`}
                      placeholder="e.g., slurm,login"
                      disabled={!enabled || targetingMode[index] === 'groups'}
                      {...register(`mounts.${index}.functional_group_prefix` as any, {
                        onChange: (e) => handleTargetingChange(index, 'prefix', e.target.value)
                      })}
                    />
                    <p className="text-sm text-gray-600 mt-1">Comma-separated values (mutually exclusive with groups)</p>
                    {functionalGroupPrefixError && <span className="error-message">{functionalGroupPrefixError.message}</span>}
                  </div>
                  <div className="form-group">
                    <label className="form-label">Groups (Required)</label>
                    <input
                      type="text"
                      className={`form-input ${groupsError ? 'error' : ''} ${targetingMode[index] === 'prefix' ? 'disabled-section' : ''}`}
                      placeholder="e.g., group1,group2"
                      disabled={!enabled || targetingMode[index] === 'prefix'}
                      {...register(`mounts.${index}.groups` as any, {
                        onChange: (e) => handleTargetingChange(index, 'groups', e.target.value)
                      })}
                    />
                    <p className="text-sm text-gray-600 mt-1">Comma-separated values (mutually exclusive with functional_group_prefix)</p>
                    {groupsError && <span className="error-message">{groupsError.message}</span>}
                  </div>
                </div>
              </div>
              <div className="form-group">
                <label className="form-label">Per-Node Bind Mount (Optional)</label>
                <div className="form-row" style={{ gridTemplateColumns: '1fr 2fr' }}>
                  <div className="form-group">
                    <label className="form-label">Node Key (Optional)</label>
                    <select
                      className={`form-select ${nodeKeyError ? 'error' : ''}`}
                      disabled={!enabled}
                      {...register(`mounts.${index}.node_key`)}
                    >
                      <option value="">Select...</option>
                      <option value="local_hostname">Local Hostname</option>
                      <option value="local_ipv4">Local IPv4</option>
                      <option value="instance_id">Instance ID</option>
                    </select>
                    <p className="text-sm text-gray-600 mt-1">Enables per-node subdirectory isolation</p>
                    {nodeKeyError && <span className="error-message">{nodeKeyError.message}</span>}
                  </div>
                  <div className="form-group">
                    <label className="form-label">Node Mount Points (Required when Node Key is set)</label>
                    <input
                      type="text"
                      className={`form-input ${nodeMountPointError ? 'error' : ''}`}
                      placeholder="e.g., /scratch,/tmp"
                      disabled={!enabled}
                      {...register(`mounts.${index}.node_mount_point` as any)}
                    />
                    <p className="text-sm text-gray-600 mt-1">Comma-separated absolute paths (required when Node Key is set)</p>
                    {nodeMountPointError && <span className="error-message">{nodeMountPointError.message}</span>}
                  </div>
                </div>
              </div>
              <div className="form-group">
                <label className="form-label">Permissions (Optional)</label>
                <div className="form-row">
                  <div className="form-group">
                    <label className="form-label">Owner (Optional)</label>
                    <input
                      type="text"
                      className={`form-input ${permissionsOwnerError ? 'error' : ''}`}
                      placeholder="root"
                      disabled={!enabled}
                      {...register(`mounts.${index}.permissions.owner` as any)}
                    />
                    {permissionsOwnerError && <span className="error-message">{permissionsOwnerError.message}</span>}
                  </div>
                  <div className="form-group">
                    <label className="form-label">Group (Optional)</label>
                    <input
                      type="text"
                      className={`form-input ${permissionsGroupError ? 'error' : ''}`}
                      placeholder="root"
                      disabled={!enabled}
                      {...register(`mounts.${index}.permissions.group` as any)}
                    />
                    {permissionsGroupError && <span className="error-message">{permissionsGroupError.message}</span>}
                  </div>
                  <div className="form-group">
                    <label className="form-label">Mode (Optional)</label>
                    <input
                      type="text"
                      className={`form-input ${permissionsModeError ? 'error' : ''}`}
                      placeholder="0755"
                      disabled={!enabled}
                      {...register(`mounts.${index}.permissions.mode` as any)}
                    />
                    <p className="text-sm text-gray-600 mt-1">Octal mode (e.g., 0755, 1777)</p>
                    {permissionsModeError && <span className="error-message">{permissionsModeError.message}</span>}
                  </div>
                </div>
              </div>
              {fields.length > 1 && (
                <Button variant="secondary" onClick={() => remove(index)} disabled={!enabled}>
                  Remove Mount Entry
                </Button>
              )}
            </div>
            );
          })}

          <Button variant="primary" onClick={() => append({
            name: '',
            source: '',
            mount_point: '',
            fs_type: 'nfs',
            mnt_opts: 'nosuid,rw,sync,hard',
            mount_on_oim: false,
            node_key: '',
            node_mount_point: [],
            permissions: { owner: 'root', group: 'root', mode: '0755' },
            functional_group_prefix: [''],
            groups: []
          } as any)} disabled={!enabled}>
            Add Mount Entry
          </Button>
        </div>
      </div>
    </>
  );
};
