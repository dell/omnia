import { useState, useEffect, useRef } from 'react';
import { useForm, FormProvider } from 'react-hook-form';
import { zodResolver } from '@hookform/resolvers/zod';
import { useCatalogStore } from '../catalogStore';
import { useAddOSPackage, useDeleteOSPackage, useUpdateOSPackage } from '../hooks/useCatalog';
import {
  OSPackageSchema,
  type PackageTypeValue,
  type OSPackage,
  type FunctionalPackage,
} from '../schemas/catalogSchema';
import BundleSelector from './BundleSelector';
import PackageForm from './PackageForm';
import { showConfirm } from '../../confirmDialog/confirmDialogStore';
import { showAlert } from '../../toast/toastStore';

const defaultPackage: OSPackage = {
  Name: '',
  Type: 'rpm' as PackageTypeValue,
  Architecture: ['x86_64'],
  SupportedOS: [{ Name: 'RHEL', Version: '10.0' }],
  Sources: [],
  Version: '',
  Tag: '',
};

const OSPackageEditor = () => {
  const catalogRoot = useCatalogStore((s) => s.catalogRoot);
  const setCatalogRoot = useCatalogStore((s) => s.setCatalogRoot);
  const addOSPackage = useAddOSPackage();
  const deleteOSPackage = useDeleteOSPackage();
  const updateOSPackage = useUpdateOSPackage();
  const [showAddForm, setShowAddForm] = useState(false);
  const [showBundleSelector, setShowBundleSelector] = useState(false);
  const [editingId, setEditingId] = useState<string | null>(null);
  const editFormRef = useRef<HTMLDivElement>(null);

  const addMethods = useForm<OSPackage>({
    resolver: zodResolver(OSPackageSchema),
    defaultValues: defaultPackage,
    mode: 'onSubmit',
  });

  const editMethods = useForm<OSPackage>({
    resolver: zodResolver(OSPackageSchema),
    defaultValues: defaultPackage,
    mode: 'onSubmit',
  });

  const isDuplicateName = (name: string, excludeId?: string | null) => {
    if (!catalogRoot?.Catalog?.OSPackages) return false;
    return Object.entries(catalogRoot.Catalog.OSPackages).some(
      ([id, pkg]) => pkg.Name === name && id !== excludeId
    );
  };
  const [osFamily, setOsFamily] = useState('RHEL');
  const [osVersion, setOsVersion] = useState('10.0');
  const [arch, setArch] = useState('x86_64');
  const [selectedBundles, setSelectedBundles] = useState<Set<string>>(new Set(['default_packages']));
  const [expandedBundles, setExpandedBundles] = useState<Set<string>>(new Set());
  const [selectedPackages, setSelectedPackages] = useState<Record<string, Set<string>>>({});
  const [bundlePackageData, setBundlePackageData] = useState<Record<string, Record<string, any[]>>>({});
  const [isImporting, setIsImporting] = useState(false);
  const prevOsPackageKeysRef = useRef<string>('');

  // Automatically derive BaseOS from OSPackages
  useEffect(() => {
    if (!catalogRoot?.Catalog?.OSPackages) return;

    const osPackageIds = Object.keys(catalogRoot.Catalog.OSPackages).sort();
    const keysString = osPackageIds.join(',');

    if (keysString === prevOsPackageKeysRef.current) return;
    prevOsPackageKeysRef.current = keysString;

    // Extract OS family and version from first package (or use defaults)
    let derivedOsFamily = 'RHEL';
    let derivedOsVersion = '10.0';

    if (osPackageIds.length > 0) {
      const firstPkg = catalogRoot.Catalog.OSPackages[osPackageIds[0]];
      if (firstPkg?.SupportedOS && firstPkg.SupportedOS.length > 0) {
        derivedOsFamily = firstPkg.SupportedOS[0].Name;
        derivedOsVersion = firstPkg.SupportedOS[0].Version;
      }
    }

    // Update BaseOS to match OSPackages
    const updatedCatalog = {
      ...catalogRoot,
      Catalog: {
        ...catalogRoot.Catalog,
        BaseOS: [{
          Name: derivedOsFamily,
          Version: derivedOsVersion,
          osPackages: osPackageIds
        }]
      }
    };

    setCatalogRoot(updatedCatalog);
  }, [catalogRoot?.Catalog?.OSPackages, setCatalogRoot]);

  const bundleMetadata: Record<string, { required: boolean; description: string }> = {
    default_packages: {
      required: true,
      description: 'Core OS packages required for basic functionality'
    },
    admin_debug_packages: {
      required: false,
      description: 'Admin and debugging tools (vim, gcc, gdb, etc.)'
    },
    openldap: {
      required: false,
      description: 'LDAP authentication packages'
    },
    openmpi: {
      required: false,
      description: 'MPI implementation for parallel computing'
    },
    ucx: {
      required: false,
      description: 'UCX communication library for HPC'
    },
    ldms: {
      required: false,
      description: 'LDMS monitoring system'
    },
    nfs: {
      required: false,
      description: 'Network File System packages'
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
    const newExpanded = new Set(expandedBundles);
    if (newExpanded.has(bundleName)) {
      newExpanded.delete(bundleName);
      setExpandedBundles(newExpanded);
    } else {
      newExpanded.add(bundleName);
      setExpandedBundles(newExpanded);

      // Fetch package data for this bundle if not already loaded
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

            // If this is a required bundle, select all its packages
            if (bundleMetadata[bundleName]?.required) {
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
          }
        } catch (error) {
          console.error('Failed to fetch bundle packages:', error);
        }
      } else if (bundleMetadata[bundleName]?.required) {
        // If data is already loaded and bundle is required, ensure all packages are selected
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
  };

  const handlePackageToggle = (bundleName: string, packageId: string) => {
    // Prevent unchecking packages in required bundles
    if (bundleMetadata[bundleName]?.required) {
      return;
    }
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
    
    // Get existing OS packages to initialize selection state
    const existingPackages = new Map<string, any>();
    if (catalogRoot?.Catalog?.OSPackages) {
      for (const [_pkgId, pkg] of Object.entries(catalogRoot.Catalog.OSPackages)) {
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
    const bundles = data.bundles as { name: string }[];
    
    // Initialize selection state based on existing packages
    const newSelectedBundles = new Set<string>();
    const newSelectedPackages: Record<string, Set<string>> = {};
    const newBundlePackageData: Record<string, Record<string, any[]>> = {};
    
    const bundleResults = await Promise.allSettled(
      bundles.map(async (bundle) => {
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

      // Always include default_packages and select all its packages
      if (bundleName === 'default_packages') {
        newSelectedBundles.add('default_packages');
        // Select all packages in default_packages
        const allPackageIds = new Set<string>();
        for (const [_sectionName, pkgList] of Object.entries(bundleData.packages)) {
          for (const pkg of pkgList as any[]) {
            const pkgId = `${pkg.package}_${pkg.type}`;
            allPackageIds.add(pkgId);
          }
        }
        newSelectedPackages['default_packages'] = allPackageIds;
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
      // Get existing OS packages to prevent duplicates
      const existingPackages = new Map<string, any>();
      if (catalogRoot?.Catalog?.OSPackages) {
        for (const [pkgId, pkg] of Object.entries(catalogRoot.Catalog.OSPackages)) {
          // Create a unique key based on Name, Type, Version, and Tag
          const key = `${pkg.Name}_${pkg.Type}_${pkg.Version || ''}_${pkg.Tag || ''}`;
          existingPackages.set(key, pkgId);
        }
      }

      const updatedPackages = { ...(catalogRoot?.Catalog?.OSPackages || {}) };

      // Fetch all missing bundle data in parallel
      const bundleNamesToFetch = new Set<string>([...selectedBundles, ...Object.keys(selectedPackages)]);
      const missingBundleNames = [...bundleNamesToFetch].filter((name) => !bundlePackageData[name]);

      const fetchResults = await Promise.allSettled(
        missingBundleNames.map(async (name) => {
          const response = await fetch(
            `/api/v1/catalog-editor/os-packages/bundle/${name}?arch=${arch}&os_family=${osFamily}&version=${osVersion}`
          );
          if (!response.ok) throw new Error(`Failed to fetch bundle ${name}`);
          const data = await response.json();
          return { name, packages: data.packages };
        })
      );

      const fetchedBundleData = { ...bundlePackageData };
      for (const result of fetchResults) {
        if (result.status === 'fulfilled') {
          fetchedBundleData[result.value.name] = result.value.packages;
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
          SupportedOS: [{ Name: osFamily, Version: osVersion }],
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
          addOSPackage.mutateAsync(payload).then((result: any) => {
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
            OSPackages: updatedPackages
          }
        });
      }
    } catch (err) {
      console.error('Failed to import bundles:', err);
    } finally {
      setShowBundleSelector(false);
      setSelectedBundles(new Set(['default_packages']));
      setSelectedPackages({});
      setExpandedBundles(new Set());
      setIsImporting(false);
    }
  };

  const handleAddPackage = async (data: OSPackage) => {
    if (isDuplicateName(data.Name)) {
      addMethods.setError('Name', { message: 'A package with this name already exists' });
      return;
    }

    const payload = { ...data };
    if (!payload.Version?.trim()) delete payload.Version;
    if (!payload.Tag?.trim()) delete payload.Tag;

    try {
      await addOSPackage.mutateAsync(payload as FunctionalPackage);
      if (catalogRoot && catalogRoot.Catalog.OSPackages) {
        const updatedCatalog = {
          ...catalogRoot,
          Catalog: {
            ...catalogRoot.Catalog,
            OSPackages: {
              ...catalogRoot.Catalog.OSPackages,
              [payload.Name]: payload
            }
          }
        };
        setCatalogRoot(updatedCatalog);
      }
    } catch (err) {
      console.error('Failed to add OS package to backend:', err);
      showAlert('Failed to add OS package to backend');
    }

    addMethods.reset(defaultPackage);
    setShowAddForm(false);
  };

  const handleDeletePackage = async (id: string) => {
    showConfirm(
      'Delete OS Package',
      `Delete OS package "${id}"?`,
      async () => {
        try {
          await deleteOSPackage.mutateAsync(id);
        } catch (err) {
          console.error('Failed to delete OS package from backend, removing from local state:', err);
        }
        if (catalogRoot && catalogRoot.Catalog.OSPackages) {
          const updatedCatalog = {
            ...catalogRoot,
            Catalog: {
              ...catalogRoot.Catalog,
              OSPackages: Object.fromEntries(
                Object.entries(catalogRoot.Catalog.OSPackages).filter(([key]) => key !== id)
              )
            }
          };
          setCatalogRoot(updatedCatalog);
        }
      }
    );
  };

  const handleEditPackage = (id: string, pkg: FunctionalPackage) => {
    setEditingId(id);
    editMethods.reset(pkg as OSPackage);
    setShowAddForm(false);
  };

  const handleSaveEdit = async (data: OSPackage) => {
    if (!editingId) return;
    if (isDuplicateName(data.Name, editingId)) {
      editMethods.setError('Name', { message: 'A package with this name already exists' });
      return;
    }

    const payload = { ...data };
    if (!payload.Version?.trim()) delete payload.Version;
    if (!payload.Tag?.trim()) delete payload.Tag;

    try {
      await updateOSPackage.mutateAsync({ packageId: editingId, pkg: payload as FunctionalPackage });
      setEditingId(null);
      editMethods.reset(defaultPackage);
      if (catalogRoot && catalogRoot.Catalog.OSPackages) {
        const updatedCatalog = {
          ...catalogRoot,
          Catalog: {
            ...catalogRoot.Catalog,
            OSPackages: {
              ...catalogRoot.Catalog.OSPackages,
              [editingId]: payload
            }
          }
        };
        setCatalogRoot(updatedCatalog);
      }
    } catch (err) {
      console.error('Failed to update OS package in backend:', err);
      showAlert('Failed to update OS package in backend');
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
  const packages = Object.entries(inner.OSPackages);

  return (
    <div className="p-8">
      <div className="flex justify-between items-center mb-4">
        <h2>OS Packages</h2>
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
            + Add OS Package
          </button>
        </div>
      </div>

      {showBundleSelector && (
        <div className="section-box">
          <h3>Import from Config Files</h3>
          <div className="grid-3-col mb-4">
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
            showOnlyType="os"
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
            onSubmit={handleAddPackage}
            onCancel={() => setShowAddForm(false)}
            submitLabel={addOSPackage.isPending ? 'Adding…' : 'Add'}
            title="Add New OS Package"
          />
        </FormProvider>
      )}

      {editingId && (
        <div ref={editFormRef}>
          <FormProvider {...editMethods}>
            <PackageForm
              onSubmit={handleSaveEdit}
              onCancel={handleCancelEdit}
              submitLabel={updateOSPackage.isPending ? 'Saving…' : 'Save'}
              title={`Edit OS Package: ${editingId}`}
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
              <th>Arch</th>
              <th>Actions</th>
            </tr>
          </thead>
          <tbody>
            {packages.map(([id, pkg]) => (
              <tr key={id}>
                <td>{extractPackageIdNumber(id)}</td>
                <td>{pkg.Name}</td>
                <td><span className="package-tag">{pkg.Type}</span></td>
                <td>{pkg.Architecture.join(', ')}</td>
                <td>
                  <button
                    onClick={() => handleEditPackage(id, pkg)}
                    className="button button-secondary button-small"
                  >
                    Edit
                  </button>
                  <button
                    onClick={() => handleDeletePackage(id)}
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

export default OSPackageEditor;
