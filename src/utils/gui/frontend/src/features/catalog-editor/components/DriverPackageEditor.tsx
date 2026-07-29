import React, { useState, useEffect, useRef } from 'react';
import { useForm, FormProvider } from 'react-hook-form';
import { zodResolver } from '@hookform/resolvers/zod';
import { useCatalogStore } from '../catalogStore';
import {
  useAddDriverPackage,
  useDeleteDriverPackage,
  useUpdateDriverPackage,
} from '../hooks/useCatalog';
import { DriverPackageSchema, type DriverPackage, type PackageTypeValue } from '../schemas/catalogSchema';
import PackageForm from './PackageForm';
import { showConfirm } from '../../confirmDialog/confirmDialogStore';
import { showAlert } from '../../toast/toastStore';

const defaultPackage: DriverPackage = {
  Name: '',
  Type: 'rpm' as PackageTypeValue,
  Architecture: ['x86_64'],
  Uri: '',
  Version: '',
  Config: { DriverBrand: '', DriverType: '' },
};

const DriverPackageEditor: React.FC = () => {
  const catalogRoot = useCatalogStore((s) => s.catalogRoot);
  const setCatalogRoot = useCatalogStore((s) => s.setCatalogRoot);
  const addPkg = useAddDriverPackage();
  const deletePkg = useDeleteDriverPackage();
  const updatePkg = useUpdateDriverPackage();
  const [showAddForm, setShowAddForm] = useState(false);
  const [editingId, setEditingId] = useState<string | null>(null);
  const editFormRef = useRef<HTMLDivElement>(null);

  const addMethods = useForm<DriverPackage>({
    resolver: zodResolver(DriverPackageSchema),
    defaultValues: defaultPackage,
    mode: 'onSubmit',
  });

  const editMethods = useForm<DriverPackage>({
    resolver: zodResolver(DriverPackageSchema),
    defaultValues: defaultPackage,
    mode: 'onSubmit',
  });

  const isDuplicateName = (name: string, excludeId?: string | null) => {
    if (!catalogRoot?.Catalog?.DriverPackages) return false;
    return Object.entries(catalogRoot.Catalog.DriverPackages).some(
      ([id, pkg]) => pkg.Name === name && id !== excludeId
    );
  };

  const prevDriverPackageKeysRef = useRef<string>('');

  // Automatically derive Drivers from DriverPackages
  useEffect(() => {
    if (!catalogRoot?.Catalog?.DriverPackages) return;

    const driverPackageIds = Object.keys(catalogRoot.Catalog.DriverPackages).sort();
    const keysString = driverPackageIds.join(',');
    if (keysString === prevDriverPackageKeysRef.current) return;
    prevDriverPackageKeysRef.current = keysString;

    const driverPackages = catalogRoot.Catalog.DriverPackages;

    // Group driver packages by DriverBrand and DriverType
    const driverGroups = new Map<string, string[]>();
    
    Object.entries(driverPackages).forEach(([pkgId, pkg]) => {
      const brand = pkg.Config.DriverBrand || 'unknown';
      const type = pkg.Config.DriverType || 'unknown';
      const key = `${brand}_${type}`;
      
      if (!driverGroups.has(key)) {
        driverGroups.set(key, []);
      }
      driverGroups.get(key)!.push(pkgId);
    });

    // Create Drivers array from grouped packages
    const drivers = Array.from(driverGroups.entries()).map(([key, packageIds]) => {
      const [brand, type] = key.split('_');
      return {
        Name: `${brand} ${type}`,
        DriverPackages: packageIds.sort()
      };
    });

    // Update Drivers section
    const updatedCatalog = {
      ...catalogRoot,
      Catalog: {
        ...catalogRoot.Catalog,
        Drivers: drivers
      }
    };

    setCatalogRoot(updatedCatalog);
  }, [catalogRoot?.Catalog?.DriverPackages, setCatalogRoot]);

  if (!catalogRoot) return <p>No catalog loaded</p>;
  const inner = catalogRoot.Catalog;
  const packages = Object.entries(inner.DriverPackages);


  const handleAddPackage = async (data: DriverPackage) => {
    if (isDuplicateName(data.Name)) {
      addMethods.setError('Name', { message: 'A package with this name already exists' });
      return;
    }

    const payload = { ...data } as any;
    if (!payload.Uri?.trim()) delete payload.Uri;
    if (!payload.Version?.trim()) delete payload.Version;

    try {
      await addPkg.mutateAsync(payload);
      addMethods.reset(defaultPackage);
      setShowAddForm(false);
      if (catalogRoot && catalogRoot.Catalog.DriverPackages) {
        const updatedCatalog = {
          ...catalogRoot,
          Catalog: {
            ...catalogRoot.Catalog,
            DriverPackages: {
              ...catalogRoot.Catalog.DriverPackages,
              [payload.Name]: payload
            }
          }
        };
        setCatalogRoot(updatedCatalog);
      }
    } catch (err) {
      console.error('Failed to add driver package to backend:', err);
      showAlert('Failed to add driver package to backend');
    }
  };

  const handleEditPackage = (id: string, pkg: DriverPackage) => {
    setEditingId(id);
    editMethods.reset(pkg);
    setShowAddForm(false); // Close add form if open
  };

  const handleSavePackage = async (data: DriverPackage) => {
    if (!editingId) return;
    if (isDuplicateName(data.Name, editingId)) {
      editMethods.setError('Name', { message: 'A package with this name already exists' });
      return;
    }

    const payload = { ...data } as any;
    if (!payload.Uri?.trim()) delete payload.Uri;
    if (!payload.Version?.trim()) delete payload.Version;

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
      if (catalogRoot && catalogRoot.Catalog.DriverPackages) {
        const updatedCatalog = {
          ...catalogRoot,
          Catalog: {
            ...catalogRoot.Catalog,
            DriverPackages: {
              ...catalogRoot.Catalog.DriverPackages,
              [editingId]: payload
            }
          }
        };
        setCatalogRoot(updatedCatalog);
      }
    } catch (err) {
      console.error('Failed to save driver package to backend:', err);
      showAlert('Failed to save driver package to backend');
    }
  };

  const handleDeletePackage = async (id: string) => {
    showConfirm(
      'Delete Driver Package',
      `Delete driver package "${id}"?`,
      async () => {
        try {
          await deletePkg.mutateAsync(id);
        } catch (err) {
          console.error('Failed to delete driver package from backend, removing from local state:', err);
        }
        if (catalogRoot && catalogRoot.Catalog.DriverPackages) {
          const updatedCatalog = {
            ...catalogRoot,
            Catalog: {
              ...catalogRoot.Catalog,
              DriverPackages: Object.fromEntries(
                Object.entries(catalogRoot.Catalog.DriverPackages).filter(([key]) => key !== id)
              )
            }
          };
          setCatalogRoot(updatedCatalog);
        }
      }
    );
  };

  const handleCancelEdit = () => {
    setEditingId(null);
    editMethods.reset(defaultPackage);
  };

  const extractPackageIdNumber = (packageId: string): string => {
    return packageId;
  };

  return (
    <div className="p-8">
      <div className="flex justify-between items-center mb-4">
        <h2>Driver Packages</h2>
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

      {showAddForm && (
        <FormProvider {...addMethods}>
          <PackageForm
            onSubmit={handleAddPackage}
            onCancel={() => setShowAddForm(false)}
            submitLabel={addPkg.isPending ? 'Adding…' : 'Add'}
            title="Add Driver Package"
            variant="driver"
          />
        </FormProvider>
      )}

      {editingId && (
        <div ref={editFormRef}>
          <FormProvider {...editMethods}>
            <PackageForm
              onSubmit={handleSavePackage}
              onCancel={handleCancelEdit}
              submitLabel={updatePkg.isPending ? 'Saving…' : 'Save'}
              title={`Edit Driver Package: ${editingId}`}
              variant="driver"
            />
          </FormProvider>
        </div>
      )}

      <div className="card">
        <table className="table">
          <thead>
            <tr>
              <th>ID</th>
              <th>Name</th>
              <th>Type</th>
              <th>Architecture</th>
              <th>Actions</th>
            </tr>
          </thead>
          <tbody>
            {packages.length === 0 ? (
              <tr>
                <td colSpan={5} className="text-center text-secondary">
                  No driver packages defined
                </td>
              </tr>
            ) : (
              packages.map(([id, pkg]) => (
                <tr key={id}>
                  <td>{extractPackageIdNumber(id)}</td>
                  <td>{pkg.Name}</td>
                  <td>{pkg.Type}</td>
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
                      className="button button-tertiary button-small"
                    >
                      Delete
                    </button>
                  </td>
                </tr>
              ))
            )}
          </tbody>
        </table>
      </div>
    </div>
  );
};

export default DriverPackageEditor;
