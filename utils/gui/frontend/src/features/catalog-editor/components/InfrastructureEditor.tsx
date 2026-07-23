import { useState, useEffect, useRef } from 'react';
import { useForm, FormProvider } from 'react-hook-form';
import { zodResolver } from '@hookform/resolvers/zod';
import { useCatalogStore } from '../catalogStore';
import {
  useAddInfrastructurePackage,
  useDeleteInfrastructurePackage,
  useUpdateInfrastructurePackage,
} from '../hooks/useCatalog';
import {
  InfrastructurePackageSchema,
  type PackageTypeValue,
  type InfrastructurePackage,
} from '../schemas/catalogSchema';
import BundleSelector from './BundleSelector';
import PackageForm from './PackageForm';
import { showConfirm } from '../../confirmDialog/confirmDialogStore';
import { showAlert } from '../../toast/toastStore';

const defaultPackage: InfrastructurePackage = {
  Name: '',
  Type: 'image' as PackageTypeValue,
  Architecture: ['x86_64'],
  Version: '',
  Tag: '',
  SupportedFunctions: [{ Name: 'csi' }],
  Sources: [],
};

const InfrastructureEditor = () => {
  const catalogRoot = useCatalogStore((s) => s.catalogRoot);
  const setCatalogRoot = useCatalogStore((s) => s.setCatalogRoot);
  const addPkg = useAddInfrastructurePackage();
  const deletePkg = useDeleteInfrastructurePackage();
  const updatePkg = useUpdateInfrastructurePackage();
  const [showAddForm, setShowAddForm] = useState(false);
  const [showBundleSelector, setShowBundleSelector] = useState(false);
  const [editingId, setEditingId] = useState<string | null>(null);
  const editFormRef = useRef<HTMLDivElement>(null);

  const addMethods = useForm<InfrastructurePackage>({
    resolver: zodResolver(InfrastructurePackageSchema),
    defaultValues: defaultPackage,
    mode: 'onSubmit',
  });

  const editMethods = useForm<InfrastructurePackage>({
    resolver: zodResolver(InfrastructurePackageSchema),
    defaultValues: defaultPackage,
    mode: 'onSubmit',
  });

  const isDuplicateName = (name: string, excludeId?: string | null) => {
    if (!catalogRoot?.Catalog?.InfrastructurePackages) return false;
    return Object.entries(catalogRoot.Catalog.InfrastructurePackages).some(
      ([id, pkg]) => pkg.Name === name && id !== excludeId
    );
  };
  const [osFamily, setOsFamily] = useState('rhel');
  const [osVersion, setOsVersion] = useState('10.0');
  const [arch, setArch] = useState('x86_64');
  const [selectedBundles, setSelectedBundles] = useState<Set<string>>(new Set());
  const [expandedBundles, setExpandedBundles] = useState<Set<string>>(new Set());
  const [selectedPackages, setSelectedPackages] = useState<Record<string, Set<string>>>({});
  const [bundlePackageData, setBundlePackageData] = useState<Record<string, Record<string, any[]>>>({});
  const [isImporting, setIsImporting] = useState(false);
  const prevInfraPackageKeysRef = useRef<string>('');

  // Automatically derive Infrastructure from InfrastructurePackages
  useEffect(() => {
    if (!catalogRoot?.Catalog?.InfrastructurePackages) return;

    const infraPackageIds = Object.keys(catalogRoot.Catalog.InfrastructurePackages).sort();
    const keysString = infraPackageIds.join(',');
    if (keysString === prevInfraPackageKeysRef.current) return;
    prevInfraPackageKeysRef.current = keysString;

    // Update Infrastructure to match InfrastructurePackages
    const updatedCatalog = {
      ...catalogRoot,
      Catalog: {
        ...catalogRoot.Catalog,
        Infrastructure: [{
          Name: 'csi',
          InfrastructurePackages: infraPackageIds
        }]
      }
    };

    setCatalogRoot(updatedCatalog);
  }, [catalogRoot?.Catalog?.InfrastructurePackages, setCatalogRoot]);

  const bundleMetadata: Record<string, { required: boolean; description: string }> = {
    csi_driver_powerscale: {
      required: false,
      description: 'CSI driver for PowerScale storage'
    }
  };

  const handleBundleToggle = async (bundleName: string, required: boolean) => {
    if (required) return;
    const newSelected = new Set(selectedBundles);
    
    if (newSelected.has(bundleName)) {
      // Deselect bundle and clear individual package selections
      newSelected.delete(bundleName);
      setSelectedPackages(prev => {
        const updated = { ...prev };
        delete updated[bundleName];
        return updated;
      });
    } else {
      // Select bundle and select all packages
      newSelected.add(bundleName);
      
      // Fetch package data if not already loaded
      if (!bundlePackageData[bundleName]) {
        try {
          const response = await fetch(
            `/api/v1/catalog-editor/os-packages/bundle/${bundleName}?arch=${arch}&os_family=${osFamily}&version=${osVersion}`
          );
          if (response.ok) {
            const data = await response.json();
            setBundlePackageData(prev => ({
              ...prev,
              [bundleName]: data.packages
            }));
            
            // Select all packages from the fetched data
            const allPackageIds = new Set<string>();
            for (const [_section, packages] of Object.entries(data.packages)) {
              for (const pkg of packages as any[]) {
                const pkgId = `${pkg.package}_${pkg.type}`;
                allPackageIds.add(pkgId);
              }
            }
            setSelectedPackages(prev => ({
              ...prev,
              [bundleName]: allPackageIds
            }));
          }
        } catch (error) {
          console.error('Failed to fetch bundle packages:', error);
        }
      } else {
        // Select all packages from already loaded data
        const allPackageIds = new Set<string>();
        for (const [_section, packages] of Object.entries(bundlePackageData[bundleName])) {
          for (const pkg of packages) {
            const pkgId = `${pkg.package}_${pkg.type}`;
            allPackageIds.add(pkgId);
          }
        }
        setSelectedPackages(prev => ({
          ...prev,
          [bundleName]: allPackageIds
        }));
      }
    }
    setSelectedBundles(newSelected);
  };

  const handleBundleExpand = async (bundleName: string) => {
    // Toggle expanded state
    const newExpanded = new Set(expandedBundles);
    if (newExpanded.has(bundleName)) {
      newExpanded.delete(bundleName);
    } else {
      newExpanded.add(bundleName);
    }
    setExpandedBundles(newExpanded);

    // Fetch package data if not already loaded
    if (!bundlePackageData[bundleName]) {
      const response = await fetch(
        `/api/v1/catalog-editor/os-packages/bundle/${bundleName}?arch=${arch}&os_family=${osFamily}&version=${osVersion}`
      );
      if (response.ok) {
        const data = await response.json();
        setBundlePackageData(prev => ({
          ...prev,
          [bundleName]: data.packages
        }));
      }
    }
  };

  const handlePackageToggle = (bundleName: string, packageId: string) => {
    setSelectedPackages(prev => {
      const bundlePackages = prev[bundleName] || new Set();
      const newBundlePackages = new Set(bundlePackages);
      if (newBundlePackages.has(packageId)) {
        newBundlePackages.delete(packageId);
      } else {
        newBundlePackages.add(packageId);
      }
      return { ...prev, [bundleName]: newBundlePackages };
    });
  };

  const handleOpenBundleSelector = async () => {
    setShowBundleSelector(true);
    
    // Get existing infrastructure packages to initialize selection state
    const existingPackages = new Map<string, any>();
    if (catalogRoot?.Catalog?.InfrastructurePackages) {
      for (const [_pkgId, pkg] of Object.entries(catalogRoot.Catalog.InfrastructurePackages)) {
        const key = `${pkg.Name}_${pkg.Type}_${pkg.Version || ''}_${pkg.Tag || ''}`;
        existingPackages.set(key, pkg);
      }
    }

    // Fetch all available bundles
    const response = await fetch(
      `/api/v1/catalog-editor/os-packages/bundles?arch=${arch}&os_family=${osFamily}&version=${osVersion}`
    );
    if (!response.ok) return;
    
    const data = await response.json();
    const bundles = data.bundles as { name: string; type: string }[];
    
    // Initialize selection state based on existing packages
    const newSelectedBundles = new Set<string>();
    const newSelectedPackages: Record<string, Set<string>> = {};
    const newBundlePackageData: Record<string, Record<string, any[]>> = {};

    const bundleResults = await Promise.allSettled(
      bundles
        .filter((bundle) => bundle.type === 'infrastructure')
        .map(async (bundle) => {
          const bundleResponse = await fetch(
            `/api/v1/catalog-editor/os-packages/bundle/${bundle.name}?arch=${arch}&os_family=${osFamily}&version=${osVersion}`
          );
          if (!bundleResponse.ok) throw new Error(`Failed to fetch bundle ${bundle.name}`);
          return { name: bundle.name, data: await bundleResponse.json() };
        })
    );

    for (const result of bundleResults) {
      if (result.status === 'rejected') {
        console.error(result.reason);
        continue;
      }

      const { name: bundleName, data: bundleData } = result.value;
      newBundlePackageData[bundleName] = bundleData.packages;

      const bundlePackageIds = new Set<string>();
      let allPackagesExist = true;
      let somePackagesExist = false;

      for (const [_sectionName, pkgList] of Object.entries(bundleData.packages)) {
        for (const pkg of pkgList as any[]) {
          const pkgId = `${pkg.package}_${pkg.type}`;
          const uniqueKey = `${pkg.package}_${pkg.type}_${pkg.version || ''}_${pkg.tag || ''}`;

          if (existingPackages.has(uniqueKey)) {
            bundlePackageIds.add(pkgId);
            somePackagesExist = true;
          } else {
            allPackagesExist = false;
          }
        }
      }

      // If all packages exist, check the bundle
      if (allPackagesExist && bundlePackageIds.size > 0) {
        newSelectedBundles.add(bundleName);
      } else if (somePackagesExist) {
        // If some packages exist, only check those packages
        newSelectedPackages[bundleName] = bundlePackageIds;
      }
    }
    
    setSelectedBundles(newSelectedBundles);
    setSelectedPackages(newSelectedPackages);
    setBundlePackageData(newBundlePackageData);
  };

  const handleImportBundles = async () => {
    if (selectedBundles.size === 0 && Object.keys(selectedPackages).length === 0) return;
    setIsImporting(true);

    try {
      // Get existing infrastructure packages to prevent duplicates
      const existingPackages = new Map<string, any>();
      if (catalogRoot?.Catalog?.InfrastructurePackages) {
        for (const [_pkgId, pkg] of Object.entries(catalogRoot.Catalog.InfrastructurePackages)) {
          // Create a unique key based on Name, Type, Version, and Tag
          const key = `${pkg.Name}_${pkg.Type}_${pkg.Version || ''}_${pkg.Tag || ''}`;
          existingPackages.set(key, pkg);
        }
      }

      const updatedPackages = { ...(catalogRoot?.Catalog?.InfrastructurePackages || {}) };

      // Fetch all missing bundle data in parallel
      const bundleNamesToFetch = new Set<string>([...selectedBundles, ...Object.keys(selectedPackages)]);
      const missingBundleNames = [...bundleNamesToFetch].filter((name) => !bundlePackageData[name]);

      const fetchResults = await Promise.allSettled(
        missingBundleNames.map(async (name) => {
          const response = await fetch(
            `/api/v1/catalog-editor/os-packages/bundle/${name}?arch=${arch}&os_family=${osFamily}&version=${osVersion}`
          );
          if (!response.ok) throw new Error(`Failed to fetch bundle ${name}`);
          return { name, data: await response.json() };
        })
      );

      const fetchedBundleData = { ...bundlePackageData };
      for (const result of fetchResults) {
        if (result.status === 'fulfilled') {
          fetchedBundleData[result.value.name] = result.value.data.packages;
        } else {
          console.error(result.reason);
        }
      }
      setBundlePackageData(fetchedBundleData);

      const payloads: any[] = [];
      const addPackage = (pkg: any) => {
        const uniqueKey = `${pkg.package}_${pkg.type}_${pkg.version || ''}_${pkg.tag || ''}`;
        // Skip if package already exists in catalog or has been queued in this import
        if (existingPackages.has(uniqueKey)) return;
        existingPackages.set(uniqueKey, pkg.package);

        let sources: any[] | undefined;
        if (pkg.repo_name) {
          sources = [{ Architecture: arch, RepoName: pkg.repo_name }];
        } else if (pkg.url) {
          sources = [{ Architecture: arch, Uri: pkg.url }];
        }

        payloads.push({
          Name: pkg.package,
          Type: pkg.type as PackageTypeValue,
          Architecture: [arch],
          SupportedFunctions: [{ Name: 'csi' }],
          Sources: sources,
          Version: pkg.version || undefined,
          Tag: pkg.tag || undefined,
        });
      };

      // Queue packages from whole selected bundles
      for (const bundleName of selectedBundles) {
        const packages = fetchedBundleData[bundleName];
        if (!packages) continue;
        for (const pkgList of Object.values(packages)) {
          for (const pkg of pkgList as any[]) addPackage(pkg);
        }
      }

      // Queue individually selected packages
      for (const [bundleName, bundleSelectedPackages] of Object.entries(selectedPackages)) {
        // Skip if this bundle is already selected as a whole
        if (selectedBundles.has(bundleName)) continue;
        const packages = fetchedBundleData[bundleName];
        if (!packages) continue;
        for (const pkgList of Object.values(packages)) {
          for (const pkg of pkgList as any[]) {
            const pkgId = `${pkg.package}_${pkg.type}`;
            if (bundleSelectedPackages.has(pkgId)) addPackage(pkg);
          }
        }
      }

      // Import all packages in parallel
      const importResults = await Promise.allSettled(
        payloads.map((payload) =>
          addPkg.mutateAsync(payload).then((result: any) => {
            const packageId = result?.package_id ?? payload.Name;
            updatedPackages[packageId] = payload;
          })
        )
      );

      importResults.forEach((result) => {
        if (result.status === 'rejected') {
          console.error('Failed to add package:', result.reason);
        }
      });

      // Update local catalogRoot with the new packages
      if (catalogRoot) {
        setCatalogRoot({
          ...catalogRoot,
          Catalog: {
            ...catalogRoot.Catalog,
            InfrastructurePackages: updatedPackages
          }
        });
      }
    } catch (err) {
      console.error('Failed to import bundles:', err);
    } finally {
      setShowBundleSelector(false);
      setSelectedBundles(new Set());
      setSelectedPackages({});
      setExpandedBundles(new Set());
      setIsImporting(false);
    }
  };

  const handleAdd = async (data: InfrastructurePackage) => {
    if (isDuplicateName(data.Name)) {
      addMethods.setError('Name', { message: 'A package with this name already exists' });
      return;
    }

    const payload = { ...data };
    if (!payload.Version?.trim()) delete payload.Version;
    if (!payload.Tag?.trim()) delete payload.Tag;

    try {
      await addPkg.mutateAsync(payload);
      if (catalogRoot && catalogRoot.Catalog.InfrastructurePackages) {
        const updatedCatalog = {
          ...catalogRoot,
          Catalog: {
            ...catalogRoot.Catalog,
            InfrastructurePackages: {
              ...catalogRoot.Catalog.InfrastructurePackages,
              [payload.Name]: payload
            }
          }
        };
        setCatalogRoot(updatedCatalog);
      }
    } catch (err) {
      console.error('Failed to add infrastructure package to backend:', err);
      showAlert('Failed to add infrastructure package to backend');
    }

    addMethods.reset(defaultPackage);
    setShowAddForm(false);
  };

  const handleDelete = async (id: string) => {
    showConfirm(
      'Delete Infrastructure Package',
      `Delete infrastructure package "${id}"?`,
      async () => {
        try {
          await deletePkg.mutateAsync(id);
        } catch (err) {
          console.error('Failed to delete infrastructure package from backend, removing from local state:', err);
        }
        // Update local catalogRoot to reflect deletion regardless of backend response
        if (catalogRoot && catalogRoot.Catalog.InfrastructurePackages) {
          const updatedCatalog = {
            ...catalogRoot,
            Catalog: {
              ...catalogRoot.Catalog,
              InfrastructurePackages: Object.fromEntries(
                Object.entries(catalogRoot.Catalog.InfrastructurePackages).filter(([key]) => key !== id)
              )
            }
          };
          setCatalogRoot(updatedCatalog);
        }
      }
    );
  };

  const handleEditPackage = (id: string, pkg: InfrastructurePackage) => {
    setEditingId(id);
    editMethods.reset(pkg);
    setShowAddForm(false); // Close add form if open
  };

  const handleSaveEdit = async (data: InfrastructurePackage) => {
    if (!editingId) return;
    if (isDuplicateName(data.Name, editingId)) {
      editMethods.setError('Name', { message: 'A package with this name already exists' });
      return;
    }

    const payload = { ...data };
    if (!payload.Version?.trim()) delete payload.Version;
    if (!payload.Tag?.trim()) delete payload.Tag;

    try {
      try {
        await updatePkg.mutateAsync({ packageId: editingId, pkg: payload });
      } catch (updateErr) {
        if ((updateErr as any).status === 404) {
          await addPkg.mutateAsync(payload);
        } else {
          throw updateErr;
        }
      }
      setEditingId(null);
      editMethods.reset(defaultPackage);
      if (catalogRoot) {
        const updatedCatalog = {
          ...catalogRoot,
          Catalog: {
            ...catalogRoot.Catalog,
            InfrastructurePackages: {
              ...(catalogRoot.Catalog.InfrastructurePackages || {}),
              [editingId]: payload
            }
          }
        };
        setCatalogRoot(updatedCatalog);
      }
    } catch (err) {
      console.error('Failed to update infrastructure package in backend:', err);
      showAlert('Failed to update infrastructure package in backend');
    }
  };

  const handleCancelEdit = () => {
    setEditingId(null);
    editMethods.reset(defaultPackage);
  };

  const extractPackageIdNumber = (packageId: string): string => {
    return packageId;
  };

  if (!catalogRoot) return <p>No catalog loaded</p>;
  const inner = catalogRoot.Catalog;
  const packages = Object.entries(
    inner.InfrastructurePackages,
  );

  return (
    <div className="p-8">
      <div className="flex justify-between items-center mb-4">
        <h2>Infrastructure Packages</h2>
        <div className="flex gap-2">
          <button onClick={handleOpenBundleSelector} className="button button-secondary">
            Import from Config
          </button>
          <button
            onClick={() => {
              setShowAddForm(true);
              setEditingId(null); // Close edit form if open
              editMethods.reset(defaultPackage);
            }}
            className="button button-primary"
          >
            + Add Package
          </button>
        </div>
      </div>

      {showBundleSelector && (
        <div className="section-box">
          <h3>Import from Config Files</h3>
          <div className="grid-3-col">
            <div className="form-group">
              <label className="form-label">OS Family</label>
              <select 
                value={osFamily}
                onChange={(e) => setOsFamily(e.target.value)}
                className="form-select"
              >
                <option value="rhel">RHEL</option>
              </select>
            </div>
            
            <div className="form-group">
              <label className="form-label">OS Version</label>
              <select 
                value={osVersion}
                onChange={(e) => setOsVersion(e.target.value)}
                className="form-select"
              >
                <option value="10.0">10.0</option>
              </select>
            </div>
            
            <div className="form-group">
              <label className="form-label">Architecture</label>
              <select 
                value={arch}
                onChange={(e) => setArch(e.target.value)}
                className="form-select"
              >
                <option value="x86_64">x86_64</option>
                <option value="aarch64">aarch64</option>
              </select>
            </div>
          </div>
          
          <BundleSelector
            arch={arch}
            osFamily={osFamily}
            version={osVersion}
            selectedBundles={selectedBundles}
            onBundleToggle={handleBundleToggle}
            bundleMetadata={bundleMetadata}
            showOnlyType="infrastructure"
            expandedBundles={expandedBundles}
            onBundleExpand={handleBundleExpand}
            selectedPackages={selectedPackages}
            onPackageToggle={handlePackageToggle}
            bundlePackageData={bundlePackageData}
          />
          
          <div className="flex gap-2 mt-4">
            <button
              onClick={handleImportBundles}
              disabled={isImporting || (selectedBundles.size === 0 && Object.keys(selectedPackages).length === 0)}
              className="button button-primary"
            >
              {isImporting ? 'Importing...' : `Import Selected (${selectedBundles.size + Object.keys(selectedPackages).filter(k => !selectedBundles.has(k)).length})`}
            </button>
            <button
              onClick={() => setShowBundleSelector(false)}
              className="button button-secondary"
            >
              Close
            </button>
          </div>
        </div>
      )}

      {showAddForm && (
        <FormProvider {...addMethods}>
          <PackageForm
            onSubmit={handleAdd}
            onCancel={() => setShowAddForm(false)}
            submitLabel={addPkg.isPending ? 'Adding…' : 'Add'}
            title="Add Infrastructure Package"
            variant="infrastructure"
          />
        </FormProvider>
      )}

      {editingId && (
        <div ref={editFormRef}>
          <FormProvider {...editMethods}>
            <PackageForm
              onSubmit={handleSaveEdit}
              onCancel={handleCancelEdit}
              submitLabel={updatePkg.isPending ? 'Saving…' : 'Save'}
              title={`Edit Infrastructure Package: ${editingId}`}
              variant="infrastructure"
            />
          </FormProvider>
        </div>
      )}

      <div className="card">
        <table className="table">
          <thead>
            <tr>
              <th>Package ID</th>
              <th>Name</th>
              <th>Type</th>
              <th>Functions</th>
              <th>Actions</th>
            </tr>
          </thead>
          <tbody>
            {packages.map(([id, pkg]) => (
              <tr key={id}>
                <td>{extractPackageIdNumber(id)}</td>
                <td>{pkg.Name}</td>
                <td><span className="package-tag">{pkg.Type}</span></td>
                <td>
                  {pkg.SupportedFunctions?.map(
                    (f) => f.Name,
                  ).join(', ') || '-'}
                </td>
                <td>
                  <button
                    onClick={() => handleEditPackage(id, pkg)}
                    className="button button-secondary button-small"
                  >
                    Edit
                  </button>
                  <button
                    onClick={() => handleDelete(id)}
                    className="button button-tertiary button-small ml-2"
                  >
                    Delete
                  </button>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
};

export default InfrastructureEditor;
