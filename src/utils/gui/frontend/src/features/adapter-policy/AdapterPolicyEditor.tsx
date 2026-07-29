import { useState, useEffect, useRef } from 'react';
import Layout from '../../components/Layout';
import Button from '../../components/Button';
import { adapterPolicySchema, type AdapterPolicyFormData } from './schemas/adapterPolicy';
import { showAlert } from '../toast/toastStore';
import { showConfirm } from '../confirmDialog/confirmDialogStore';
import { useAdapterPolicy, useSaveAdapterPolicy, useDeleteAdapterPolicy } from './hooks/useAdapterPolicy';
import { TargetListSection } from './components/TargetListSection';
import { TargetEditSection } from './components/TargetEditSection';
import { AddTargetSection } from './components/AddTargetSection';

const DEFAULT_POLICY: AdapterPolicyFormData = {
  version: '2.0.0',
  description: 'Adapter policy for package transformation',
  targets: {},
};

export const AdapterPolicyEditor = () => {
  const [policy, setPolicy] = useState<AdapterPolicyFormData>(DEFAULT_POLICY);
  const [selectedTarget, setSelectedTarget] = useState<string | null>(null);
  const [errors, setErrors] = useState<Record<string, string>>({});
  const [newTargetName, setNewTargetName] = useState<string>('');
  const [newTargetNameError, setNewTargetNameError] = useState<string>('');
  const [saveError, setSaveError] = useState<string>('');
  const [policySource, setPolicySource] = useState<'custom' | 'default'>('default');
  const [hasInitialized, setHasInitialized] = useState(false);
  const editSectionRef = useRef<HTMLDivElement>(null);

  const { data: policyData, isLoading, error: loadError } = useAdapterPolicy();
  const saveMutation = useSaveAdapterPolicy();
  const deleteMutation = useDeleteAdapterPolicy();

  // Sync policy from API response
  useEffect(() => {
    if (policyData) {
      if (policyData && policyData.policy) {
        setPolicy(policyData.policy);
        setPolicySource(policyData.source || 'default');
      } else {
        setPolicy(DEFAULT_POLICY);
        setPolicySource('default');
      }
      setHasInitialized(true);
    } else if (loadError) {
      setPolicy(DEFAULT_POLICY);
      setPolicySource('default');
      setHasInitialized(true);
    }
  }, [policyData, loadError]);

  // Scroll to edit section when target is selected
  useEffect(() => {
    if (selectedTarget && editSectionRef.current) {
      editSectionRef.current.scrollIntoView({ behavior: 'smooth', block: 'start' });
    }
  }, [selectedTarget]);

  // Real-time validation
  useEffect(() => {
    const result = adapterPolicySchema.safeParse(policy);
    if (!result.success) {
      const errorMessages: Record<string, string> = {};
      result.error.issues.forEach((err) => {
        const path = err.path.join('.');
        errorMessages[path] = err.message;
      });
      setErrors(errorMessages);
    } else {
      setErrors({});
    }
    // Clear save error when user edits
    setSaveError('');
  }, [policy]);

  const addTarget = () => {
    if (!newTargetName.trim()) {
      setNewTargetNameError('Target filename is required');
      return;
    }
    
    // Validate target name format
    if (!newTargetName.endsWith('.json')) {
      setNewTargetNameError('Target filename must end with .json');
      return;
    }

    // Validate that there's content before .json extension
    const nameWithoutExtension = newTargetName.slice(0, -5);
    if (!nameWithoutExtension.trim()) {
      setNewTargetNameError('Target filename must have a name before .json extension');
      return;
    }

    setPolicy((prev) => ({
      ...prev,
      targets: {
        ...prev.targets,
        [newTargetName]: {
          transform: { exclude_fields: ['architecture'] },
          sources: [],
          derived: [],
        },
      },
    }));
    setSelectedTarget(newTargetName);
    setNewTargetName('');
    setNewTargetNameError('');
  };

  const addSource = (targetName: string) => {
    setPolicy((prev: AdapterPolicyFormData) => ({
      ...prev,
      targets: {
        ...prev.targets,
        [targetName]: {
          ...prev.targets[targetName],
          sources: [
            ...(prev.targets[targetName]?.sources || []),
            {
              source_file: 'functional_layer.json',
              pulls: [],
            },
          ],
        },
      },
    }));
  };

  const removeSource = (targetName: string, sourceIndex: number) => {
    setPolicy((prev: AdapterPolicyFormData) => {
      const target = { ...prev.targets[targetName] };
      const sources = target.sources.filter((_, idx) => idx !== sourceIndex);
      target.sources = sources;
      return {
        ...prev,
        targets: { ...prev.targets, [targetName]: target },
      };
    });
  };

  const addPull = (targetName: string, sourceIndex: number) => {
    setPolicy((prev: AdapterPolicyFormData) => {
      const newPolicy = { ...prev };
      const target = { ...newPolicy.targets[targetName] };
      const sources = [...target.sources];
      const source = { ...sources[sourceIndex] };
      source.pulls = [...(source.pulls || []), { source_key: '', target_key: '' }];
      sources[sourceIndex] = source;
      target.sources = sources;
      newPolicy.targets[targetName] = target;
      return newPolicy;
    });
  };

  const removePull = (targetName: string, sourceIndex: number, pullIndex: number) => {
    setPolicy((prev: AdapterPolicyFormData) => {
      const newPolicy = { ...prev };
      const target = { ...newPolicy.targets[targetName] };
      const sources = [...target.sources];
      const source = { ...sources[sourceIndex] };
      source.pulls = source.pulls?.filter((_, idx) => idx !== pullIndex) || [];
      sources[sourceIndex] = source;
      target.sources = sources;
      newPolicy.targets[targetName] = target;
      return newPolicy;
    });
  };

  const addDerived = (targetName: string) => {
    setPolicy((prev: AdapterPolicyFormData) => {
      const newPolicy = { ...prev };
      const target = { ...newPolicy.targets[targetName] };
      target.derived = [...(target.derived || []), {
        target_key: '',
        operation: {
          type: 'extract_common',
          from_keys: [],
          min_occurrences: 2,
          remove_from_sources: true,
        },
      }];
      newPolicy.targets[targetName] = target;
      return newPolicy;
    });
  };

  const removeDerived = (targetName: string, derivedIndex: number) => {
    setPolicy((prev: AdapterPolicyFormData) => {
      const newPolicy = { ...prev };
      const target = { ...newPolicy.targets[targetName] };
      target.derived = target.derived?.filter((_, idx) => idx !== derivedIndex) || [];
      newPolicy.targets[targetName] = target;
      return newPolicy;
    });
  };

  const removeTarget = (targetName: string) => {
    console.log('Removing target:', targetName, 'Current targets:', Object.keys(policy.targets));
    setPolicy((prev: AdapterPolicyFormData) => {
      const newTargets = { ...prev.targets };
      delete newTargets[targetName];
      console.log('After deletion:', Object.keys(newTargets));
      return { ...prev, targets: newTargets };
    });
    if (selectedTarget === targetName) {
      setSelectedTarget(null);
    }
  };

  const onSubmit = async () => {
    const result = adapterPolicySchema.safeParse(policy);
    if (!result.success) {
      const errorMessages: Record<string, string> = {};
      result.error.issues.forEach((err) => {
        const path = err.path.join('.');
        errorMessages[path] = err.message;
      });
      setErrors(errorMessages);
      
      // Show showAlert for root-level errors that don't map to UI fields
      const rootErrors = result.error.issues.filter(err => err.path.length === 0);
      if (rootErrors.length > 0) {
        setSaveError(rootErrors.map(err => err.message).join(', '));
      } else {
        // Show the actual field-level errors instead of generic message
        const errorList = Object.entries(errorMessages)
          .map(([field, message]) => `${field}: ${message}`)
          .join('; ');
        setSaveError(`Please fix the validation errors: ${errorList}`);
      }
      return;
    }

    setSaveError('');
    try {
      await saveMutation.mutateAsync(policy);
      setPolicySource('custom');
      showAlert('Adapter policy saved successfully!');
    } catch (error) {
      console.error('Failed to save adapter policy:', error);
      setSaveError('Failed to save adapter policy. Please try again.');
    }
  };

  const handleRevertToDefault = () => {
    showConfirm(
      'Revert to Default',
      'Are you sure you want to revert to the default adapter policy? This will delete your custom policy.',
      async () => {
        try {
          await deleteMutation.mutateAsync();
          setPolicy(DEFAULT_POLICY);
          setPolicySource('default');
          showAlert('Reverted to default adapter policy');
        } catch (error) {
          console.error('Failed to revert to default policy:', error);
          showAlert('Failed to revert to default policy. Please try again.');
        }
      }
    );
  };

  const isPolicyValid = () => {
    const result = adapterPolicySchema.safeParse(policy);
    return result.success;
  };

  const selectedTargetData = selectedTarget ? policy.targets[selectedTarget] : null;

  return (
    <Layout>
      <div className="space-y-6">
        <div>
          <h1>Adapter Policy Editor</h1>
          <p className="text-gray-600">
            Create and edit adapter policies to transform source JSON files into target JSON files.
          </p>
        </div>

        {isLoading && (
          <div className="text-center py-4">
            <div className="text-gray-600">Loading adapter policy...</div>
          </div>
        )}

        {loadError && (
          <div className="bg-yellow-50 border border-yellow-200 rounded p-4 text-yellow-800">
            {loadError instanceof Error ? loadError.message : 'Failed to load adapter policy. Using default template.'}
          </div>
        )}

        {!isLoading && hasInitialized && (
          <>
            <div className="flex items-center justify-between">
              <div>
                <span className="text-sm text-gray-600">
                  Current policy: <strong>{policySource === 'custom' ? 'Custom' : 'Default'}</strong>
                </span>
              </div>
              {policySource === 'custom' && (
                <Button size="sm" onClick={handleRevertToDefault}>
                  Revert to Default
                </Button>
              )}
            </div>

            <div className="space-y-6">
              <div className="form-group">
                <label className="form-label">Description</label>
                <input
                  type="text"
                  className="form-input"
                  value={policy.description}
                  onChange={(e) => setPolicy({ ...policy, description: e.target.value })}
                  placeholder="Describe this adapter policy"
                />
                {errors['description'] && (
                  <div className="error-message">{errors['description']}</div>
                )}
              </div>

              <div className="form-group">
                <label className="form-label">Targets</label>
                
                <TargetListSection
                  targets={policy.targets}
                  onEditTarget={setSelectedTarget}
                  onRemoveTarget={removeTarget}
                />

                {/* Edit section when target is selected */}
                {selectedTarget && selectedTargetData && (
                  <div ref={editSectionRef}>
                    <TargetEditSection
                      targetName={selectedTarget}
                      targetData={selectedTargetData}
                      policy={policy}
                      onPolicyChange={setPolicy}
                      onClose={() => setSelectedTarget(null)}
                      onAddSource={addSource}
                      onRemoveSource={removeSource}
                      onAddPull={addPull}
                      onRemovePull={removePull}
                      onAddDerived={addDerived}
                      onRemoveDerived={removeDerived}
                      errors={errors}
                    />
                  </div>
                )}

                {/* Add new target section */}
                <AddTargetSection
                  newTargetName={newTargetName}
                  onNameChange={(name) => {
                    setNewTargetName(name);
                    setNewTargetNameError('');
                  }}
                  onAdd={addTarget}
                  error={newTargetNameError}
                />
              </div>
            </div>

            <div className="flex mt-4">
              <Button variant="primary" onClick={onSubmit} disabled={isLoading}>
                {isLoading ? 'Saving...' : 'Save Policy'}
              </Button>
              <Button
                onClick={() => {
                  console.log('Exporting policy with targets:', Object.keys(policy.targets));
                  const blob = new Blob([JSON.stringify(policy, null, 2)], { type: 'application/json' });
                  const url = URL.createObjectURL(blob);
                  const a = document.createElement('a');
                  a.href = url;
                  a.download = 'adapter_policy.json';
                  a.click();
                  URL.revokeObjectURL(url);
                }}
                disabled={!isPolicyValid() || isLoading}
              >
                Export JSON
              </Button>
            </div>
            {saveError && (
              <div className="error-message mt-2">
                {saveError}
              </div>
            )}
          </>
        )}
      </div>
    </Layout>
  );
};
