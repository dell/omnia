import type { UseFormRegister, Control } from 'react-hook-form';
import { useFieldArray } from 'react-hook-form';
import Button from '../../../../components/Button';
import { StorageConfigFormData } from '../../schemas/storageConfig';
import type { FormFieldError } from '../../hooks/useFormErrors';

interface PowerVaultTabProps {
  register: UseFormRegister<StorageConfigFormData>;
  control: Control<StorageConfigFormData>;
  enabled: boolean;
  onToggle: (enabled: boolean) => void;
  onClear: () => void;
  getError: (path: string) => FormFieldError | undefined;
}

export const PowerVaultTab = ({ register, control, enabled, onToggle, onClear, getError }: PowerVaultTabProps) => {
  const { fields, append, remove } = useFieldArray({
    control,
    name: 'powervault_config',
  });

  return (
    <>
      <div className="form-group">
        <label className="form-label">PowerVault iSCSI Configurations (Optional)</label>
        <div className="form-checkbox">
          <input
            type="checkbox"
            id="enable-powervault"
            checked={enabled}
            onChange={(e) => {
              onToggle(e.target.checked);
              if (!e.target.checked) {
                onClear();
              }
            }}
          />
          <label htmlFor="enable-powervault">Enable PowerVault iSCSI Configuration</label>
        </div>
      </div>

      <div className={!enabled ? 'disabled-section' : ''}>
        <div className="space-y-2 section-style">
          <p className="text-sm text-gray-600">
            Configure Dell PowerVault iSCSI storage arrays for nodes.
          </p>

          {fields.map((field, index) => {
            const nameError = getError(`powervault_config.${index}.name`);
            const mountPointError = getError(`powervault_config.${index}.mount_point`);
            const portError = getError(`powervault_config.${index}.port`);
            const ipError = getError(`powervault_config.${index}.ip`);
            const iscsiInitiatorError = getError(`powervault_config.${index}.iscsi_initiator`);
            const volumeIdError = getError(`powervault_config.${index}.volume_id`);
            const fsTypeError = getError(`powervault_config.${index}.fs_type`);
            const functionalGroupPrefixError = getError(`powervault_config.${index}.functional_group_prefix`);
            const nodeKeyError = getError(`powervault_config.${index}.node_key`);
            const nodeMountPointError = getError(`powervault_config.${index}.node_mount_point`);
            const permissionsOwnerError = getError(`powervault_config.${index}.permissions.owner`);
            const permissionsGroupError = getError(`powervault_config.${index}.permissions.group`);
            const permissionsModeError = getError(`powervault_config.${index}.permissions.mode`);
            const dumpFreqError = getError(`powervault_config.${index}.dump_freq`);
            const fsckPassError = getError(`powervault_config.${index}.fsck_pass`);
            const mntOptsError = getError(`powervault_config.${index}.mnt_opts`);
            const mountParamsError = getError(`powervault_config.${index}.mount_params`);

            return (
            <div key={field.id} className="space-y-2 section-style">
              <div className="form-row">
                <div className="form-group">
                  <label className="form-label">Name (Required)</label>
                  <input
                    type="text"
                    className={`form-input ${nameError ? 'error' : ''}`}
                    placeholder="e.g., pv_iscsi"
                    disabled={!enabled}
                    {...register(`powervault_config.${index}.name`)}
                  />
                  {nameError && <span className="error-message">{nameError.message}</span>}
                </div>
                <div className="form-group">
                  <label className="form-label">Mount Point (Required)</label>
                  <input
                    type="text"
                    className={`form-input ${mountPointError ? 'error' : ''}`}
                    placeholder="e.g., /mnt/pv"
                    disabled={!enabled}
                    {...register(`powervault_config.${index}.mount_point`)}
                  />
                  {mountPointError && <span className="error-message">{mountPointError.message}</span>}
                </div>
                <div className="form-group">
                  <label className="form-label">Port (Optional)</label>
                  <input
                    type="number"
                    className={`form-input ${portError ? 'error' : ''}`}
                    placeholder="3260"
                    disabled={!enabled}
                    {...register(`powervault_config.${index}.port`)}
                  />
                  {portError && <span className="error-message">{portError.message}</span>}
                </div>
              </div>
              <div className="form-row form-row-2-col">
                <div className="form-group">
                  <label className="form-label">Controller IPs (Required)</label>
                  <input
                    type="text"
                    className={`form-input ${ipError ? 'error' : ''}`}
                    placeholder="e.g., 192.168.1.100,192.168.1.101"
                    disabled={!enabled}
                    {...register(`powervault_config.${index}.ip` as any)}
                  />
                  <p className="text-sm text-gray-600 mt-1">Comma-separated IPv4 addresses</p>
                  {ipError && <span className="error-message">{ipError.message}</span>}
                </div>
                <div className="form-group">
                  <label className="form-label">Functional Group Prefix (Required)</label>
                  <input
                    type="text"
                    className={`form-input ${functionalGroupPrefixError ? 'error' : ''}`}
                    placeholder="e.g., slurm,login"
                    disabled={!enabled}
                    {...register(`powervault_config.${index}.functional_group_prefix` as any)}
                  />
                  <p className="text-sm text-gray-600 mt-1">Comma-separated values (required)</p>
                  {functionalGroupPrefixError && <span className="error-message">{functionalGroupPrefixError.message}</span>}
                </div>
              </div>
              <div className="form-row form-row-2-col">
                <div className="form-group">
                  <label className="form-label">iSCSI Initiator IQN (Required)</label>
                  <input
                    type="text"
                    className={`form-input ${iscsiInitiatorError ? 'error' : ''}`}
                    placeholder="e.g., iqn.2024-01.com.example:hostname"
                    disabled={!enabled}
                    {...register(`powervault_config.${index}.iscsi_initiator`)}
                  />
                  {iscsiInitiatorError && <span className="error-message">{iscsiInitiatorError.message}</span>}
                </div>
                <div className="form-group">
                  <label className="form-label">Volume ID (Required)</label>
                  <input
                    type="text"
                    className={`form-input ${volumeIdError ? 'error' : ''}`}
                    placeholder="e.g., 123456789abcdef"
                    disabled={!enabled}
                    {...register(`powervault_config.${index}.volume_id`)}
                  />
                  {volumeIdError && <span className="error-message">{volumeIdError.message}</span>}
                </div>
              </div>
              <div className="form-row">
                <div className="form-group">
                  <label className="form-label">Filesystem Type (Optional)</label>
                  <select
                    className={`form-select ${fsTypeError ? 'error' : ''}`}
                    disabled={!enabled}
                    {...register(`powervault_config.${index}.fs_type`)}
                  >
                    <option value="">Select...</option>
                    <option value="xfs">xfs</option>
                    <option value="ext4">ext4</option>
                    <option value="ext3">ext3</option>
                    <option value="ext2">ext2</option>
                    <option value="nfs">nfs</option>
                    <option value="nfs4">nfs4</option>
                    <option value="cifs">cifs</option>
                    <option value="ntfs">ntfs</option>
                    <option value="auto">auto</option>
                  </select>
                  {fsTypeError && <span className="error-message">{fsTypeError.message}</span>}
                </div>
                <div className="form-group">
                  <label className="form-label">Dump Frequency (0-2) (Optional)</label>
                  <input
                    type="text"
                    className={`form-input ${dumpFreqError ? 'error' : ''}`}
                    placeholder="0"
                    disabled={!enabled}
                    {...register(`powervault_config.${index}.dump_freq`)}
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
                    {...register(`powervault_config.${index}.fsck_pass`)}
                  />
                  {fsckPassError && <span className="error-message">{fsckPassError.message}</span>}
                </div>
              </div>
              <div className="form-row form-row-2-col">
                <div className="form-group">
                  <label className="form-label">Mount Options (Optional)</label>
                  <input
                    type="text"
                    className={`form-input ${mntOptsError ? 'error' : ''}`}
                    placeholder="e.g., _netdev"
                    disabled={!enabled}
                    {...register(`powervault_config.${index}.mnt_opts`)}
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
                    {...register(`powervault_config.${index}.mount_params`)}
                  />
                  {mountParamsError && <span className="error-message">{mountParamsError.message}</span>}
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
                      {...register(`powervault_config.${index}.node_key`)}
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
                      placeholder="e.g., /var/lib/mysql,/var/spool/slurm"
                      disabled={!enabled}
                      {...register(`powervault_config.${index}.node_mount_point` as any)}
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
                      {...register(`powervault_config.${index}.permissions.owner` as any)}
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
                      {...register(`powervault_config.${index}.permissions.group` as any)}
                    />
                    {permissionsGroupError && <span className="error-message">{permissionsGroupError.message}</span>}
                  </div>
                  <div className="form-group">
                    <label className="form-label">Mode (Optional)</label>
                    <input
                      type="text"
                      className={`form-input ${permissionsModeError ? 'error' : ''}`}
                      placeholder="0750"
                      disabled={!enabled}
                      {...register(`powervault_config.${index}.permissions.mode` as any)}
                    />
                    <p className="text-sm text-gray-600 mt-1">Octal mode (e.g., 0750, 0755)</p>
                    {permissionsModeError && <span className="error-message">{permissionsModeError.message}</span>}
                  </div>
                </div>
              </div>
              {fields.length > 1 && (
                <Button variant="secondary" onClick={() => remove(index)} disabled={!enabled}>
                  Remove PowerVault Entry
                </Button>
              )}
            </div>
            );
          })}

          <Button
            variant="primary"
            onClick={() => append({
              name: '',
              ip: [''],
              port: 3260,
              iscsi_initiator: '',
              volume_id: '',
              mount_point: '',
              fs_type: 'xfs',
              node_key: '',
              node_mount_point: [],
              permissions: { owner: 'root', group: 'root', mode: '0755' },
              functional_group_prefix: ['']
            } as any)}
            disabled={!enabled}
          >
            Add PowerVault Entry
          </Button>
        </div>
      </div>
    </>
  );
};
