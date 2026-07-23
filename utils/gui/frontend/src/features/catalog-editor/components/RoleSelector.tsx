interface RoleSelectorProps {
  show: boolean;
  osFamily: string;
  osVersion: string;
  arch: string;
  selectedRole: string;
  roles: string[] | undefined;
  onOsFamilyChange: (value: string) => void;
  onOsVersionChange: (value: string) => void;
  onArchChange: (value: string) => void;
  onRoleChange: (value: string) => void;
  onAutoPopulate: () => void;
  onClose: () => void;
  isLoading?: boolean;
}

export const RoleSelector = ({
  show,
  osFamily,
  osVersion,
  arch,
  selectedRole,
  roles,
  onOsFamilyChange,
  onOsVersionChange,
  onArchChange,
  onRoleChange,
  onAutoPopulate,
  onClose,
  isLoading = false,
}: RoleSelectorProps) => {
  if (!show) return null;

  return (
    <div className="section-box">
      <h3>Auto-populate Layers from Roles</h3>
      <p className="text-small-muted mb-4">
        Select a role to automatically populate functional layers with suggested packages.
      </p>
      <div className="grid-4-col" style={{ gridTemplateColumns: 'minmax(0, 1fr) minmax(0, 1fr) minmax(0, 1fr) minmax(0, 3fr)' }}>
        <div className="form-group">
          <label className="form-label">OS Family</label>
          <select
            value={osFamily}
            onChange={(e) => onOsFamilyChange(e.target.value)}
            className="form-select"
          >
            <option value="rhel">RHEL</option>
            <option value="ubuntu">Ubuntu</option>
          </select>
        </div>

        <div className="form-group">
          <label className="form-label">OS Version</label>
          <input
            type="text"
            value={osVersion}
            onChange={(e) => onOsVersionChange(e.target.value)}
            className="form-input"
            placeholder="e.g. 10.0"
          />
        </div>

        <div className="form-group">
          <label className="form-label">Architecture</label>
          <select
            value={arch}
            onChange={(e) => onArchChange(e.target.value)}
            className="form-select"
          >
            <option value="x86_64">x86_64</option>
            <option value="aarch64">aarch64</option>
          </select>
        </div>

        <div className="form-group">
          <label className="form-label">Role</label>
          <select
            value={selectedRole}
            onChange={(e) => onRoleChange(e.target.value)}
            className="form-select"
          >
            <option value="">Select a role...</option>
            {roles && roles.map(role => (
              <option key={role} value={role}>{role}</option>
            ))}
          </select>
        </div>
      </div>
      
      <div className="flex gap-2">
        <button
          onClick={onAutoPopulate}
          disabled={!selectedRole || isLoading}
          className="button button-primary"
        >
          {isLoading ? 'Populating...' : 'Auto-populate Layer'}
        </button>
        <button
          onClick={onClose}
          className="button button-secondary"
        >
          Close
        </button>
      </div>
    </div>
  );
};
