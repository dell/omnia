import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import type { AdapterPolicyFormData } from '../schemas/adapterPolicy';

export const useAdapterPolicy = () =>
  useQuery({
    queryKey: ['adapter-policy'],
    queryFn: async () => {
      const res = await fetch('/api/v1/adapter-policy');
      if (!res.ok) throw new Error('Failed to load adapter policy');
      const data = await res.json();
      return data;
    },
  });

export const useSaveAdapterPolicy = () => {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async (policy: AdapterPolicyFormData) => {
      const res = await fetch('/api/v1/adapter-policy', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(policy),
      });
      if (!res.ok) throw new Error('Failed to save adapter policy');
      return res.json();
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['adapter-policy'] });
    },
  });
};

export const useDeleteAdapterPolicy = () => {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async () => {
      const res = await fetch('/api/v1/adapter-policy', { method: 'DELETE' });
      if (!res.ok) throw new Error('Failed to delete custom adapter policy');
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['adapter-policy'] });
    },
  });
};
