import { useQuery } from '@tanstack/react-query';

interface BundleInfo {
  name: string;
  type: string;
  package_count: number;
  sections: string[];
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

