import { useQuery } from '@tanstack/react-query';

const API_BASE = '/api/v1/catalog-editor';

export const useAvailableRoles = () => {
  return useQuery({
    queryKey: ['roles'],
    queryFn: async (): Promise<string[]> => {
      const res = await fetch(`${API_BASE}/roles`);
      if (!res.ok) throw new Error('Failed to fetch roles');
      const data = await res.json();
      return data.roles;
    },
  });
};

export const useRolePackages = (
  role: string,
  arch: string,
  osFamily: string,
  version: string
) => {
  return useQuery({
    queryKey: ['role-packages', role, arch, osFamily, version],
    queryFn: async (): Promise<Record<string, any[]>> => {
      const res = await fetch(
        `${API_BASE}/roles/${encodeURIComponent(role)}/packages?arch=${arch}&os_family=${osFamily}&version=${version}`
      );
      if (!res.ok) throw new Error('Failed to fetch role packages');
      const data = await res.json();
      return data.packages;
    },
    enabled: !!role && !!arch && !!osFamily && !!version,
  });
};
