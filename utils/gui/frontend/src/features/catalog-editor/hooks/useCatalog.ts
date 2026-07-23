import { useMutation } from '@tanstack/react-query';
import type {
  CatalogRoot,
  FunctionalPackage,
  InfrastructurePackage,
  FunctionalLayer,
  DriverPackage,
  OSPackage,
  MiscellaneousPackage,
} from '../schemas/catalogSchema';
import { extractErrorMessage } from '../utils/extractErrorMessage';

const API_BASE = '/api/v1/catalog';

// NOTE: Mutations in this file do NOT invalidate queries.
// The catalog editor manages local state manually via catalogStore.

async function apiRequest<T>(
  path: string,
  method: string = 'GET',
  body?: unknown,
): Promise<T> {
  const options: RequestInit = { method };
  if (body) {
    options.headers = { 'Content-Type': 'application/json' };
    options.body = JSON.stringify(body);
  }
  
  const res = await fetch(`${API_BASE}${path}`, options);
  if (!res.ok) {
    const data = await res.json().catch(() => null);
    const err = new Error(extractErrorMessage({ data })) as Error & {
      status?: number;
      data?: any;
    };
    err.status = res.status;
    err.data = data;
    throw err;
  }
  return res.json();
}

// ─── VALIDATE ──────────────────────────────────────────────

export const useValidateCatalog = () =>
  useMutation({
    mutationFn: async (catalog: CatalogRoot) =>
      apiRequest<{
        valid: boolean;
        errors: string[];
        warnings: string[];
      }>('/validate', 'POST', catalog),
  });

// ─── Functional Packages ────────────────────────────────────

export const useAddFunctionalPackage = () =>
  useMutation({
    mutationFn: (pkg: FunctionalPackage) =>
      apiRequest<{
        package_id: string;
        package: FunctionalPackage;
      }>('/packages/functional', 'POST', pkg),
  });

export const useUpdateFunctionalPackage = () =>
  useMutation({
    mutationFn: ({ packageId, pkg }: { packageId: string; pkg: FunctionalPackage }) =>
      apiRequest<FunctionalPackage>(
        `/packages/functional/${encodeURIComponent(packageId)}`,
        'PUT',
        pkg,
      ),
    // Note: Unlike infrastructure/driver updates, this does not support 404-fallback to add
  });

export const useDeleteFunctionalPackage = () =>
  useMutation({
    mutationFn: (packageId: string) =>
      apiRequest(`/packages/functional/${encodeURIComponent(packageId)}`, 'DELETE'),
  });

// ─── OS Packages ────────────────────────────────────────────

export const useAddOSPackage = () =>
  useMutation({
    mutationFn: (pkg: OSPackage) =>
      apiRequest('/packages/os', 'POST', pkg),
  });

export const useDeleteOSPackage = () =>
  useMutation({
    mutationFn: (packageId: string) =>
      apiRequest(`/packages/os/${encodeURIComponent(packageId)}`, 'DELETE'),
  });

export const useUpdateOSPackage = () =>
  useMutation({
    mutationFn: ({ packageId, pkg }: { packageId: string; pkg: OSPackage }) =>
      apiRequest(
        `/packages/os/${encodeURIComponent(packageId)}`,
        'PUT',
        pkg,
      ),
    // Note: Unlike infrastructure/driver updates, this does not support 404-fallback to add
  });

// ─── Infrastructure Packages ────────────────────────────────

export const useAddInfrastructurePackage = () =>
  useMutation({
    mutationFn: (pkg: InfrastructurePackage) =>
      apiRequest('/packages/infrastructure', 'POST', pkg),
  });

export const useDeleteInfrastructurePackage = () =>
  useMutation({
    mutationFn: (packageId: string) =>
      apiRequest(`/packages/infrastructure/${encodeURIComponent(packageId)}`, 'DELETE'),
  });

export const useUpdateInfrastructurePackage = () =>
  useMutation({
    mutationFn: ({ packageId, pkg }: { packageId: string; pkg: InfrastructurePackage }) =>
      apiRequest<InfrastructurePackage>(
        `/packages/infrastructure/${encodeURIComponent(packageId)}`,
        'PUT',
        pkg,
      ),
    // Supports 404-fallback: editors can check err.status === 404 to fall back to add operation
  });

// ─── Functional Layers ──────────────────────────────────────

export const useAddFunctionalLayer = () =>
  useMutation({
    mutationFn: (layer: FunctionalLayer) =>
      apiRequest('/layers', 'POST', layer),
  });

export const useUpdateFunctionalLayer = () =>
  useMutation({
    mutationFn: ({ layerName, layer }: { layerName: string; layer: FunctionalLayer }) =>
      apiRequest<FunctionalLayer>(
        `/layers/${encodeURIComponent(layerName)}`,
        'PUT',
        layer,
      ),
    // Note: Unlike infrastructure/driver updates, this does not support 404-fallback to add
  });

export const useDeleteFunctionalLayer = () =>
  useMutation({
    mutationFn: (layerName: string) =>
      apiRequest(`/layers/${encodeURIComponent(layerName)}`, 'DELETE'),
  });

// ─── Miscellaneous Packages ─────────────────────────────────

export const useAddMiscellaneousPackage = () =>
  useMutation({
    mutationFn: (pkg: MiscellaneousPackage) =>
      apiRequest<{
        package_id: string;
        package: MiscellaneousPackage;
      }>('/packages/miscellaneous', 'POST', pkg),
  });

export const useUpdateMiscellaneousPackage = () =>
  useMutation({
    mutationFn: ({ packageId, pkg }: { packageId: string; pkg: MiscellaneousPackage }) =>
      apiRequest<MiscellaneousPackage>(
        `/packages/miscellaneous/${encodeURIComponent(packageId)}`,
        'PUT',
        pkg,
      ),
    // Note: Unlike infrastructure/driver updates, this does not support 404-fallback to add
  });

export const useDeleteMiscellaneousPackage = () =>
  useMutation({
    mutationFn: (packageId: string) =>
      apiRequest(`/packages/miscellaneous/${encodeURIComponent(packageId)}`, 'DELETE'),
  });

// ─── Driver Packages ────────────────────────────────────────

export const useAddDriverPackage = () =>
  useMutation({
    mutationFn: (pkg: DriverPackage) =>
      apiRequest('/packages/driver', 'POST', pkg),
  });

export const useDeleteDriverPackage = () =>
  useMutation({
    mutationFn: (packageId: string) =>
      apiRequest(`/packages/driver/${encodeURIComponent(packageId)}`, 'DELETE'),
  });

export const useUpdateDriverPackage = () =>
  useMutation({
    mutationFn: ({ packageId, pkg }: { packageId: string; pkg: DriverPackage }) =>
      apiRequest<DriverPackage>(
        `/packages/driver/${encodeURIComponent(packageId)}`,
        'PUT',
        pkg,
      ),
    // Supports 404-fallback: editors can check err.status === 404 to fall back to add operation
  });

// ─── Import / Export ────────────────────────────────────────

export const useImportCatalog = () =>
  useMutation({
    mutationFn: (catalog: CatalogRoot) =>
      apiRequest<CatalogRoot>('/import', 'POST', catalog),
  });
