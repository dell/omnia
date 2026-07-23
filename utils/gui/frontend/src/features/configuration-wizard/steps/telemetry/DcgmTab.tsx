interface DcgmTabProps {
}

export const DcgmTab = ({}: DcgmTabProps) => {
  return (
    <div className="space-y-6">
      <div className="form-group">
        <label className="form-label">DCGM Telemetry Configuration</label>
        <div className="section-style">
          <div className="space-y-2">
            <p className="text-small-muted">DCGM is enabled. Additional configuration fields will appear here as needed.</p>
          </div>
        </div>
      </div>
    </div>
  );
};
