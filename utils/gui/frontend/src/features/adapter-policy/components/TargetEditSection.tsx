import { useRef } from 'react';
import Button from '../../../components/Button';
import type { AdapterPolicyFormData } from '../schemas/adapterPolicy';

const FILTER_TYPES = [
  { value: 'substring', label: 'Substring Match' },
  { value: 'allowlist', label: 'Allowlist' },
  { value: 'field_in', label: 'Field In' },
  { value: 'any_of', label: 'Composite (Any Of)' },
];

interface TargetEditSectionProps {
  targetName: string;
  targetData: AdapterPolicyFormData['targets'][string];
  policy: AdapterPolicyFormData;
  onPolicyChange: (policy: AdapterPolicyFormData) => void;
  onClose: () => void;
  onAddSource: (targetName: string) => void;
  onRemoveSource: (targetName: string, sourceIdx: number) => void;
  onAddPull: (targetName: string, sourceIdx: number) => void;
  onRemovePull: (targetName: string, sourceIdx: number, pullIdx: number) => void;
  onAddDerived: (targetName: string) => void;
  onRemoveDerived: (targetName: string, derivedIdx: number) => void;
  errors: Record<string, string>;
}

export const TargetEditSection = ({
  targetName,
  targetData,
  policy,
  onPolicyChange,
  onClose,
  onAddSource,
  onRemoveSource,
  onAddPull,
  onRemovePull,
  onAddDerived,
  onRemoveDerived,
  errors,
}: TargetEditSectionProps) => {
  const editSectionRef = useRef<HTMLDivElement>(null);

  const updatePolicy = (updater: (policy: AdapterPolicyFormData) => AdapterPolicyFormData) => {
    onPolicyChange(updater(policy));
  };

  return (
    <div className="border rounded p-6 mb-4" ref={editSectionRef}>
      <h2 className="text-xl font-semibold mb-4">Edit: {targetName}</h2>

      <div className="space-y-2">
        <div>
          <label className="form-label">Transform Rules</label>
          <div className="space-y-2">
            <label className="form-checkbox">
              <input
                type="checkbox"
                checked={targetData.transform?.exclude_fields?.includes('architecture')}
                onChange={(e) => {
                  updatePolicy((prev) => {
                    const newPolicy = { ...prev };
                    const target = { ...newPolicy.targets[targetName] };
                    target.transform = {
                      ...target.transform,
                      exclude_fields: e.target.checked
                        ? [...(target.transform?.exclude_fields || []), 'architecture']
                        : (target.transform?.exclude_fields || []).filter((f) => f !== 'architecture'),
                    };
                    newPolicy.targets[targetName] = target;
                    return newPolicy;
                  });
                }}
              />
              <span>Exclude architecture field</span>
            </label>
          </div>
        </div>

        <div>
          <label className="form-label">Sources</label>
          {targetData.sources?.map((source, sourceIdx) => (
            <div key={sourceIdx} className="border rounded p-4 mb-4">
              <div className="flex items-center justify-between mb-4">
                <h4 className="font-medium">Source {sourceIdx + 1}</h4>
                <Button size="sm" onClick={() => onRemoveSource(targetName, sourceIdx)}>
                  Remove Source
                </Button>
              </div>

              <div>
                <label className="form-label">Source File</label>
                <select
                  className="form-select"
                  value={source.source_file}
                  onChange={(e) => {
                    updatePolicy((prev: AdapterPolicyFormData) => {
                      const newPolicy = { ...prev };
                      const target = { ...newPolicy.targets[targetName] };
                      const sources = [...target.sources];
                      sources[sourceIdx] = { ...sources[sourceIdx], source_file: e.target.value };
                      target.sources = sources;
                      newPolicy.targets[targetName] = target;
                      return newPolicy;
                    });
                  }}
                >
                  <option value="functional_layer.json">functional_layer.json</option>
                  <option value="base_os.json">base_os.json</option>
                  <option value="infrastructure.json">infrastructure.json</option>
                  <option value="drivers.json">drivers.json</option>
                  <option value="miscellaneous.json">miscellaneous.json</option>
                </select>
                {errors[`targets.${targetName}.sources.${sourceIdx}.source_file`] && (
                  <div className="error-message">{errors[`targets.${targetName}.sources.${sourceIdx}.source_file`]}</div>
                )}
              </div>

              <div className="space-y-2 mb-3">
                <label className="form-label">Pulls</label>
                {source.pulls?.map((pull, pullIdx) => (
                  <div key={pullIdx} className="border rounded p-3 bg-gray-50">
                    <div className="flex items-center justify-between mb-3">
                      <h5 className="text-sm font-medium">Pull {pullIdx + 1}</h5>
                      <Button size="sm" onClick={() => onRemovePull(targetName, sourceIdx, pullIdx)}>
                        Remove
                      </Button>
                    </div>
                    <div className="grid grid-cols-2 gap-4 mb-3">
                      <div>
                        <label className="form-label">Source Key</label>
                        <input
                          type="text"
                          className="form-input"
                          value={pull.source_key}
                          onChange={(e) => {
                            updatePolicy((prev: AdapterPolicyFormData) => {
                              const newPolicy = { ...prev };
                              const target = { ...newPolicy.targets[targetName] };
                              const sources = [...target.sources];
                              const source = { ...sources[sourceIdx] };
                              const pulls = [...source.pulls];
                              pulls[pullIdx] = { ...pulls[pullIdx], source_key: e.target.value };
                              source.pulls = pulls;
                              sources[sourceIdx] = source;
                              target.sources = sources;
                              newPolicy.targets[targetName] = target;
                              return newPolicy;
                            });
                          }}
                          placeholder="e.g., name"
                        />
                        {errors[`targets.${targetName}.sources.${sourceIdx}.pulls.${pullIdx}.source_key`] && (
                          <div className="error-message">{errors[`targets.${targetName}.sources.${sourceIdx}.pulls.${pullIdx}.source_key`]}</div>
                        )}
                      </div>
                      <div>
                        <label className="form-label">Target Key</label>
                        <input
                          type="text"
                          className="form-input"
                          value={pull.target_key}
                          onChange={(e) => {
                            updatePolicy((prev: AdapterPolicyFormData) => {
                              const newPolicy = { ...prev };
                              const target = { ...newPolicy.targets[targetName] };
                              const sources = [...target.sources];
                              const source = { ...sources[sourceIdx] };
                              const pulls = [...source.pulls];
                              pulls[pullIdx] = { ...pulls[pullIdx], target_key: e.target.value };
                              source.pulls = pulls;
                              sources[sourceIdx] = source;
                              target.sources = sources;
                              newPolicy.targets[targetName] = target;
                              return newPolicy;
                            });
                          }}
                          placeholder="e.g., name"
                        />
                        {errors[`targets.${targetName}.sources.${sourceIdx}.pulls.${pullIdx}.target_key`] && (
                          <div className="error-message">{errors[`targets.${targetName}.sources.${sourceIdx}.pulls.${pullIdx}.target_key`]}</div>
                        )}
                      </div>
                    </div>

                    <div>
                      <label className="form-label">Filter Type</label>
                      <select
                        className="form-select"
                        value={pull.filter?.type || ''}
                        onChange={(e) => {
                          const filterType = e.target.value as any;
                          updatePolicy((prev: AdapterPolicyFormData) => {
                            const newPolicy = { ...prev };
                            const target = { ...newPolicy.targets[targetName] };
                            const sources = [...target.sources];
                            const source = { ...sources[sourceIdx] };
                            const pulls = [...source.pulls];
                            const newPull = { ...pulls[pullIdx] };
                            
                            if (filterType === 'any_of') {
                              newPull.filter = {
                                type: filterType,
                                field: 'package',
                                case_sensitive: false,
                                filters: [{ type: 'substring', field: 'package', case_sensitive: false, values: [] }],
                              };
                            } else if (filterType) {
                              newPull.filter = {
                                type: filterType,
                                field: 'package',
                                case_sensitive: false,
                                values: [],
                              };
                            } else {
                              newPull.filter = undefined;
                            }
                            pulls[pullIdx] = newPull;
                            source.pulls = pulls;
                            sources[sourceIdx] = source;
                            target.sources = sources;
                            newPolicy.targets[targetName] = target;
                            return newPolicy;
                          });
                        }}
                      >
                        <option value="">No Filter</option>
                        {FILTER_TYPES.map((type) => (
                          <option key={type.value} value={type.value}>
                            {type.label}
                          </option>
                        ))}
                      </select>
                    </div>

                    {pull.filter?.type && pull.filter?.type !== 'any_of' && (
                      <div className="mt-3">
                        <label className="form-label">Filter Values</label>
                        <input
                          type="text"
                          className="form-input"
                          defaultValue={pull.filter.values?.join(', ') || ''}
                          onBlur={(e) => {
                            const values = e.target.value.split(',').map(v => v.trim()).filter(v => v);
                            updatePolicy((prev: AdapterPolicyFormData) => {
                              const newPolicy = { ...prev };
                              const target = { ...newPolicy.targets[targetName] };
                              const sources = [...target.sources];
                              const source = { ...sources[sourceIdx] };
                              const pulls = [...source.pulls];
                              const newPull = { ...pulls[pullIdx] };
                              newPull.filter = { ...newPull.filter, values };
                              pulls[pullIdx] = newPull;
                              source.pulls = pulls;
                              sources[sourceIdx] = source;
                              target.sources = sources;
                              newPolicy.targets[targetName] = target;
                              return newPolicy;
                            });
                          }}
                          placeholder="e.g., value1, value2, value3"
                        />
                      </div>
                    )}

                    {pull.filter?.type === 'any_of' && (
                      <div className="mt-3">
                        <label className="form-label">Composite Filters</label>
                        <div className="text-sm text-gray-600 mb-2">
                          {pull.filter.filters?.length || 0} filters configured
                        </div>
                      </div>
                    )}
                  </div>
                ))}
                <Button size="sm" onClick={() => onAddPull(targetName, sourceIdx)}>
                  Add Pull
                </Button>
              </div>
            </div>
          ))}
          <Button onClick={() => onAddSource(targetName)}>
            Add Source
          </Button>
        </div>

        <div>
          <label className="form-label">Derived Operations</label>
          {targetData.derived?.map((derived, derivedIdx) => (
            <div key={derivedIdx} className="border rounded p-4 mb-4">
              <div className="flex items-center justify-between mb-4">
                <h4 className="font-medium">Derived Operation {derivedIdx + 1}</h4>
                <Button size="sm" onClick={() => onRemoveDerived(targetName, derivedIdx)}>
                  Remove
                </Button>
              </div>

              <div className="grid grid-cols-2 gap-4 mb-3">
                <div>
                  <label className="form-label">Target Key</label>
                  <input
                    type="text"
                    className="form-input"
                    value={derived.target_key}
                    onChange={(e) => {
                      updatePolicy((prev: AdapterPolicyFormData) => {
                        const newPolicy = { ...prev };
                        const target = { ...newPolicy.targets[targetName] };
                        const derivedOps = [...(target.derived || [])];
                        derivedOps[derivedIdx] = { ...derivedOps[derivedIdx], target_key: e.target.value };
                        target.derived = derivedOps;
                        newPolicy.targets[targetName] = target;
                        return newPolicy;
                      });
                    }}
                    placeholder="e.g., common_name"
                  />
                </div>
                <div>
                  <label className="form-label">From Keys</label>
                  <input
                    type="text"
                    className="form-input"
                    defaultValue={derived.operation.from_keys?.join(', ') || ''}
                    onBlur={(e) => {
                      const fromKeys = e.target.value.split(',').map(k => k.trim()).filter(k => k);
                      updatePolicy((prev: AdapterPolicyFormData) => {
                        const newPolicy = { ...prev };
                        const target = { ...newPolicy.targets[targetName] };
                        const derivedOps = [...(target.derived || [])];
                        derivedOps[derivedIdx] = {
                          ...derivedOps[derivedIdx],
                          operation: { ...derivedOps[derivedIdx].operation, from_keys: fromKeys },
                        };
                        target.derived = derivedOps;
                        newPolicy.targets[targetName] = target;
                        return newPolicy;
                      });
                    }}
                    placeholder="e.g., key1, key2, key3"
                  />
                </div>
              </div>

              <div className="grid grid-cols-2 gap-4">
                <div>
                  <label className="form-label">Min Occurrences</label>
                  <input
                    type="number"
                    className="form-input"
                    value={derived.operation.min_occurrences}
                    onChange={(e) => {
                      updatePolicy((prev: AdapterPolicyFormData) => {
                        const newPolicy = { ...prev };
                        const target = { ...newPolicy.targets[targetName] };
                        const derivedOps = [...(target.derived || [])];
                        derivedOps[derivedIdx] = {
                          ...derivedOps[derivedIdx],
                          operation: { ...derivedOps[derivedIdx].operation, min_occurrences: parseInt(e.target.value) },
                        };
                        target.derived = derivedOps;
                        newPolicy.targets[targetName] = target;
                        return newPolicy;
                      });
                    }}
                    min="1"
                  />
                </div>
                <div>
                  <label className="form-label">Remove from Sources</label>
                  <label className="form-checkbox">
                    <input
                      type="checkbox"
                      checked={derived.operation.remove_from_sources}
                      onChange={(e) => {
                        updatePolicy((prev: AdapterPolicyFormData) => {
                          const newPolicy = { ...prev };
                          const target = { ...newPolicy.targets[targetName] };
                          const derivedOps = [...(target.derived || [])];
                          derivedOps[derivedIdx] = {
                            ...derivedOps[derivedIdx],
                            operation: { ...derivedOps[derivedIdx].operation, remove_from_sources: e.target.checked },
                          };
                          target.derived = derivedOps;
                          newPolicy.targets[targetName] = target;
                          return newPolicy;
                        });
                      }}
                    />
                    <span>Remove after extraction</span>
                  </label>
                </div>
              </div>
            </div>
          ))}
          <Button onClick={() => onAddDerived(targetName)}>
            Add Derived Operation
          </Button>
        </div>
      </div>

      <div className="flex mt-4">
        <Button onClick={onClose}>
          Close Editor
        </Button>
      </div>
    </div>
  );
};
