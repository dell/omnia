import React, { useState, useRef } from 'react';
import { useForm, FormProvider } from 'react-hook-form';
import { zodResolver } from '@hookform/resolvers/zod';
import { useCatalogStore } from '../catalogStore';
import { useAddMiscellaneousPackage, useDeleteMiscellaneousPackage, useUpdateMiscellaneousPackage } from '../hooks/useCatalog';
import {
  MiscellaneousPackageSchema,
  type PackageTypeValue,
  type MiscellaneousPackage,
  type FunctionalPackage,
} from '../schemas/catalogSchema';
import PackageForm from './PackageForm';
import { showConfirm } from '../../confirmDialog/confirmDialogStore';
import { showAlert } from '../../toast/toastStore';

const defaultPackage: MiscellaneousPackage = {
  Name: '',
  Type: 'rpm' as PackageTypeValue,
  Architecture: ['x86_64'],
  SupportedOS: [{ Name: 'RHEL', Version: '10.0' }],
  Sources: [],
  Version: '',
  Tag: '',
};

const MiscellaneousEditor: React.FC = () => {
  const catalogRoot = useCatalogStore((s) => s.catalogRoot);
  const setCatalogRoot = useCatalogStore((s) => s.setCatalogRoot);
  const addPackage = useAddMiscellaneousPackage();
  const deletePackage = useDeleteMiscellaneousPackage();
  const updatePackage = useUpdateMiscellaneousPackage();
  const [showAddForm, setShowAddForm] = useState(false);
  const [editingId, setEditingId] = useState<string | null>(null);
  const editFormRef = useRef<HTMLDivElement>(null);

  const addMethods = useForm<MiscellaneousPackage>({
    resolver: zodResolver(MiscellaneousPackageSchema),
    defaultValues: defaultPackage,
    mode: 'onSubmit',
  });

  const editMethods = useForm<MiscellaneousPackage>({
    resolver: zodResolver(MiscellaneousPackageSchema),
    defaultValues: defaultPackage,
    mode: 'onSubmit',
  });

  const isDuplicateName = (name: string, excludeId?: string | null) => {
    if (!catalogRoot?.Catalog?.FunctionalPackages) return false;
    return Object.entries(catalogRoot.Catalog.FunctionalPackages).some(
      ([id, pkg]) => pkg.Name === name && id !== excludeId
    );
  };

  const handleAddPackage = async (data: MiscellaneousPackage) => {
    if (isDuplicateName(data.Name)) {
      addMethods.setError('Name', { message: 'A package with this name already exists' });
      return;
    }

    const payload = { ...data };
    if (!payload.Version?.trim()) delete payload.Version;
    if (!payload.Tag?.trim()) delete payload.Tag;

    try {
      const result = await addPackage.mutateAsync(payload as FunctionalPackage);

      addMethods.reset(defaultPackage);
      setShowAddForm(false);
      // Update local catalogRoot to reflect addition
      const packageId = result.package_id || payload.Name;
      const packageData = result.package || payload;
      if (catalogRoot) {
        const updatedCatalog = {
          ...catalogRoot,
          Catalog: {
            ...catalogRoot.Catalog,
            Miscellaneous: [...(catalogRoot.Catalog.Miscellaneous || []), packageId],
            FunctionalPackages: {
              ...(catalogRoot.Catalog.FunctionalPackages || {}),
              [packageId]: packageData
            }
          }
        };
        setCatalogRoot(updatedCatalog);
      }
    } catch (err) {
      console.error('Failed to add miscellaneous package to backend:', err);
      showAlert('Failed to add miscellaneous package to backend');
    }
  };

  const handleDeletePackage = async (packageId: string) => {
    showConfirm(
      'Delete Miscellaneous Package',
      `Delete miscellaneous package "${packageId}"? This cannot be undone.`,
      async () => {
        try {
          await deletePackage.mutateAsync(packageId);
        } catch (err) {
          // If backend returns 404, the package might not exist in backend
          // but we should still remove it from local state
          console.error('Failed to delete miscellaneous package from backend, removing from local state:', err);
        }
        // Update local catalogRoot to reflect deletion regardless of backend response
        if (catalogRoot) {
          const updatedCatalog = {
            ...catalogRoot,
            Catalog: {
              ...catalogRoot.Catalog,
              Miscellaneous: (catalogRoot.Catalog.Miscellaneous || []).filter(id => id !== packageId),
              FunctionalPackages: Object.fromEntries(
                Object.entries(catalogRoot.Catalog.FunctionalPackages || {}).filter(([key]) => key !== packageId)
              )
            }
          };
          setCatalogRoot(updatedCatalog);
        }
      }
    );
  };

  const handleEditPackage = (packageId: string, pkg: FunctionalPackage) => {
    setEditingId(packageId);
    editMethods.reset(pkg as MiscellaneousPackage);
    setShowAddForm(false); // Close add form if open
  };

  const handleSaveEdit = async (data: MiscellaneousPackage) => {
    if (!editingId) return;
    if (isDuplicateName(data.Name, editingId)) {
      editMethods.setError('Name', { message: 'A package with this name already exists' });
      return;
    }

    const payload = { ...data };
    if (!payload.Version?.trim()) delete payload.Version;
    if (!payload.Tag?.trim()) delete payload.Tag;

    try {
      const result = await updatePackage.mutateAsync({ packageId: editingId, pkg: payload as FunctionalPackage });
      setEditingId(null);
      editMethods.reset(defaultPackage);
      // Update local catalogRoot to reflect update
      if (catalogRoot) {
        const updatedCatalog = {
          ...catalogRoot,
          Catalog: {
            ...catalogRoot.Catalog,
            Miscellaneous: (catalogRoot.Catalog.Miscellaneous || []).map(id => id === editingId ? payload.Name : id),
            FunctionalPackages: {
              ...(catalogRoot.Catalog.FunctionalPackages || {}),
              [editingId]: result || payload
            }
          }
        };
        setCatalogRoot(updatedCatalog);
      }
    } catch (err) {
      console.error('Failed to update miscellaneous package in backend:', err);
      showAlert('Failed to update miscellaneous package in backend');
    }
  };

  const handleCancelEdit = () => {
    setEditingId(null);
    editMethods.reset(defaultPackage);
  };

  if (!catalogRoot) return <p>No catalog loaded</p>;
  const inner = catalogRoot.Catalog;
  const miscellaneousPackages = inner.Miscellaneous.map(id => ({
    id,
    pkg: inner.FunctionalPackages[id],
  })).filter(item => item.pkg !== undefined);

  return (
    <div className="p-8">
      <div className="flex justify-between items-center mb-4">
        <h2>Miscellaneous Packages</h2>
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
            submitLabel="Add Package"
            title="Add New Miscellaneous Package"
          />
        </FormProvider>
      )}

      {editingId && (
        <div ref={editFormRef}>
          <FormProvider {...editMethods}>
            <PackageForm
              onSubmit={handleSaveEdit}
              onCancel={handleCancelEdit}
              submitLabel="Save"
              title={`Edit Package: ${editingId}`}
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
            {miscellaneousPackages.length === 0 ? (
              <tr>
                <td colSpan={5} className="text-center text-secondary">
                  No miscellaneous packages defined
                </td>
              </tr>
            ) : (
              miscellaneousPackages.map(({ id, pkg }) => (
                <tr key={id}>
                  <td>{id}</td>
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
              ))
            )}
          </tbody>
        </table>
      </div>
    </div>
  );
};

export default MiscellaneousEditor;
