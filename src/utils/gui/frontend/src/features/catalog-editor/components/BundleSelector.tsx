import { useState } from 'react';
import { useAvailableBundles } from '../hooks/useBundleSelection';

interface BundleSelectorProps {
  arch: string;
  osFamily: string;
  version: string;
  selectedBundles: Set<string>;
  onBundleToggle: (bundleName: string, required: boolean) => void;
  bundleMetadata?: Record<string, { required: boolean; description: string }>;
  showOnlyType?: 'functional' | 'infrastructure' | 'os' | 'all';
  expandedBundles?: Set<string>;
  onBundleExpand?: (bundleName: string) => void;
  selectedPackages?: Record<string, Set<string>>;
  onPackageToggle?: (bundleName: string, packageId: string) => void;
  bundlePackageData?: Record<string, Record<string, any[]>>;
}

const BundleSelector = ({
  arch,
  osFamily,
  version,
  selectedBundles,
  onBundleToggle,
  bundleMetadata = {},
  showOnlyType = 'all',
  expandedBundles = new Set(),
  onBundleExpand,
  selectedPackages = {},
  onPackageToggle,
  bundlePackageData = {}
}: BundleSelectorProps) => {
  const [searchQuery, setSearchQuery] = useState('');
  
  const { data: bundles, isLoading, error } = useAvailableBundles(arch, osFamily, version);
  
  const filteredBundles = bundles?.filter(bundle => {
    if (showOnlyType !== 'all' && bundle.type !== showOnlyType) {
      return false;
    }
    if (searchQuery && !bundle.name.toLowerCase().includes(searchQuery.toLowerCase())) {
      return false;
    }
    return true;
  }) || [];

  if (isLoading) {
    return <p>Loading bundles...</p>;
  }

  if (error) {
    return <p className="error">Failed to load bundles</p>;
  }

  if (filteredBundles.length === 0) {
    return <p className="text-center text-secondary">No bundles found</p>;
  }

  return (
    <div>
      <div className="form-group mb-4">
        <label className="form-label">Search bundles:</label>
        <input
          type="text"
          placeholder="Search..."
          value={searchQuery}
          onChange={(e) => setSearchQuery(e.target.value)}
          className="form-input"
        />
      </div>
      
      <div className="grid-auto-fit items-start" style={{ gap: '12px', overflow: 'auto' }}>
        {filteredBundles.map(bundle => {
          const metadata = bundleMetadata[bundle.name] || { required: false, description: '' };
          const isSelected = selectedBundles.has(bundle.name);
          
          return (
            <div
              key={bundle.name}
              className={`bundle-card ${isSelected ? 'bundle-card-selected' : ''}`}
              style={{ cursor: metadata.required ? 'not-allowed' : undefined }}
            >
              <div className="flex justify-between items-start">
                <label className={`flex items-center gap-2 ${metadata.required ? '' : 'cursor-pointer'}`} style={{ cursor: metadata.required ? 'not-allowed' : undefined }}>
                  <input
                    type="checkbox"
                    checked={isSelected}
                    onChange={(e) => {
                      e.stopPropagation();
                      onBundleToggle(bundle.name, metadata.required);
                    }}
                    disabled={metadata.required}
                    style={{ verticalAlign: 'middle' }}
                  />
                  <span style={{ fontWeight: 600, verticalAlign: 'middle' }}>{bundle.name}</span>
                  {metadata.required && <span className="package-tag">Required</span>}
                </label>
                {onBundleExpand && (
                  <button
                    type="button"
                    onClick={(e) => {
                      e.stopPropagation();
                      onBundleExpand(bundle.name);
                    }}
                    className="button-expand"
                  >
                    {expandedBundles.has(bundle.name) ? '▼' : '▶'}
                  </button>
                )}
              </div>
              
              <div className="text-secondary text-xs" style={{ marginTop: '4px', marginBottom: '4px', marginLeft: '10px' }}>
                {bundle.package_count} packages
              </div>
              
              <div className="flex items-center gap-2">
                <span className="package-tag">{bundle.type}</span>
              </div>
              
              {metadata.description && (
                <p className="text-secondary text-xs mt-2">
                  {metadata.description}
                </p>
              )}
              
              {expandedBundles.has(bundle.name) && bundlePackageData[bundle.name] && (
                <div style={{ marginTop: '12px', borderTop: '1px solid #e0e0e0', paddingTop: '8px' }}>
                  <div className="text-subtitle-xs">
                    Select packages:
                  </div>
                  {Object.entries(bundlePackageData[bundle.name]).map(([section, packages]: [string, any[]]) => (
                    <div key={section} className="mb-2">
                      <div className="text-small-muted text-xs" style={{ marginBottom: '4px' }}>
                        {section}
                      </div>
                      {packages.map((pkg: any) => {
                        const pkgId = `${pkg.package}_${pkg.type}`;
                        const bundlePkgs = selectedPackages[bundle.name] || new Set();
                        const isPkgSelected = bundlePkgs.has(pkgId);
                        
                        return (
                          <label key={pkgId} className={`flex items-center gap-2 text-xs ${metadata.required ? '' : 'cursor-pointer'}`} style={{ padding: '4px 0' }}>
                            <input
                              type="checkbox"
                              checked={isPkgSelected}
                              onChange={() => onPackageToggle && onPackageToggle(bundle.name, pkgId)}
                              disabled={metadata.required}
                            />
                            <span>{pkg.package}</span>
                            <span className="text-secondary" style={{ fontSize: '10px' }}>
                              ({pkg.type})
                            </span>
                          </label>
                        );
                      })}
                    </div>
                  ))}
                </div>
              )}
            </div>
          );
        })}
      </div>
    </div>
  );
};

export default BundleSelector;
