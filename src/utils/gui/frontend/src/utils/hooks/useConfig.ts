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
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { api } from '../api'

export const useGenerateAll = () => {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: api.config.generateAll,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['job-status'] })
    },
  })
}

export const useJobStatus = (jobId: string) => {
  return useQuery({
    queryKey: ['job-status', jobId],
    queryFn: () => api.config.getJobStatus(jobId),
    enabled: !!jobId,
    refetchInterval: (query: any) => {
      const data = query.state.data
      // Standard React Query pattern: poll while in progress, stop when complete or failed
      if (data?.status === 'in_progress') return 50  // Very fast polling for quick jobs
      // Keep polling briefly if completed but no result yet (race condition protection)
      if (data?.status === 'completed' && !data?.result) return 50
      if (data?.status === 'failed' && !data?.error) return 50
      return false
    },
  })
}

