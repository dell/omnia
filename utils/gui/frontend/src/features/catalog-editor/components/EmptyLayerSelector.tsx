interface EmptyLayerSelectorProps {
  show: boolean;
  selectedLayer: string;
  predefinedLayers: string[];
  customLayerName: string;
  customLayerError?: string;
  onLayerChange: (value: string) => void;
  onCustomLayerNameChange: (value: string) => void;
  onAddLayer: () => void;
  onClose: () => void;
}

export const EmptyLayerSelector = ({
  show,
  selectedLayer,
  predefinedLayers,
  customLayerName,
  customLayerError,
  onLayerChange,
  onCustomLayerNameChange,
  onAddLayer,
  onClose,
}: EmptyLayerSelectorProps) => {
  if (!show) return null;

  const isCustom = selectedLayer === '__custom__';
  const isAddDisabled = !selectedLayer || (isCustom && (!customLayerName.trim() || !!customLayerError));

  return (
    <div className="section-box">
      <h3>Add Empty Functional Layer</h3>
      <p className="text-small-muted mb-4">
        Select a predefined functional layer name or choose Custom to create a named empty layer.
      </p>
      <div className="flex gap-4 flex-wrap">
        <div className="form-group" style={{ flex: '0 1 auto', minWidth: 0 }}>
          <label className="form-label">Functional Layer Name</label>
          <select
            value={selectedLayer}
            onChange={(e) => onLayerChange(e.target.value)}
            className="form-select"
          >
            <option value="">Select a layer name...</option>
            {predefinedLayers.map(layerName => (
              <option key={layerName} value={layerName}>{layerName}</option>
            ))}
            <option value="__custom__">Custom...</option>
          </select>
        </div>
        {isCustom && (
          <div className="form-group flex-1" style={{ minWidth: 0 }}>
            <label className="form-label">Custom Layer Name</label>
            <input
              type="text"
              value={customLayerName}
              onChange={(e) => onCustomLayerNameChange(e.target.value)}
              placeholder="e.g. my_custom_layer_x86_64"
              className="form-input"
            />
            {customLayerError && (
              <div className="text-error text-xs mt-1">{customLayerError}</div>
            )}
          </div>
        )}
      </div>

      <div className="flex gap-2">
        <button
          onClick={onAddLayer}
          disabled={isAddDisabled}
          className="button button-primary"
        >
          Add Empty Layer
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
