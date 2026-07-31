// Copyright 2026 Dell Inc. or its subsidiaries. All Rights Reserved.
//
// Licensed under the Apache License, Version 2.0 (the "License");
// you may not use this file except in compliance with the License.
// You may obtain a copy of the License at
//
//     http://www.apache.org/licenses/LICENSE-2.0
//
// Unless required by applicable law or agreed to in writing, software
// distributed under the License is distributed on an "AS IS" BASIS,
// WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
// See the License for the specific language governing permissions and
// limitations under the License.
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
