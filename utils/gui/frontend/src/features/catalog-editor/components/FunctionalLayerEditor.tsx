import { useState, useEffect, useRef } from 'react';
import React from 'react';
import { useForm, FormProvider } from 'react-hook-form';
import { zodResolver } from '@hookform/resolvers/zod';
import { useCatalogStore } from '../catalogStore';
import {
  useUpdateFunctionalLayer,
  useAddFunctionalLayer,
  useAddFunctionalPackage,
  useDeleteFunctionalLayer,
  useDeleteFunctionalPackage,
  useUpdateFunctionalPackage,
} from '../hooks/useCatalog';
import { useAvailableRoles, useRolePackages } from '../hooks/useRoleMappings';
import {
  type FunctionalLayer,
  FunctionalPackageSchema,
  type FunctionalPackage,
} from '../schemas/catalogSchema';
import PackageForm from './PackageForm';
import { RoleSelector } from './RoleSelector';
import { EmptyLayerSelector } from './EmptyLayerSelector';
import { showConfirm } from '../../confirmDialog/confirmDialogStore';
import { showAlert } from '../../toast/toastStore';
const defaultPackage: FunctionalPackage = {
  Name: '',
  Type: 'rpm',
  Architecture: ['x86_64'],
  SupportedOS: [{ Name: 'RHEL', Version: '10.0' }],
  Sources: [],
  Version: '',
  Tag: '',
};
interface LayerPackageFormProps {
  onSubmit: (data: FunctionalPackage) => void;
  onCancel: () => void;
  submitLabel: string;
  title: string;
  defaultValues?: FunctionalPackage;
}
const LayerPackageForm: React.FC<LayerPackageFormProps> = ({
  onSubmit,
  onCancel,
  submitLabel,
  title,
  defaultValues = defaultPackage,
}) => {
  const methods = useForm<FunctionalPackage>({
    resolver: zodResolver(FunctionalPackageSchema),
    defaultValues,
    mode: 'onSubmit',
  });
  useEffect(() => {
    methods.reset(defaultValues);
  }, [defaultValues, methods]);
  return (
    <FormProvider {...methods}>
      <PackageForm
        onSubmit={onSubmit}
        onCancel={onCancel}
        submitLabel={submitLabel}
        title={title}
      />
    </FormProvider>
  );
};
const FunctionalLayerEditor = () => {
  const catalogRoot = useCatalogStore((s) => s.catalogRoot);
  const setCatalogRoot = useCatalogStore((s) => s.setCatalogRoot);
  const updateLayer = useUpdateFunctionalLayer();
  const addLayer = useAddFunctionalLayer();
  const deleteLayer = useDeleteFunctionalLayer();
  const deleteFunctionalPackage = useDeleteFunctionalPackage();
  const addFunctionalPackage = useAddFunctionalPackage();
  const updateFunctionalPackage = useUpdateFunctionalPackage();
  const [showRoleSelector, setShowRoleSelector] = useState(false);
  const [showEmptyLayerSelector, setShowEmptyLayerSelector] = useState(false);
  const [showPackagesLayer, setShowPackagesLayer] = useState<string | null>(null);
  const [showAddPackageForm, setShowAddPackageForm] = useState<string | null>(null);
  const [showEditPackageForm, setShowEditPackageForm] = useState<{ layerName: string; packageId: string } | null>(null);
  const [editDefaultValues, setEditDefaultValues] = useState<FunctionalPackage>(defaultPackage);
  const [isPopulating, setIsPopulating] = useState(false);
  const [selectedLayers, setSelectedLayers] = useState<string[]>(() => {
    // Load selectedLayers from localStorage on initial render
    if (typeof window !== 'undefined') {
      const saved = localStorage.getItem('selectedFunctionalLayers');
      return saved ? JSON.parse(saved) : [];
    }
    return [];
  });
  const [selectedRole, setSelectedRole] = useState('');
  const [osFamily, setOsFamily] = useState('rhel');
  const [osVersion, setOsVersion] = useState('10.0');
  const [arch, setArch] = useState('x86_64');
  const editFormRef = useRef<HTMLDivElement>(null);
  
  // Predefined functional layer names from functional_groups_config.json
  const PREDEFINED_FUNCTIONAL_LAYERS = [
    "os_x86_64",
    "service_kube_node_x86_64",
    "service_kube_control_plane_x86_64",
    "login_node_x86_64",
    "login_node_aarch64",
    "login_compiler_node_x86_64",
    "login_compiler_node_aarch64",
    "slurm_control_node_x86_64",
    "os_aarch64",
    "slurm_node_x86_64",
    "slurm_node_aarch64"
  ];
  
  const [selectedPredefinedLayer, setSelectedPredefinedLayer] = useState('');
  const [customLayerName, setCustomLayerName] = useState('');

  const CUSTOM_LAYER_NAME_REGEX = /^[A-Za-z][A-Za-z0-9_]+_(x86_64|aarch64)$/;
  const customLayerError = selectedPredefinedLayer === '__custom__' && customLayerName.trim() && !CUSTOM_LAYER_NAME_REGEX.test(customLayerName.trim())
    ? 'Custom layer name must start with a letter, contain only letters/numbers/underscores, and end with _x86_64 or _aarch64.'
    : '';

  const { data: roles } = useAvailableRoles();
  const { data: rolePackages, refetch: refetchRolePackages } = useRolePackages(selectedRole, arch, osFamily, osVersion);
  // Sync selectedLayers with actual catalog layers on load
  useEffect(() => {
    if (catalogRoot && catalogRoot.Catalog.FunctionalLayer) {
      const existingLayerNames = catalogRoot.Catalog.FunctionalLayer.map((l: any) => l.Name);
      // Always sync selectedLayers with catalog layers when catalog changes
      setSelectedLayers(existingLayerNames);
    }
  }, [catalogRoot]);
  // Save selectedLayers to localStorage whenever it changes
  useEffect(() => {
    if (typeof window !== 'undefined') {
      localStorage.setItem('selectedFunctionalLayers', JSON.stringify(selectedLayers));
    }
  }, [selectedLayers]);
  // Scroll to edit form when opened
  useEffect(() => {
    if (showEditPackageForm && editFormRef.current) {
      editFormRef.current.scrollIntoView({ behavior: 'smooth', block: 'start' });
    }
  }, [showEditPackageForm]);
  const handleAutoPopulateFromRole = async () => {
    if (!selectedRole) {
      showAlert('Please select a role first');
      return;
    }
    if (!catalogRoot) {
      showAlert('No catalog loaded');
      return;
    }
    // Check if role architecture matches selected architecture
    const roleArch = selectedRole.includes('aarch64') ? 'aarch64' : 'x86_64';
    if (roleArch !== arch) {
      showAlert(`Role architecture (${roleArch}) does not match selected architecture (${arch}). Please select the correct architecture first.`);
      return;
    }
    // Check if layer already exists in catalog
    const layerAlreadyExists = catalogRoot.Catalog.FunctionalLayer.find((l: any) => l.Name === selectedRole);
    if (layerAlreadyExists) {
      showAlert(`Layer ${selectedRole} already exists in the catalog. Please edit the existing layer instead.`);
      return;
    }
    setIsPopulating(true);
    await refetchRolePackages();
    if (!rolePackages || Object.keys(rolePackages).length === 0) {
      showAlert(`No packages found for role ${selectedRole}. The bundle files may not exist in the config directory.`);
      setIsPopulating(false);
      return;
    }
    // Create a functional layer name based on role (role already includes architecture)
    const layerName = selectedRole;
    
    // Collect all package IDs from the role packages
    const packagesToAdd: any[] = [];
    for (const [_sectionName, pkgList] of Object.entries(rolePackages)) {
      for (const pkg of pkgList as any[]) {
        packagesToAdd.push(pkg);
      }
    }
    
    if (packagesToAdd.length === 0) {
      showAlert('No packages found for role packages');
      setIsPopulating(false);
      return;
    }
    
    // Add packages to catalog first and collect the returned package IDs
    const actualPackageIds: string[] = [];
    const existingPackages = catalogRoot.Catalog.FunctionalPackages || {};
    const addedPackageNames = new Set<string>();
    const updatedPackages = { ...existingPackages };
    
    // Parallelize package additions with Promise.allSettled
    const packageAdditionResults = await Promise.allSettled(
      packagesToAdd.map(async (pkgData) => {
        const existingPackageId = Object.keys(existingPackages).find(
          id => {
            const pkg = existingPackages[id];
            return pkg.Name === pkgData.package && 
                   pkg.Architecture && 
                   pkg.Architecture.includes(arch)
          }
        );
        if (existingPackageId) {
          return { type: 'reuse', packageId: existingPackageId, packageName: pkgData.package };
        }
        const sources: any[] = [];
        if (pkgData.repo_name) {
          sources.push({ Architecture: arch, RepoName: pkgData.repo_name });
        }
        if (pkgData.url) {
          sources.push({ Architecture: arch, Uri: pkgData.url });
        }
        try {
          const result = await addFunctionalPackage.mutateAsync({
            Name: pkgData.package,
            Type: pkgData.type,
            Architecture: [arch],
            Version: pkgData.version || undefined,
            Tag: pkgData.tag || undefined,
            Sources: sources.length > 0 ? sources : undefined,
            SupportedOS: [{ Name: osFamily, Version: osVersion }]
          });
          return { 
            type: 'added', 
            packageId: result.package_id, 
            packageName: pkgData.package,
            packageData: {
              Name: pkgData.package,
              Type: pkgData.type,
              Architecture: [arch],
              Version: pkgData.version || undefined,
              Tag: pkgData.tag || undefined,
              Sources: sources.length > 0 ? sources : undefined,
              SupportedOS: [{ Name: osFamily, Version: osVersion }]
            }
          };
        } catch (error) {
          return { type: 'failed', packageName: pkgData.package, error };
        }
      })
    );
    
    for (const result of packageAdditionResults) {
      if (result.status === 'fulfilled') {
        const { type, packageId, packageName, packageData, error } = result.value;
        if (type === 'reuse' && packageId) {
          actualPackageIds.push(packageId);
          addedPackageNames.add(packageName || '');
        } else if (type === 'added' && packageId && packageData) {
          actualPackageIds.push(packageId);
          addedPackageNames.add(packageName || '');
          updatedPackages[packageId] = packageData;
        } else if (type === 'failed') {
          console.error(`Failed to add package ${packageName || 'unknown'}:`, error);
        }
      }
    }
    
    const updatedCatalogRoot = {
      ...catalogRoot,
      Catalog: {
        ...catalogRoot.Catalog,
        FunctionalPackages: updatedPackages
      }
    };
    
    setCatalogRoot(updatedCatalogRoot);
    
    if (actualPackageIds.length === 0) {
      showAlert('No packages were successfully added to the catalog');
      setIsPopulating(false);
      return;
    }
    
    const existingLayer = updatedCatalogRoot.Catalog.FunctionalLayer.find(l => l.Name === layerName);
    
    if (existingLayer) {
      const updatedLayer = {
        ...existingLayer,
        FunctionalPackages: [...existingLayer.FunctionalPackages, ...actualPackageIds]
      };
      try {
        await updateLayer.mutateAsync({ layerName, layer: updatedLayer });
        setCatalogRoot({
          ...updatedCatalogRoot,
          Catalog: {
            ...updatedCatalogRoot.Catalog,
            FunctionalLayer: updatedCatalogRoot.Catalog.FunctionalLayer.map(l =>
              l.Name === layerName ? updatedLayer : l
            )
          }
        });
        showAlert(`Updated layer ${layerName} with ${actualPackageIds.length} packages`);
      } catch (error) {
        console.error('Failed to update layer:', error);
        showAlert('Failed to update layer in backend');
      }
    } else {
      const newLayer: FunctionalLayer = {
        Name: layerName,
        Architecture: arch,
        FunctionalPackages: actualPackageIds
      };
      try {
        await addLayer.mutateAsync(newLayer);
        setCatalogRoot({
          ...updatedCatalogRoot,
          Catalog: {
            ...updatedCatalogRoot.Catalog,
            FunctionalLayer: [...updatedCatalogRoot.Catalog.FunctionalLayer, newLayer]
          }
        });
        showAlert(`Created layer ${layerName} with ${actualPackageIds.length} packages`);
      } catch (err) {
        console.error('Failed to add layer:', err);
        if (err instanceof Error && err.message === 'Failed to add layer') {
          try {
            const existingLayer = updatedCatalogRoot.Catalog.FunctionalLayer.find((l: any) => l.Name === layerName);
            if (existingLayer) {
              const updatedLayer = {
                ...existingLayer,
                FunctionalPackages: [...existingLayer.FunctionalPackages, ...actualPackageIds]
              };
              await updateLayer.mutateAsync({ layerName, layer: updatedLayer });
              setCatalogRoot({
                ...updatedCatalogRoot,
                Catalog: {
                  ...updatedCatalogRoot.Catalog,
                  FunctionalLayer: updatedCatalogRoot.Catalog.FunctionalLayer.map(l =>
                    l.Name === layerName ? updatedLayer : l
                  )
                }
              });
              showAlert(`Updated existing layer ${layerName} with ${actualPackageIds.length} packages`);
            } else {
              setCatalogRoot({
                ...updatedCatalogRoot,
                Catalog: {
                  ...updatedCatalogRoot.Catalog,
                  FunctionalLayer: [...updatedCatalogRoot.Catalog.FunctionalLayer, newLayer]
                }
              });
              showAlert(`Layer ${layerName} already exists in backend, added to local state`);
            }
          } catch (updateErr) {
            console.error('Failed to update layer:', updateErr);
            showAlert('Failed to add or update layer in backend');
          }
        } else {
          showAlert('Failed to add layer to backend');
        }
      }
    }
    
    if (!selectedLayers.includes(layerName)) {
      setSelectedLayers([...selectedLayers, layerName]);
    }
    
    setShowRoleSelector(false);
    setIsPopulating(false);
  };
  const inferArchitectureFromName = (name: string): string => {
    if (name.includes('x86_64')) return 'x86_64';
    if (name.includes('aarch64')) return 'aarch64';
    if (name.includes('ppc64le')) return 'ppc64le';
    if (name.includes('s390x')) return 's390x';
    return 'x86_64'; // default
  };
  const handleAddEmptyLayer = async () => {
    if (!selectedPredefinedLayer) {
      showAlert('Please select a functional layer name');
      return;
    }

    if (!catalogRoot) return;

    const effectiveName = selectedPredefinedLayer === '__custom__'
      ? customLayerName.trim()
      : selectedPredefinedLayer;

    if (selectedPredefinedLayer === '__custom__') {
      if (!effectiveName) {
        showAlert('Please enter a custom layer name');
        return;
      }
      if (!CUSTOM_LAYER_NAME_REGEX.test(effectiveName)) {
        showAlert('Custom layer name must start with a letter, contain only letters/numbers/underscores, and end with _x86_64 or _aarch64.');
        return;
      }
    }

    const existingLayer = catalogRoot.Catalog.FunctionalLayer?.find((l: any) => l.Name === effectiveName);
    if (existingLayer) {
      showAlert(`Layer "${effectiveName}" already exists`);
      return;
    }

    const layerArch = effectiveName.endsWith('_aarch64') ? 'aarch64' : 'x86_64';

    const newLayer: FunctionalLayer = {
      Name: effectiveName,
      Architecture: layerArch,
      FunctionalPackages: []
    };

    try {
      await addLayer.mutateAsync(newLayer);
      const updatedCatalog = {
        ...catalogRoot,
        Catalog: {
          ...catalogRoot.Catalog,
          FunctionalLayer: [...(catalogRoot.Catalog.FunctionalLayer || []), newLayer]
        }
      };
      setCatalogRoot(updatedCatalog);
      setSelectedPredefinedLayer('');
      setCustomLayerName('');
    } catch (error) {
      console.error('Failed to add layer:', error);
      showAlert('Failed to add layer');
    }
  };
  const handleRemoveLayer = (layerName: string) => {
    showConfirm(
      'Remove Layer',
      `Are you sure you want to remove layer ${layerName} and all its packages from the catalog?`,
      async () => {
        const currentCatalog = catalogRoot;
        if (!currentCatalog) {
          showAlert('No catalog loaded');
          return;
        }
        const layer = currentCatalog.Catalog.FunctionalLayer.find((l: any) => l.Name === layerName);
        if (!layer) {
          showAlert('Layer not found');
          return;
        }
        // Packages orphaned after the layer is removed will be deleted in the cleanup pass below.
        
        try {
          await deleteLayer.mutateAsync(layerName);
          setSelectedLayers(selectedLayers.filter(name => name !== layerName));
          const updatedCatalog = {
            ...catalogRoot,
            Catalog: {
              ...catalogRoot.Catalog,
              FunctionalLayer: catalogRoot.Catalog.FunctionalLayer.filter((l: any) => l.Name !== layerName)
            }
          };
          setCatalogRoot(updatedCatalog);
          const allReferencedPackageIds = new Set<string>();
          updatedCatalog.Catalog.FunctionalLayer.forEach((l: any) => {
            l.FunctionalPackages.forEach((pkgId: string) => allReferencedPackageIds.add(pkgId));
          });
          const allPackageIds = Object.keys(updatedCatalog.Catalog.FunctionalPackages || {});
          const orphanedPackageIds = allPackageIds.filter(id => !allReferencedPackageIds.has(id));
          
          if (orphanedPackageIds.length > 0) {
            await Promise.allSettled(
              orphanedPackageIds.map(async (packageId) => {
                try {
                  await deleteFunctionalPackage.mutateAsync(packageId);
                } catch (error) {
                  console.error(`Failed to delete orphaned package ${packageId}:`, error);
                }
              })
            );
            const finalCatalog = {
              ...updatedCatalog,
              Catalog: {
                ...updatedCatalog.Catalog,
                FunctionalPackages: Object.fromEntries(
                  Object.entries(updatedCatalog.Catalog.FunctionalPackages || {}).filter(([id]) => !orphanedPackageIds.includes(id))
                )
              }
            };
            setCatalogRoot(finalCatalog);
          }
        } catch (error) {
          console.error('Failed to delete layer:', error);
          showAlert('Failed to delete layer');
        }
      }
    );
  };
  const handleAddPackageToLayer = async (layerName: string, data: FunctionalPackage) => {
    if (!catalogRoot) {
      showAlert('No catalog loaded');
      return;
    }
    const payload = { ...data };
    if (!payload.Version?.trim()) delete payload.Version;
    if (!payload.Tag?.trim()) delete payload.Tag;
    if (!payload.Sources || payload.Sources.length === 0) delete payload.Sources;
    try {
      const result = await addFunctionalPackage.mutateAsync(payload);
      const packageId = result.package_id || payload.Name;
      const packageData = result.package || payload;
      const updatedPackages = {
        ...(catalogRoot.Catalog?.FunctionalPackages || {}),
        [packageId]: packageData
      };
      let updatedCatalogRoot = {
        ...catalogRoot,
        Catalog: {
          ...catalogRoot.Catalog,
          FunctionalPackages: updatedPackages
        }
      };
      const layer = updatedCatalogRoot.Catalog.FunctionalLayer.find((l: any) => l.Name === layerName);
      if (layer) {
        const updatedLayer = {
          ...layer,
          FunctionalPackages: [...layer.FunctionalPackages, packageId]
        };
        await updateLayer.mutateAsync({ layerName, layer: updatedLayer });
        updatedCatalogRoot = {
          ...updatedCatalogRoot,
          Catalog: {
            ...updatedCatalogRoot.Catalog,
            FunctionalLayer: updatedCatalogRoot.Catalog.FunctionalLayer.map((l: any) =>
              l.Name === layerName ? updatedLayer : l
            )
          }
        };
        setCatalogRoot(updatedCatalogRoot);
      }
      setShowAddPackageForm(null);
    } catch (error) {
      console.error('Failed to add package to layer:', error);
      showAlert('Failed to add package to layer');
    }
  };
  const handleEditPackage = (packageId: string, layerName: string) => {
    if (!catalogRoot) return;
    const pkg = catalogRoot.Catalog.FunctionalPackages[packageId];
    if (pkg) {
      setEditDefaultValues({
        Name: pkg.Name,
        Type: pkg.Type,
        Architecture: pkg.Architecture || ['x86_64'],
        SupportedOS: pkg.SupportedOS || [{ Name: 'RHEL', Version: '10.0' }],
        Sources: pkg.Sources || [],
        Version: pkg.Version || '',
        Tag: pkg.Tag || '',
      });
      setShowEditPackageForm({ layerName, packageId });
      setShowAddPackageForm(null); // Close add form if open
    } else {
      showAlert(`Package ${packageId} not found in catalog. It may have been deleted.`);
    }
  };
  const handleSavePackageEdit = async (data: FunctionalPackage) => {
    if (!showEditPackageForm || !catalogRoot) return;
    const payload = { ...data };
    if (!payload.Version?.trim()) delete payload.Version;
    if (!payload.Tag?.trim()) delete payload.Tag;
    if (!payload.Sources || payload.Sources.length === 0) delete payload.Sources;
    try {
      const result = await updateFunctionalPackage.mutateAsync({
        packageId: showEditPackageForm.packageId,
        pkg: payload
      });
      const updatedPackages = {
        ...(catalogRoot.Catalog?.FunctionalPackages || {}),
        [showEditPackageForm.packageId]: result || payload
      };
      const updatedCatalogRoot = {
        ...catalogRoot,
        Catalog: {
          ...catalogRoot.Catalog,
          FunctionalPackages: updatedPackages
        }
      };
      setCatalogRoot(updatedCatalogRoot);
      setShowEditPackageForm(null);
    } catch (error) {
      console.error('Failed to update package:', error);
      showAlert('Failed to update package');
    }
  };
  const handleDeletePackageFromLayer = async (packageId: string, layerName: string) => {
    showConfirm(
      'Remove Package from Layer',
      `Remove package ${packageId} from layer ${layerName}?`,
      async () => {
        if (!catalogRoot) {
          showAlert('No catalog loaded');
          return;
        }
        try {
          const layer = catalogRoot.Catalog.FunctionalLayer.find((l: any) => l.Name === layerName);
          if (layer) {
            const updatedLayer = {
              ...layer,
              FunctionalPackages: layer.FunctionalPackages.filter((id: string) => id !== packageId)
            };
            await updateLayer.mutateAsync({ layerName, layer: updatedLayer });
            // Update local catalogRoot to reflect the layer update
            const updatedCatalog = {
              ...catalogRoot,
              Catalog: {
                ...catalogRoot.Catalog,
                FunctionalLayer: catalogRoot.Catalog.FunctionalLayer.map((l: any) =>
                  l.Name === layerName ? updatedLayer : l
                )
              }
            };
            setCatalogRoot(updatedCatalog);
            // Check if package is used by other layers
            const packageUsedByOtherLayers = catalogRoot.Catalog.FunctionalLayer.some((l: any) =>
              l.Name !== layerName && l.FunctionalPackages.includes(packageId)
            );
            // If package is not used by any other layer, delete it from FunctionalPackages
            if (!packageUsedByOtherLayers) {
              try {
                await deleteFunctionalPackage.mutateAsync(packageId);
              } catch (err) {
                // If backend returns 404, the package might not exist in backend
                // but we should still remove it from local state
                console.error('Failed to delete functional package from backend, removing from local state:', err);
              }
              // Update catalogRoot to remove the deleted package
              const finalCatalog = {
                ...updatedCatalog,
                Catalog: {
                  ...updatedCatalog.Catalog,
                  FunctionalPackages: Object.fromEntries(
                    Object.entries(updatedCatalog.Catalog.FunctionalPackages || {}).filter(([id]) => id !== packageId)
                  )
                }
              };
              setCatalogRoot(finalCatalog);
            }
          }
        } catch (error) {
          console.error('Failed to remove package from layer:', error);
          showAlert('Failed to remove package from layer');
        }
      }
    );
  };
  const getPackageDisplayName = (packageId: string) => {
    if (!catalogRoot) return packageId;
    const pkg = catalogRoot.Catalog.FunctionalPackages[packageId];
    return pkg ? pkg.Name : packageId;
  };
  if (!catalogRoot) return <p>No catalog loaded</p>;
  return (
    <div className="p-8">
      <div className="flex justify-between items-center mb-4">
        <h2>Functional Layers</h2>
        <div className="flex gap-2">
          <button onClick={() => setShowRoleSelector(true)} className="button button-secondary">
            Auto-populate from Roles
          </button>
          <button onClick={() => setShowEmptyLayerSelector(true)} className="button button-secondary">
            Add Empty Layer
          </button>
        </div>
      </div>
      <RoleSelector
        show={showRoleSelector}
        osFamily={osFamily}
        osVersion={osVersion}
        arch={arch}
        selectedRole={selectedRole}
        roles={roles}
        onOsFamilyChange={setOsFamily}
        onOsVersionChange={setOsVersion}
        onArchChange={setArch}
        onRoleChange={setSelectedRole}
        onAutoPopulate={handleAutoPopulateFromRole}
        onClose={() => setShowRoleSelector(false)}
        isLoading={isPopulating}
      />
      <EmptyLayerSelector
        show={showEmptyLayerSelector}
        selectedLayer={selectedPredefinedLayer}
        predefinedLayers={PREDEFINED_FUNCTIONAL_LAYERS}
        customLayerName={customLayerName}
        customLayerError={customLayerError}
        onLayerChange={setSelectedPredefinedLayer}
        onCustomLayerNameChange={setCustomLayerName}
        onAddLayer={handleAddEmptyLayer}
        onClose={() => {
          setShowEmptyLayerSelector(false);
          setSelectedPredefinedLayer('');
          setCustomLayerName('');
        }}
      />
      <div className="card">
        <h3>Selected Functional Layers ({selectedLayers.length})</h3>
        {selectedLayers.length === 0 ? (
          <p className="text-center text-secondary padding-lg">
            No functional layers selected. Click "Auto-populate from Roles" to create and select layers.
          </p>
        ) : (
          <div>
            {selectedLayers.map(layerName => {
              const layer = catalogRoot.Catalog.FunctionalLayer.find((l: any) => l.Name === layerName);
              return (
                <React.Fragment key={layerName}>
                <div className="flex justify-between items-center padding-sm border-bottom">
                  <div>
                    <div className="text-subtitle">{layerName}</div>
                    <div className="text-secondary text-xs">
                      Architecture: {layer?.Architecture || inferArchitectureFromName(layerName)} | 
                      Packages: {layer?.FunctionalPackages.length || 0}
                    </div>
                  </div>
                  <div className="flex gap-2">
                    <button
                      onClick={() => setShowPackagesLayer(showPackagesLayer === layerName ? null : layerName)}
                      className="button button-secondary button-sm"
                    >
                      {showPackagesLayer === layerName ? 'Hide Packages' : 'View Packages'}
                    </button>
                    <button
                      onClick={() => handleRemoveLayer(layerName)}
                      className="button button-tertiary button-sm"
                    >
                      Remove
                    </button>
                  </div>
                </div>
                {showPackagesLayer === layerName && layer && (
                  <div className="p-4 bg-gray-light border-bottom overflow-hidden">
                    <div className="text-subtitle-sm">
                      Packages in {layerName} ({layer.FunctionalPackages?.length || 0}):
                    </div>
                    {layer.FunctionalPackages && layer.FunctionalPackages.length > 0 ? (
                      <div className="grid-auto-fit">
                        {layer.FunctionalPackages.map(pkgId => (
                          <div key={pkgId} className="flex justify-between items-center text-xs text-dark overflow-hidden">
                            <span className="text-ellipsis">• {getPackageDisplayName(pkgId)}</span>
                            <div className="flex gap-2 flex-shrink-0">
                              <button
                                onClick={() => handleEditPackage(pkgId, layerName)}
                                className="button button-secondary button-xs"
                              >
                                Edit
                              </button>
                              <button
                                onClick={() => handleDeletePackageFromLayer(pkgId, layerName)}
                                className="button button-tertiary button-xs"
                              >
                                Remove
                              </button>
                            </div>
                          </div>
                        ))}
                      </div>
                    ) : (
                      <div className="text-secondary text-xs">No packages in this layer</div>
                    )}
                    <div className="mt-4">
                      <button
                        onClick={() => {
                          setShowAddPackageForm(layerName);
                          setShowEditPackageForm(null);
                        }}
                        className="button button-secondary button-sm"
                      >
                        + Add Package
                      </button>
                    </div>
                    {showAddPackageForm === layerName && (
                      <LayerPackageForm
                        onSubmit={(data) => handleAddPackageToLayer(layerName, data)}
                        onCancel={() => setShowAddPackageForm(null)}
                        submitLabel="Add"
                        title={`Add Package to ${layerName}`}
                      />
                    )}
                    {showEditPackageForm?.layerName === layerName && (
                      <div ref={editFormRef}>
                        <LayerPackageForm
                          onSubmit={handleSavePackageEdit}
                          onCancel={() => setShowEditPackageForm(null)}
                          submitLabel="Save"
                          title={`Edit Package ${showEditPackageForm.packageId}`}
                          defaultValues={editDefaultValues}
                        />
                      </div>
                    )}
                  </div>
                )}
                </React.Fragment>
              );
            })}
          </div>
        )}
      </div>
    </div>
  );
};
export default FunctionalLayerEditor;