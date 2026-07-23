import { useQuery } from '@tanstack/react-query';

interface BundleInfo {
  name: string;
  type: string;
  package_count: number;
  sections: string[];
}

interface PackageDefinition {
  package: string;
  type: string;
  repo_name?: string;
  url?: string;
  tag?: string;
  version?: string;
}

const API_BASE = '/api/v1/catalog-editor';

export const useAvailableBundles = (
  arch: string,
  osFamily: string,
  version: string
) => {
  return useQuery({
    queryKey: ['bundles', arch, osFamily, version],
    queryFn: async (): Promise<BundleInfo[]> => {
      const res = await fetch(
        `${API_BASE}/os-packages/bundles?arch=${arch}&os_family=${osFamily}&version=${version}`
      );
      if (!res.ok) throw new Error('Failed to fetch bundles');
      const data = await res.json();
      return data.bundles;
    },
    enabled: !!arch && !!osFamily && !!version,
  });
};

export const useBundlePackages = (
  arch: string,
  osFamily: string,
  version: string,
  bundleName: string
) => {
  return useQuery({
    queryKey: ['bundle-packages', arch, osFamily, version, bundleName],
    queryFn: async (): Promise<Record<string, PackageDefinition[]>> => {
      const res = await fetch(
        `${API_BASE}/os-packages/bundle/${encodeURIComponent(bundleName)}?arch=${arch}&os_family=${osFamily}&version=${version}`
      );
      if (!res.ok) throw new Error('Failed to fetch bundle packages');
      const data = await res.json();
      return data.packages;
    },
    enabled: !!arch && !!osFamily && !!version && !!bundleName,
  });
};

